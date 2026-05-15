#!/usr/bin/env python3
"""CLI to check historical backfill integrity for a given FX pair."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import NoReturn

# Ensure pipeline/src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.validation.backfill_integrity import check_historical_prices_integrity


def main() -> NoReturn:
    parser = argparse.ArgumentParser(
        description="Check historical price backfill integrity for a pair."
    )
    parser.add_argument(
        "--pair",
        required=True,
        help="FX pair to check (e.g. EURUSD)",
    )
    parser.add_argument(
        "--max-gap-days",
        type=int,
        default=5,
        help="Maximum allowed calendar gap between consecutive bars (default: 5)",
    )
    args = parser.parse_args()

    result = check_historical_prices_integrity(
        pair=args.pair,
        max_gap_days=args.max_gap_days,
    )
    print(json.dumps(result, indent=2))

    sys.exit(0 if result["is_valid"] else 1)


if __name__ == "__main__":
    main()
