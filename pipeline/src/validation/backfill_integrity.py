"""Backfill integrity validation for historical price series."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.db import writer
from src.fx_types import SpotBar


def validate_backfill_gaps(
    bars: list[SpotBar],
    *,
    max_gap_days: int = 5,
) -> tuple[bool, list[tuple[date, date]]]:
    """Return (is_valid, list_of_gaps) where each gap is (missing_start, missing_end).

    A gap is defined as > max_gap_days calendar days between consecutive bars.
    """
    if len(bars) < 2:
        return True, []

    sorted_bars = sorted(bars, key=lambda b: b.date)
    gaps: list[tuple[date, date]] = []

    for prev_bar, next_bar in zip(sorted_bars[:-1], sorted_bars[1:]):
        delta_days = (next_bar.date - prev_bar.date).days
        if delta_days > max_gap_days:
            missing_start = prev_bar.date + timedelta(days=1)
            missing_end = next_bar.date - timedelta(days=1)
            gaps.append((missing_start, missing_end))

    is_valid = len(gaps) == 0
    return is_valid, gaps


def check_historical_prices_integrity(
    pair: str,
    max_gap_days: int = 5,
) -> dict[str, Any]:
    """Fetch historical prices for *pair* and check for calendar gaps.

    Returns a diagnostic dict with total row count, date range, any gaps,
    and an overall ``is_valid`` flag.
    """
    rows = writer.get_historical_prices(pair)

    bars: list[SpotBar] = []
    for row in rows:
        row_date = row.get("date")
        if row_date is None:
            continue
        if isinstance(row_date, str):
            row_date = date.fromisoformat(row_date)
        bars.append(
            SpotBar(
                date=row_date,
                pair=pair,
                open=float(row.get("open", 0.0)),
                high=float(row.get("high", 0.0)),
                low=float(row.get("low", 0.0)),
                close=float(row.get("close", 0.0)),
                volume=float(row.get("volume", 0.0)),
            )
        )

    is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=max_gap_days)

    date_range: list[str | None] = [None, None]
    if bars:
        sorted_bars = sorted(bars, key=lambda b: b.date)
        date_range = [sorted_bars[0].date.isoformat(), sorted_bars[-1].date.isoformat()]

    gap_list = [
        {"missing_start": gap_start.isoformat(), "missing_end": gap_end.isoformat()}
        for gap_start, gap_end in gaps
    ]

    return {
        "pair": pair,
        "total_rows": len(bars),
        "date_range": date_range,
        "gaps": gap_list,
        "is_valid": is_valid,
    }


def check_historical_price_gaps(
    *,
    pair: str,
    max_gap_days: int = 5,
    lookback_years: int = 5,
) -> list[dict[str, Any]]:
    """Query historical prices for *pair* and return calendar gaps > *max_gap_days*.

    Each gap dict contains ``start_date`` (ISO), ``end_date`` (ISO), and
    ``gap_days`` (calendar delta).
    """
    rows = writer.get_historical_prices(pair, limit=lookback_years * 260)
    rows_sorted = sorted(rows, key=lambda r: str(r.get("date") or ""))
    gaps: list[dict[str, Any]] = []

    for i in range(1, len(rows_sorted)):
        prev_date_str = str(rows_sorted[i - 1].get("date") or "")
        next_date_str = str(rows_sorted[i].get("date") or "")
        if not prev_date_str or not next_date_str:
            continue
        prev_date = date.fromisoformat(prev_date_str[:10])
        next_date = date.fromisoformat(next_date_str[:10])
        delta_days = (next_date - prev_date).days
        if delta_days > max_gap_days:
            gaps.append(
                {
                    "start_date": prev_date.isoformat(),
                    "end_date": next_date.isoformat(),
                    "gap_days": delta_days,
                }
            )

    return gaps


def validate_backfill_completeness(
    pairs: list[str] | None = None,
) -> dict[str, Any]:
    """Run gap checks across the default 3 pairs (or *pairs*) and return summary.

    Returns ``{"ok": bool, "gaps_found": int, "details": dict[str, list[dict]]}``.
    """
    if pairs is None:
        pairs = ["EURUSD", "USDJPY", "USDINR"]

    details: dict[str, list[dict[str, Any]]] = {}
    total_gaps = 0

    for pair in pairs:
        gaps = check_historical_price_gaps(pair=pair)
        details[pair] = gaps
        total_gaps += len(gaps)

    return {
        "ok": total_gaps == 0,
        "gaps_found": total_gaps,
        "details": details,
    }


if __name__ == "__main__":
    import json

    result = validate_backfill_completeness()
    print(json.dumps(result, indent=2))
