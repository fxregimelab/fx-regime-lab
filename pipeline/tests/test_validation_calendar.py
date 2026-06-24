"""Tests for src/validation/calendar.py trading-day helpers."""

from __future__ import annotations

from datetime import date

import pytest

from src.validation.calendar import add_trading_days


class TestAddTradingDays:
    def test_zero_returns_same_day(self) -> None:
        start = date(2024, 6, 24)
        assert add_trading_days(start, 0) == start

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="n must be >= 0"):
            add_trading_days(date(2024, 6, 24), -1)

    def test_single_trading_day(self) -> None:
        start = date(2024, 6, 24)  # Monday
        assert add_trading_days(start, 1) == date(2024, 6, 25)

    def test_skips_weekend(self) -> None:
        start = date(2024, 6, 21)  # Friday
        assert add_trading_days(start, 1) == date(2024, 6, 24)  # Monday

    def test_longer_span_over_weekend(self) -> None:
        start = date(2024, 6, 21)  # Friday
        assert add_trading_days(start, 5) == date(2024, 6, 28)  # next Friday

    def test_multiple_weekends(self) -> None:
        start = date(2024, 6, 21)  # Friday
        assert add_trading_days(start, 10) == date(2024, 7, 5)  # 2 Fridays later

    def test_start_on_saturday(self) -> None:
        start = date(2024, 6, 22)  # Saturday
        assert add_trading_days(start, 1) == date(2024, 6, 24)  # Monday
