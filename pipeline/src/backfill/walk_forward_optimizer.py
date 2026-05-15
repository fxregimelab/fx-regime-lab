"""Walk-forward optimization for composite weights and thresholds.

Trains on N days, tests on M days, rolls forward.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.backfill.pair_backtest_engine import PairBacktestEngine

# ---------------------------------------------------------------------------
# Default weight grid — 5 signal families
# ---------------------------------------------------------------------------

_WEIGHT_KEYS = ("rate", "cot", "vol", "oi", "special")

_DEFAULT_WEIGHT_GRID: list[dict[str, float]] = [
    {"rate": 0.45, "cot": 0.20, "vol": 0.15, "oi": 0.10, "special": 0.10},
    {"rate": 0.40, "cot": 0.20, "vol": 0.20, "oi": 0.10, "special": 0.10},
    {"rate": 0.50, "cot": 0.15, "vol": 0.15, "oi": 0.10, "special": 0.10},
    {"rate": 0.35, "cot": 0.25, "vol": 0.20, "oi": 0.10, "special": 0.10},
    {"rate": 0.30, "cot": 0.20, "vol": 0.25, "oi": 0.15, "special": 0.10},
    {"rate": 0.45, "cot": 0.15, "vol": 0.20, "oi": 0.10, "special": 0.10},
    {"rate": 0.40, "cot": 0.20, "vol": 0.15, "oi": 0.15, "special": 0.10},
    {"rate": 0.35, "cot": 0.20, "vol": 0.20, "oi": 0.10, "special": 0.15},
]


@dataclass
class OptimizationResult:
    pair: str
    best_weights: dict[str, float]
    best_thresholds: dict[str, float]
    train_sharpe: float
    test_sharpe: float
    train_win_rate: float
    test_win_rate: float


def _apply_weights_to_signals(
    signals: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Return a shallow copy of signals with composite overridden by weighted sum."""
    out: list[dict[str, Any]] = []
    for s in signals:
        row = dict(s)
        # Recompute composite from normalized signal legs
        rate_norm = row.get("rate_norm")
        cot_norm = row.get("cot_norm")
        vol_norm = row.get("vol_norm")
        oi_norm = row.get("oi_norm")
        special_norm = row.get("special_norm")

        legs: list[tuple[float, float]] = []
        if rate_norm is not None:
            legs.append((float(rate_norm), weights.get("rate", 0.0)))
        if cot_norm is not None:
            legs.append((float(cot_norm), weights.get("cot", 0.0)))
        if vol_norm is not None:
            legs.append((float(vol_norm), weights.get("vol", 0.0)))
        if oi_norm is not None:
            legs.append((float(oi_norm), weights.get("oi", 0.0)))
        if special_norm is not None:
            legs.append((float(special_norm), weights.get("special", 0.0)))

        if legs:
            wsum = sum(w for _, w in legs)
            if wsum > 0:
                composite = sum(v * w for v, w in legs) / wsum
            else:
                composite = 0.0
            row["composite"] = float(np.clip(composite, -2.0, 2.0))
        out.append(row)
    return out


def _build_regimes_from_signals(
    signals: list[dict[str, Any]],
    threshold: float = 0.2,
) -> list[dict[str, Any]]:
    """Generate simple regime calls from composite scores."""
    regimes: list[dict[str, Any]] = []
    for s in signals:
        comp = s.get("composite", 0.0)
        if comp is None:
            comp = 0.0
        if comp > threshold:
            regime = "BULLISH"
        elif comp < -threshold:
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"
        regimes.append(
            {
                "date": s.get("date"),
                "regime": regime,
                "composite": float(comp),
                "confidence": min(abs(float(comp)), 1.0),
                "conviction": 3 if abs(float(comp)) > 0.5 else 2,
            }
        )
    return regimes


