"""Round 3 Phase 2 — Aggregate validation statistics.

Computes per-pair and overall track-record metrics from ``validation_log``:
- Brier score (mean, skill vs random)
- Win rate (directional accuracy)
- Sharpe-like ratio from log-return bps
- Calibration buckets
- Max drawdown

All metrics are append-only to ``validation_stats`` for institutional audit.
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from scipy.stats import beta as beta_dist

from src.db import writer

logger = logging.getLogger(__name__)

_RANDOM_BRIER_BASELINE = 0.25


@dataclass(frozen=True, slots=True)
class HorizonStats:
    """Statistics for a single horizon (T+5 or T+20)."""

    horizon: str
    total_calls: int
    directional_calls: int
    wins: int
    win_rate: float | None
    mean_brier: float | None
    brier_skill: float | None
    mean_log_return_bps: float | None
    return_std_bps: float | None
    sharpe_like: float | None
    max_drawdown_bps: float | None
    calibration_json: str
    rolling_90d_accuracy: float | None
    win_rate_ci_lower: float | None
    win_rate_ci_upper: float | None
    net_win_rate: float | None
    net_win_rate_ci_lower: float | None
    net_win_rate_ci_upper: float | None
    cost_bps: float | None


@dataclass(frozen=True, slots=True)
class AggregateStats:
    """Full aggregate payload for one pair (or ``ALL`` for overall)."""

    pair: str
    as_of_date: date
    t5: HorizonStats
    t20: HorizonStats


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
    """Bucket predictions by confidence decile and report observed accuracy."""
    if not confidences or len(confidences) != len(corrects):
        return {}

    pairs = sorted(zip(confidences, corrects), key=lambda x: x[0])
    bucket_size = max(1, len(pairs) // n_buckets)
    buckets: list[dict[str, Any]] = []
    for i in range(0, len(pairs), bucket_size):
        chunk = pairs[i : i + bucket_size]
        avg_conf = _mean([c for c, _ in chunk])
        obs_acc = sum(1 for _, y in chunk if y) / len(chunk) if chunk else None
        buckets.append(
            {
                "bucket_index": i // bucket_size,
                "avg_confidence": round(avg_conf, 4) if avg_conf is not None else None,
                "observed_accuracy": round(obs_acc, 4) if obs_acc is not None else None,
                "n": len(chunk),
            }
        )
    return {"buckets": buckets}


def _clopper_pearson_ci(
    wins: int, n: int, alpha: float = 0.05
) -> tuple[float | None, float | None]:
    """Exact confidence interval for binomial proportion."""
    if n == 0:
        return None, None
    lower = float(beta_dist.ppf(alpha / 2, wins, n - wins + 1)) if wins > 0 else 0.0
    upper = float(beta_dist.ppf(1 - alpha / 2, wins + 1, n - wins)) if wins < n else 1.0
    return (lower, upper)


def _compute_horizon(
    rows: list[dict[str, Any]],
    horizon: str,
    brier_key: str,
    correct_key: str,
    return_key: str,
    as_of_date: date,
) -> HorizonStats:
    total = len(rows)
    directional: list[dict[str, Any]] = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "").strip().upper()
        if pred != "NEUTRAL":
            directional.append(r)

    directional_calls = len(directional)
    wins = sum(1 for r in directional if r.get(correct_key) is True)
    win_rate = wins / directional_calls if directional_calls > 0 else None

    # Gross CI
    win_rate_ci_lower, win_rate_ci_upper = _clopper_pearson_ci(wins, directional_calls)

    # Net wins
    net_correct_key = correct_key.replace("correct", "correct_net")
    net_wins = sum(1 for r in directional if r.get(net_correct_key) is True)
    net_win_rate = net_wins / directional_calls if directional_calls > 0 else None
    net_ci_lower, net_ci_upper = _clopper_pearson_ci(net_wins, directional_calls)

    # Average cost bps
    cost_key = correct_key.replace("correct", "cost_bps")
    costs = [float(r[cost_key]) for r in directional if r.get(cost_key) is not None]
    avg_cost = _mean(costs) if costs else None

    briers = [
        float(r[brier_key])
        for r in directional
        if r.get(brier_key) is not None
    ]
    mean_brier = _mean(briers) if briers else None
    brier_skill = (
        (_RANDOM_BRIER_BASELINE - mean_brier) / _RANDOM_BRIER_BASELINE
        if mean_brier is not None
        else None
    )

    returns = [
        float(r[return_key])
        for r in directional
        if r.get(return_key) is not None
    ]
    mean_ret = _mean(returns) if returns else None
    std_ret = _std(returns) if returns else None
    sharpe = _sharpe_like(returns) if returns else None
    mdd = _max_drawdown_bps(returns) if returns else None

    confidences = [
        float(r.get("confidence") or 0.0)
        for r in directional
        if r.get("confidence") is not None
    ]
    corrects = [bool(r.get(correct_key)) for r in directional if r.get(correct_key) is not None]
    calib = _calibration_buckets(confidences, corrects)

    # v1.0: rolling 90-day accuracy (last 90 calendar days of directional calls)
    from datetime import timedelta
    cutoff_90d = as_of_date - timedelta(days=90)

    def _parse_date(raw: Any) -> date | None:
        if isinstance(raw, date):
            return raw
        if raw:
            try:
                return date.fromisoformat(str(raw)[:10])
            except Exception:
                return None
        return None

    recent_directional = [
        r for r in directional
        if (d := _parse_date(r.get("date") or r.get("call_date"))) is not None and d >= cutoff_90d
    ]
    recent_wins = sum(1 for r in recent_directional if r.get(correct_key) is True)
    rolling_90d_acc = (
        recent_wins / len(recent_directional)
        if recent_directional
        else None
    )

    return HorizonStats(
        horizon=horizon,
        total_calls=total,
        directional_calls=directional_calls,
        wins=wins,
        win_rate=round(win_rate, 6) if win_rate is not None else None,
        win_rate_ci_lower=round(win_rate_ci_lower, 6) if win_rate_ci_lower is not None else None,
        win_rate_ci_upper=round(win_rate_ci_upper, 6) if win_rate_ci_upper is not None else None,
        mean_brier=round(mean_brier, 6) if mean_brier is not None else None,
        brier_skill=round(brier_skill, 6) if brier_skill is not None else None,
        mean_log_return_bps=round(mean_ret, 6) if mean_ret is not None else None,
        return_std_bps=round(std_ret, 6) if std_ret is not None else None,
        sharpe_like=round(sharpe, 6) if sharpe is not None else None,
        max_drawdown_bps=round(mdd, 6) if mdd is not None else None,
        calibration_json=json.dumps(calib),
        rolling_90d_accuracy=round(rolling_90d_acc, 6) if rolling_90d_acc is not None else None,
        net_win_rate=round(net_win_rate, 6) if net_win_rate is not None else None,
        net_win_rate_ci_lower=round(net_ci_lower, 6) if net_ci_lower is not None else None,
        net_win_rate_ci_upper=round(net_ci_upper, 6) if net_ci_upper is not None else None,
        cost_bps=round(avg_cost, 6) if avg_cost is not None else None,
    )


def compute_aggregate_stats(
    pair_filter: str | None = None,
    as_of_date: date | None = None,
    lookback_days: int | None = None,
) -> list[AggregateStats]:
    """Compute aggregate stats for ``pair_filter`` (or all pairs) as of today.

    If ``lookback_days`` is set, only consider calls within that window;
    otherwise use the full history.
    """
    if as_of_date is None:
        as_of_date = date.today()

    rows = writer.get_validation_log_for_stats(pair_filter, lookback_days)
    if not rows:
        logger.warning("No validation rows found for stats computation")
        return []

    # Group by pair
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        p = str(r.get("pair") or "UNKNOWN")
        by_pair[p].append(r)

    results: list[AggregateStats] = []
    pairs_to_process = [pair_filter] if pair_filter else sorted(by_pair.keys())

    for pair in pairs_to_process:
        if pair is None:
            continue
        prs = by_pair.get(pair, [])
        if not prs:
            continue
        t5 = _compute_horizon(
            prs, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps", as_of_date
        )
        t20 = _compute_horizon(
            prs, "T+20", "brier_score_t20", "correct_t20", "log_return_t20_bps", as_of_date
        )
        results.append(AggregateStats(pair=pair, as_of_date=as_of_date, t5=t5, t20=t20))

    # Overall "ALL" aggregate
    if not pair_filter and len(by_pair) > 1:
        all_rows: list[dict[str, Any]] = []
        for prs in by_pair.values():
            all_rows.extend(prs)
        t5_all = _compute_horizon(
            all_rows, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps", as_of_date
        )
        t20_all = _compute_horizon(
            all_rows, "T+20", "brier_score_t20", "correct_t20", "log_return_t20_bps", as_of_date
        )
        results.append(AggregateStats(pair="ALL", as_of_date=as_of_date, t5=t5_all, t20=t20_all))

    return results


def _stats_to_payload(stats: AggregateStats) -> dict[str, Any]:
    """Serialize ``AggregateStats`` to a Supabase row dict."""
    base: dict[str, Any] = {
        "as_of_date": stats.as_of_date.isoformat(),
        "pair": stats.pair,
        "computed_at": date.today().isoformat(),
    }
    for horizon in ("t5", "t20"):
        h: HorizonStats = getattr(stats, horizon)
        prefix = f"{horizon}_"
        base[f"{prefix}total_calls"] = h.total_calls
        base[f"{prefix}directional_calls"] = h.directional_calls
        base[f"{prefix}wins"] = h.wins
        base[f"{prefix}win_rate"] = h.win_rate
        base[f"{prefix}mean_brier"] = h.mean_brier
        base[f"{prefix}brier_skill"] = h.brier_skill
        base[f"{prefix}mean_log_return_bps"] = h.mean_log_return_bps
        base[f"{prefix}return_std_bps"] = h.return_std_bps
        base[f"{prefix}sharpe_like"] = h.sharpe_like
        base[f"{prefix}max_drawdown_bps"] = h.max_drawdown_bps
        base[f"{prefix}calibration_json"] = h.calibration_json
        base[f"{prefix}rolling_90d_accuracy"] = h.rolling_90d_accuracy
        base[f"{prefix}win_rate_ci_lower"] = h.win_rate_ci_lower
        base[f"{prefix}win_rate_ci_upper"] = h.win_rate_ci_upper
        base[f"{prefix}net_win_rate"] = h.net_win_rate
        base[f"{prefix}net_win_rate_ci_lower"] = h.net_win_rate_ci_lower
        base[f"{prefix}net_win_rate_ci_upper"] = h.net_win_rate_ci_upper
        base[f"{prefix}cost_bps"] = h.cost_bps
    return base


def run_aggregate_stats(
    pair_filter: str | None = None,
    as_of_date: date | None = None,
    lookback_days: int | None = None,
) -> list[AggregateStats]:
    """Compute and persist aggregate stats to ``validation_stats``."""
    stats_list = compute_aggregate_stats(pair_filter, as_of_date, lookback_days)
    for stats in stats_list:
        payload = _stats_to_payload(stats)
        writer.write_validation_stats(payload)
        logger.info(
            "Validation stats persisted: %s T+5 win_rate=%s brier=%s",
            stats.pair,
            stats.t5.win_rate,
            stats.t5.mean_brier,
        )
    return stats_list


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_aggregate_stats()
