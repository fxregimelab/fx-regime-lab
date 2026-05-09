"""Round 4 Phase 2 — Historical pipeline backfill orchestrator.

Walks a date range and attempts to replay the daily pipeline for each
calendar day, using ``historical_prices`` as the spot source.  Non-spot
signals (COT, rates, vol) are fetched live where possible; missing
inputs trigger the existing invalidation logic rather than fabricating
data.

Usage::

    python -m src.backfill.orchestrator 2024-01-01 2024-12-31
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from typing import Any

from src.backfill.historical_fetcher import backfill_spot_for_pair
from src.types import load_universe

logger = logging.getLogger(__name__)


_DEFAULT_PAIRS = ["EURUSD", "USDJPY", "USDINR"]


def _daterange(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def backfill_spots(
    start: date,
    end: date,
    pairs: list[str] | None = None,
) -> dict[str, int]:
    """Fetch and persist historical spot bars for all pairs."""
    if pairs is None:
        pairs = sorted(
            k
            for k, meta in load_universe().items()
            if isinstance(meta, dict) and meta.get("class") == "FX"
        ) or _DEFAULT_PAIRS

    counts: dict[str, int] = {}
    for pair in pairs:
        try:
            n = backfill_spot_for_pair(pair, start, end)
            counts[pair] = n
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backfill spot failed for %s: %s", pair, exc)
            counts[pair] = 0
    return counts


def replay_pipeline_for_date(
    target_date: date,
    pairs: list[str] | None = None,
) -> dict[str, Any]:
    """Replay the daily orchestrator for ``target_date``.

    This imports and delegates to ``src.scheduler.orchestrator.run_daily``
    with an explicit ``date_str`` override.  The orchestrator already
    supports historical replay when ``historical_prices`` rows exist.

    Returns a summary dict with success / failure per pair.
    """
    from src.scheduler.orchestrator import run_daily

    summary: dict[str, Any] = {"date": target_date.isoformat(), "pairs": {}}
    date_str = target_date.isoformat()

    try:
        # run_daily is async; wrap it
        import asyncio

        asyncio.run(run_daily(date_str=date_str))
        summary["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.error("Replay failed for %s: %s", date_str, exc)
        summary["status"] = "error"
        summary["error"] = str(exc)

    return summary


def run_backfill_range(
    start: date,
    end: date,
    *,
    pairs: list[str] | None = None,
    step_days: int = 1,
    skip_weekends: bool = True,
) -> list[dict[str, Any]]:
    """Backfill spot data and optionally replay pipeline for a date range.

    Parameters
    ----------
    start, end:
        Inclusive date range.
    pairs:
        FX pairs to backfill (defaults to universe FX class).
    step_days:
        Replay frequency (1 = every calendar day).
    skip_weekends:
        If True, skip Saturday/Sunday for replay (spot still backfilled).
    """
    logger.info("Backfill start: %s -> %s, pairs=%s", start, end, pairs)

    # Phase 1 — spot prices (idempotent)
    spot_counts = backfill_spots(start, end, pairs)
    logger.info("Spot backfill complete: %s", spot_counts)

    # Phase 2 — optional pipeline replay
    summaries: list[dict[str, Any]] = []
    for d in _daterange(start, end):
        if skip_weekends and d.weekday() >= 5:
            continue
        if (d - start).days % step_days != 0:
            continue
        summary = replay_pipeline_for_date(d, pairs)
        summaries.append(summary)

    logger.info("Backfill replay complete: %d dates attempted", len(summaries))
    return summaries


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="FX Regime Lab historical backfill")
    parser.add_argument("start", help="Start date YYYY-MM-DD")
    parser.add_argument("end", help="End date YYYY-MM-DD")
    parser.add_argument("--pairs", nargs="+", default=None, help="FX pairs to backfill")
    parser.add_argument("--step", type=int, default=1, help="Replay every N days")
    parser.add_argument("--spots-only", action="store_true", help="Only fetch spots, skip replay")
    args = parser.parse_args()

    start_d = date.fromisoformat(args.start)
    end_d = date.fromisoformat(args.end)

    if args.spots_only:
        counts = backfill_spots(start_d, end_d, args.pairs)
        logger.info("Backfill spots: %s", counts)
        sys.exit(0)

    results = run_backfill_range(
        start_d,
        end_d,
        pairs=args.pairs,
        step_days=args.step,
    )
    ok = sum(1 for r in results if r.get("status") == "ok")
    logger.info("Backfill complete: %d/%d dates succeeded", ok, len(results))
