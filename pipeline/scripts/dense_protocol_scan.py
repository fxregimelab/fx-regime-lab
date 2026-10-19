"""Protocol sensitivity for the dense harness (research only).

The per-year stability table showed the apparent edge decaying after 2023. Two
protocol levers could plausibly address that: a shorter training window (faster
regime adaptation) and a more selective threshold (fewer, higher-conviction
trades). This script tests both on a fixed geometry, with the same walk-forward

that the main harness uses.

Nothing here is tuned into production automatically; the output is evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.paper.backtest.data import (
    DEFAULT_DATA_DIR,
    PAIRS,
    data_fingerprint,
    load_series,
)
from src.paper.backtest.dense import DenseConfig, run_walk_forward
from src.paper.backtest.dense_report import summary

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"

TRAIN_DAYS = (180, 365, 730)
SIGNAL_RATES = (0.005, 0.01, 0.02, 0.05)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="h1")
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--stop", type=float, default=2.5)
    parser.add_argument("--target", type=float, default=1.5)
    parser.add_argument("--hold", type=int, default=48)
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start).replace(tzinfo=UTC)
    series = {
        pair: [
            b
            for b in load_series(pair, args.timeframe, data_dir=DEFAULT_DATA_DIR).bars
            if b.timestamp >= start
        ]
        for pair in PAIRS
    }

    base = DenseConfig(
        stop_atr_mult=args.stop,
        target_r=args.target,
        max_hold_bars=args.hold,
        min_edge_r=0.0,
    )
    rows: list[dict[str, Any]] = []
    for train_days in TRAIN_DAYS:
        for signal_rate in SIGNAL_RATES:
            cfg = replace(base, train_days=train_days, signal_rate=signal_rate)
            pair_rows: list[dict[str, Any]] = []
            results = []
            for pair in PAIRS:
                result = run_walk_forward(pair, series[pair], cfg=cfg)
                results.append(result)
                row = summary(result)
                pair_rows.append(
                    {
                        "pair": pair,
                        "trades": row["trades"],
                        "trades_per_week": row["trades_per_week"],
                        "win_rate": row["win_rate"],
                        "expectancy_r": row["expectancy_r"],
                        "net_r": row["total_net_r"],
                        "edge_r": row["edge_vs_unconditional_r"],
                        "fold_net": [f["net_r"] for f in row["fold_results"]],
                    }
                )
            total_trades = sum(int(r["trades"]) for r in pair_rows)
            total_net = sum(float(r["net_r"]) for r in pair_rows)
            span_start = min(r.folds[0].test_start for r in results if r.folds)
            span_end = max(r.end for r in results)
            span_weeks = max(
                (span_end - span_start).total_seconds() / (7 * 86400.0), 1.0
            )
            rows.append(
                {
                    "train_days": train_days,
                    "signal_rate": signal_rate,
                    "pairs": pair_rows,
                    "total_trades": total_trades,
                    "total_trades_per_week": round(total_trades / span_weeks, 3),
                    "total_net_r": round(total_net, 3),
                    "net_r_per_week": round(total_net / span_weeks, 3),
                }
            )
            print(
                f"train={train_days:3d}d rate={signal_rate:.3f}: "
                f"{total_trades:4d} trades ({total_trades / span_weeks:.1f}/wk) "
                f"net={total_net:+.1f}R ({total_net / span_weeks:+.2f}R/wk)",
                flush=True,
            )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "protocol_scan.json").write_text(
        json.dumps(
            {
                "base": asdict(base),
                "timeframe": args.timeframe,
                "start": args.start,
                "data_fingerprint": data_fingerprint(DEFAULT_DATA_DIR),
                "grid": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ranked = sorted(rows, key=lambda r: float(r["net_r_per_week"]), reverse=True)
    print("\nTop 3 by net R/week:")
    for row in ranked[:3]:
        print(
            f"  train={row['train_days']} rate={row['signal_rate']} -> "
            f"{row['net_r_per_week']:+.3f}R/wk "
            f"({row['total_trades_per_week']:.1f} trades/wk)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
