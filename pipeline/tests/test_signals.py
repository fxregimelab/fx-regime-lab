"""Pure signal logic tests (no network, no env)."""

from __future__ import annotations

import datetime

import pytest

from src.regime.composite import compute_composite
from src.signals.cot import compute_cot_percentile, normalize_cot_signal
from src.signals.rate import (
    build_real_yield_10y_spread_history_from_rows,
    compute_risk_adjusted_carry,
    normalize_rate_signal,
    rate_direction_from_spreads,
)
from src.signals.volatility import compute_vol_signal
from src.types import CotRow


def make_date(n: int) -> datetime.date:
    return datetime.date(2026, 1, n + 1)


def test_rate_normalize_eurusd() -> None:
    history = [0.0, 1.0, 2.0]
    z = normalize_rate_signal(1.5, "EURUSD", history)
    assert z.z_tactical == pytest.approx(0.17, abs=0.01)
    assert z.z_structural == pytest.approx(0.17, abs=0.01)


def test_rate_normalize_clips() -> None:
    history = [0.0, 0.5, 1.0]
    z_hi = normalize_rate_signal(10.0, "EURUSD", history)
    z_lo = normalize_rate_signal(-10.0, "EURUSD", history)
    assert z_hi.z_tactical == pytest.approx(1.0)
    assert z_hi.z_structural == pytest.approx(1.0)
    assert z_lo.z_tactical == pytest.approx(-1.0)
    assert z_lo.z_structural == pytest.approx(-1.0)


def test_rate_normalize_noise_floor_zero() -> None:
    """Identical history → MAD below floor → Z = 0."""
    history = [1.0] * 30
    z = normalize_rate_signal(2.0, "EURUSD", history)
    assert z.z_tactical == pytest.approx(0.0)
    assert z.z_structural == pytest.approx(0.0)


def test_rate_normalize_empty_history_none() -> None:
    z = normalize_rate_signal(1.0, "EURUSD", [])
    assert z.z_tactical is None and z.z_structural is None


def test_real_yield_history_from_rows() -> None:
    rows = [
        {"date": "2026-01-01", "rate_diff_10y": 2.0, "breakeven_inflation_10y": 2.5},
        {"date": "2026-01-02", "rate_diff_10y": 1.0, "breakeven_inflation_10y": 2.5},
    ]
    hist = build_real_yield_10y_spread_history_from_rows(rows, max_points=1260)
    assert hist == pytest.approx([-0.5, -1.5])


def test_normalize_structural_uses_real_spread_series() -> None:
    carry_hist = [0.0, 1.0, 2.0, 3.0, 4.0]
    real_hist = [-1.0, 0.0, 1.0, 2.0, 3.0]
    z = normalize_rate_signal(
        1.5,
        "EURUSD",
        carry_hist,
        spread_structural=0.0,
        historical_structural=real_hist,
    )
    assert z.z_tactical is not None
    assert z.z_structural is not None


def test_rate_direction_neutral_when_spreads_missing() -> None:
    assert rate_direction_from_spreads(None, None) == "NEUTRAL"


def test_rate_direction_from_2y() -> None:
    assert rate_direction_from_spreads(1.0, None) == "BULLISH"
    assert rate_direction_from_spreads(-1.0, None) == "BEARISH"
    assert rate_direction_from_spreads(0.0, None) == "NEUTRAL"


def test_risk_adjusted_carry() -> None:
    assert compute_risk_adjusted_carry(1.0, 10.0, "EURUSD") == pytest.approx(0.1, abs=1e-9)
    assert compute_risk_adjusted_carry(1.0, 0.0, "EURUSD") is None


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
    assert c == pytest.approx(0.25, abs=0.01)


def test_composite_both_none_reweights() -> None:
    c = compute_composite(None, None, 0.5, 0.0)
    assert c == pytest.approx(1.0 / 3.0, abs=0.01)


def test_composite_all_none() -> None:
    assert compute_composite(None, None, None, None) is None
