"""Layer 1 regime labels, UI metadata, and adapter to the deterministic gate engine."""

from __future__ import annotations

from dataclasses import dataclass

from src.logic.layer1_gate import (
    VOL_EXPANDING_SUFFIX_LOCAL,
    regime_from_composite_snapshot,
    run_layer1_gate,
)
from src.types import Layer1ClassifierContext, Layer1GateOutput

VOL_EXPANDING_SUFFIX = VOL_EXPANDING_SUFFIX_LOCAL


@dataclass(frozen=True)
class RegimeMetadata:
    ui_color_key: str
    base_regime: str


REGIME_METADATA: dict[str, RegimeMetadata] = {
    "USD_POLICY_BREAKOUT": RegimeMetadata(ui_color_key="bullish", base_regime="USD_POLICY"),
    "CARRY_COLLAPSE": RegimeMetadata(ui_color_key="caution", base_regime="CARRY_STRESS"),
    "GROWTH_SURPRISE_USD": RegimeMetadata(ui_color_key="bullish", base_regime="USD_POLICY"),
    "LIQUIDITY_SHOCK": RegimeMetadata(ui_color_key="risk_off", base_regime="VOL_STRESS"),
    "RISK_OFF_DOLLAR_BID": RegimeMetadata(ui_color_key="bullish", base_regime="USD_STRENGTH"),
    "RISK_ON_DOLLAR_OFF": RegimeMetadata(ui_color_key="bearish", base_regime="USD_WEAKNESS"),
    "NEUTRAL": RegimeMetadata(ui_color_key="neutral", base_regime="NEUTRAL"),
    "INR_DEPRECIATION_STRONG": RegimeMetadata(ui_color_key="bullish", base_regime="USD_STRENGTH"),
    "INR_DEPRECIATION_MODERATE": RegimeMetadata(ui_color_key="bullish", base_regime="USD_STRENGTH"),
    "INR_NEUTRAL": RegimeMetadata(ui_color_key="neutral", base_regime="NEUTRAL"),
    "INR_APPRECIATION_MODERATE": RegimeMetadata(ui_color_key="bearish", base_regime="USD_WEAKNESS"),
    "INR_APPRECIATION_STRONG": RegimeMetadata(ui_color_key="bearish", base_regime="USD_WEAKNESS"),
}


def _strip_gate_suffix(regime: str) -> str:
    return regime.split(VOL_EXPANDING_SUFFIX, maxsplit=1)[0]


def get_regime_metadata(regime: str) -> RegimeMetadata:
    """Resolve regime metadata while preserving base color under vol suffixes."""

    base = _strip_gate_suffix(regime)
    return REGIME_METADATA.get(
        base,
        RegimeMetadata(ui_color_key="neutral", base_regime="NEUTRAL"),
    )


def classify_regime_layer1(ctx: Layer1ClassifierContext) -> Layer1GateOutput:
    """Run the deterministic Layer 1 gate."""

    return run_layer1_gate(ctx)


def classify_regime(composite: float, pair: str, vol_expanding: bool = False) -> str:
    """Map composite magnitude to hysteresis-stable Layer 1 labels (no stochastic inputs).

    Prefer :func:`classify_regime_layer1` in orchestration paths with full histories;
    this snapshot ignores Marcus staleness and is regression-friendly for composite-only tests.
    """

    return regime_from_composite_snapshot(
        composite,
        pair,
        vol_expanding=vol_expanding,
        prior_regime_label=None,
    )
