"""Pure signal logic tests (no network, no env)."""

from __future__ import annotations

import datetime

import pytest

from src.regime.composite import compute_composite
from src.signals.cot import compute_cot_percentile, normalize_cot_signal
from src.signals.rate import compute_rate_signal, normalize_rate_signal
from src.signals.volatility import compute_vol_signal
from src.types import CotRow, RawYields


def make_date(n: int) -> datetime.date:
    return datetime.date(2026, 1, n + 1)


def test_rate_normalize_eurusd() -> None:
    history = [0.0, 1.0, 2.0]
    assert normalize_rate_signal(1.5, "EURUSD", history) == pytest.approx(0.31, abs=0.01)


def test_rate_normalize_clips() -> None:
    history = [0.0, 0.5, 1.0]
    assert normalize_rate_signal(10.0, "EURUSD", history) == 1.0
    assert normalize_rate_signal(-10.0, "EURUSD", history) == -1.0


def test_rate_signal_none_when_leg_missing() -> None:
    y = RawYields(date=make_date(0), us_2y=4.5, de_2y=None, jp_2y=None, in_2y=None)
    spread_2y, spread_10y, direction = compute_rate_signal(y, "EURUSD")
    assert spread_2y is None and spread_10y is None and direction == "NEUTRAL"


def test_cot_percentile_max() -> None:
    rows = [CotRow(make_date(i), "EURUSD", net_long=i * 100, open_interest=1000) for i in range(10)]
    assert compute_cot_percentile(rows, "EURUSD") == pytest.approx(100.0)


def test_cot_percentile_too_few_rows() -> None:
    rows = [CotRow(make_date(0), "EURUSD", net_long=100, open_interest=1000)]
    assert compute_cot_percentile(rows, "EURUSD") is None


def test_cot_normalize() -> None:
    assert normalize_cot_signal(75.0) == pytest.approx(0.5, abs=0.01)
    assert normalize_cot_signal(50.0) == pytest.approx(0.0, abs=0.01)


def test_vol_signal_expanding() -> None:
    assert compute_vol_signal(15.0, 8.0, 12.0) == 1.0


def test_vol_signal_stable() -> None:
    result = compute_vol_signal(8.0, 8.0, 12.0)
    assert -0.1 < result < 0.1


def test_composite_full() -> None:
    c = compute_composite(1.0, 1.0, 1.0, 0.0)
    assert c == pytest.approx(0.90, abs=0.01)


def test_composite_rate_none() -> None:
    c = compute_composite(None, 0.5, 0.0, 0.0)
    assert c == pytest.approx(0.15, abs=0.01)


def test_composite_both_none() -> None:
    assert compute_composite(None, None, 0.5, 0.0) is None
