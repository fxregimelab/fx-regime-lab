"""Tests for Round 4 — Historical backfill infrastructure."""

from __future__ import annotations

from datetime import date

from src.backfill.historical_fetcher import fetch_historical_spot_yfinance
from src.backfill.orchestrator import _daterange


def test_daterange_basic() -> None:
    dr = _daterange(date(2024, 1, 1), date(2024, 1, 3))
    assert dr == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]


def test_daterange_single_day() -> None:
    dr = _daterange(date(2024, 6, 15), date(2024, 6, 15))
    assert dr == [date(2024, 6, 15)]


def test_fetch_historical_spot_missing_ticker() -> None:
    # When universe has no ticker for a fake pair, returns empty
    bars = fetch_historical_spot_yfinance("FAKEPAIR", date(2024, 1, 1), date(2024, 1, 5))
    assert bars == []
