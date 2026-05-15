#!/usr/bin/env python3
"""Run pair-specific backtest from command line."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

from src.backfill.pair_backtest_engine import BacktestResult, PairBacktestEngine
from src.db import writer

logger = logging.getLogger(__name__)


def _result_to_dict(result: BacktestResult) -> dict[str, Any]:
    """Serialize BacktestResult to a plain dict."""
    return {
        "pair": result.pair,
        "start_date": result.start_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "avg_win_bps": result.avg_win_bps,
        "avg_loss_bps": result.avg_loss_bps,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown_pct": result.max_drawdown_pct,
        "profit_factor": result.profit_factor,
        "equity_curve": [(d.isoformat(), v) for d, v in result.equity_curve],
        "trades": [
            {
                "date": t.date.isoformat(),
                "pair": t.pair,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "position_size": t.position_size,
                "stop_level": t.stop_level,
                "take_profit": t.take_profit,
                "pnl_bps": t.pnl_bps,
                "exit_reason": t.exit_reason,
            }
            for t in result.trades
        ],
        "brier_score": result.brier_score,
        "calibration_error": result.calibration_error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FX Regime Lab Pair Backtest")
    parser.add_argument(
        "--pair", required=True, choices=["EURUSD", "USDJPY", "USDINR"]
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--output", default="backtest_result.json")
    parser.add_argument("--kelly", action="store_true", help="Use Kelly sizing")
    parser.add_argument("--stress", action="store_true", help="Use stress controls")
    parser.add_argument(
        "--correlation", action="store_true", help="Use correlation adjustment"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    logger.info("Loading historical signals for %s", args.pair)
    raw_rows = writer.get_historical_signals(args.pair, limit=5000)
    if not raw_rows:
        logger.error("No historical signals found for %s", args.pair)
        return 1

    signals: list[dict[str, Any]] = []
    for r in raw_rows:
        d = date.fromisoformat(str(r["date"])[:10])
        if start_date <= d <= end_date:
            signals.append(r)
    signals.sort(key=lambda x: x["date"])

    if len(signals) < 30:
        logger.error("Insufficient data: %s rows", len(signals))
        return 1

    # Build simple regime calls from signal composites (production would use
    # actual regime_call rows; backtest reconstructs them for convenience).
    regimes: list[dict[str, Any]] = []
    for s in signals:
        comp = s.get("composite")
        if comp is None:
            comp = 0.0
        if comp > 0.2:
            regime = "BULLISH"
        elif comp < -0.2:
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"
        regimes.append(
            {
                "date": s["date"],
                "regime": regime,
                "composite": float(comp),
                "confidence": min(abs(float(comp)), 1.0),
                "conviction": 3 if abs(float(comp)) > 0.5 else 2,
            }
        )

    engine = PairBacktestEngine(args.pair)
    result = engine.run(
        signals,
        regimes,
        use_kelly=args.kelly,
        use_stress_controls=args.stress,
        use_correlation_adjustment=args.correlation,
    )

    result_dict = _result_to_dict(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2, default=str)

    print(f"Backtest complete. Results saved to {args.output}")
    print(f"  Trades: {result.total_trades}")
    print(f"  Win rate: {result.win_rate:.2f}%")
    print(f"  Sharpe: {result.sharpe_ratio:.3f}")
    print(f"  Max DD: {result.max_drawdown_pct:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
