"""Shared mathematical utilities for pair-specific composite scoring and sizing.

Pure functions — no side effects, no DB writes.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt

# ---------------------------------------------------------------------------
# Feature interaction terms
# ---------------------------------------------------------------------------


def compute_interaction_terms(
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
    oi_norm: float | None,
    special_norm: float | None,
) -> dict[str, float]:
    """Compute feature interaction terms for composite scoring.

    Interactions capture non-linear synergies between signal families:
    - rate × cot: monetary policy amplified by positioning
    - vol × oi: volatility dynamics combined with flow
    - special × rate: cross-asset special factor interacting with rates
    """
    return {
        "rate_cot": (
            rate_norm * cot_norm * 0.15
            if all(v is not None for v in [rate_norm, cot_norm])
            else 0.0
        ),
        "vol_oi": (
            vol_norm * oi_norm * 0.10 if all(v is not None for v in [vol_norm, oi_norm]) else 0.0
        ),
        "special_rate": (
            special_norm * rate_norm * 0.10
            if all(v is not None for v in [special_norm, rate_norm])
            else 0.0
        ),
    }


# ---------------------------------------------------------------------------
# Regime-conditional weight adjustment
# ---------------------------------------------------------------------------

REGIME_MULTIPLIERS: dict[str, dict[str, float]] = {
    "HIGH_VOL": {
        "rate": 0.85,
        "cot": 0.85,
        "vol": 1.35,
        "oi": 0.85,
        "special": 0.85,
    },
    "TRENDING": {
        "rate": 1.25,
        "cot": 0.90,
        "vol": 0.90,
        "oi": 0.90,
        "special": 0.90,
    },
    "RANGING": {
        "rate": 0.90,
        "cot": 1.20,
        "vol": 0.90,
        "oi": 1.10,
        "special": 0.90,
    },
    "CARRY": {
        "rate": 1.20,
        "cot": 0.90,
        "vol": 0.85,
        "oi": 0.90,
        "special": 1.05,
    },
    "NEUTRAL": {
        "rate": 1.0,
        "cot": 1.0,
        "vol": 1.0,
        "oi": 1.0,
        "special": 1.0,
    },
}


def apply_regime_adjustment(
    base_weights: dict[str, float],
    vol_regime: str,
    rate_regime: str,
) -> dict[str, float]:
    """Adjust weights based on current market regime.

    Dominant regime is resolved via priority: HIGH_VOL > TRENDING > CARRY > RANGING > NEUTRAL.
    Weights are multiplied by regime factors and renormalized to preserve relative structure.
    """
    priority = ["HIGH_VOL", "TRENDING", "CARRY", "RANGING", "NEUTRAL"]
    regimes = [vol_regime.upper(), rate_regime.upper()]

    dominant = "NEUTRAL"
    for r in priority:
        if r in regimes:
            dominant = r
            break

    mult = REGIME_MULTIPLIERS.get(dominant, REGIME_MULTIPLIERS["NEUTRAL"])
    raw: dict[str, float] = {}
    for k, w in base_weights.items():
        raw[k] = w * mult.get(k, 1.0)

    total = math.fsum(raw.values())
    if total <= 0.0:
        return dict(base_weights)

    return {k: v / total for k, v in raw.items()}


# ---------------------------------------------------------------------------
# Kelly criterion sizing
# ---------------------------------------------------------------------------


def kelly_fraction(
    win_rate: float,
    avg_win_bps: float,
    avg_loss_bps: float,
    *,
    safety_factor: float = 0.25,
    max_risk: float = 0.01,
) -> float:
    """Compute Kelly criterion fraction with safety factor and max risk cap.

    Parameters
    ----------
    win_rate:
        Probability of a winning trade (0–1).
    avg_win_bps:
        Average win size in basis points.
    avg_loss_bps:
        Average loss size in basis points (positive number).
    safety_factor:
        Fractional Kelly multiplier (default ¼ Kelly).
    max_risk:
        Hard cap on returned fraction (default 1 %).

    Returns
    -------
    Position size as a fraction of capital (0 … max_risk).
    """
    if avg_loss_bps <= 0.0 or win_rate <= 0.0 or avg_win_bps <= 0.0:
        return 0.0
    b = avg_win_bps / avg_loss_bps  # odds
    q = 1.0 - win_rate
    kelly = (win_rate * b - q) / b
    return float(min(max(kelly * safety_factor, 0.0), max_risk))


# ---------------------------------------------------------------------------
# Pair-specific thresholds
# ---------------------------------------------------------------------------


def pair_specific_thresholds(pair: str) -> dict[str, Any]:
    """Return pair-specific regime and execution thresholds."""
    thresholds = {
        "EURUSD": {
            "hysteresis_tier4": 1.0,
            "hysteresis_tier3": 0.45,
            "hysteresis_tier2": -0.35,
            "hysteresis_tier1": -1.0,
            "vol_rank_enter_max": 0.85,
            "conviction_enter_min": 3,
            "adr_multiplier": 1.3,
            "mie_multiplier": 1.0,
        },
        "USDJPY": {
            "hysteresis_tier4": 1.0,
            "hysteresis_tier3": 0.40,
            "hysteresis_tier2": -0.40,
            "hysteresis_tier1": -1.0,
            "vol_rank_enter_max": 0.90,
            "conviction_enter_min": 3,
            "adr_multiplier": 1.5,
            "mie_multiplier": 1.2,
            "intervention_proximity_discount": True,
        },
        "USDINR": {
            "hysteresis_tier4": 1.0,
            "hysteresis_tier3": 0.50,
            "hysteresis_tier2": -0.30,
            "hysteresis_tier1": -1.0,
            "vol_rank_enter_max": 0.82,
            "conviction_enter_min": 4,
            "adr_multiplier": 1.2,
            "mie_multiplier": 1.0,
            "rbi_management_discount": True,
        },
    }
    key = pair.upper().replace("/", "")
    return thresholds.get(key, thresholds["EURUSD"])


# ---------------------------------------------------------------------------
# Correlation-adjusted sizing
# ---------------------------------------------------------------------------


def correlation_adjusted_size(
    base_size: float,
    pair: str,
    portfolio: dict[str, float],
    corr_matrix: dict[str, dict[str, float]],
) -> float:
    """Reduce position size if highly correlated with existing positions.

    Parameters
    ----------
    base_size:
        Unadjusted position size.
    pair:
        Target pair key.
    portfolio:
        Current positions keyed by pair.
    corr_matrix:
        Symmetric correlation matrix keyed by pair.

    Returns
    -------
    Adjusted position size (base_size × 0.7 if total corr exposure > 0.5,
    × 0.85 if > 0.3, else unchanged).
    """
    total_corr_exposure = 0.0
    target = pair.upper().replace("/", "")
    for other_pair, other_size in portfolio.items():
        other = other_pair.upper().replace("/", "")
        if other == target:
            continue
        inner = corr_matrix.get(target, {})
        corr = abs(inner.get(other, 0.0))
        total_corr_exposure += corr * other_size

    if total_corr_exposure > 0.5:
        return base_size * 0.7
    if total_corr_exposure > 0.3:
        return base_size * 0.85
    return base_size


# ---------------------------------------------------------------------------
# Expected value
# ---------------------------------------------------------------------------

_CONVICTION_MULTIPLIER: dict[int, float] = {
    1: 0.5,
    2: 0.7,
    3: 1.0,
    4: 1.2,
    5: 1.4,
}


def compute_expected_value(
    win_prob: float,
    avg_win_bps: float,
    avg_loss_bps: float,
    conviction: int,
    regime: str,
) -> float:
    """Compute expected value in bps for a trade.

    EV = win_prob × avg_win − loss_prob × avg_loss, scaled by conviction.
    The ``regime`` parameter is reserved for future regime-conditional EV
    adjustments and is currently unused.
    """
    _ = regime  # reserved for future regime-conditional adjustments
    loss_prob = 1.0 - win_prob
    gross_ev = win_prob * avg_win_bps - loss_prob * avg_loss_bps
    mult = _CONVICTION_MULTIPLIER.get(conviction, 1.0)
    return gross_ev * mult


# ---------------------------------------------------------------------------
# Vectorized helpers
# ---------------------------------------------------------------------------


def clip_composite(score: float | npt.NDArray[np.float64]) -> float | npt.NDArray[np.float64]:
    """Clip composite score to the canonical [-2, 2] interval."""
    return np.clip(score, -2.0, 2.0)


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Renormalize a weight dictionary so values sum to 1.0.

    Missing or zero-sum weights return the input unchanged.
    """
    total = math.fsum(weights.values())
    if total <= 0.0:
        return dict(weights)
    return {k: v / total for k, v in weights.items()}
