"""Sensitivity probe: which gate is actually binding? (diagnostic only)

This does NOT change the shipped rules. It re-runs the same replay with exactly
one frozen rule relaxed in-process, so the owner can see what each gate costs
in trade count. Any relaxation here is a *measurement*, never a proposal: the
production detectors in ``src.paper.strategies`` are untouched, and the frozen
spec still governs execution.

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
from src.paper.backtest.engine import BacktestConfig, run_backtest  # noqa: E402
from src.paper.features import Swing  # noqa: E402

_BASELINE_STRUCTURE = features.structure_state_at


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

    scenarios: dict[str, dict[str, object]] = {}

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
        trades = [t for r in results for t in r.trades]
        net = sum(t.net_r for t in trades)
        wins = sum(1 for t in trades if t.net_r > 0)
        weeks = max(1.0, (results[0].end - results[0].start).days / 7.0)
        scenarios[label] = {
            "trades": len(trades),
            "trades_per_week": round(len(trades) / weeks, 3),
            "net_r": round(net, 3),
            "expectancy_r": round(net / len(trades), 3) if trades else 0.0,
            "win_rate": round(wins / len(trades), 3) if trades else 0.0,
            "by_pair": {r.pair: len(r.trades) for r in results},
            "by_setup": {
                setup: sum(1 for t in trades if t.setup_id == setup)
                for setup in ("SU1-v1", "SU2-v1", "SU3-v1")
            },
        }
        print(f"{label:44s} trades={len(trades):4d} netR={net:+7.2f}")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
