#!/usr/bin/env python3
"""Compare legacy (v2) model vs pair-specific (v3) model performance.

Usage:
    python scripts/compare_models.py --pair EURUSD --start 2025-01-01 --end 2026-05-01
    python scripts/compare_models.py --pair ALL --start 2024-01-01 --end 2025-01-01
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

_ALLOWED_PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")


def compare_models(pair: str, start: str, end: str) -> dict[str, Any]:
    """Run both legacy (v2) and new (v3) models, compare metrics."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    logger.info("Comparing models for %s (%s to %s)", pair, start, end)

    daily_results, stats_v2, stats_v3 = _run_backtest_for_pair(
        pair, start_date, end_date, verbose=True
    )

    def _fmt_stats(s: Any) -> dict[str, Any]:
        return {k: v for k, v in asdict(s).items() if k != "daily"}

    return {
        "pair": pair,
        "start_date": start,
        "end_date": end,
        "total_days": len(daily_results),
        "legacy_v2": _fmt_stats(stats_v2),
        "pair_specific_v3": _fmt_stats(stats_v3),
        "comparison": {
            "accuracy_t1_delta": _delta(stats_v3.accuracy_t1, stats_v2.accuracy_t1),
            "accuracy_t5_delta": _delta(stats_v3.accuracy_t5, stats_v2.accuracy_t5),
            "accuracy_t20_delta": _delta(stats_v3.accuracy_t20, stats_v2.accuracy_t20),
            "sharpe_delta": _delta(stats_v3.sharpe_ratio, stats_v2.sharpe_ratio),
            "pnl_delta": stats_v3.total_pnl - stats_v2.total_pnl,
            "winner_t1": _winner(stats_v3.accuracy_t1, stats_v2.accuracy_t1),
            "winner_sharpe": _winner(stats_v3.sharpe_ratio, stats_v2.sharpe_ratio),
            "winner_pnl": (
                "v3"
                if stats_v3.total_pnl > stats_v2.total_pnl
                else "v2" if stats_v2.total_pnl > stats_v3.total_pnl else "tie"
            ),
        },
        "daily": [asdict(d) for d in daily_results],
    }


def _delta(v3: float | None, v2: float | None) -> float | None:
    if v3 is None or v2 is None:
        return None
    return v3 - v2


def _winner(v3: float | None, v2: float | None) -> str:
    if v3 is None or v2 is None:
        return "N/A"
    if v3 > v2:
        return "v3"
    if v2 > v3:
        return "v2"
    return "tie"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare legacy vs pair-specific model performance"
    )
    parser.add_argument("--pair", required=True, choices=[*_ALLOWED_PAIRS, "ALL"])
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    pairs = _ALLOWED_PAIRS if args.pair == "ALL" else (args.pair,)
    all_results: dict[str, Any] = {}

    for pair in pairs:
        try:
            all_results[pair] = compare_models(pair, args.start, args.end)
        except Exception as exc:
            logger.error("Comparison failed for %s: %s", pair, exc)
            all_results[pair] = {"pair": pair, "error": str(exc)}

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(all_results, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
