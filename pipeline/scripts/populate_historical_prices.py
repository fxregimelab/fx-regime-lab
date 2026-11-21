"""Archive Yahoo observations for the three locked pairs.

These rows retain provider metadata. They are not qualified canonical closes
and do not make S0/S5/S20 validation prices or historical replay ready.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, date, datetime

# Ensure the pipeline package root is available when this file is run directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.backfill.orchestrator import backfill_spots

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PAIRS = ["EURUSD", "USDJPY", "USDINR"]
# Start a bit before earliest regime call (2026-04-05) to cover T+20 lookback
START = date(2026, 3, 1)
END = datetime.now(UTC).date()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Archive Yahoo provider observations. This does not populate qualified "
            "validation closes."
        )
    )
    parser.add_argument("--start", type=date.fromisoformat, default=START)
    parser.add_argument("--end", type=date.fromisoformat, default=END)
    parser.add_argument("--pairs", nargs="+", choices=PAIRS, default=PAIRS)
    args = parser.parse_args(argv)

    logger.info("Fetching %s from %s to %s", args.pairs, args.start, args.end)
    counts = backfill_spots(args.start, args.end, args.pairs)
    for pair, count in counts.items():
        logger.info("Archived %d provider observations for %s", count, pair)
    total = sum(counts.values())
    logger.info(
        "Archived %d provider observations; canonical validation closes remain unqualified",
        total,
    )


if __name__ == "__main__":
    main()
