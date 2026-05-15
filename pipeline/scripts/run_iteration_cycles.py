#!/usr/bin/env python3
"""Run iteration cycles 1-3 for pair-specific pipeline optimization.

Compares OLD (legacy v2) vs NEW (pair-specific v3) composite models,
iteratively adjusts v3 weights based on backtest signal-family attribution,
and outputs a JSON report plus Markdown summary.

Usage:
    python scripts/run_iteration_cycles.py
    python scripts/run_iteration_cycles.py --synthetic --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# Ensure pipeline/src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.pairs.eurusd.composite import EURUSDComposite
from src.pairs.usdinr.composite import USDINRComposite
from src.pairs.usdjpy.composite import USDJPYComposite
from src.regime.composite import compute_composite

logger = logging.getLogger(__name__)

_ALLOWED_PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")

_ITERATION_ADJUSTMENTS: dict[str, float] = {
    "underperforming_weight_penalty": 0.05,
    "overperforming_weight_bonus": 0.03,
    "min_weight": 0.05,
    "max_weight": 0.60,
}

# Pair-specific default v3 base weights (aligned with composite modules)
_PAIR_BASE_WEIGHTS: dict[str, dict[str, float]] = {
    "EURUSD": {"rate": 0.45, "cot": 0.20, "vol": 0.15, "oi": 0.10, "special": 0.10},
    "USDJPY": {"rate": 0.30, "cot": 0.20, "vol": 0.25, "oi": 0.10, "special": 0.15},
    "USDINR": {"rate": 0.25, "cot": 0.05, "vol": 0.15, "oi": 0.10, "special": 0.45},
}

# Legacy v2 universal weights
_LEGACY_WEIGHTS: dict[str, float] = {"rate": 0.40, "cot": 0.30, "vol": 0.20, "oi": 0.10}

_RANDOM_SEED = 42
np.random.seed(_RANDOM_SEED)

_TRANSACTION_COST_BPS = 1.0
_INITIAL_CAPITAL = 100_000.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BacktestMetrics:
    pair: str
    model: str
    iteration: int
    total_days: int
    total_trades: int
    win_rate: float
    sharpe_ratio: float | None
    max_drawdown_pct: float | None
    mean_brier: float | None
    total_pnl: float
    accuracy_t1: float | None
    weights: dict[str, float] | None = None
    family_accuracy: dict[str, float] | None = None


@dataclass
class SignalFamilyAccuracy:
    family: str
    correct: int
    total: int
    accuracy_pct: float


# ---------------------------------------------------------------------------
# Synthetic data generator
# ---------------------------------------------------------------------------


def generate_synthetic_signals(n_days: int = 252) -> list[dict[str, Any]]:
    """Generate realistic synthetic FX signals for backtesting."""
    np.random.seed(_RANDOM_SEED)

    # Generate correlated signals
    rate = np.random.randn(n_days) * 0.5
    cot = np.random.randn(n_days) * 0.3 + rate * 0.4
    vol = np.random.randn(n_days) * 0.4 - rate * 0.2
    oi = np.random.randn(n_days) * 0.2
    special = np.random.randn(n_days) * 0.3 + rate * 0.3

    # Generate spot prices with regime persistence
    spot = 100.0
    spots: list[float] = []
    for i in range(n_days):
        composite = (
            0.4 * rate[i]
            + 0.25 * cot[i]
            + 0.15 * vol[i]
            + 0.10 * oi[i]
            + 0.10 * special[i]
        )
        spot *= 1.0 + composite * 0.001 + np.random.randn() * 0.003
        spots.append(spot)

    signals: list[dict[str, Any]] = []
    base_date = date(2025, 1, 1)
    for i in range(n_days):
        signals.append(
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "rate_norm": float(rate[i]),
                "cot_norm": float(cot[i]),
                "vol_norm": float(vol[i]),
                "oi_norm": float(oi[i]),
                "special_norm": float(special[i]),
                "spot": float(spots[i]),
                "composite": float(
                    0.4 * rate[i]
                    + 0.25 * cot[i]
                    + 0.15 * vol[i]
                    + 0.10 * oi[i]
                    + 0.10 * special[i]
                ),
            }
        )
    return signals


# ---------------------------------------------------------------------------
# DB loader (with synthetic fallback)
# ---------------------------------------------------------------------------


def _try_load_db_signals(pair: str) -> list[dict[str, Any]] | None:
    """Attempt to load historical signals from Supabase."""
    try:
        from src.db import writer

        raw_rows = writer.get_historical_signals(pair, limit=5000)
        if not raw_rows:
            return None

        signals: list[dict[str, Any]] = []
        for r in raw_rows:
            d = str(r.get("date", ""))[:10]
            spot = r.get("spot")
            if spot is None:
                continue

            rate_diff = r.get("rate_diff_2y")
            cot_pct = r.get("cot_percentile")
            rv20 = r.get("realized_vol_20d")
            rv5 = r.get("realized_vol_5d")
            oi = r.get("oi_delta")

            rate_norm = None
            if rate_diff is not None and rv20 is not None and rv20 > 0:
                rate_norm = rate_diff / rv20

            cot_norm = None
            if cot_pct is not None:
                cot_norm = (cot_pct - 50.0) / 50.0

            vol_norm = None
            if rv5 is not None and rv20 is not None and rv20 > 0:
                vol_norm = ((rv5 / rv20) - 1.0) * 2.0

            oi_norm = None
            if oi is not None:
                oi_norm = float(oi)

            signals.append(
                {
                    "date": d,
                    "spot": float(spot),
                    "rate_norm": rate_norm,
                    "cot_norm": cot_norm,
                    "vol_norm": vol_norm,
                    "oi_norm": oi_norm,
                    "special_norm": None,
                    "rate_diff_2y": rate_diff,
                    "cot_percentile": cot_pct,
                    "realized_vol_20d": rv20,
                    "realized_vol_5d": rv5,
                    "oi_delta": oi,
                }
            )
        signals.sort(key=lambda x: x["date"])
        return signals if len(signals) >= 30 else None
    except Exception as exc:
        logger.warning("DB load failed for %s: %s", pair, exc)
        return None


def load_signals(pair: str, *, force_synthetic: bool = False) -> list[dict[str, Any]]:
    """Load historical signals; fall back to synthetic data on failure."""
    if not force_synthetic:
        db_signals = _try_load_db_signals(pair)
        if db_signals is not None:
            logger.info("Loaded %s DB signals for %s", len(db_signals), pair)
            return db_signals

    logger.info("Using synthetic data for %s", pair)
    synthetic = generate_synthetic_signals(n_days=252)
    # Tag with pair for downstream use
    for s in synthetic:
        s["pair"] = pair
    return synthetic


# ---------------------------------------------------------------------------
# Composite computation
# ---------------------------------------------------------------------------


def _compute_legacy_composite(row: dict[str, Any], pair: str) -> float | None:
    """Reconstruct v2 (legacy) composite from signal row."""
    rate_norm = row.get("rate_norm")
    cot_norm = row.get("cot_norm")
    vol_norm = row.get("vol_norm")
    oi_norm = row.get("oi_norm")
    return compute_composite(
        rate_norm, cot_norm, vol_norm, oi_norm,
        pair=pair, special_signal=None,
    )


def _compute_new_composite(
    row: dict[str, Any],
    pair: str,
    weights: dict[str, float] | None = None,
) -> float | None:
    """Reconstruct v3 (pair-specific) composite from signal row."""
    rate_norm = row.get("rate_norm")
    cot_norm = row.get("cot_norm")
    vol_norm = row.get("vol_norm")
    oi_norm = row.get("oi_norm")

    if pair == "EURUSD":
        comp = EURUSDComposite()
        return comp.score(rate_norm, cot_norm, vol_norm, oi_norm)
    if pair == "USDJPY":
        comp = USDJPYComposite()
        return comp.score(rate_norm, cot_norm, vol_norm, oi_norm)
    if pair == "USDINR":
        comp = USDINRComposite()
        return comp.score(rate_norm, cot_norm, vol_norm, oi_norm)
    return None


def _compute_new_composite_with_weights(
    row: dict[str, Any],
    pair: str,
    weights: dict[str, float],
) -> float | None:
    """Compute v3 composite using explicit custom weights (no regime adjustment)."""
    rate_norm = row.get("rate_norm")
    cot_norm = row.get("cot_norm")
    vol_norm = row.get("vol_norm")
    oi_norm = row.get("oi_norm")
    special_norm = row.get("special_norm")

    values: dict[str, float | None] = {
        "rate": rate_norm,
        "cot": cot_norm,
        "vol": vol_norm,
        "oi": oi_norm,
        "special": special_norm,
    }

    active = [k for k, v in values.items() if v is not None]
    if not active:
        return None

    acc = 0.0
    wsum = 0.0
    for k in active:
        v = values[k]
        if v is None:
            continue
        w = weights.get(k, 0.0)
        acc += float(v) * w
        wsum += w

    if wsum <= 0.0:
        return None

    # Normalize by active weight mass if some legs are missing
    composite = acc / wsum if wsum < 1.0 else acc
    return float(np.clip(composite, -2.0, 2.0))


# ---------------------------------------------------------------------------
# Backtest engine (simplified)
# ---------------------------------------------------------------------------


def _predicted_direction(composite: float | None, threshold: float = 0.2) -> str:
    if composite is None:
        return "NEUTRAL"
    if composite > threshold:
        return "BULLISH"
    if composite < -threshold:
        return "BEARISH"
    return "NEUTRAL"


def _realized_direction(bps: float, deadband: float = 5.0) -> str:
    if bps > deadband:
        return "UP"
    if bps < -deadband:
        return "DOWN"
    return "NEUTRAL"


def _is_correct(predicted: str, realized: str) -> bool:
    p = predicted.strip().upper()
    r = realized.strip().upper()
    if p == "BULLISH":
        return r == "UP"
    if p == "BEARISH":
        return r == "DOWN"
    if p == "NEUTRAL":
        return r == "NEUTRAL"
    return False


def _brier_score(confidence: float, correct: bool) -> float:
    p = float(np.clip(confidence, 0.0, 1.0))
    y = 1.0 if correct else 0.0
    return (p - y) ** 2


def _log_return_bps(s0: float, s1: float) -> float:
    if s0 <= 0 or s1 <= 0:
        return 0.0
    return 10_000.0 * math.log(s1 / s0)


def _simulate_pnl(
    composites: list[float | None],
    spots: list[float | None],
    holding_days: int = 1,
) -> tuple[list[float], int]:
    pnls: list[float] = []
    trades = 0
    n = len(composites)
    for i in range(n - holding_days):
        comp = composites[i]
        s0 = spots[i]
        s1 = spots[i + holding_days]
        if comp is None or s0 is None or s1 is None or s0 <= 0:
            pnls.append(0.0)
            continue
        size = min(abs(comp), 1.0) * _INITIAL_CAPITAL
        direction = 1.0 if comp > 0 else -1.0 if comp < 0 else 0.0
        if direction == 0.0:
            pnls.append(0.0)
            continue
        gross_return = (s1 / s0 - 1.0) * direction
        tc = _TRANSACTION_COST_BPS / 10_000.0
        net_return = gross_return - tc
        pnl = size * net_return
        pnls.append(pnl)
        trades += 1
    for _ in range(holding_days):
        pnls.append(0.0)
    return pnls, trades


def _compute_sharpe(pnls: list[float]) -> float | None:
    arr = np.array([x for x in pnls if x != 0.0], dtype=float)
    if len(arr) < 2:
        return None
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std <= 0:
        return None
    return (mean / std) * math.sqrt(252.0)


def _compute_max_drawdown(pnls: list[float]) -> float | None:
    cumulative = np.cumsum([x for x in pnls], dtype=float)
    if len(cumulative) == 0:
        return None
    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    if peak == 0:
        return None
    return (max_dd / abs(peak)) * 100.0


def run_backtest(
    signals: list[dict[str, Any]],
    pair: str,
    model: str,
    iteration: int,
    weights: dict[str, float] | None = None,
) -> BacktestMetrics:
    """Run a simple backtest and return metrics."""
    composites: list[float | None] = []
    spots: list[float | None] = []
    predictions: list[str] = []
    realized: list[str | None] = []

    for idx, row in enumerate(signals):
        spot = row.get("spot")
        spots.append(spot)

        if model == "legacy":
            comp = _compute_legacy_composite(row, pair)
        elif weights is not None:
            comp = _compute_new_composite_with_weights(row, pair, weights)
        else:
            comp = _compute_new_composite(row, pair)
        composites.append(comp)

        pred = _predicted_direction(comp)
        predictions.append(pred)

        # T+1 realized direction
        if idx + 1 < len(signals):
            s0 = spot
            s1 = signals[idx + 1].get("spot")
            if s0 is not None and s1 is not None and s0 > 0:
                bps = _log_return_bps(s0, s1)
                realized.append(_realized_direction(bps))
            else:
                realized.append(None)
        else:
            realized.append(None)

    pnls, trades = _simulate_pnl(composites, spots, holding_days=1)

    correct_count = 0
    total_pred = 0
    briers: list[float] = []
    family_correct: dict[str, int] = {"rate": 0, "cot": 0, "vol": 0, "oi": 0, "special": 0}
    family_total: dict[str, int] = {"rate": 0, "cot": 0, "vol": 0, "oi": 0, "special": 0}

    for i in range(len(signals)):
        pred = predictions[i]
        real = realized[i]
        if real is None or pred == "NEUTRAL":
            continue

        is_corr = _is_correct(pred, real)
        correct_count += 1 if is_corr else 0
        total_pred += 1

        conf = min(abs(composites[i] or 0.0), 1.0)
        briers.append(_brier_score(conf, is_corr))

        # Attribute to dominant signal family
        row = signals[i]
        strengths: dict[str, float] = {}
        for fam in ("rate", "cot", "vol", "oi", "special"):
            v = row.get(f"{fam}_norm")
            if v is not None:
                strengths[fam] = abs(float(v))
        if strengths:
            dominant = max(strengths, key=lambda k: strengths[k])
            family_correct[dominant] += 1 if is_corr else 0
            family_total[dominant] += 1

    win_rate = (correct_count / total_pred * 100.0) if total_pred > 0 else 0.0
    sharpe = _compute_sharpe(pnls)
    mdd = _compute_max_drawdown(pnls)
    mean_brier = sum(briers) / len(briers) if briers else None
    total_pnl = sum(pnls)

    # Signal-family accuracy map
    family_accuracy: dict[str, float] = {}
    for fam in family_total:
        if family_total[fam] > 0:
            family_accuracy[fam] = family_correct[fam] / family_total[fam] * 100.0
        else:
            family_accuracy[fam] = 50.0  # neutral default

    return BacktestMetrics(
        pair=pair,
        model=model,
        iteration=iteration,
        total_days=len(signals),
        total_trades=trades,
        win_rate=win_rate,
        sharpe_ratio=sharpe,
        max_drawdown_pct=mdd,
        mean_brier=mean_brier,
        total_pnl=total_pnl,
        accuracy_t1=win_rate,
        weights=dict(weights) if weights else None,
        family_accuracy=family_accuracy,
    )


# ---------------------------------------------------------------------------
# Weight iteration logic
# ---------------------------------------------------------------------------


def iterate_weights(
    base_weights: dict[str, float],
    backtest_result: BacktestMetrics,
) -> dict[str, float]:
    """Adjust weights based on which signal family contributed most to wins/losses."""
    family_accuracy: dict[str, float] = getattr(
        backtest_result, "family_accuracy", {}
    ) or {}

    new_weights = dict(base_weights)
    min_w = _ITERATION_ADJUSTMENTS["min_weight"]
    max_w = _ITERATION_ADJUSTMENTS["max_weight"]
    penalty = _ITERATION_ADJUSTMENTS["underperforming_weight_penalty"]
    bonus = _ITERATION_ADJUSTMENTS["overperforming_weight_bonus"]

    for family, acc in family_accuracy.items():
        if family not in new_weights:
            continue
        if acc < 50.0:
            new_weights[family] = max(min_w, new_weights[family] - penalty)
        elif acc > 60.0:
            new_weights[family] = min(max_w, new_weights[family] + bonus)

    # Renormalize to sum to 1.0
    total = math.fsum(new_weights.values())
    if total > 0.0:
        new_weights = {k: v / total for k, v in new_weights.items()}

    return new_weights


# ---------------------------------------------------------------------------
# Iteration cycle runner
# ---------------------------------------------------------------------------


def run_iteration_cycles(
    pair: str,
    signals: list[dict[str, Any]],
    n_cycles: int = 3,
) -> dict[str, Any]:
    """Run 3 iteration cycles for a single pair."""
    base_weights = dict(_PAIR_BASE_WEIGHTS[pair])

    # Baseline backtests
    legacy_result = run_backtest(signals, pair, "legacy", iteration=0)
    new_baseline = run_backtest(signals, pair, "new", iteration=0)

    cycles: list[dict[str, Any]] = []
    current_weights = dict(base_weights)
    best_result = new_baseline
    best_weights = dict(current_weights)

    for cycle in range(1, n_cycles + 1):
        result = run_backtest(
            signals, pair, "new", iteration=cycle, weights=current_weights
        )

        # Update best
        if (result.sharpe_ratio or 0.0) > (best_result.sharpe_ratio or 0.0):
            best_result = result
            best_weights = dict(current_weights)

        cycles.append(
            {
                "cycle": cycle,
                "weights": dict(current_weights),
                "win_rate": result.win_rate,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
                "mean_brier": result.mean_brier,
                "total_pnl": result.total_pnl,
                "accuracy_t1": result.accuracy_t1,
                "family_accuracy": getattr(result, "family_accuracy", {}),
            }
        )

        # Iterate weights for next cycle
        current_weights = iterate_weights(current_weights, result)
        logger.info(
            "%s cycle %d complete: Sharpe=%s WinRate=%.1f%%",
            pair, cycle, result.sharpe_ratio, result.win_rate,
        )

    return {
        "pair": pair,
        "legacy": {
            "win_rate": legacy_result.win_rate,
            "sharpe_ratio": legacy_result.sharpe_ratio,
            "max_drawdown_pct": legacy_result.max_drawdown_pct,
            "mean_brier": legacy_result.mean_brier,
            "total_pnl": legacy_result.total_pnl,
            "accuracy_t1": legacy_result.accuracy_t1,
        },
        "new_baseline": {
            "win_rate": new_baseline.win_rate,
            "sharpe_ratio": new_baseline.sharpe_ratio,
            "max_drawdown_pct": new_baseline.max_drawdown_pct,
            "mean_brier": new_baseline.mean_brier,
            "total_pnl": new_baseline.total_pnl,
            "accuracy_t1": new_baseline.accuracy_t1,
        },
        "cycles": cycles,
        "best_weights": best_weights,
        "best_sharpe": best_result.sharpe_ratio,
        "best_win_rate": best_result.win_rate,
        "best_total_pnl": best_result.total_pnl,
        "improvement": {
            "sharpe_delta": (best_result.sharpe_ratio or 0.0)
            - (legacy_result.sharpe_ratio or 0.0),
            "win_rate_delta": best_result.win_rate - legacy_result.win_rate,
            "pnl_delta": best_result.total_pnl - legacy_result.total_pnl,
        },
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _build_json_report(all_results: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(),
        "pairs": all_results,
        "summary": {
            "total_pairs": len(all_results),
            "pairs_improved_sharpe": sum(
                1
                for r in all_results.values()
                if r.get("improvement", {}).get("sharpe_delta", 0.0) > 0
            ),
            "pairs_improved_win_rate": sum(
                1
                for r in all_results.values()
                if r.get("improvement", {}).get("win_rate_delta", 0.0) > 0
            ),
        },
    }


def _build_markdown_report(all_results: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Iteration Cycles 1-3 Results",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Overview",
        "",
        "This report documents the results of 3 iteration cycles "
        "optimizing pair-specific composite weights.",
        "Each cycle adjusts weights based on signal-family attribution "
        "from the previous backtest.",
        "",
        "## Methodology",
        "",
        "1. **Baseline:** Run legacy v2 and new v3 models on historical (or synthetic) data.",
        "2. **Iteration:** For each cycle, adjust weights:",
        "   - Reduce weight by 5% if signal-family accuracy < 50%",
        "   - Increase weight by 3% if signal-family accuracy > 60%",
        "   - Renormalize weights to sum to 1.0",
        "3. **Selection:** Choose the best-performing weight set by Sharpe ratio.",
        "",
        "---",
        "",
    ]

    for pair in _ALLOWED_PAIRS:
        result = all_results.get(pair)
        if result is None:
            continue

        lines.extend(
            [
                f"## {pair}",
                "",
                "### Legacy (v2) Baseline",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Win Rate | {result['legacy']['win_rate']:.2f}% |",
                f"| Sharpe | {result['legacy']['sharpe_ratio'] or 'N/A'} |",
                f"| Max DD | {result['legacy']['max_drawdown_pct'] or 'N/A'}% |",
                f"| Mean Brier | {result['legacy']['mean_brier'] or 'N/A'} |",
                f"| Total P&L | ${result['legacy']['total_pnl']:,.2f} |",
                "",
                "### New (v3) Baseline",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Win Rate | {result['new_baseline']['win_rate']:.2f}% |",
                f"| Sharpe | {result['new_baseline']['sharpe_ratio'] or 'N/A'} |",
                f"| Max DD | {result['new_baseline']['max_drawdown_pct'] or 'N/A'}% |",
                f"| Mean Brier | {result['new_baseline']['mean_brier'] or 'N/A'} |",
                f"| Total P&L | ${result['new_baseline']['total_pnl']:,.2f} |",
                "",
                "### Iteration Cycles",
                "",
            ]
        )

        for cycle in result["cycles"]:
            lines.extend(
                [
                    f"#### Cycle {cycle['cycle']}",
                    "",
                    f"**Weights:** {json.dumps(cycle['weights'])}",
                    "",
                    "| Metric | Value |",
                    "|--------|-------|",
                    f"| Win Rate | {cycle['win_rate']:.2f}% |",
                    f"| Sharpe | {cycle['sharpe_ratio'] or 'N/A'} |",
                    f"| Max DD | {cycle['max_drawdown_pct'] or 'N/A'}% |",
                    f"| Mean Brier | {cycle['mean_brier'] or 'N/A'} |",
                    f"| Total P&L | ${cycle['total_pnl']:,.2f} |",
                    "",
                ]
            )

        lines.extend(
            [
                "### Best Weights Selected",
                "",
                f"```json\n{json.dumps(result['best_weights'], indent=2)}\n```",
                "",
                f"**Best Sharpe:** {result['best_sharpe'] or 'N/A'}",
                f"**Best Win Rate:** {result['best_win_rate']:.2f}%",
                "",
                "### Improvement vs Legacy",
                "",
                "| Metric | Delta |",
                "|--------|-------|",
                f"| Sharpe | {result['improvement']['sharpe_delta']:+.4f} |",
                f"| Win Rate | {result['improvement']['win_rate_delta']:+.2f}% |",
                f"| Total P&L | ${result['improvement']['pnl_delta']:+.2f} |",
                "",
                "---",
                "",
            ]
        )

    # Global summary
    summary = _build_json_report(all_results)["summary"]
    lines.extend(
        [
            "## Global Summary",
            "",
            f"- **Pairs tested:** {summary['total_pairs']}",
            f"- **Sharpe improved:** {summary['pairs_improved_sharpe']}"
            f"/{summary['total_pairs']}",
            f"- **Win-rate improved:** {summary['pairs_improved_win_rate']}"
            f"/{summary['total_pairs']}",
            "",
            "## Conclusion",
            "",
            "The iteration cycles demonstrate the sensitivity of "
            "pair-specific composite performance to weight allocation. "
            "Recommended next steps:",
            "",
            "1. Validate best weights on a hold-out test set.",
            "2. Implement regime-conditional weight overlays.",
            "3. Add cross-validation across multiple time windows.",
            "",
        ]
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run iteration cycles 1-3 for pair-specific pipeline optimization"
    )
    parser.add_argument(
        "--pair",
        choices=[*_ALLOWED_PAIRS, "ALL"],
        default="ALL",
        help="Pair to optimize (default: ALL)",
    )
    parser.add_argument(
        "--synthetic", action="store_true", help="Force synthetic data"
    )
    parser.add_argument(
        "--n-days", type=int, default=252, help="Synthetic data length"
    )
    parser.add_argument(
        "--n-cycles", type=int, default=3, help="Number of iteration cycles"
    )
    parser.add_argument(
        "--output-json",
        default="reports/iteration_results.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--output-md",
        default="reports/ITERATION_1_3_RESULTS.md",
        help="Markdown output path",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    pairs = _ALLOWED_PAIRS if args.pair == "ALL" else (args.pair,)
    all_results: dict[str, Any] = {}

    for pair in pairs:
        logger.info("=" * 50)
        logger.info("Starting iteration cycles for %s", pair)
        logger.info("=" * 50)

        signals = load_signals(pair, force_synthetic=args.synthetic)
        if args.synthetic and args.n_days != 252:
            signals = generate_synthetic_signals(n_days=args.n_days)
            for s in signals:
                s["pair"] = pair

        result = run_iteration_cycles(pair, signals, n_cycles=args.n_cycles)
        all_results[pair] = result

        logger.info(
            "%s complete — best Sharpe: %s, best win rate: %.2f%%",
            pair, result["best_sharpe"], result["best_win_rate"],
        )

    # Write JSON
    json_report = _build_json_report(all_results)
    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(json_report, fh, indent=2, default=str)
    logger.info("JSON report saved to %s", json_path)

    # Write Markdown
    md_report = _build_markdown_report(all_results)
    md_path = Path(args.output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(md_report)
    logger.info("Markdown report saved to %s", md_path)

    print("\nIteration cycles complete. Reports saved to:")
    print(f"  JSON: {json_path.resolve()}")
    print(f"  MD:   {md_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
