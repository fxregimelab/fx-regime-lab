"""Populate historical_prices for the 3 locked pairs using yfinance.

Run this before the validation backfill so S0/S5/S20 prices are available.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date

# Ensure pipeline/src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.backfill.historical_fetcher import backfill_spot_for_pair

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PAIRS = ["EURUSD", "USDJPY", "USDINR"]
# Start a bit before earliest regime call (2026-04-05) to cover T+20 lookback
START = date(2026, 3, 1)
END = date.today()


def main() -> None:
    total = 0
    for pair in PAIRS:
        logger.info("Fetching %s from %s to %s", pair, START, END)
        count = backfill_spot_for_pair(pair, START, END)
        logger.info("Wrote %d bars for %s", count, pair)
        total += count
    logger.info("Total bars written: %d", total)


if __name__ == "__main__":
    main()
