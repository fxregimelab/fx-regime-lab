"""Sensitivity probe: which gate is actually binding? (diagnostic only)

This does NOT change the shipped rules. It re-runs the same replay with exactly
one frozen rule relaxed in-process, so the owner can see what each gate costs
in trade count. Any relaxation here is a *measurement*, never a proposal: the
production detectors in ``src.paper.strategies`` are untouched, and the frozen
spec still governs execution.

Every aggregate here is SETTLED-ONLY, exactly like the desk report
(``src.paper.backtest.report``): a trade whose outcome is unknown (the input
ended before its horizon) is never a win and never part of a performance
number. The censored tail is reported beside the settled figures, never folded
into them, so this probe cannot silently disagree with the report.

Usage (from ``pipeline/``)::

    python scripts/backtest_sensitivity.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import src.paper.features as features  # noqa: E402
import src.paper.strategies as strategies  # noqa: E402
from src.paper.backtest.data import (  # noqa: E402
    DEFAULT_DATA_DIR,
    PAIRS,
    data_fingerprint,
    load_pair,
)
from src.paper.backtest.engine import (  # noqa: E402
    BacktestConfig,
    BacktestResult,
    run_backtest,
)
from src.paper.features import Swing  # noqa: E402

_BASELINE_STRUCTURE = features.structure_state_at

_SETUPS = ("SU1-v1", "SU2-v1", "SU3-v1")


def scenario_summary(results: Sequence[BacktestResult]) -> dict[str, Any]:
    """The SETTLED-ONLY aggregates of one scenario.

    The same basis as the desk report: the performance numbers count the
    settled trades only, and the censored tail is reported beside them as
    ``trades_total``, ``trades_censored``, ``net_r_all`` and ``unresolved_r``.
    """
    trades = [t for r in results for t in r.trades]
    settled = [t for t in trades if t.settled]
    censored = [t for t in trades if not t.settled]
    net = sum(t.net_r for t in settled)
    marks = sum(t.net_r for t in censored)
    wins = sum(1 for t in settled if t.net_r > 0)
    # the same sample span the report uses for its combined block
    span_start = min((r.start for r in results), default=None)
    span_end = max((r.end for r in results), default=None)
    days = 0
    if span_start is not None and span_end is not None:
        days = (span_end - span_start).days
    weeks = max(1.0, days / 7.0)
    return {
        "basis": "settled_only",
        "trades": len(settled),
        "trades_total": len(trades),
        "trades_censored": len(censored),
        "trades_per_week": round(len(settled) / weeks, 3),
        "net_r": round(net, 3),
        "net_r_all": round(net + marks, 3),
        "unresolved_r": round(marks, 3),
        "expectancy_r": round(net / len(settled), 3) if settled else 0.0,
        "expectancy_r_all": (
            round((net + marks) / len(trades), 3) if trades else 0.0
        ),
        "win_rate": round(wins / len(settled), 3) if settled else 0.0,
        "by_pair": {r.pair: r.settled_count for r in results},
        "by_pair_total": {r.pair: r.trade_count for r in results},
        "by_setup": {
            setup: sum(1 for t in settled if t.setup_id == setup) for setup in _SETUPS
        },
        "by_setup_total": {
            setup: sum(1 for t in trades if t.setup_id == setup) for setup in _SETUPS
        },
    }


def _structure_allow_neutral(
    swings: Sequence[Swing], *, direction: str, as_of: datetime
) -> str:
    """Treat neutral H4 structure as acceptable; opposed still blocks."""
    state = _BASELINE_STRUCTURE(swings, direction=direction, as_of=as_of)
    return "aligned" if state == "neutral" else state


def _always_allow(*args: object, **kwargs: object) -> bool:
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate sensitivity probe (read-only)")
    parser.add_argument("--pair", action="append", choices=PAIRS, default=None)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--out",
        type=Path,
        default=_ROOT.parent / "reports" / "desk" / "research" / "sensitivity.json",
    )
    args = parser.parse_args()
    pairs = tuple(args.pair) if args.pair else PAIRS
    cfg = BacktestConfig()

    scenarios: dict[str, dict[str, Any]] = {}

    def run(label: str) -> None:
        results = []
        for pair in pairs:
            frames = load_pair(pair, data_dir=args.data_dir)
            result = run_backtest(
                pair,
                d1=list(frames["d1"].bars),
                h4=list(frames["h4"].bars),
                h1=list(frames["h1"].bars),
                m15=list(frames["m15"].bars),
                cfg=cfg,
            )
            results.append(result)
        summary = scenario_summary(results)
        scenarios[label] = summary
        net = summary["net_r"]
        settled = summary["trades"]
        print(
            f"{label:44s} trades={settled:4d} netR={net:+7.2f} "
            f"(settled-only, {summary['trades_censored']} censored)"
        )

    print("baseline (frozen rules as shipped):")
    run("baseline")

    print("\ndiagnostic relaxations (NOT proposals; production rules unchanged):")
    setattr(strategies, "structure_state_at", _structure_allow_neutral)
    run("h4_structure_allows_neutral")
    setattr(strategies, "structure_state_at", _BASELINE_STRUCTURE)

    original_floor = strategies._MIN_STOP_ATR
    strategies._MIN_STOP_ATR = 1.0
    run("stop_floor_1.0xATR")
    strategies._MIN_STOP_ATR = 0.8
    run("stop_floor_0.8xATR")
    strategies._MIN_STOP_ATR = original_floor

    setattr(strategies, "structure_state_at", _structure_allow_neutral)
    strategies._MIN_STOP_ATR = 1.0
    run("both_relaxed")
    setattr(strategies, "structure_state_at", _BASELINE_STRUCTURE)
    strategies._MIN_STOP_ATR = original_floor

    # Cost cap is a hard economic gate; probe it separately.
    original_cost = strategies._MAX_COST_SHARE
    strategies._MAX_COST_SHARE = 0.20
    run("cost_share_cap_20pct")
    strategies._MAX_COST_SHARE = original_cost

    # Weekend/session gate: are entries being lost to the window?
    original_session = getattr(strategies, "session_allows_entry")
    setattr(strategies, "session_allows_entry", _always_allow)
    run("session_window_removed")
    setattr(strategies, "session_allows_entry", original_session)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data_fingerprint": data_fingerprint(DEFAULT_DATA_DIR),
        **scenarios,
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    print("\nReminder: the baseline row is the only one that reflects the shipped rules.")
    print(
        "Reminder: every row is SETTLED-ONLY; the censored tail is reported beside "
        "the settled figures, never folded into them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
