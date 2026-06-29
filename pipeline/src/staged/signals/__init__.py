"""Signal family adapters for the staged SignalStage registry runner."""

from src.staged.signals.cot_family import CotFamily
from src.staged.signals.protocol import SignalFamily
from src.staged.signals.rate_family import RateFamily
from src.staged.signals.rate_history import (
    RateHistoryProvider,
    SinglePointFallbackProvider,
    SnapshotRateHistoryProvider,
)
from src.staged.signals.special_family import SpecialFamily
from src.staged.signals.types import (
    CotFamilyOutput,
    FamilyOutput,
    RateFamilyOutput,
    SpecialFamilyOutput,
    VolFamilyOutput,
)
from src.staged.signals.vol_family import VolFamily

__all__ = [
    "CotFamily",
    "CotFamilyOutput",
    "FamilyOutput",
    "RateFamily",
    "RateFamilyOutput",
    "RateHistoryProvider",
    "SignalFamily",
    "SinglePointFallbackProvider",
    "SnapshotRateHistoryProvider",
    "SpecialFamily",
    "SpecialFamilyOutput",
    "VolFamily",
    "VolFamilyOutput",
]
