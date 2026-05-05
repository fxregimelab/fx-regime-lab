"""Pure deterministic pipeline logic (math + regime gate)."""

from src.logic.layer1_gate import regime_from_composite_snapshot, run_layer1_gate
from src.logic.layer2_directional import run_layer2_directional
from src.logic.layer3_execution import run_layer3_execution
from src.logic.math_utils import (
    hysteresis_tier_composite,
    log_return_series,
    momentum_last,
    rolling_zscore_last,
    rolling_zscore_series,
)

__all__ = [
    "hysteresis_tier_composite",
    "log_return_series",
    "momentum_last",
    "regime_from_composite_snapshot",
    "rolling_zscore_last",
    "rolling_zscore_series",
    "run_layer1_gate",
    "run_layer2_directional",
    "run_layer3_execution",
]
