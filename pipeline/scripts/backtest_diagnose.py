"""Diagnose which gate blocks the funnel, with mutually exclusive stage counts.

Answers the owner's question "are the gates too strict?" without loosening
anything: for every H1 opportunity (bar x direction) it records only the FIRST
failing gate, so the stage counts add up to the number of opportunities instead
of double-counting inner detector loops.

Research only: local CSVs, no broker, no database.

Usage (from ``pipeline/``)::

    python scripts/backtest_diagnose.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import bisect  # noqa: E402

from src.paper.backtest.data import DEFAULT_DATA_DIR, PAIRS, load_pair  # noqa: E402
from src.paper.backtest.engine import (  # noqa: E402
    _M15_LOOKAHEAD,
    _M15_LOOKBACK,
    BacktestConfig,
    _h4_swings_at,
    context_at,
    d1_context_series,
)
from src.paper.features import Swing  # noqa: E402
from src.paper.strategies import (  # noqa: E402
    Rejection,
    detect_su1,
    detect_su2,
    detect_su3,
)

DETECTORS = (("SU1-v1", detect_su1), ("SU2-v1", detect_su2), ("SU3-v1", detect_su3))

# Order in which gates are evaluated inside each detector; used to bucket the
# first failure into a human-readable stage.
STAGE_OF_REASON = {
    "insufficient_bars": "input",
    "d1_context_mismatch": "1_d1_context",
    "structure_not_aligned": "2_h4_structure",
    "last_close_wrong_side_of_ema": "3a_setup_conditions",
    "no_ema_touch": "3a_setup_conditions",
    "pullback_closed_through_swing": "3a_setup_conditions",
    "trigger_close_not_beyond_prior_extreme": "3a_setup_conditions",
    "trigger_not_directional_body": "3a_setup_conditions",
    "trigger_range_too_wide": "3a_setup_conditions",
    "breakout_close_below_margin": "3a_setup_conditions",
    "sweep_not_beyond_pool_band": "3a_setup_conditions",
    "sweep_did_not_reclaim_pool": "3a_setup_conditions",
    "no_retest_within_window": "3b_m15_retest",
    "retest_made_new_low_beyond_sweep": "3b_m15_retest",
    "h1_close_through_zone": "3b_m15_retest",
    "no_next_m15_bar": "3c_entry_band",
    "entry_outside_band": "3c_entry_band",
    "session_closed": "4_session",
    "stop_below_atr_floor": "5_geometry",
    "cost_share_above_cap": "5_geometry",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Funnel diagnosis (read-only)")
    parser.add_argument("--pair", action="append", choices=PAIRS, default=None)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--out", type=Path, default=_ROOT.parent / "reports" / "desk" / "research" / "funnel.json"
    )
    args = parser.parse_args()

    pairs = tuple(args.pair) if args.pair else PAIRS
    cfg = BacktestConfig()
    payload: dict[str, object] = {"pairs": {}}

    for pair in pairs:
        frames = load_pair(pair, data_dir=args.data_dir)
        d1 = list(frames["d1"].bars)
        h4 = list(frames["h4"].bars)
        h1 = list(frames["h1"].bars)
        m15 = list(frames["m15"].bars)

        d1_series = d1_context_series(d1, period=cfg.d1_ema_period, slope_bars=cfg.d1_slope_bars)
        m15_times = [b.timestamp for b in m15]
        h4_times = [b.timestamp for b in h4]
        swing_cache: dict[int, list[Swing]] = {}
        m15_start = m15[0].timestamp

        context_counts: Counter[str] = Counter()
        stages: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        candidates: Counter[str] = Counter()

        for i in range(len(h1)):
            trigger = h1[i]
            if trigger.timestamp < m15_start:
                continue
            label = context_at(d1_series, trigger.timestamp)
            context_counts[label] += 1
            if label == "neutral":
                stages["1_d1_context"] += 2
                reasons["both:no_directional_context"] += 2
                continue

            swings = _h4_swings_at(h4, h4_times, trigger.timestamp, swing_cache)
            lo = bisect.bisect_right(m15_times, trigger.timestamp - _M15_LOOKBACK)
            hi = bisect.bisect_right(m15_times, trigger.timestamp + _M15_LOOKAHEAD)
            m15_window = m15[lo:hi]
            window = h1[max(0, i - 255) : i + 1]
            if len(window) < 60 or len(m15_window) < 32:
                stages["0_input"] += 1
                reasons["both:insufficient_window"] += 1
                continue
            last = len(window) - 1

            for setup_id, detector in DETECTORS:
                sink: list[Rejection] = []
                found = detector(
                    window,
                    swings,
                    m15_window,
                    pair=pair,
                    d1_context=label,
                    direction=label,
                    only_index=last,
                    rejections=sink,
                )
                if found:
                    candidates[setup_id] += len(found)
                    continue
                if not sink:
                    stages["unclassified"] += 1
                    reasons[f"{setup_id}:no_reason"] += 1
                    continue
                reason = sink[0].reason
                stages[STAGE_OF_REASON.get(reason, "unclassified")] += 1
                reasons[f"{setup_id}:{reason}"] += 1

        total_opps = sum(context_counts.values())
        print(f"\n=== {pair} ===")
        print(f"H1 opportunities (bar x single direction): {total_opps}")
        print("D1 context distribution:", dict(context_counts))
        print("first-failing stage (per setup evaluation):")
        for stage, count in sorted(stages.items()):
            print(f"  {stage:24s} {count:7d}  ({count / max(1, sum(stages.values())):.1%})")
        print("candidates:", dict(candidates))
        print("top reasons:")
        for reason, count in reasons.most_common(10):
            print(f"  {count:7d}  {reason}")
        payload["pairs"][pair] = {  # type: ignore[index]
            "opportunities": total_opps,
            "d1_context": dict(context_counts),
            "stages": dict(stages),
            "reasons": dict(reasons),
            "candidates": dict(candidates),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
