"""Map composite score to normalized regime labels and UI metadata."""

from __future__ import annotations

from dataclasses import dataclass

VOL_EXPANDING_SUFFIX = "__VOL_EXPANDING"


@dataclass(frozen=True)
class RegimeMetadata:
    ui_color_key: str
    base_regime: str


REGIME_METADATA: dict[str, RegimeMetadata] = {
    "USD_STRENGTH_STRONG": RegimeMetadata(ui_color_key="bullish", base_regime="USD_STRENGTH"),
    "USD_STRENGTH_MODERATE": RegimeMetadata(
        ui_color_key="bullish", base_regime="USD_STRENGTH"
    ),
    "USD_WEAKNESS_MODERATE": RegimeMetadata(
        ui_color_key="bearish", base_regime="USD_WEAKNESS"
    ),
    "USD_WEAKNESS_STRONG": RegimeMetadata(ui_color_key="bearish", base_regime="USD_WEAKNESS"),
    "NEUTRAL": RegimeMetadata(ui_color_key="neutral", base_regime="NEUTRAL"),
    "INR_DEPR_STRONG": RegimeMetadata(
        ui_color_key="bullish", base_regime="USD_STRENGTH"
    ),
    "INR_DEPR_MODERATE": RegimeMetadata(
        ui_color_key="bullish", base_regime="USD_STRENGTH"
    ),
    "INR_APPR_MODERATE": RegimeMetadata(
        ui_color_key="bearish", base_regime="USD_WEAKNESS"
    ),
    "INR_APPR_STRONG": RegimeMetadata(
        ui_color_key="bearish", base_regime="USD_WEAKNESS"
    ),
}


def get_regime_metadata(regime: str) -> RegimeMetadata:
    """Resolve regime metadata while preserving base color under vol suffixes."""
    base = regime.split(VOL_EXPANDING_SUFFIX, maxsplit=1)[0]
    return REGIME_METADATA.get(base, RegimeMetadata(ui_color_key="neutral", base_regime="NEUTRAL"))


def classify_regime(composite: float, pair: str, vol_expanding: bool = False) -> str:
    """Return stable regime keys consumed by database clients and UI maps."""
    if pair == "USDINR":
        if composite > 1.0:
            regime = "INR_DEPR_STRONG"
        elif composite > 0.4:
            regime = "INR_DEPR_MODERATE"
        elif composite >= -0.4:
            regime = "NEUTRAL"
        elif composite >= -1.0:
            regime = "INR_APPR_MODERATE"
        else:
            regime = "INR_APPR_STRONG"
    else:
        if composite > 1.0:
            regime = "USD_STRENGTH_STRONG"
        elif composite > 0.4:
            regime = "USD_STRENGTH_MODERATE"
        elif composite >= -0.4:
            regime = "NEUTRAL"
        elif composite >= -1.0:
            regime = "USD_WEAKNESS_MODERATE"
        else:
            regime = "USD_WEAKNESS_STRONG"

    if vol_expanding and regime == "NEUTRAL":
        return f"{regime}{VOL_EXPANDING_SUFFIX}"
    return regime
