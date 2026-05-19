"""Accuracy comparison report: old (pre-M.1) vs new (post-M.3) composite logic.

Usage::

    python -m src.diagnostics.accuracy_report --pair EURUSD --start 2024-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import logging
import statistics
from datetime import date
from pathlib import Path
from typing import Any

from src.backfill.simulation_engine import (
    _load_all_yields,
    simulate_all_days,
    simulate_all_days_v2,
)
from src.diagnostics.permutation_importance import run_permutation_importance
from src.types import RegimeCall, normalize_fx_pair_key
from src.validation.engine import is_correct, log_return_bps, realized_direction

logger = logging.getLogger(__name__)


def _accuracy_and_brier(
    results: list[tuple[Any, RegimeCall]],
    spots: dict[date, float],
    horizon: int = 5,
) -> dict[str, Any]:
    """Compute T+{horizon} accuracy and Brier score from simulation results."""
    correct = 0
    total = 0
    briers: list[float] = []
    composites: list[float] = []
    transitions = 0
    prior_regime: str | None = None

    sorted_dates = sorted(spots.keys())
    date_to_idx = {d: i for i, d in enumerate(sorted_dates)}

    for _signal_row, call in results:
        as_of = call.date
        if as_of not in date_to_idx:
            continue
        idx = date_to_idx[as_of]
        if idx + horizon >= len(sorted_dates):
            continue
        t_date = sorted_dates[idx + horizon]
        s0 = spots.get(as_of)
        sh = spots.get(t_date)
        if s0 is None or sh is None or s0 <= 0 or sh <= 0:
            continue

        predicted = str(call.predicted_direction or "NEUTRAL")
        if predicted == "NEUTRAL":
            continue

        bps = log_return_bps(s0, sh)
        realized = realized_direction(bps)
        ok = is_correct(predicted, realized)
        if ok:
            correct += 1
        total += 1

        # Brier using calibrated confidence
        confidence = float(call.confidence or 0.0)
        briers.append((confidence - (1.0 if ok else 0.0)) ** 2)
        composites.append(float(call.signal_composite or 0.0))

        if prior_regime is not None and call.regime != prior_regime:
            transitions += 1
        prior_regime = call.regime

    if total == 0:
        return {
            "accuracy": 0.0,
            "brier": None,
            "dispersion": 0.0,
            "transitions": 0,
            "n": 0,
        }

    return {
        "accuracy": correct / total,
        "brier": statistics.mean(briers) if briers else None,
        "dispersion": statistics.stdev(composites) if len(composites) > 1 else 0.0,
        "transitions": transitions,
        "n": total,
    }


def _load_spots_for_range(pair: str, start: date, end: date) -> dict[date, float]:
    """Load spot closes from DB for the pair over the range."""
    from src.backfill.simulation_engine import _pg_conn

    conn = _pg_conn()
    result = conn.run(
        "SELECT date, close FROM historical_prices WHERE pair = :pair "
        "AND date >= :start AND date <= :end ORDER BY date",
        pair=pair,
        start=start.isoformat(),
        end=end.isoformat(),
    )
    conn.close()
    out: dict[date, float] = {}
    for r in result:
        d = r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])[:10])
        out[d] = float(r[1]) if r[1] is not None else 0.0
    return out


def compare_old_vs_new(
    pair: str,
    start: date,
    end: date,
) -> dict[str, Any]:
    """Run old (pre-M.1) and new (post-M.3) composite logic on same data."""
    pair = normalize_fx_pair_key(pair) or pair
    yields_by_series = _load_all_yields()
    spots = _load_spots_for_range(pair, start, end)

    logger.info("Running v1 simulation for %s", pair)
    v1_results = simulate_all_days(pair, start, end, yields_by_series)
    logger.info("Running v2 simulation for %s", pair)
    v2_results = simulate_all_days_v2(pair, start, end, yields_by_series)

    v1_t5 = _accuracy_and_brier(v1_results, spots, horizon=5)
    v1_t20 = _accuracy_and_brier(v1_results, spots, horizon=20)
    v2_t5 = _accuracy_and_brier(v2_results, spots, horizon=5)
    v2_t20 = _accuracy_and_brier(v2_results, spots, horizon=20)

    logger.info("Running permutation importance for %s", pair)
    perm = run_permutation_importance(pair, lookback_days=252, n_shuffle=5)

    return {
        "pair": pair,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "v1": {"t5": v1_t5, "t20": v1_t20},
        "v2": {"t5": v2_t5, "t20": v2_t20},
        "permutation": perm,
    }


def _verdict(delta: float) -> str:
    if delta > 0.03:
        return "CRITICAL"
    if delta > 0.015:
        return "HIGH"
    if delta > 0.005:
        return "MEDIUM"
    if delta > -0.005:
        return "LOW"
    return "NOISE"


def generate_markdown(report: dict[str, Any]) -> str:
    pair = report["pair"]
    start = report["start"]
    end = report["end"]
    v1_t5 = report["v1"]["t5"]
    v1_t20 = report["v1"]["t20"]
    v2_t5 = report["v2"]["t5"]
    v2_t20 = report["v2"]["t20"]
    perm = report["permutation"]

    lines: list[str] = [
        f"# Accuracy Comparison: {pair} ({start} to {end})",
        "",
        "## Baseline (Pre-M.1)",
        f"- T+5 accuracy: {v1_t5['accuracy']*100:.1f}% (n={v1_t5['n']})",
        f"- T+20 accuracy: {v1_t20['accuracy']*100:.1f}% (n={v1_t20['n']})",
        (
            f"- Brier score: {v1_t5['brier']:.3f}"
            if v1_t5['brier'] is not None
            else "- Brier score: N/A"
        ),
        f"- Composite dispersion: {v1_t5['dispersion']:.2f}",
        f"- Regime transitions: {v1_t5['transitions']}",
        "",
        "## Post-M.3",
        (
            f"- T+5 accuracy: {v2_t5['accuracy']*100:.1f}% "
            f"({_pp_diff(v2_t5['accuracy'], v1_t5['accuracy'])}"
        ),
        (
            f"- T+20 accuracy: {v2_t20['accuracy']*100:.1f}% "
            f"({_pp_diff(v2_t20['accuracy'], v1_t20['accuracy'])}"
        ),
        (
            f"- Brier score: {v2_t5['brier']:.3f} "
            f"({_pp_diff(v2_t5['brier'], v1_t5['brier'], invert=True)})"
            if v2_t5['brier'] is not None
            else "- Brier score: N/A"
        ),
        f"- Composite dispersion: {v2_t5['dispersion']:.2f}",
        f"- Regime transitions: {v2_t5['transitions']}",
        "",
        "## Permutation Importance",
        "| Family | Delta Accuracy | Verdict |",
        "|--------|---------------|---------|",
    ]

    families = perm.get("families", {})
    for family in ("rate", "special", "cot", "vol", "oi", "fpi"):
        if family in families:
            delta = families[family].get("delta", 0.0)
            lines.append(f"| {family} | {delta:+.3f} | {_verdict(delta)} |")

    lines.extend([
        "",
        "## Key Findings",
        "1. Fill in interpretation based on the numbers above.",
        "2. Positive delta = signal family is informative.",
        "3. Negative delta = signal family may add noise.",
    ])

    return "\n".join(lines)


def _pp_diff(new: float | None, old: float | None, invert: bool = False) -> str:
    if new is None or old is None:
        return "N/A"
    diff = new - old
    if invert:
        diff = -diff
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff*100:.1f} pp"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()

    report = compare_old_vs_new(
        args.pair,
        date.fromisoformat(args.start),
        date.fromisoformat(args.end),
    )

    md = generate_markdown(report)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        out_dir
        / f"accuracy_comparison_{report['pair']}_{report['start']}_{report['end']}.md"
    )
    out_path.write_text(md, encoding="utf-8")
    logger.info("Report saved to %s", out_path)


if __name__ == "__main__":
    main()
