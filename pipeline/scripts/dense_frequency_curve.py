"""Frequency/expectancy curve for the dense selector (research only).

The mandate asks for 10-15 settled trades per week. On a fixed geometry this
script varies the calibration quantile (``signal_rate``), and can separately
vary the minimum predicted edge and the number of concurrent positions per
pair. Those are the only levers that can raise frequency without changing the
model.

Nothing here is promoted automatically. A positive low-frequency cell is not an
edge at the mandated frequency if expectancy collapses as trades are added.
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
from src.paper.backtest.dense_report import summary
from src.paper.features import OHLCBar

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"
SIGNAL_RATES = (0.02, 0.05, 0.10, 0.20, 0.35, 0.50)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="m15")
    parser.add_argument("--start", default=None)
    parser.add_argument("--stop", type=float, default=1.5)
    parser.add_argument("--target", type=float, default=1.5)
    parser.add_argument("--hold", type=int, default=32)
    parser.add_argument("--min-edge", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--tag", default="")
    args = parser.parse_args()

    start = (
        datetime.fromisoformat(args.start).replace(tzinfo=UTC) if args.start else None
    )
    series: dict[str, list[OHLCBar]] = {}
    for pair in PAIRS:
        loaded = load_series(pair, args.timeframe, data_dir=DEFAULT_DATA_DIR)
        series[pair] = [
            bar for bar in loaded.bars if start is None or bar.timestamp >= start
        ]

    base = DenseConfig(
        stop_atr_mult=args.stop,
        target_r=args.target,
        max_hold_bars=args.hold,
        min_edge_r=args.min_edge,
        max_concurrent=args.concurrency,
    )
    rows = []
    for signal_rate in SIGNAL_RATES:
        cfg = replace(base, signal_rate=signal_rate)
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
                    "unconditional_r": row["unconditional_expectancy_r"],
                    "matched_unconditional_r": row["matched_unconditional_r"],
                    "edge_r": row["edge_vs_matched_r"],
                    "max_fold_share_of_positive": row["max_fold_share_of_positive"],
                }
            )
        span_start = min(r.folds[0].test_start for r in results if r.folds)
        span_end = max(r.end for r in results)
        span_weeks = max((span_end - span_start).total_seconds() / (7 * 86400.0), 1.0)
        total_trades = sum(int(r["trades"]) for r in pair_rows)
        total_net = sum(float(r["net_r"]) for r in pair_rows)
        rows.append(
            {
                "signal_rate": signal_rate,
                "pairs": pair_rows,
                "total_trades": total_trades,
                "total_trades_per_week": round(total_trades / span_weeks, 3),
                "total_net_r": round(total_net, 3),
                "net_r_per_week": round(total_net / span_weeks, 3),
            }
        )
        print(
            f"rate={signal_rate:.2f}: {total_trades:5d} trades "
            f"({total_trades / span_weeks:5.1f}/wk) net={total_net:+8.1f}R "
            f"({total_net / span_weeks:+.2f}R/wk)",
            flush=True,
        )
        for row in pair_rows:
            print(
                f"    {row['pair']}: {row['trades']:4d} "
                f"({row['trades_per_week']:5.1f}/wk) exp={row['expectancy_r']:+.3f}R "
                f"edge={row['edge_r']:+.3f}R",
                flush=True,
            )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.tag}" if args.tag else ""
    (REPORT_DIR / f"frequency_curve{suffix}.json").write_text(
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
