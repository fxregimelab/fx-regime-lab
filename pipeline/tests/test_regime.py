"""Regime classifier and confidence tests."""

from __future__ import annotations

from src.regime.classifier import classify_regime
from src.regime.confidence import compute_confidence


def test_strong_strength() -> None:
    assert classify_regime(1.5, "EURUSD") == "RISK_OFF_DOLLAR_BID"


def test_moderate_strength() -> None:
    assert classify_regime(0.7, "EURUSD") == "GROWTH_SURPRISE_USD"


def test_neutral() -> None:
    assert classify_regime(0.0, "EURUSD") == "NEUTRAL"


def test_moderate_weakness() -> None:
    assert classify_regime(-0.7, "EURUSD") == "RISK_ON_DOLLAR_OFF"


def test_strong_weakness() -> None:
    assert classify_regime(-1.5, "EURUSD") == "RISK_ON_DOLLAR_OFF"


def test_inr_depreciation() -> None:
    assert classify_regime(0.8, "USDINR") == "INR_DEPRECIATION_MODERATE"


def test_inr_appreciation() -> None:
    assert classify_regime(-0.8, "USDINR") == "INR_APPRECIATION_MODERATE"


def test_neutral_vol_expanding() -> None:
    assert classify_regime(0.0, "EURUSD", vol_expanding=True) == "NEUTRAL__VOL_EXPANDING"


def test_non_neutral_vol_expanding_unchanged() -> None:
    assert classify_regime(1.5, "EURUSD", vol_expanding=True) == "RISK_OFF_DOLLAR_BID"


def test_confidence_midband() -> None:
    # composite=0.7 → base=0.35; rate/cot agree + both >0.3 → +0.10
    # raw=0.45; haircut → 0.42
    c = compute_confidence(0.7, 0.6, 0.5)
    assert 0.40 < c < 0.50


def test_confidence_minimum() -> None:
    # composite=0.4 → base=0.20; rate/cot agree but weak → +0.05
    # raw=0.25 → clipped to floor 0.30; haircut → 0.27 → clipped to 0.30
    c = compute_confidence(0.4, 0.1, 0.1)
    assert c >= 0.30
