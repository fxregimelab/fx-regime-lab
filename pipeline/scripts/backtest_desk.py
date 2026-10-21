"""Run the offline backtest over all available history and write a report.

Usage (from ``pipeline/``)::

    .\\.venv\\Scripts\\python.exe scripts\\backtest_desk.py
    python scripts/backtest_desk.py --pair EURUSD --out reports/desk/research
    python scripts/backtest_desk.py --per-pair     # legacy per-pair replay

The DEFAULT path is the JOINT replay: EURUSD and USDJPY share ONE set of
caps, one loss capacity and one correlated-USD ticket cap, exactly as the
live desk would. The per-pair replay (``--per-pair``) stays available for
comparison.

The historical ``reports/desk/research/backtest.json`` is NOT regenerated.
It was written before the PD-00B engine repair and the PD-00C event-time
replay, so it is stale by design and must not be compared with a new run.
New runs write a NEW stem (``backtest_joint`` by default) and this script
refuses to overwrite the historical file.

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
from src.paper.backtest.portfolio import PairBars, run_joint_backtest  # noqa: E402
from src.paper.backtest.report import (  # noqa: E402
    build_report,
    joint_to_results,
    write_report,
)

# The stem of the HISTORICAL report. The stem itself is RESERVED: no run may
# write a file named "backtest.json"/"backtest.md", so a stray copy elsewhere
# can never be mistaken for the historical artifact. The historical PATH is
# protected a second time, inside write_report, for library callers.
_HISTORICAL_STEM = "backtest"
_DEFAULT_STEM = "backtest_joint"
_HISTORICAL_DIR = _ROOT.parent / "reports" / "desk" / "research"


def historical_conflicts(out_dir: Path, stem: str) -> list[Path]:
    """The historical files this run would overwrite, or an empty list.

    The RESERVED STEM is refused outright: ``--stem backtest`` is rejected
    whatever ``--out`` says, so no file named like the historical report can
    be produced anywhere. The historical PATH is refused again by
    :func:`src.paper.backtest.report.write_report` for direct library callers.
    """
    if stem == _HISTORICAL_STEM:
        return [out_dir / f"{_HISTORICAL_STEM}{suffix}" for suffix in (".json", ".md")]
    conflicts: list[Path] = []
    for suffix in (".json", ".md"):
        candidate = out_dir / f"{stem}{suffix}"
        try:
            resolved = candidate.resolve()
            historical = (_HISTORICAL_DIR / f"{_HISTORICAL_STEM}{suffix}").resolve()
        except OSError:
            # An unreadable path cannot be proven safe: REFUSE, never allow.
            return [candidate]
        if resolved == historical:
            conflicts.append(candidate)
    return conflicts


def build_parser() -> argparse.ArgumentParser:
    """The command line of the desk backtest.

    The joint replay is the DEFAULT; ``--per-pair`` keeps the legacy path.
    """
    parser = argparse.ArgumentParser(description="Offline desk strategy backtest")
    parser.add_argument("--pair", action="append", choices=PAIRS, default=None)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out", type=Path, default=_ROOT.parent / "reports" / "desk" / "research")
    parser.add_argument("--risk", type=float, default=0.01, help="risk per trade as a fraction")
    parser.add_argument(
        "--stem",
        default=_DEFAULT_STEM,
        help="output stem; the reserved 'backtest' stem is refused anywhere",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--joint",
        dest="mode",
        action="store_const",
        const="joint",
        default="joint",
        help="joint cross-pair replay (the DEFAULT)",
    )
    mode.add_argument(
        "--per-pair",
        dest="mode",
        action="store_const",
        const="per_pair",
        help="legacy per-pair replay: one independent portfolio per pair",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    conflicts = historical_conflicts(args.out, args.stem)
    if conflicts:
        for path in conflicts:
            print(f"refusing to overwrite the historical report: {path}", file=sys.stderr)
        print(
            "the historical backtest.json is stale by design and is not regenerated; "
            "choose another --stem.",
            file=sys.stderr,
        )
        return 2

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
    if args.mode == "joint":
        series = [
            PairBars(
                pair=pair,
                d1=list(bundle[pair]["d1"].bars),
                h4=list(bundle[pair]["h4"].bars),
                h1=list(bundle[pair]["h1"].bars),
                m15=list(bundle[pair]["m15"].bars),
            )
            for pair in pairs
        ]
        print("\njoint replay (one shared portfolio across the pairs) ...", flush=True)
        t0 = time.time()
        joint_result = run_joint_backtest(series, cfg=cfg)
        results = joint_to_results(joint_result, series, cfg=cfg)
        report = build_report(results, joint=joint_result)
        print(
            f"  emitted {joint_result.emitted_count}, admitted "
            f"{joint_result.admitted_count}, settled {joint_result.settled_count}, "
            f"censored {joint_result.censored_count}"
        )
        print(
            f"  net {joint_result.net_r:+.2f}R settled-only "
            f"(marks {joint_result.unresolved_r:+.2f}R), "
            f"fingerprint {joint_result.fingerprint[:16]} ({time.time() - t0:.0f}s)"
        )
    else:
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
                f"  {result.trade_count} booked, {result.settled_count} settled, "
                f"{result.censored_count} censored, net {result.net_r:+.2f}R settled-only "
                f"(marks {result.unresolved_r:+.2f}R), win rate {result.win_rate:.1%} "
                f"({time.time() - t0:.0f}s)"
            )
            results.append(result)
        report = build_report(results)

    report["data_coverage"] = coverage
    md_path, json_path = write_report(report, args.out, stem=args.stem)
    combined = report["combined"]["trade_stats"]
    print(f"\nwrote {md_path}")
    print(f"wrote {json_path}")
    print(
        f"note: every performance figure below and in the report is SETTLED-ONLY "
        f"(R, win rate, expectancy, per-week rates: {combined['trades_settled']} "
        f"settled trades); the censored tail "
        f"({combined['trades_censored']} trades, {combined['unresolved_r']:+.2f}R) is "
        f"reported separately as marks."
    )
    print(
        "note: the historical reports/desk/research/backtest.json is NOT regenerated "
        "by this script; it predates the PD-00B engine repair and the PD-00C "
        "event-time replay, so it is stale by design and must not be compared with "
        "this run."
    )
    print(f"total {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
