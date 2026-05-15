"""USDJPY enhanced composite scoring with feature interactions and regime adjustment.

Special signal components:
    - BoJ intervention proximity
    - JPY swap stress
    - VIX
"""

from __future__ import annotations

import numpy as np

from src.pairs.math_core import (
    apply_regime_adjustment,
    clip_composite,
    compute_interaction_terms,
)

_BASE_WEIGHTS: dict[str, float] = {
    "rate": 0.30,
    "cot": 0.20,
    "vol": 0.25,
    "oi": 0.10,
    "special": 0.15,
}

_INTERACTION_KEYS = ("special_rate",)


def _compute_usdjpy_special(
    boj_intervention_proximity: float | None,
    jpy_swap_stress: float | None,
    vix: float | None,
) -> float | None:
    """Aggregate USDJPY special signal from cross-asset components.

    Each component is expected to be pre-normalised (e.g. Z-scored).  The
    special signal is the simple average of available components.
    """
    components: list[float] = []
    if boj_intervention_proximity is not None:
        components.append(float(boj_intervention_proximity))
    if jpy_swap_stress is not None:
        components.append(float(jpy_swap_stress))
    if vix is not None:
        components.append(float(vix))
    if not components:
        return None
    return float(np.mean(components))


class USDJPYComposite:
    """USDJPY composite scorer.

    Weights: rate=0.30, cot=0.20, vol=0.25, oi=0.10, special=0.15
    Feature interactions: rate×special (carry + intervention risk)
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
        boj_intervention_proximity: float | None = None,
        jpy_swap_stress: float | None = None,
        vix: float | None = None,
    ) -> float | None:
        """Compute USDJPY composite score.

        Returns ``None`` when no signal legs are available.
        """
        special = _compute_usdjpy_special(boj_intervention_proximity, jpy_swap_stress, vix)

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
