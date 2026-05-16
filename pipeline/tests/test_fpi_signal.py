"""Tests for FPI signal normalization (no network, no env)."""

from __future__ import annotations

import pytest

from src.signals.fpi import normalize_fpi_signal


def test_normalize_fpi_signal_basic() -> None:
    history = [1000.0] * 19 + [2000.0]
    z = normalize_fpi_signal(latest_flow=2500.0, history=history)
    assert z is not None
    assert z > 0.0
    assert z <= 1.0


def test_normalize_fpi_signal_short_history() -> None:
    """Less than 10 historical points → None."""
    history = [1000.0] * 5
    assert normalize_fpi_signal(latest_flow=2000.0, history=history) is None


def test_normalize_fpi_signal_none_flow() -> None:
    assert normalize_fpi_signal(latest_flow=None, history=[1000.0] * 20) is None


def test_normalize_fpi_signal_clips() -> None:
    history = [0.0] * 19 + [1.0]
    z_hi = normalize_fpi_signal(latest_flow=100.0, history=history)
    z_lo = normalize_fpi_signal(latest_flow=-100.0, history=history)
    assert z_hi == pytest.approx(1.0)
    assert z_lo == pytest.approx(-1.0)
