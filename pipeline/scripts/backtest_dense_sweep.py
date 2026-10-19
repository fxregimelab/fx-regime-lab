"""Geometry sweep for the dense harness on any timeframe (research only).

Usage (from pipeline/):
    .\\.venv\\Scripts\\python.exe scripts\\backtest_dense_sweep.py
    .\\.venv\\Scripts\\python.exe scripts\\backtest_dense_sweep.py --timeframe h1 --start 2022-01-01

Every configuration uses the same expanding-window walk-forward. The sweep
selects nothing automatically; treat the winner as a hypothesis, not a rule.
"""

from __future__ import annotations

import argparse
import itertools
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
from src.paper.features import OHLCBar

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"

GRIDS: dict[str, tuple[tuple[float, ...], tuple[float, ...], tuple[int, ...]]] = {
    "m15": ((1.5, 2.5, 4.0), (1.0, 1.5, 2.0), (32, 64, 96)),
    "h1": ((1.0, 1.5, 2.5), (1.0, 1.5, 2.0), (12, 24, 48)),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", choices=sorted(GRIDS), default="m15")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--min-edge", type=float, default=0.0)
    parser.add_argument("--signal-rate", type=float, default=0.03)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    tag = args.tag or args.timeframe
    stop_mults, targets, holds = GRIDS[args.timeframe]
    start = (
        datetime.fromisoformat(args.start).replace(tzinfo=UTC) if args.start else None
    )
    end = datetime.fromisoformat(args.end).replace(tzinfo=UTC) if args.end else None

    base = DenseConfig(
        min_edge_r=args.min_edge,
        signal_rate=args.signal_rate,
        max_concurrent=args.concurrency,
    )
    loaded = {
        pair: load_series(pair, args.timeframe, data_dir=DEFAULT_DATA_DIR) for pair in PAIRS
    }
    series: dict[str, list[OHLCBar]] = {
        pair: [
            bar
            for bar in loaded[pair].bars
            if (start is None or bar.timestamp >= start)
            and (end is None or bar.timestamp < end)
        ]
        for pair in PAIRS
    }

    rows: list[dict[str, Any]] = []
    for stop_mult, target, hold in itertools.product(stop_mults, targets, holds):
        cfg = replace(
            base, stop_atr_mult=stop_mult, target_r=target, max_hold_bars=hold
        )
        pair_rows = []
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
                    "costs_r": row["total_costs_r"],
                    "unconditional_r": row["unconditional_expectancy_r"],
                    "edge_r": row["edge_vs_unconditional_r"],
                    "first_test_start": (
                        result.folds[0].test_start.isoformat()
                        if result.folds
                        else None
                    ),
                    "last_test_end": (
                        result.folds[-1].test_end.isoformat()
                        if result.folds
                        else None
                    ),
                }
            )
        total_trades = sum(int(r["trades"]) for r in pair_rows)
        total_net = sum(float(r["net_r"]) for r in pair_rows)
        # Rate denominator is the out-of-sample span only, never the training bars.
        span_start = min(r.folds[0].test_start for r in results if r.folds)
        span_end = max(r.end for r in results)
        span_weeks = max(
            (span_end - span_start).total_seconds() / (7 * 86400.0), 1.0
        )
        rows.append(
            {
                "stop_mult": stop_mult,
                "target_r": target,
                "max_hold_bars": hold,
                "pairs": pair_rows,
                "total_trades": total_trades,
                "total_trades_per_week": round(total_trades / span_weeks, 3),
                "total_net_r": round(total_net, 3),
                "net_r_per_week": round(total_net / span_weeks, 3),
            }
        )
        print(
            f"stop={stop_mult} target={target} hold={hold}: "
            f"{total_trades} trades ({total_trades / span_weeks:.1f}/wk) "
            f"net={total_net:+.1f}R ({total_net / span_weeks:+.2f}R/wk)",
            flush=True,
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = "sweep.json" if tag == "m15" else f"sweep_{tag}.json"
    (REPORT_DIR / filename).write_text(
        json.dumps(
            {
                "base": asdict(base),
                "timeframe": args.timeframe,
                "start": args.start,
                "end": args.end,
                "data_fingerprint": data_fingerprint(DEFAULT_DATA_DIR),
                "grid": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ranked = sorted(rows, key=lambda r: float(r["net_r_per_week"]), reverse=True)
    print(f"\nTop 5 by net R/week ({args.timeframe}):")
    for row in ranked[:5]:
        print(
            f"  stop={row['stop_mult']} target={row['target_r']} "
            f"hold={row['max_hold_bars']} -> {row['net_r_per_week']:+.3f}R/wk "
            f"({row['total_trades_per_week']:.1f} trades/wk)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
