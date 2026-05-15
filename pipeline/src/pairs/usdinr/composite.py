"""USDINR enhanced composite scoring with feature interactions and regime adjustment.

Special signal components:
    - RBI reserves trajectory
    - FPI flow
    - Oil price impulse
    - DXY strength
    - EM stress index
    - Forward premium
"""

from __future__ import annotations

import numpy as np

from src.pairs.math_core import (
    apply_regime_adjustment,
    clip_composite,
    compute_interaction_terms,
)

_BASE_WEIGHTS: dict[str, float] = {
    "rate": 0.25,
    "cot": 0.05,
    "vol": 0.15,
    "oi": 0.10,
    "special": 0.45,
}

_INTERACTION_KEYS = ("special_rate",)


def _compute_usdinr_special(
    rbi_reserves: float | None,
    fpi_flow: float | None,
    oil: float | None,
    dxy: float | None,
    em_stress: float | None,
    forward_premium: float | None,
) -> float | None:
    """Aggregate USDINR special signal from EM-specific components.

    Each component is expected to be pre-normalised (e.g. Z-scored).  The
    special signal is the simple average of available components.
    """
    components: list[float] = []
    if rbi_reserves is not None:
        components.append(float(rbi_reserves))
    if fpi_flow is not None:
        components.append(float(fpi_flow))
    if oil is not None:
        components.append(float(oil))
    if dxy is not None:
        components.append(float(dxy))
    if em_stress is not None:
        components.append(float(em_stress))
    if forward_premium is not None:
        components.append(float(forward_premium))
    if not components:
        return None
    return float(np.mean(components))


class USDINRComposite:
    """USDINR composite scorer.

    Weights: rate=0.25, cot=0.05, vol=0.15, oi=0.10, special=0.45
    Feature interactions: special×rate (RBI + rate differential)
    Output clipped to [-2, 2].
    """

    __slots__ = ("weights", "vol_regime", "rate_regime")

    def __init__(
        self,
        *,
        vol_regime: str = "NEUTRAL",
        rate_regime: str = "NEUTRAL",
    ) -> None:
        self.vol_regime = vol_regime
        self.rate_regime = rate_regime
        self.weights = apply_regime_adjustment(_BASE_WEIGHTS, vol_regime, rate_regime)

    def score(
        self,
        rate_norm: float | None,
        cot_norm: float | None,
        vol_norm: float | None,
        oi_norm: float | None,
        *,
        rbi_reserves: float | None = None,
        fpi_flow: float | None = None,
        oil: float | None = None,
        dxy: float | None = None,
        em_stress: float | None = None,
        forward_premium: float | None = None,
    ) -> float | None:
        """Compute USDINR composite score.

        Returns ``None`` when no signal legs are available.
        """
        special = _compute_usdinr_special(
            rbi_reserves, fpi_flow, oil, dxy, em_stress, forward_premium
        )

        values: dict[str, float | None] = {
            "rate": rate_norm,
            "cot": cot_norm,
            "vol": vol_norm,
            "oi": oi_norm,
            "special": special,
        }

        active = [k for k, v in values.items() if v is not None]
        if not active:
            return None

        interactions = compute_interaction_terms(rate_norm, cot_norm, vol_norm, oi_norm, special)

        acc = 0.0
        wsum = 0.0
        for k in active:
            v = values[k]
            if v is None:
                continue
            w = self.weights.get(k, 0.0)
            acc += float(v) * w
            wsum += w

        if wsum <= 0.0:
            return None

        interaction_boost = 0.0
        for ik in _INTERACTION_KEYS:
            interaction_boost += interactions.get(ik, 0.0)

        composite = acc + interaction_boost * (wsum / 1.0)
        return float(clip_composite(composite))
