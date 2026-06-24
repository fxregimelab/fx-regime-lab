"""Validation logic tests."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from src.types import RegimeCall, SpotBar
from src.validation.backtest import validate_call


def make_bar(pair: str, date_offset: int, close: float) -> SpotBar:
    d = datetime.date(2026, 4, 24 + date_offset)
    return SpotBar(date=d, pair=pair, open=close, high=close, low=close, close=close)


def make_call(pair: str, regime: str) -> RegimeCall:
    return RegimeCall(
        pair=pair,
        date=datetime.date(2026, 4, 24),
        regime=regime,
        confidence=0.75,
        signal_composite=1.0,
        rate_signal="BULLISH",
        primary_driver="Rate differential",
    )


def _spots(pair: str, closes: list[float]) -> dict[str, Sequence[SpotBar]]:
    return {pair: [make_bar(pair, i, c) for i, c in enumerate(closes)]}


def test_strength_correct() -> None:
    spots = _spots("EURUSD", [1.0700, 1.0721])
    result = validate_call(make_call("EURUSD", "USD_STRENGTH_STRONG"), spots)
    assert result["correct_1d"] is True


def test_weakness_incorrect() -> None:
    spots = _spots("EURUSD", [1.0700, 1.0721])
    result = validate_call(make_call("EURUSD", "USD_WEAKNESS_STRONG"), spots)
    assert result["correct_1d"] is False


def test_neutral_correct_small_move() -> None:
    spots = _spots("EURUSD", [1.0700, 1.0702])
    result = validate_call(make_call("EURUSD", "NEUTRAL"), spots)
    assert result["correct_1d"] is True


def test_inr_depreciation_correct() -> None:
    spots = _spots("USDINR", [83.80, 83.94])
    result = validate_call(make_call("USDINR", "INR_DEPR_MODERATE"), spots)
    assert result["correct_1d"] is True


def test_neutral_dynamic_threshold_with_realized_vol() -> None:
    spots = _spots("EURUSD", [1.0700, 1.0721])
    result = validate_call(make_call("EURUSD", "NEUTRAL"), spots, realized_vol_20d=10.0)
    assert result["correct_1d"] is True
