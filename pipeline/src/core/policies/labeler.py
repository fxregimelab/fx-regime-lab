"""Signal label policies for regime call assembly."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SignalLabeler(Protocol):
    """Label normalized signal values as BULLISH / BEARISH / NEUTRAL."""

    def label_cot(self, cot_norm: float | None) -> str: ...

    def label_vol(self, vol_norm: float | None, *, vol_expanding: bool) -> str: ...

    def label_oi(self, oi_norm: float | None) -> str: ...

    def label_rr(self, risk_reversal_25d: float | None) -> str: ...

    def label_special(self, pair: str) -> str | None: ...


_THRESHOLD = 0.15


class DefaultSignalLabeler:
    """Default ±0.15 threshold labeling rules."""

    def label_cot(self, cot_norm: float | None) -> str:
        if cot_norm is not None and cot_norm > _THRESHOLD:
            return "BULLISH"
        if cot_norm is not None and cot_norm < -_THRESHOLD:
            return "BEARISH"
        return "NEUTRAL"

    def label_vol(self, vol_norm: float | None, *, vol_expanding: bool) -> str:
        if vol_expanding:
            return "VOL_EXPANDING"
        if vol_norm is not None and vol_norm > _THRESHOLD:
            return "BULLISH"
        if vol_norm is not None and vol_norm < -_THRESHOLD:
            return "BEARISH"
        return "NEUTRAL"

    def label_oi(self, oi_norm: float | None) -> str:
        if oi_norm is not None and oi_norm > _THRESHOLD:
            return "BULLISH"
        if oi_norm is not None and oi_norm < -_THRESHOLD:
            return "BEARISH"
        return "NEUTRAL"

    def label_rr(self, risk_reversal_25d: float | None) -> str:
        if risk_reversal_25d is not None and risk_reversal_25d > _THRESHOLD:
            return "BULLISH"
        if risk_reversal_25d is not None and risk_reversal_25d < -_THRESHOLD:
            return "BEARISH"
        return "NEUTRAL"

    def label_special(self, pair: str) -> str | None:
        return {
            "EURUSD": "Bund-BTP + ECB BS",
            "USDJPY": "VIX + JPY Funding Stress",
            "USDINR": "Oil + DXY + EM Risk",
        }.get(pair)
