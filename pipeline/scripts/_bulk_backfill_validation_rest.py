"""Bulk backfill validation_log via Supabase REST.

Loads prices and regime_calls in memory, computes T+5/T+20 metrics, and
upserts validation_log rows in batches. Idempotent via upsert on
(call_date, pair).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, cast

from src.db import writer
from src.validation.calculator import compute_horizon_metrics, horizon_metrics_to_payload
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)


def _paginate_table(table: str, select: str, *, order_by: str = "id") -> list[dict[str, Any]]:
    """Fetch all rows from a Supabase table, paginating past the 1000-row limit."""
    client = writer._client()
    rows: list[dict[str, Any]] = []
    start = 0
    page_size = 1000
    while True:
        res = (
            client.table(table)
            .select(select)
            .order(order_by)
            .range(start, start + page_size - 1)
            .execute()
        )
        page = cast(list[dict[str, Any]], res.data or [])
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def _load_prices() -> dict[str, dict[date, float]]:
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for pair in ("EURUSD", "USDJPY", "USDINR"):
        rows = _paginate_table(
            "historical_prices",
            "date,close",
            order_by="date",
        )
        for row in rows:
            d = row["date"]
            if isinstance(d, str):
                d = date.fromisoformat(d)
            out[pair][d] = float(row["close"])
    return dict(out)


def _get_spot(prices: dict[date, float], target: date) -> float | None:
    if target in prices:
        return prices[target]
    # Forward-fill (next available)
    for offset in range(1, 10):
        d = target + timedelta(days=offset)
        if d in prices:
            return prices[d]
    # Backward-fill (previous available)
    for offset in range(1, 10):
        d = target - timedelta(days=offset)
        if d in prices:
            return prices[d]
    return None


def _build_rows(
    calls: list[dict[str, Any]],
    prices: dict[str, dict[date, float]],
    as_of: date,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in calls:
        pair = str(call.get("pair"))
        call_date_raw = call.get("date")
        if isinstance(call_date_raw, str):
            call_date = date.fromisoformat(call_date_raw[:10])
        elif isinstance(call_date_raw, date):
            call_date = call_date_raw
        else:
            continue

        pair_prices = prices.get(pair, {})
        s0 = _get_spot(pair_prices, call_date)
        if s0 is None:
            continue

        predicted = str(call.get("predicted_direction") or call.get("rate_signal") or "")
        confidence = float(call.get("confidence") or 0.0)

        t5_date = add_trading_days(call_date, 5)
        t20_date = add_trading_days(call_date, 20)

        row: dict[str, Any] = {
            "call_date": call_date.isoformat(),
            "date": call_date.isoformat(),
            "pair": pair,
            "predicted_direction": predicted,
            "predicted_regime": call.get("regime"),
            "confidence": confidence,
            "call_id": call.get("id"),
            "validation_date": as_of.isoformat(),
            "is_superseded": False,
            "strategy_version": call.get("strategy_version") or "v2",
            "data_source": call.get("data_source") or "live",
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


def _existing_non_superseded_keys() -> set[tuple[str, str]]:
    client = writer._client()
    keys: set[tuple[str, str]] = set()
    start = 0
    page_size = 1000
    while True:
        res = (
            client.table("validation_log")
            .select("call_date,pair,is_superseded")
            .or_("is_superseded.is.null,is_superseded.eq.false")
            .order("id")
            .range(start, start + page_size - 1)
            .execute()
        )
        page = cast(list[dict[str, Any]], res.data or [])
        if not page:
            break
        for row in page:
            keys.add((row["call_date"], row["pair"]))
        if len(page) < page_size:
            break
        start += page_size
    return keys


def _bulk_insert(rows: list[dict[str, Any]], batch_size: int = 500) -> None:
    if not rows:
        return
    client = writer._client()
    existing = _existing_non_superseded_keys()
    if existing:
        before = len(rows)
        rows = [
            r for r in rows if (r.get("call_date"), r.get("pair")) not in existing
        ]
        logger.info("Skipping %d rows already validated", before - len(rows))
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        # Retry loop strips any columns not present in the live schema.
        while True:
            try:
                client.table("validation_log").insert(batch).execute()
                break
            except Exception as exc:
                msg = str(getattr(exc, "message", "")) or str(exc)
                if "Could not find the '" in msg and "column of 'validation_log'" in msg:
                    col = msg.split("Could not find the '")[1].split("'")[0]
                    logger.warning("Stripping unknown column '%s' from batch", col)
                    for row in batch:
                        row.pop(col, None)
                    continue
                raise
        logger.info("Inserted validation batch %d-%d", i, i + len(batch) - 1)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    as_of = date.today()
    logger.info("Loading prices...")
    prices = _load_prices()
    logger.info("Loading regime_calls...")
    calls = _paginate_table(
        "regime_calls",
        "id,date,pair,regime,predicted_direction,rate_signal,confidence,strategy_version,data_source",
        order_by="id",
    )
    logger.info("Loaded %d calls", len(calls))
    rows = _build_rows(calls, prices, as_of)
    logger.info("Built %d validation rows", len(rows))
    _bulk_insert(rows)
    logger.info("Done")


if __name__ == "__main__":
    main()
