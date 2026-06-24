"""Tests for src/signals/open_interest.py OI normalization."""

from __future__ import annotations

import pytest

from src.signals.open_interest import compute_oi_signal


class TestComputeOiSignal:
    def test_none_returns_none(self) -> None:
        assert compute_oi_signal(None) is None

    def test_median_returns_zero(self) -> None:
        assert compute_oi_signal(50.0) == pytest.approx(0.0)

    def test_high_oi_is_bearish(self) -> None:
        assert compute_oi_signal(100.0) == pytest.approx(-1.0)
        assert compute_oi_signal(80.0) == pytest.approx(-0.6)

    def test_low_oi_is_bullish(self) -> None:
        assert compute_oi_signal(0.0) == pytest.approx(1.0)
        assert compute_oi_signal(20.0) == pytest.approx(0.6)

    def test_clamped_to_bounds(self) -> None:
        assert compute_oi_signal(150.0) == pytest.approx(-1.0)
        assert compute_oi_signal(-50.0) == pytest.approx(1.0)
