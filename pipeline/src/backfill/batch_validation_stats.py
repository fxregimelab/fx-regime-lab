"""Batch compute validation_stats directly via SQL to bypass REST API limits."""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


def _pg_conn(max_retries: int = 5) -> Any:
    import os
    import ssl
    import time

    import pg8000.native
    ctx = ssl._create_unverified_context()
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError("SUPABASE_DB_PASSWORD must be set in the environment.")
    last_err: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return pg8000.native.Connection(
                host=host,
                database="postgres",
                user="postgres",
                password=password,
                ssl_context=ctx,
                timeout=30,
            )
        except Exception as e:
            last_err = e
            logger.warning("DB connection attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            time.sleep(min(2 ** attempt, 30))
    if last_err is None:
        raise RuntimeError("Failed to connect after retries")
    raise last_err


def _mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    return math.fsum(xs) / len(xs)


def _std(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = math.fsum(xs) / len(xs)
    var = math.fsum((x - m) ** 2 for x in xs) / len(xs)
    return float(math.sqrt(var))


def _sharpe_like(returns: list[float]) -> float | None:
    mu = _mean(returns)
    sigma = _std(returns)
    if mu is None or sigma is None or sigma == 0:
        return None
    return mu / sigma


def _max_drawdown_bps(returns: list[float]) -> float | None:
    if not returns:
        return None
    cum = 0.0
    peak = 0.0
    dd = 0.0
    for r in returns:
        cum += r
        if cum > peak:
            peak = cum
        draw = peak - cum
        if draw > dd:
            dd = draw
    return dd


def _calibration_buckets(
    confidences: list[float],
    corrects: list[bool],
    n_buckets: int = 5,
) -> dict[str, Any]:
    if not confidences or len(confidences) != len(corrects):
        return {}
    pairs = sorted(zip(confidences, corrects), key=lambda x: x[0])
    bucket_size = max(1, len(pairs) // n_buckets)
    buckets: list[dict[str, Any]] = []
    for i in range(0, len(pairs), bucket_size):
        chunk = pairs[i : i + bucket_size]
        avg_conf = _mean([c for c, _ in chunk])
        obs_acc = sum(1 for _, y in chunk if y) / len(chunk) if chunk else None
        buckets.append({
            "bucket_index": i // bucket_size,
            "avg_confidence": round(avg_conf, 4) if avg_conf is not None else None,
            "observed_accuracy": round(obs_acc, 4) if obs_acc is not None else None,
            "n": len(chunk),
        })
    return {"buckets": buckets}


def _compute_horizon(
    rows: list[dict[str, Any]],
    horizon: str,
    brier_key: str,
    correct_key: str,
    return_key: str,
) -> dict[str, Any]:
    total = len(rows)
    directional = [
        r for r in rows
        if str(r.get("predicted_direction") or "").strip().upper() != "NEUTRAL"
    ]
    directional_calls = len(directional)
    wins = sum(1 for r in directional if r.get(correct_key) is True)
    win_rate = wins / directional_calls if directional_calls > 0 else None

    briers = [float(r[brier_key]) for r in directional if r.get(brier_key) is not None]
    mean_brier = _mean(briers) if briers else None
    brier_skill = ((0.25 - mean_brier) / 0.25) if mean_brier is not None else None

    returns = [float(r[return_key]) for r in directional if r.get(return_key) is not None]
    mean_ret = _mean(returns) if returns else None
    std_ret = _std(returns) if returns else None
    sharpe = _sharpe_like(returns) if returns else None
    mdd = _max_drawdown_bps(returns) if returns else None

    confidences = [
        float(r.get("confidence") or 0.0) for r in directional
        if r.get("confidence") is not None
    ]
    corrects = [bool(r.get(correct_key)) for r in directional if r.get(correct_key) is not None]
    calib = _calibration_buckets(confidences, corrects)

    return {
        "horizon": horizon,
        "total_calls": total,
        "directional_calls": directional_calls,
        "wins": wins,
        "win_rate": round(win_rate, 6) if win_rate is not None else None,
        "mean_brier": round(mean_brier, 6) if mean_brier is not None else None,
        "brier_skill": round(brier_skill, 6) if brier_skill is not None else None,
        "mean_log_return_bps": round(mean_ret, 6) if mean_ret is not None else None,
        "return_std_bps": round(std_ret, 6) if std_ret is not None else None,
        "sharpe_like": round(sharpe, 6) if sharpe is not None else None,
        "max_drawdown_bps": round(mdd, 6) if mdd is not None else None,
        "calibration_json": json.dumps(calib),
    }


def _load_validation_rows() -> list[dict[str, Any]]:
    conn = _pg_conn()
    result = conn.run(
        "SELECT pair, predicted_direction, confidence, date, "
        "actual_direction_t5, log_return_t5_bps, correct_t5, brier_score_t5, "
        "actual_direction_t20, log_return_t20_bps, correct_t20, brier_score_t20 "
        "FROM validation_log WHERE is_superseded = FALSE"
    )
    rows: list[dict[str, Any]] = []
    for r in result:
        rows.append({
            "pair": r[0],
            "predicted_direction": r[1],
            "confidence": float(r[2] or 0.0),
            "date": r[3],
            "actual_direction_t5": r[4],
            "log_return_t5_bps": r[5],
            "correct_t5": r[6],
            "brier_score_t5": r[7],
            "actual_direction_t20": r[8],
            "log_return_t20_bps": r[9],
            "correct_t20": r[10],
            "brier_score_t20": r[11],
            "strategy_version": "v2",
        })
    conn.close()
    logger.info("Loaded %d validation rows", len(rows))
    return rows


def _stats_to_payload(
    pair: str,
    strategy_version: str,
    as_of: date,
    t5: dict[str, Any],
    t20: dict[str, Any],
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "as_of_date": as_of.isoformat(),
        "pair": pair,
        "computed_at": date.today().isoformat(),
    }
    for horizon, h in (("t5", t5), ("t20", t20)):
        prefix = f"{horizon}_"
        base[f"{prefix}total_calls"] = h["total_calls"]
        base[f"{prefix}directional_calls"] = h["directional_calls"]
        base[f"{prefix}wins"] = h["wins"]
        base[f"{prefix}win_rate"] = h["win_rate"]
        base[f"{prefix}mean_brier"] = h["mean_brier"]
        base[f"{prefix}brier_skill"] = h["brier_skill"]
        base[f"{prefix}mean_log_return_bps"] = h["mean_log_return_bps"]
        base[f"{prefix}return_std_bps"] = h["return_std_bps"]
        base[f"{prefix}sharpe_like"] = h["sharpe_like"]
        base[f"{prefix}max_drawdown_bps"] = h["max_drawdown_bps"]
        base[f"{prefix}calibration_json"] = h["calibration_json"]
    return base


def _insert_stats(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    conn = _pg_conn()
    conn.run("ALTER TABLE validation_stats DISABLE TRIGGER ALL")
    conn.run("DELETE FROM validation_stats")
    columns = list(rows[0].keys())
    col_str = ", ".join(columns)
    placeholders = []
    params: dict[str, Any] = {}
    for bidx, row in enumerate(rows):
        prefix = f"p{bidx}_"
        row_placeholders = []
        for cidx, col in enumerate(columns):
            param_key = f"{prefix}c{cidx}"
            row_placeholders.append(f":{param_key}")
            val = row.get(col)
            if isinstance(val, bool):
                val = str(val).lower()
            params[param_key] = val
        placeholders.append(f"({', '.join(row_placeholders)})")

    sql = f"INSERT INTO validation_stats ({col_str}) VALUES {', '.join(placeholders)}"
    conn.run(sql, **params)
    conn.run("ALTER TABLE validation_stats ENABLE TRIGGER ALL")
    conn.close()
    logger.info("Inserted %d validation_stats rows", len(rows))


def run_batch_stats() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rows = _load_validation_rows()
    as_of = date.today()

    by_pair_version: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (str(r.get("pair") or "UNKNOWN"), str(r.get("strategy_version") or "v2"))
        by_pair_version[key].append(r)

    stats_rows: list[dict[str, Any]] = []
    for (pair, version) in sorted(by_pair_version.keys()):
        prs = by_pair_version[(pair, version)]
        t5 = _compute_horizon(prs, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps")
        t20 = _compute_horizon(prs, "T+20", "brier_score_t20", "correct_t20", "log_return_t20_bps")
        stats_rows.append(_stats_to_payload(pair, version, as_of, t5, t20))
        logger.info(
            "%s: T+5 win_rate=%s brier=%s | T+20 win_rate=%s brier=%s",
            pair, t5["win_rate"], t5["mean_brier"], t20["win_rate"], t20["mean_brier"]
        )

    # Overall ALL
    all_rows = []
    for prs in by_pair_version.values():
        all_rows.extend(prs)
    t5_all = _compute_horizon(
        all_rows, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps"
    )
    t20_all = _compute_horizon(
        all_rows, "T+20", "brier_score_t20", "correct_t20", "log_return_t20_bps"
    )
    stats_rows.append(_stats_to_payload("ALL", "v2", as_of, t5_all, t20_all))
    logger.info(
        "ALL: T+5 win_rate=%s brier=%s | T+20 win_rate=%s brier=%s",
        t5_all["win_rate"], t5_all["mean_brier"], t20_all["win_rate"], t20_all["mean_brier"]
    )

    _insert_stats(stats_rows)


if __name__ == "__main__":
    run_batch_stats()
