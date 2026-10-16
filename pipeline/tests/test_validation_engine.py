"""Round 3 validation engine tests."""

from __future__ import annotations

import datetime

from src.validation.calendar import add_trading_days


def test_add_trading_days_skips_weekend() -> None:
    fri = datetime.date(2026, 5, 1)
    assert add_trading_days(fri, 1) == datetime.date(2026, 5, 4)


def test_add_trading_days_t5_over_weekend() -> None:
    fri = datetime.date(2026, 5, 1)
    assert add_trading_days(fri, 5) == datetime.date(2026, 5, 8)
