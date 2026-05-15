#!/usr/bin/env python3
"""Run paper trading simulation for pair-specific models."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

from src.backfill.paper_trading import PaperTradingSimulator
from src.db import writer

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FX Regime Lab Paper Trading Simulator"
    )
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["EURUSD", "USDJPY", "USDINR"],
        choices=["EURUSD", "USDJPY", "USDINR"],
        help="Pairs to simulate",
    )
    parser.add_argument(
        "--start", required=True, help="Start date YYYY-MM-DD"
    )
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--output", default="paper_trading_summary.json"
    )
    parser.add_argument(
        "--log-dir", default=None, help="Directory for JSONL trade logs"
    )
    parser.add_argument(
        "--capital", type=float, default=1_000_000.0, help="Initial capital per pair"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)
    log_dir = Path(args.log_dir) if args.log_dir else None

    simulator = PaperTradingSimulator(
        pairs=args.pairs,
        initial_capital=args.capital,
        log_dir=log_dir,
    )

    for pair in args.pairs:
        logger.info("Loading signals for %s", pair)
        raw_rows = writer.get_historical_signals(pair, limit=5000)
        if not raw_rows:
            logger.warning("No historical signals for %s", pair)
            continue

        signals: list[dict[str, Any]] = []
        for r in raw_rows:
            d = date.fromisoformat(str(r["date"])[:10])
            if start_date <= d <= end_date:
                signals.append(r)
        signals.sort(key=lambda x: x["date"])

        # Simulate walk through dates
        for idx, signal in enumerate(signals):
            d = str(signal["date"])[:10]
            comp = signal.get("composite", 0.0)
            if comp is None:
                comp = 0.0
            if comp > 0.2:
                regime = "BULLISH"
            elif comp < -0.2:
                regime = "BEARISH"
            else:
                regime = "NEUTRAL"
            regime_call = {
                "regime": regime,
                "composite": float(comp),
                "confidence": min(abs(float(comp)), 1.0),
                "conviction": 3 if abs(float(comp)) > 0.5 else 2,
            }

            # Close positions at T+20 or on reversal
            portfolio = simulator.portfolios[pair]
            pos = portfolio.positions.get(pair)
            if pos is not None:
                entry_date = date.fromisoformat(str(pos["entry_date"])[:10])
                current_date = date.fromisoformat(d)
                days_held = (current_date - entry_date).days
                spot = float(signal.get("spot", 0.0) or 0.0)
                if days_held >= 20 and spot > 0:
                    simulator.close_positions(pair, d, spot, reason="T+20")
                elif (
                    pos["direction"] == "LONG"
                    and regime == "BEARISH"
                    and spot > 0
                ):
                    simulator.close_positions(pair, d, spot, reason="REVERSAL")
                elif (
                    pos["direction"] == "SHORT"
                    and regime == "BULLISH"
                    and spot > 0
                ):
                    simulator.close_positions(pair, d, spot, reason="REVERSAL")

            simulator.on_regime_call(pair, d, regime_call, signal)

        # Force-close any remaining open positions
        final_spot = float(signals[-1].get("spot", 0.0) or 0.0) if signals else 0.0
        if final_spot > 0 and simulator.portfolios[pair].positions.get(pair):
            simulator.close_positions(
                pair,
                str(signals[-1]["date"])[:10],
                final_spot,
                reason="TIME",
            )

    summary = simulator.get_performance_summary()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"Paper trading complete. Summary saved to {args.output}")
    for pair, metrics in summary.items():
        print(f"\n{pair}:")
        print(f"  Capital:     ${metrics['capital']:,.2f}")
        print(f"  Trades:      {metrics['total_trades']}")
        print(f"  Win rate:    {metrics['win_rate']:.2f}%")
        print(f"  Sharpe:      {metrics['sharpe_ratio']:.3f}")
        print(f"  Max DD:      {metrics['max_drawdown_pct']:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