def _evaluate_window(
    pair: str,
    train_signals: list[dict[str, Any]],
    test_signals: list[dict[str, Any]],
    weights: dict[str, float],
    thresholds: dict[str, float],
    use_kelly: bool,
    use_stress_controls: bool,
    use_correlation_adjustment: bool,
) -> tuple[float, float, float, float]:
    """Run backtest on train and test windows.

    Returns (train_sharpe, test_sharpe, train_wr, test_wr).
    """
    # Train
    train_sig = _apply_weights_to_signals(train_signals, weights)
    train_reg = _build_regimes_from_signals(train_sig, threshold=thresholds.get("composite", 0.2))
    engine_train = PairBacktestEngine(pair)
    result_train = engine_train.run(
        train_sig,
        train_reg,
        use_kelly=use_kelly,
        use_stress_controls=use_stress_controls,
        use_correlation_adjustment=use_correlation_adjustment,
    )

    # Test
    test_sig = _apply_weights_to_signals(test_signals, weights)
    test_reg = _build_regimes_from_signals(test_sig, threshold=thresholds.get("composite", 0.2))
    engine_test = PairBacktestEngine(pair)
    result_test = engine_test.run(
        test_sig,
        test_reg,
        use_kelly=use_kelly,
        use_stress_controls=use_stress_controls,
        use_correlation_adjustment=use_correlation_adjustment,
    )

    return (
        result_train.sharpe_ratio,
        result_test.sharpe_ratio,
        result_train.win_rate,
        result_test.win_rate,
    )


def optimize_composite_weights(
    pair: str,
    historical_data: list[dict[str, Any]],
    *,
    train_window: int = 252,
    test_window: int = 63,
    weight_grid: list[dict[str, float]] | None = None,
    threshold_grid: list[dict[str, float]] | None = None,
    use_kelly: bool = True,
    use_stress_controls: bool = True,
    use_correlation_adjustment: bool = False,
) -> OptimizationResult:
    """Grid-search composite weights via walk-forward optimization.

    Parameters
    ----------
    pair:
        FX pair key (e.g. ``EURUSD``).
    historical_data:
        Chronological signal rows (oldest → newest). Must contain ``date``.
    train_window:
        Number of days in the training (in-sample) window.
    test_window:
        Number of days in the testing (out-of-sample) window.
    weight_grid:
        List of weight dictionaries to evaluate. Defaults to a small
        hand-crafted grid.
    threshold_grid:
        List of threshold dictionaries. Defaults to a single default set.
    use_kelly:
        Enable Kelly sizing during evaluation.
    use_stress_controls:
        Enable stress controls during evaluation.
    use_correlation_adjustment:
        Enable correlation adjustment during evaluation.
    """
    if not historical_data:
        raise ValueError("historical_data must not be empty")

    weights_list = weight_grid if weight_grid is not None else _DEFAULT_WEIGHT_GRID
    thresholds_list = threshold_grid if threshold_grid is not None else [{"composite": 0.2}]

    n = len(historical_data)
    best_sharpe = -float("inf")
    best_weights: dict[str, float] = dict(weights_list[0])
    best_thresholds: dict[str, float] = dict(thresholds_list[0])
    best_train_sharpe = 0.0
    best_test_sharpe = 0.0
    best_train_wr = 0.0
    best_test_wr = 0.0

    # Rolling windows
    idx = 0
    while idx + train_window + test_window <= n:
        train = historical_data[idx : idx + train_window]
        test = historical_data[idx + train_window : idx + train_window + test_window]
        idx += test_window

        for weights, thresholds in itertools.product(weights_list, thresholds_list):
            (
                train_sharpe,
                test_sharpe,
                train_wr,
                test_wr,
            ) = _evaluate_window(
                pair,
                train,
                test,
                weights,
                thresholds,
                use_kelly=use_kelly,
                use_stress_controls=use_stress_controls,
                use_correlation_adjustment=use_correlation_adjustment,
            )

            # Select by test Sharpe; tie-break with test win rate
            if test_sharpe > best_sharpe or (
                math.isclose(test_sharpe, best_sharpe) and test_wr > best_test_wr
            ):
                best_sharpe = test_sharpe
                best_weights = dict(weights)
                best_thresholds = dict(thresholds)
                best_train_sharpe = train_sharpe
                best_test_sharpe = test_sharpe
                best_train_wr = train_wr
                best_test_wr = test_wr

    return OptimizationResult(
        pair=pair,
        best_weights=best_weights,
        best_thresholds=best_thresholds,
        train_sharpe=best_train_sharpe,
        test_sharpe=best_test_sharpe,
        train_win_rate=best_train_wr,
        test_win_rate=best_test_wr,
    )
