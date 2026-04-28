"""Validation logic tests."""

from __future__ import annotations

import datetime

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


def test_strength_correct() -> None:
    spots = {"EURUSD": [make_bar("EURUSD", 0, 1.0700), make_bar("EURUSD", 1, 1.0721)]}
    result = validate_call(make_call("EURUSD", "USD_STRENGTH_STRONG"), spots)
    assert result["correct_1d"] is True


def test_weakness_incorrect() -> None:
    spots = {"EURUSD": [make_bar("EURUSD", 0, 1.0700), make_bar("EURUSD", 1, 1.0721)]}
    result = validate_call(make_call("EURUSD", "USD_WEAKNESS_STRONG"), spots)
    assert result["correct_1d"] is False


def test_neutral_correct_small_move() -> None:
    spots = {"EURUSD": [make_bar("EURUSD", 0, 1.0700), make_bar("EURUSD", 1, 1.0702)]}
    result = validate_call(make_call("EURUSD", "NEUTRAL"), spots)
    assert result["correct_1d"] is True


def test_inr_depreciation_correct() -> None:
    spots = {"USDINR": [make_bar("USDINR", 0, 83.80), make_bar("USDINR", 1, 83.94)]}
    result = validate_call(make_call("USDINR", "INR_DEPR_MODERATE"), spots)
    assert result["correct_1d"] is True


def test_neutral_dynamic_threshold_with_realized_vol() -> None:
    spots = {"EURUSD": [make_bar("EURUSD", 0, 1.0700), make_bar("EURUSD", 1, 1.0721)]}
    result = validate_call(make_call("EURUSD", "NEUTRAL"), spots, realized_vol_20d=10.0)
    assert result["correct_1d"] is True
