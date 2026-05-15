"""Tests for backfill integrity validation."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from src.fx_types import SpotBar
from src.validation.backfill_integrity import (
    check_historical_prices_integrity,
    validate_backfill_gaps,
)


def _make_bar(d: date, pair: str = "EURUSD", close: float = 1.0) -> SpotBar:
    return SpotBar(
        date=d,
        pair=pair,
        open=close,
        high=close,
        low=close,
        close=close,
    )


class TestValidateBackfillGaps:
    def test_no_gaps_consecutive_dates(self) -> None:
        bars = [
            _make_bar(date(2024, 1, 1)),
            _make_bar(date(2024, 1, 2)),
            _make_bar(date(2024, 1, 3)),
        ]
        is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=5)
        assert is_valid is True
        assert gaps == []

    def test_small_gap_within_threshold(self) -> None:
        bars = [
            _make_bar(date(2024, 1, 1)),
            _make_bar(date(2024, 1, 6)),  # 5-day delta, not > 5
        ]
        is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=5)
        assert is_valid is True
        assert gaps == []

    def test_large_gap_exceeding_threshold(self) -> None:
        bars = [
            _make_bar(date(2024, 1, 1)),
            _make_bar(date(2024, 1, 10)),  # 9-day delta > 5
        ]
        is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=5)
        assert is_valid is False
        assert gaps == [(date(2024, 1, 2), date(2024, 1, 9))]

    def test_empty_data(self) -> None:
        is_valid, gaps = validate_backfill_gaps([], max_gap_days=5)
        assert is_valid is True
        assert gaps == []

    def test_single_row(self) -> None:
        bars = [_make_bar(date(2024, 1, 1))]
        is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=5)
        assert is_valid is True
        assert gaps == []

    def test_unsorted_input_gets_sorted(self) -> None:
        bars = [
            _make_bar(date(2024, 1, 10)),
            _make_bar(date(2024, 1, 1)),
        ]
        is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=5)
        assert is_valid is False
        assert gaps == [(date(2024, 1, 2), date(2024, 1, 9))]

    def test_multiple_gaps(self) -> None:
        bars = [
            _make_bar(date(2024, 1, 1)),
            _make_bar(date(2024, 1, 10)),  # gap 1
            _make_bar(date(2024, 1, 12)),  # ok
            _make_bar(date(2024, 1, 25)),  # gap 2
        ]
        is_valid, gaps = validate_backfill_gaps(bars, max_gap_days=5)
        assert is_valid is False
        assert gaps == [
            (date(2024, 1, 2), date(2024, 1, 9)),
            (date(2024, 1, 13), date(2024, 1, 24)),
        ]


class TestCheckHistoricalPricesIntegrity:
    @patch("src.validation.backfill_integrity.writer.get_historical_prices")
    def test_valid_data(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [
            {
                "date": "2024-01-01",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 100,
            },
            {
                "date": "2024-01-02",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 100,
            },
        ]
        result = check_historical_prices_integrity("EURUSD", max_gap_days=5)
        assert result["pair"] == "EURUSD"
        assert result["total_rows"] == 2
        assert result["is_valid"] is True
        assert result["gaps"] == []
        assert result["date_range"] == ["2024-01-01", "2024-01-02"]

    @patch("src.validation.backfill_integrity.writer.get_historical_prices")
    def test_with_gap(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [
            {
                "date": "2024-01-01",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 100,
            },
            {
                "date": "2024-01-10",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 100,
            },
        ]
        result = check_historical_prices_integrity("EURUSD", max_gap_days=5)
        assert result["is_valid"] is False
        assert result["total_rows"] == 2
        assert result["gaps"] == [{"missing_start": "2024-01-02", "missing_end": "2024-01-09"}]

    @patch("src.validation.backfill_integrity.writer.get_historical_prices")
    def test_empty_data(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = []
        result = check_historical_prices_integrity("EURUSD", max_gap_days=5)
        assert result["pair"] == "EURUSD"
        assert result["total_rows"] == 0
        assert result["is_valid"] is True
        assert result["date_range"] == [None, None]
        assert result["gaps"] == []

    @patch("src.validation.backfill_integrity.writer.get_historical_prices")
    def test_date_objects(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [
            {
                "date": date(2024, 1, 1),
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 100,
            },
            {
                "date": date(2024, 1, 2),
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 100,
            },
        ]
        result = check_historical_prices_integrity("USDJPY", max_gap_days=5)
        assert result["is_valid"] is True
        assert result["date_range"] == ["2024-01-01", "2024-01-02"]
