"""Regime classifier and confidence tests."""

from __future__ import annotations

from src.regime.classifier import classify_regime
from src.regime.confidence import compute_confidence


def test_strong_strength() -> None:
    assert classify_regime(1.5, "EURUSD") == "STRONG USD STRENGTH"


def test_moderate_strength() -> None:
    assert classify_regime(0.7, "EURUSD") == "MODERATE USD STRENGTH"


def test_neutral() -> None:
    assert classify_regime(0.0, "EURUSD") == "NEUTRAL"


def test_moderate_weakness() -> None:
    assert classify_regime(-0.7, "EURUSD") == "MODERATE USD WEAKNESS"


def test_strong_weakness() -> None:
    assert classify_regime(-1.5, "EURUSD") == "STRONG USD WEAKNESS"


def test_inr_depreciation() -> None:
    assert classify_regime(0.8, "USDINR") == "MODERATE DEPRECIATION PRESSURE"


def test_inr_appreciation() -> None:
    assert classify_regime(-0.8, "USDINR") == "MODERATE APPRECIATION PRESSURE"


def test_neutral_vol_expanding() -> None:
    assert classify_regime(0.0, "EURUSD", vol_expanding=True) == "NEUTRAL / VOL_EXPANDING"


def test_non_neutral_vol_expanding_unchanged() -> None:
    assert classify_regime(1.5, "EURUSD", vol_expanding=True) == "STRONG USD STRENGTH"


def test_confidence_midband() -> None:
    c = compute_confidence(0.7, 0.6, 0.5)
    assert 0.50 < c < 0.95


def test_confidence_minimum() -> None:
    c = compute_confidence(0.4, 0.1, 0.1)
    assert c >= 0.40
