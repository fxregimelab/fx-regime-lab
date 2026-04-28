"""OI signal derived from CFTC COT open_interest field."""

from __future__ import annotations

import logging

from src.types import CotRow

logger = logging.getLogger(__name__)


def compute_oi_from_cot(cot_rows: list[CotRow], pair: str) -> float | None:
    """
    Rank the most recent week's OI among the last 52 weeks for the pair.
    Returns a percentile (0–100) or None if fewer than 4 weeks of data.
    """
    rows = sorted(
        [r for r in cot_rows if r.pair == pair],
        key=lambda r: r.date,
    )
    if len(rows) < 4:
        logger.debug("Not enough COT rows for OI percentile on %s", pair)
        return None
    oi_series = [r.open_interest for r in rows if r.open_interest > 0]
    if not oi_series:
        return None
    latest = oi_series[-1]
    rank = sum(1 for v in oi_series if v <= latest)
    return round(rank / len(oi_series) * 100, 1)


def compute_oi_delta_from_cot(cot_rows: list[CotRow], pair: str) -> int | None:
    """Return latest week-over-week open-interest delta for a pair."""
    rows = sorted(
        [r for r in cot_rows if r.pair == pair and r.open_interest > 0],
        key=lambda r: r.date,
    )
    if len(rows) < 2:
        logger.debug("Not enough COT rows for OI delta on %s", pair)
        return None
    latest = rows[-1].open_interest
    previous = rows[-2].open_interest
    return int(latest - previous)
