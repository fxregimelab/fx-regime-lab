"""SRE rollback: delete pipeline rows for a bad calendar date (single batch of deletes)."""

from __future__ import annotations

import argparse
import logging

from src.db import writer

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Delete all pipeline rows for DATE from signals, regime_calls, brief_log, "
            "historical_prices, research_analogs (as_of_date), strategy_ledger, desk_open_cards."
        ),
    )
    parser.add_argument(
        "date_str",
        help="Calendar date YYYY-MM-DD",
    )
    args = parser.parse_args()
    d = str(args.date_str).strip()[:10]
    if len(d) != 10 or d[4] != "-" or d[7] != "-":
        raise SystemExit("date_str must be YYYY-MM-DD")
    logger.warning("Rolling back pipeline data for %s", d)
    writer.delete_pipeline_data_for_date(d)
    logger.info("Rollback finished for %s", d)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
