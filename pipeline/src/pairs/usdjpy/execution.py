"""USDJPY execution sizing: intervention-aware stops and pair-specific ADR.

- Intervention-aware stops (wider near intervention levels)
- Pair-specific ADR multiplier (1.5× for USDJPY)
- Kelly-optimal sizing with safety factor
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from src.fx_types import Layer2DirectionalBias, SpotBar
from src.pairs.math_core import (
    correlation_adjusted_size,
    kelly_fraction,
    pair_specific_thresholds,
)
from src.pairs.usdjpy.regime import (
    BojInterventionRegime,
    detect_boj_intervention_regime,
)

_ADR_MIE_LOOKBACK = 20
_ATR_LOOKBACK = 14
_MAX_RISK_DEFAULT = 0.01
_SAFETY_FACTOR_DEFAULT = 0.25

# Intervention-level widening multipliers
_INTERVENTION_BUF_MULT_ACTIVE = 1.4
_INTERVENTION_BUF_MULT_PROXIMAL = 1.2


def _atr_from_bars(bars: Sequence[SpotBar], lookback: int) -> float | None:
    """Average True Range (Wilder-style) from SpotBar sequence."""
    if len(bars) < 2:
        return None
    n = min(lookback, len(bars))
    recent = bars[-n:]
    trs: list[float] = []
    for i in range(1, len(recent)):
        prev = recent[i - 1]
        curr = recent[i]
        tr1 = float(curr.high) - float(curr.low)
        tr2 = abs(float(curr.high) - float(prev.close))
        tr3 = abs(float(curr.low) - float(prev.close))
        trs.append(max(tr1, tr2, tr3))
    if not trs:
        return None
    return float(np.mean(trs))


def average_daily_range(
    spot_bars: Sequence[SpotBar],
    lookback: int = _ADR_MIE_LOOKBACK,
) -> float | None:
    """Mean daily high-low range."""
    if not spot_bars:
        return None
    n = min(lookback, len(spot_bars))
    recent = spot_bars[-n:]
    ranges = [max(0.0, float(b.high) - float(b.low)) for b in recent]
    if not ranges:
        return None
    return math.fsum(ranges) / len(ranges)


def mie_proxy_points(
    spot_bars: Sequence[SpotBar],
    bias: Layer2DirectionalBias,
    lookback: int = _ADR_MIE_LOOKBACK,
) -> float | None:
    """Maximum intraday excursion against directional bias from the open."""
    if not spot_bars:
        return None
    n = min(lookback, len(spot_bars))
    recent = spot_bars[-n:]
    adverse: list[float] = []
    for b in recent:
        o, hi, lo = float(b.open), float(b.high), float(b.low)
        if bias == "LONG":
            adverse.append(max(0.0, o - lo))
        elif bias == "SHORT":
            adverse.append(max(0.0, hi - o))
        else:
            adverse.append(max(max(0.0, o - lo), max(0.0, hi - o)))
    return max(adverse) if adverse else None


def compute_kelly_size(
    win_rate: float,
    avg_win_bps: float,
    avg_loss_bps: float,
    *,
    safety_factor: float = _SAFETY_FACTOR_DEFAULT,
    max_risk: float = _MAX_RISK_DEFAULT,
) -> float:
    """Kelly-optimal position size as fraction of capital."""
    return kelly_fraction(
        win_rate,
        avg_win_bps,
        avg_loss_bps,
        safety_factor=safety_factor,
        max_risk=max_risk,
    )


def _intervention_buffer_multiplier(boj_regime: BojInterventionRegime) -> float:
    if boj_regime == "ACTIVE":
        return _INTERVENTION_BUF_MULT_ACTIVE
    if boj_regime == "PROXIMAL":
        return _INTERVENTION_BUF_MULT_PROXIMAL
    return 1.0


def compute_stop_level(
    spot: float | None,
    bias: Layer2DirectionalBias,
    adr: float | None,
    mie: float | None,
    atr: float | None,
    boj_regime: BojInterventionRegime = "DORMANT",
    *,
    adr_multiplier: float = 1.5,
    mie_multiplier: float = 1.2,
) -> tuple[float | None, float | None]:
    """Return (stop_buffer, stop_price) for USDJPY.

    Buffer = max(adr_multiplier × ADR, mie_multiplier × MIE, 1.0 × ATR).
    Near intervention levels the buffer is widened to avoid being stopped
    out by BoJ-driven volatility.
    """
    if spot is None or bias == "NEUTRAL":
        return None, None

    parts: list[float] = []
    if adr is not None and adr > 0.0:
        parts.append(adr_multiplier * adr)
    if mie is not None and mie > 0.0:
        parts.append(mie_multiplier * mie)
    if atr is not None and atr > 0.0:
        parts.append(atr)

    if not parts:
        return None, None

    buf = max(parts) * _intervention_buffer_multiplier(boj_regime)
    s = float(spot)
    if bias == "LONG":
        return buf, s - buf
    return buf, s + buf


def compute_usdjpy_position_size(
    *,
    base_size: float,
    win_rate: float,
    avg_win_bps: float,
    avg_loss_bps: float,
    portfolio: dict[str, float],
    corr_matrix: dict[str, dict[str, float]],
    boj_regime: BojInterventionRegime = "DORMANT",
    safety_factor: float = _SAFETY_FACTOR_DEFAULT,
    max_risk: float = _MAX_RISK_DEFAULT,
) -> float:
    """Full USDJPY position sizing pipeline.

    1. Kelly fraction
    2. Intervention proximity discount (reduce size near intervention levels)
    3. Correlation adjustment vs existing positions
    """
    kelly = compute_kelly_size(
        win_rate,
        avg_win_bps,
        avg_loss_bps,
        safety_factor=safety_factor,
        max_risk=max_risk,
    )
    size = base_size * kelly

    # Intervention proximity discount
    if boj_regime == "ACTIVE":
        size *= 0.60
    elif boj_regime == "PROXIMAL":
        size *= 0.80

    size = correlation_adjusted_size(size, "USDJPY", portfolio, corr_matrix)
    return size


def get_usdjpy_execution_params(
    spot: float | None,
    bias: Layer2DirectionalBias,
    spot_bars: Sequence[SpotBar],
    last_intervention_high: float | None = None,
    last_intervention_low: float | None = None,
    days_since_last_intervention: int | None = None,
) -> dict[str, float | None]:
    """Convenience bundle: ADR, MIE, ATR, stop levels, and BoJ regime for USDJPY."""
    thresholds = pair_specific_thresholds("USDJPY")
    adr_mult = float(thresholds.get("adr_multiplier", 1.5))
    mie_mult = float(thresholds.get("mie_multiplier", 1.2))

    boj_regime = detect_boj_intervention_regime(
        spot, last_intervention_high, last_intervention_low, days_since_last_intervention
    )

    adr = average_daily_range(spot_bars, _ADR_MIE_LOOKBACK)
    mie = mie_proxy_points(spot_bars, bias, _ADR_MIE_LOOKBACK)
    atr = _atr_from_bars(spot_bars, _ATR_LOOKBACK)
    buf, stop_px = compute_stop_level(
        spot,
        bias,
        adr,
        mie,
        atr,
        boj_regime=boj_regime,
        adr_multiplier=adr_mult,
        mie_multiplier=mie_mult,
    )

    return {
        "adr": adr,
        "mie_proxy": mie,
        "atr": atr,
        "stop_buffer": buf,
        "stop_level": stop_px,
        "adr_multiplier": adr_mult,
        "mie_multiplier": mie_mult,
        "boj_regime": boj_regime,
    }
