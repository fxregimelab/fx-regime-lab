"""Batch validation backfill for all historical regime_calls.

Loads prices into memory, computes T+5/T+20 metrics in bulk,
and inserts via pg8000 direct SQL for speed.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.validation.calculator import compute_horizon_metrics, horizon_metrics_to_payload
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)


def _pg_conn() -> Any:
    import ssl

    import pg8000.native
    ctx = ssl._create_unverified_context()
    import os
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError("SUPABASE_DB_PASSWORD must be set in the environment.")
    return pg8000.native.Connection(
        host=host,
        database="postgres",
        user="postgres",
        password=password,
        ssl_context=ctx,
    )


def _load_prices() -> dict[str, dict[date, float]]:
    conn = _pg_conn()
    result = conn.run(
        "SELECT pair, date, close FROM historical_prices ORDER BY pair, date"
    )
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for row in result:
        pair = row[0]
        d = row[1] if isinstance(row[1], date) else date.fromisoformat(str(row[1])[:10])
        out[pair][d] = float(row[2])
    conn.close()
    logger.info("Loaded %d price series", len(out))
    return dict(out)


def _load_regime_calls() -> list[dict[str, Any]]:
    conn = _pg_conn()
    result = conn.run(
        "SELECT id, date, pair, regime, predicted_direction, confidence, "
        "strategy_version, data_source "
        "FROM regime_calls ORDER BY date"
    )
    out: list[dict[str, Any]] = []
    for row in result:
        d = row[1] if isinstance(row[1], date) else date.fromisoformat(str(row[1])[:10])
        out.append({
            "id": int(row[0]),
            "date": d,
            "pair": row[2],
            "regime": row[3],
            "predicted_direction": row[4] or "NEUTRAL",
            "confidence": float(row[5] or 0.0),
            "strategy_version": row[6] or "v2",
            "data_source": row[7] or "live",
        })
    conn.close()
    logger.info("Loaded %d regime_calls", len(out))
    return out


def _load_validated_call_keys() -> set[tuple[int | None, date, str]]:
    """Load (call_id, date, pair) keys that already have a T+5 validation row."""
    conn = _pg_conn()
    try:
        result = conn.run(
            "SELECT call_id, date, pair FROM validation_log "
            "WHERE brier_score_t5 IS NOT NULL"
        )
    except Exception:
        # Legacy schema without call_id or brier_score_t5: disable idempotency.
        conn.close()
        return set()
    out: set[tuple[int | None, date, str]] = set()
    for row in result:
        call_id = int(row[0]) if row[0] is not None else None
        d = row[1] if isinstance(row[1], date) else date.fromisoformat(str(row[1])[:10])
        out.add((call_id, d, str(row[2])))
    conn.close()
    logger.info("Loaded %d existing validation keys", len(out))
    return out


def _get_spot(prices: dict[date, float], target: date) -> float | None:
    """Exact match first, then forward-fill (next available), then backward-fill."""
    if target in prices:
        return prices[target]
    # Forward-fill: next available date
    for offset in range(1, 10):
        d = target + timedelta(days=offset)
        if d in prices:
            return prices[d]
    # Backward-fill: previous available date
    for offset in range(1, 10):
        d = target - timedelta(days=offset)
        if d in prices:
            return prices[d]
    return None


def _build_validation_rows(
    calls: list[dict[str, Any]],
    prices: dict[str, dict[date, float]],
    as_of: date,
    validated_keys: set[tuple[int | None, date, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in calls:
        pair = call["pair"]
        call_date = call["date"]
        call_id = call["id"]
        if (call_id, call_date, pair) in validated_keys:
            continue

        pair_prices = prices.get(pair, {})

        s0 = _get_spot(pair_prices, call_date)
        if s0 is None:
            continue

        predicted = str(call.get("predicted_direction") or "NEUTRAL")
        confidence = float(call.get("confidence") or 0.0)

        t5_date = add_trading_days(call_date, 5)
        t20_date = add_trading_days(call_date, 20)

        row: dict[str, Any] = {
            "call_date": call_date,
            "date": call_date,
            "pair": pair,
            "predicted_direction": predicted,
            "predicted_regime": call.get("regime"),
            "confidence": confidence,
            "call_id": call["id"],
            "validation_date": as_of,
            "created_at": datetime.now(UTC).isoformat(),
            "is_superseded": False,
            "strategy_version": call.get("strategy_version", "v2"),
            "data_source": call.get("data_source", "live"),
        }

        has_any = False

        if as_of >= t5_date:
            s5 = _get_spot(pair_prices, t5_date)
            metrics_t5 = compute_horizon_metrics(s0, s5, predicted, confidence, pair)
            if metrics_t5 is not None:
                row.update(horizon_metrics_to_payload(metrics_t5, "t5"))
                has_any = True

        if as_of >= t20_date:
            s20 = _get_spot(pair_prices, t20_date)
            metrics_t20 = compute_horizon_metrics(s0, s20, predicted, confidence, pair)
            if metrics_t20 is not None:
                row.update(horizon_metrics_to_payload(metrics_t20, "t20"))
                has_any = True

        if has_any:
            rows.append(row)

    return rows


def _batch_insert(rows: list[dict[str, Any]], batch_size: int = 1000) -> None:
    if not rows:
        return

    conn = _pg_conn()

    # Get column list from first row (all rows have same keys)
    columns = list(rows[0].keys())
    col_str = ", ".join(columns)

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        placeholders = []
        params: dict[str, Any] = {}
        for bidx, row in enumerate(batch):
            prefix = f"p{i}_{bidx}_"
            row_placeholders = []
            for cidx, col in enumerate(columns):
                param_key = f"{prefix}c{cidx}"
                row_placeholders.append(f":{param_key}")
                val = row.get(col)
                # Handle booleans for pg8000
                if isinstance(val, bool):
                    val = str(val).lower()
                params[param_key] = val
            placeholders.append(f"({', '.join(row_placeholders)})")

        sql = f"INSERT INTO validation_log ({col_str}) VALUES {', '.join(placeholders)}"
        conn.run(sql, **params)
        logger.info("Inserted batch %d-%d", i, i + len(batch) - 1)

    conn.close()


def run_batch_backfill(
    *,
    dry_run: bool = False,
    as_of: date | None = None,
) -> tuple[int, int]:
    as_of = as_of or date.today()
    prices = _load_prices()
    calls = _load_regime_calls()
    validated_keys = _load_validated_call_keys()
    rows = _build_validation_rows(calls, prices, as_of, validated_keys)

    logger.info("Built %d validation rows from %d calls", len(rows), len(calls))

    if dry_run:
        logger.info("[DRY-RUN] Would insert %d rows", len(rows))
        return len(rows), 0

    _batch_insert(rows)
    logger.info("Batch backfill complete: %d rows inserted", len(rows))
    return len(rows), len(calls) - len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    args = parser.parse_args()

    processed, skipped = run_batch_backfill(dry_run=args.dry_run, as_of=args.as_of)
    logger.info("Done: %d processed, %d skipped", processed, skipped)


if __name__ == "__main__":
    main()
