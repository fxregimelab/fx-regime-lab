"""Compatibility entry point for canonical validation cohort aggregation.

Historical statistics are computed and persisted only by
``src.validation.aggregate``. Keeping this small adapter avoids a second set
of formulas and prevents direct database maintenance from bypassing the writer.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from src.validation import aggregate as aggregate
from src.validation.aggregate import AggregateStats


def run_batch_stats(as_of_date: date | None = None) -> list[AggregateStats]:
    """Run the canonical cohort aggregator for the requested as-of date."""

    return aggregate.run_aggregate_stats(as_of_date=as_of_date)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute validation statistics with the canonical cohort aggregator"
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        help="Aggregation date in YYYY-MM-DD format (defaults to today)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    arguments = _parse_args()
    run_batch_stats(as_of_date=arguments.as_of_date)
