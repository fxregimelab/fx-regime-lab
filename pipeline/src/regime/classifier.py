"""Map composite score to regime label."""

from __future__ import annotations


def classify_regime(composite: float, pair: str, vol_expanding: bool = False) -> str:
    if pair == "USDINR":
        if composite > 1.0:
            regime = "STRONG DEPRECIATION PRESSURE"
        elif composite > 0.4:
            regime = "MODERATE DEPRECIATION PRESSURE"
        elif composite >= -0.4:
            regime = "NEUTRAL"
        elif composite >= -1.0:
            regime = "MODERATE APPRECIATION PRESSURE"
        else:
            regime = "STRONG APPRECIATION PRESSURE"
    else:
        if composite > 1.0:
            regime = "STRONG USD STRENGTH"
        elif composite > 0.4:
            regime = "MODERATE USD STRENGTH"
        elif composite >= -0.4:
            regime = "NEUTRAL"
        elif composite >= -1.0:
            regime = "MODERATE USD WEAKNESS"
        else:
            regime = "STRONG USD WEAKNESS"

    if vol_expanding and regime == "NEUTRAL":
        return "NEUTRAL / VOL_EXPANDING"
    return regime
