"""Run the offline backtest over all available history and write a report.

Usage (from ``pipeline/``)::

    .\\.venv\\Scripts\\python.exe scripts\\backtest_desk.py
    python scripts/backtest_desk.py --pair EURUSD --out reports/desk/research

Research only: reads local CSVs, never touches a broker or the database.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.paper.backtest.data import (  # noqa: E402
    DEFAULT_DATA_DIR,
    PAIRS,
    coverage_summary,
    load_bundle,
)
from src.paper.backtest.engine import BacktestConfig, run_backtest  # noqa: E402
from src.paper.backtest.report import build_report, write_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline desk strategy backtest")
    parser.add_argument("--pair", action="append", choices=PAIRS, default=None)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out", type=Path, default=_ROOT.parent / "reports" / "desk" / "research")
    parser.add_argument("--risk", type=float, default=0.01, help="risk per trade as a fraction")
    parser.add_argument("--stem", default="backtest")
    args = parser.parse_args()

    pairs = tuple(args.pair) if args.pair else PAIRS
    started = time.time()
    bundle = load_bundle(data_dir=args.data_dir)
    coverage = [row for row in coverage_summary(bundle) if row["pair"] in pairs]
    print("data coverage:")
    for row in coverage:
        print(
            f"  {row['pair']} {row['timeframe']:3s} {row['bars']:6d} bars "
            f"{row['first'][:10]} -> {row['last'][:10]} ({row['days']}d)"
        )

    cfg = BacktestConfig(risk_per_trade=args.risk)
    results = []
    for pair in pairs:
        frames = bundle[pair]
        print(f"\n{pair}: replaying ...", flush=True)
        t0 = time.time()
        result = run_backtest(
            pair,
            d1=list(frames["d1"].bars),
            h4=list(frames["h4"].bars),
            h1=list(frames["h1"].bars),
            m15=list(frames["m15"].bars),
            cfg=cfg,
        )
        print(
            f"  {len(result.trades)} trades, net {result.net_r:+.2f}R, "
            f"win rate {result.win_rate:.1%} ({time.time() - t0:.0f}s)"
        )
        results.append(result)

    report = build_report(results)
    report["data_coverage"] = coverage
    md_path, json_path = write_report(report, args.out, stem=args.stem)
    print(f"\nwrote {md_path}")
    print(f"wrote {json_path}")
    print(f"total {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
