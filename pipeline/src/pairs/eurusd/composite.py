"""EURUSD enhanced composite scoring with feature interactions and regime adjustment.

Special signal components:
    - ECB balance sheet trajectory
    - Bund-BTP spread
    - EU HY OAS
"""

from __future__ import annotations

import numpy as np

from src.pairs.math_core import (
    apply_regime_adjustment,
    clip_composite,
    compute_interaction_terms,
)

_BASE_WEIGHTS: dict[str, float] = {
    "rate": 0.45,
    "cot": 0.20,
    "vol": 0.15,
    "oi": 0.10,
    "special": 0.10,
}

_INTERACTION_KEYS = ("rate_cot", "special_rate")


def _compute_eurusd_special(
    ecb_bs_trajectory: float | None,
    bund_btp_spread: float | None,
    eu_hy_oas: float | None,
) -> float | None:
    """Aggregate EURUSD special signal from cross-asset components.

    Each component is expected to be pre-normalised (e.g. Z-scored).  The
    special signal is the simple average of available components.
    """
    components: list[float] = []
    if ecb_bs_trajectory is not None:
        components.append(float(ecb_bs_trajectory))
    if bund_btp_spread is not None:
        components.append(float(bund_btp_spread))
    if eu_hy_oas is not None:
        components.append(float(eu_hy_oas))
    if not components:
        return None
    return float(np.mean(components))


class EURUSDComposite:
    """EURUSD composite scorer.

    Weights: rate=0.45, cot=0.20, vol=0.15, oi=0.10, special=0.10
    Feature interactions: rate×cot, special×rate
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
        ecb_bs_trajectory: float | None = None,
        bund_btp_spread: float | None = None,
        eu_hy_oas: float | None = None,
    ) -> float | None:
        """Compute EURUSD composite score.

        Returns ``None`` when no signal legs are available.
        """
        special = _compute_eurusd_special(ecb_bs_trajectory, bund_btp_spread, eu_hy_oas)

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

        # Base weighted sum
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

        # Add interaction terms (scaled by active weight mass so they don't
        # dominate when legs are missing)
        interaction_boost = 0.0
        for ik in _INTERACTION_KEYS:
            interaction_boost += interactions.get(ik, 0.0)

        composite = acc + interaction_boost * (wsum / 1.0)
        return float(clip_composite(composite))
