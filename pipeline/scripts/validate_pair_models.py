#!/usr/bin/env python3
"""Validate pair-specific models against historical data.

Compares model predictions vs actual outcomes over a date range and
computes accuracy, Brier score, and Sharpe ratio.

Usage:
    python scripts/validate_pair_models.py --pair EURUSD --start 2025-01-01 --end 2026-05-01
    python scripts/validate_pair_models.py --pair USDJPY --start 2024-06-01 \
        --end 2025-06-01 --output validation.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import date
from typing import Any

# Ensure pipeline/src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.pairs.backtest import _run_backtest_for_pair

logger = logging.getLogger(__name__)


def validate_pair(pair: str, start_date: str, end_date: str) -> dict[str, Any]:
    """Validate a pair model over a date range.

    Fetches historical signals, reconstructs v2 and v3 composites,
    compares predicted direction vs realized, and returns metrics.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    logger.info("Validating %s from %s to %s", pair, start_date, end_date)

    daily_results, stats_v2, stats_v3 = _run_backtest_for_pair(
        pair, start, end, verbose=True
    )

    # Summarize into a flat dict for CLI consumption
    return {
        "pair": pair,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(daily_results),
        "v2": {
            "accuracy_t1": stats_v2.accuracy_t1,
            "accuracy_t5": stats_v2.accuracy_t5,
            "accuracy_t20": stats_v2.accuracy_t20,
            "mean_brier_t1": stats_v2.mean_brier_t1,
            "mean_brier_t5": stats_v2.mean_brier_t5,
            "mean_brier_t20": stats_v2.mean_brier_t20,
            "total_pnl": stats_v2.total_pnl,
            "sharpe_ratio": stats_v2.sharpe_ratio,
            "max_drawdown_pct": stats_v2.max_drawdown_pct,
            "num_trades": stats_v2.num_trades,
        },
        "v3": {
            "accuracy_t1": stats_v3.accuracy_t1,
            "accuracy_t5": stats_v3.accuracy_t5,
            "accuracy_t20": stats_v3.accuracy_t20,
            "mean_brier_t1": stats_v3.mean_brier_t1,
            "mean_brier_t5": stats_v3.mean_brier_t5,
            "mean_brier_t20": stats_v3.mean_brier_t20,
            "total_pnl": stats_v3.total_pnl,
            "sharpe_ratio": stats_v3.sharpe_ratio,
            "max_drawdown_pct": stats_v3.max_drawdown_pct,
            "num_trades": stats_v3.num_trades,
        },
        "daily": [asdict(d) for d in daily_results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pair-specific model performance")
    parser.add_argument("--pair", required=True, choices=("EURUSD", "USDJPY", "USDINR"))
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="validation_result.json", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    result = validate_pair(args.pair, args.start, args.end)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    v3 = result["v3"]
    acc = v3.get("accuracy_t1")
    if acc is not None:
        print(f"Validation complete: {acc:.1f}% T+1 accuracy (v3)")
    else:
        print("Validation complete: insufficient data for T+1 accuracy")

    print(f"Results saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
