"""Evaluate the interpretable dense rule baselines (research only)."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from src.paper.backtest.data import DEFAULT_DATA_DIR, PAIRS, load_series
from src.paper.backtest.dense_report import weekly_rows
from src.paper.backtest.rules import RuleConfig, run_rule

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"
RULES = ("london_breakout", "mean_reversion", "momentum_pullback")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="m15")
    parser.add_argument("--start", default=None)
    parser.add_argument("--stop", type=float, default=None)
    parser.add_argument("--target", type=float, default=None)
    parser.add_argument("--hold", type=int, default=None)
    args = parser.parse_args()

    rule_cfg = RuleConfig()
    if args.stop is not None:
        rule_cfg = RuleConfig(
            stop_atr_mult=args.stop,
            target_r=args.target if args.target is not None else rule_cfg.target_r,
            max_hold_bars=args.hold if args.hold is not None else rule_cfg.max_hold_bars,
        )
    start = (
        datetime.fromisoformat(args.start).replace(tzinfo=UTC) if args.start else None
    )

    series = {
        pair: load_series(pair, args.timeframe, data_dir=DEFAULT_DATA_DIR) for pair in PAIRS
    }
    rows = []
    for rule in RULES:
        for pair in PAIRS:
            bars = [
                b
                for b in series[pair].bars
                if start is None or b.timestamp >= start
            ]
            trades = run_rule(pair, bars, rule, rule_cfg=rule_cfg)
            weeks = weekly_rows(trades)
            active = [w for w in weeks if int(w["trades"]) > 0]
            span_weeks = max(
                (bars[-1].timestamp - bars[0].timestamp).total_seconds() / (7 * 86400.0),
                1.0,
            )
            wins = [t for t in trades if t.net_r > 0.0]
            row = {
                "rule": rule,
                "pair": pair,
                "trades": len(trades),
                "trades_per_week": round(len(trades) / span_weeks, 3),
                "win_rate": round(len(wins) / len(trades), 4) if trades else 0.0,
                "expectancy_r": round(
                    sum(t.net_r for t in trades) / len(trades), 4
                ) if trades else 0.0,
                "net_r": round(sum(t.net_r for t in trades), 3),
                "costs_r": round(sum(t.cost_r for t in trades), 3),
                "active_weeks": len(active),
            }
            rows.append(row)
            print(
                f"{rule:18s} {pair}: {row['trades']:5d} trades "
                f"({row['trades_per_week']:.2f}/wk) win={row['win_rate']:.1%} "
                f"exp={row['expectancy_r']:+.3f}R net={row['net_r']:+.1f}R",
                flush=True,
            )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"rules_{args.timeframe}.json").write_text(
        json.dumps(
            {"config": asdict(rule_cfg), "timeframe": args.timeframe, "results": rows},
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
