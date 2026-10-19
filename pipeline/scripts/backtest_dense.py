"""Run the dense walk-forward research harness over one timeframe.

Research only: reads CSVs, writes a report, never touches the broker.

Usage (from pipeline/):
    .\\.venv\\Scripts\\python.exe scripts\\backtest_dense.py
    .\\.venv\\Scripts\\python.exe scripts\\backtest_dense.py --timeframe h1 \\
        --start 2022-01-01 --stop 2.5 --target 2.0 --hold 48 --tag h1_edge
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from src.paper.backtest.data import (
    DEFAULT_DATA_DIR,
    PAIRS,
    data_fingerprint,
    load_series,
)
from src.paper.backtest.dense import DenseConfig, run_walk_forward
from src.paper.backtest.dense_report import render_markdown, summary
from src.paper.features import OHLCBar

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="m15")
    parser.add_argument("--start", default=None)
    parser.add_argument("--stop", type=float, default=None)
    parser.add_argument("--target", type=float, default=None)
    parser.add_argument("--hold", type=int, default=None)
    parser.add_argument("--signal-rate", type=float, default=None)
    parser.add_argument("--min-edge", type=float, default=None)
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    cfg = DenseConfig()
    overrides = {}
    if args.stop is not None:
        overrides["stop_atr_mult"] = args.stop
    if args.target is not None:
        overrides["target_r"] = args.target
    if args.hold is not None:
        overrides["max_hold_bars"] = args.hold
    if args.signal_rate is not None:
        overrides["signal_rate"] = args.signal_rate
    if args.min_edge is not None:
        overrides["min_edge_r"] = args.min_edge
    if overrides:
        cfg = replace(cfg, **overrides)

    start = (
        datetime.fromisoformat(args.start).replace(tzinfo=UTC) if args.start else None
    )
    rows = []
    for pair in PAIRS:
        series = load_series(pair, args.timeframe, data_dir=DEFAULT_DATA_DIR)
        bars: list[OHLCBar] = [
            bar for bar in series.bars if start is None or bar.timestamp >= start
        ]
        print(
            f"{pair}: {len(bars)} {args.timeframe.upper()} bars "
            f"{bars[0].timestamp} -> {bars[-1].timestamp}"
        )
        result = run_walk_forward(pair, bars, cfg=cfg)
        row = summary(result)
        rows.append(row)
        print(
            f"  trades={row['trades']} ({row['trades_per_week']}/wk) "
            f"win={row['win_rate']:.1%} exp={row['expectancy_r']:+.3f}R "
            f"net={row['total_net_r']:+.2f}R "
            f"unconditional={row['unconditional_expectancy_r']:+.3f}R "
            f"fold_conc={row['fold_profit_concentration']}"
        )

    tag = args.tag or args.timeframe
    stem = "dense" if tag == "m15" else f"dense_{tag}"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_by": "scripts/backtest_dense.py",
        "timeframe": args.timeframe,
        "start": args.start,
        "config": asdict(cfg),
        "data_fingerprint": data_fingerprint(DEFAULT_DATA_DIR),
        "pairs": rows,
    }
    (REPORT_DIR / f"{stem}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (REPORT_DIR / f"{stem}.md").write_text(
        render_markdown(
            rows,
            title=f"Dense walk-forward research ({args.timeframe.upper()})",
            config=asdict(cfg),
        ),
        encoding="utf-8",
    )
    print(f"wrote {REPORT_DIR / f'{stem}.json'} and {stem}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
