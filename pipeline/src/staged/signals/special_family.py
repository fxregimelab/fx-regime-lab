"""Pair-specific special signal family adapter."""

from __future__ import annotations

from typing import Any

from src.signals.special import compute_special_signal
from src.staged.contracts import IngestionSnapshot
from src.staged.signals.types import FamilyOutput, SpecialFamilyOutput


class SpecialFamily:
    """Compute pair-specific macro / cross-asset special signal."""

    def compute(self, pair: str, snapshot: IngestionSnapshot) -> FamilyOutput:
        cross_for_special: dict[str, Any] = dict(snapshot.cross_asset)
        macro = snapshot.macro or {}
        special_signal = compute_special_signal(
            pair,
            cross_for_special,
            bund_btp_spread=macro.get("bund_btp_spread"),
            ecb_balance_sheet=macro.get("ecb_balance_sheet"),
        )

        return FamilyOutput(
            rate=None,
            cot=None,
            vol=None,
            special=SpecialFamilyOutput(signal=special_signal),
        )
