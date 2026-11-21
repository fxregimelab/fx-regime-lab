"""Historical observation acquisition with the unsafe replay entry point retired."""

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
_LOCKED_PAIRS = frozenset(_DEFAULT_PAIRS)


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
    """Fetch and archive historical provider observations for all pairs."""
    if start > end:
        raise ValueError("Historical acquisition start date must not follow end date")
    if pairs is None:
        pairs = sorted(
            k
            for k, meta in load_universe().items()
            if isinstance(meta, dict) and meta.get("class") == "FX"
        ) or _DEFAULT_PAIRS
    if not pairs:
        raise ValueError("Historical acquisition requires at least one locked pair")
    if len(pairs) != len(set(pairs)):
        raise ValueError("Historical acquisition pairs must not contain duplicates")
    unsupported = sorted(set(pairs) - _LOCKED_PAIRS)
    if unsupported:
        raise ValueError(
            "Historical acquisition pairs are outside the locked universe: "
            + ", ".join(unsupported)
        )

    return {pair: backfill_spot_for_pair(pair, start, end) for pair in pairs}


def replay_pipeline_for_date(
    target_date: date,
    pairs: list[str] | None = None,
) -> dict[str, Any]:
    """Reject the retired live-orchestrator replay boundary before any I/O."""
    raise RuntimeError(
        "Historical replay through scheduler.run_daily is retired because it can fetch live "
        "inputs and publish live calls. Use backfill_spots for archive-only acquisition; a "
        "separate point-in-time replay contract is required before inference."
    )


def run_backfill_range(
    start: date,
    end: date,
    *,
    pairs: list[str] | None = None,
    step_days: int = 1,
    skip_weekends: bool = True,
) -> list[dict[str, Any]]:
    """Reject the former acquisition-plus-live-replay workflow before any I/O."""
    raise RuntimeError(
        "run_backfill_range is retired: archived provider observations are not replay-ready "
        "canonical closes. Use backfill_spots for archive-only acquisition."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="FX Regime Lab historical observation archive")
    parser.add_argument("start", help="Start date YYYY-MM-DD")
    parser.add_argument("end", help="End date YYYY-MM-DD")
    parser.add_argument("--pairs", nargs="+", default=None, help="FX pairs to backfill")
    parser.add_argument(
        "--spots-only", action="store_true", help="Archive observations without inference"
    )
    args = parser.parse_args()

    start_d = date.fromisoformat(args.start)
    end_d = date.fromisoformat(args.end)

    if args.spots_only:
        counts = backfill_spots(start_d, end_d, args.pairs)
        logger.info("Archived historical observations: %s", counts)
        sys.exit(0)
    parser.error(
        "historical replay is retired; pass --spots-only for archive-only acquisition"
    )
