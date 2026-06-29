"""Pair-specific macro field gating for SignalRow assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PairMacroFields:
    """Macro fields gated to the active pair."""

    ecb_balance_sheet: float | None = None
    bund_btp_spread: float | None = None
    boj_policy_rate: float | None = None
    india_vix: float | None = None
    inr_forward_premium: float | None = None


@runtime_checkable
class PairMacroGater(Protocol):
    """Select pair-specific macro fields from a macro dict."""

    def gate(self, pair: str, macro: dict[str, Any] | None) -> PairMacroFields: ...


class DefaultPairMacroGater:
    """Gate ECB/Bund-BTP for EURUSD, BoJ for USDJPY, India VIX/INR for USDINR."""

    def gate(self, pair: str, macro: dict[str, Any] | None) -> PairMacroFields:
        m = macro or {}
        if pair == "EURUSD":
            return PairMacroFields(
                ecb_balance_sheet=m.get("ecb_balance_sheet"),
                bund_btp_spread=m.get("bund_btp_spread"),
            )
        if pair == "USDJPY":
            return PairMacroFields(boj_policy_rate=m.get("boj_policy_rate"))
        if pair == "USDINR":
            return PairMacroFields(
                india_vix=m.get("india_vix"),
                inr_forward_premium=m.get("inr_forward_premium"),
            )
        return PairMacroFields()
