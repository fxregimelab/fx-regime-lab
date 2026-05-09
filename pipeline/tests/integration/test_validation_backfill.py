"""Integration test for P1-T1 validation backfill.

Inserts a synthetic regime_call with known dates, mocks historical_prices
for S0, S5, S20, runs backfill, and asserts correct validation_log values.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.backfill import validation_backfill as backfill
from src.db import writer


class TestValidationBackfill:
    @patch.object(writer, "get_historical_price_for_date")
    @patch.object(writer, "get_validation_log_entry")
    @patch.object(writer, "write_validation_row")
    def test_backfill_one_call(
        self,
        mock_write: MagicMock,
        mock_get_val: MagicMock,
        mock_get_price: MagicMock,
    ) -> None:
        """Backfill a single BULLISH call with known prices."""
        call_date = date(2024, 1, 2)  # Tuesday
        t5 = date(2024, 1, 9)  # +5 trading days
        t20 = date(2024, 1, 30)  # +20 trading days

        # S0 = 100.0, S5 = 102.0 (+1.98% ~ 198 bps), S20 = 105.0 (+4.88% ~ 488 bps)
        s0, s5, s20 = 100.0, 102.0, 105.0

        def _price_side(pair: str, date_str: str) -> dict[str, Any] | None:
            d = date.fromisoformat(date_str)
            if d == call_date:
                return {"date": call_date.isoformat(), "pair": pair, "close": s0}
            if d == t5:
                return {"date": t5.isoformat(), "pair": pair, "close": s5}
            if d == t20:
                return {"date": t20.isoformat(), "pair": pair, "close": s20}
            return None

        mock_get_price.side_effect = _price_side
        mock_get_val.return_value = None  # No existing validation

        call: dict[str, Any] = {
            "id": 9999,
            "date": call_date.isoformat(),
            "pair": "EURUSD",
            "regime": "CARRY_POSITIVE",
            "rate_signal": "BULLISH",
            "confidence": 0.80,
        }

        result = backfill.backfill_validation_for_call(
            call, dry_run=False, as_of_date=date(2024, 12, 31)
        )

        assert result is True
        mock_write.assert_called_once()
        payload = mock_write.call_args[0][0]

        # T+5 math
        bps5 = 10_000.0 * math.log(s5 / s0)
        assert payload["log_return_t5_bps"] == pytest.approx(bps5, abs=0.01)
        assert payload["actual_direction_t5"] == "UP"
        assert payload["correct_t5"] is True
        assert payload["correct_5d"] is True
        assert payload["actual_return_5d"] == pytest.approx(bps5 / 10_000.0, abs=1e-6)
        # Brier: p=0.8, y=1.0 -> (0.8-1)^2 = 0.04
        assert payload["brier_score_t5"] == pytest.approx(0.04, abs=1e-6)
        assert payload["brier_5d"] == pytest.approx(0.04, abs=1e-6)

        # T+20 math
        bps20 = 10_000.0 * math.log(s20 / s0)
        assert payload["log_return_t20_bps"] == pytest.approx(bps20, abs=0.01)
        assert payload["actual_direction_t20"] == "UP"
        assert payload["correct_t20"] is True
        assert payload["correct_20d"] is True
        assert payload["actual_return_20d"] == pytest.approx(bps20 / 10_000.0, abs=1e-6)
        assert payload["brier_score_t20"] == pytest.approx(0.04, abs=1e-6)
        assert payload["brier_20d"] == pytest.approx(0.04, abs=1e-6)

    @patch.object(writer, "get_historical_price_for_date")
    @patch.object(writer, "get_validation_log_entry")
    @patch.object(writer, "write_validation_row")
    def test_idempotent_re_run(
        self,
        mock_write: MagicMock,
        mock_get_val: MagicMock,
        mock_get_price: MagicMock,
    ) -> None:
        """Re-running backfill on an already-validated call must not write."""
        call_date = date(2024, 1, 2)

        mock_get_price.return_value = {
            "date": call_date.isoformat(),
            "pair": "EURUSD",
            "close": 100.0,
        }
        # Existing validation already has brier_score_t5
        mock_get_val.return_value = {"brier_score_t5": 0.04}

        call: dict[str, Any] = {
            "id": 9999,
            "date": call_date.isoformat(),
            "pair": "EURUSD",
            "regime": "CARRY_POSITIVE",
            "rate_signal": "BULLISH",
            "confidence": 0.80,
        }

        result = backfill.backfill_validation_for_call(
            call, dry_run=False, as_of_date=date(2024, 12, 31)
        )

        assert result is True  # Processed (skipped due to existing)
        mock_write.assert_not_called()

    @patch.object(writer, "get_historical_price_for_date")
    @patch.object(writer, "get_validation_log_entry")
    @patch.object(writer, "write_validation_row")
    def test_dead_band_neutral(
        self,
        mock_write: MagicMock,
        mock_get_val: MagicMock,
        mock_get_price: MagicMock,
    ) -> None:
        """BULLISH call with S5 barely changed (< 5 bps) → NEUTRAL outcome."""
        call_date = date(2024, 1, 2)
        t5 = date(2024, 1, 9)

        s0, s5 = 100.0, 100.02  # ~2 bps — within dead band

        def _price_side(pair: str, date_str: str) -> dict[str, Any] | None:
            d = date.fromisoformat(date_str)
            if d == call_date:
                return {"date": call_date.isoformat(), "pair": pair, "close": s0}
            if d == t5:
                return {"date": t5.isoformat(), "pair": pair, "close": s5}
            return None

        mock_get_price.side_effect = _price_side
        mock_get_val.return_value = None

        call: dict[str, Any] = {
            "id": 9999,
            "date": call_date.isoformat(),
            "pair": "EURUSD",
            "regime": "CARRY_POSITIVE",
            "rate_signal": "BULLISH",
            "confidence": 0.80,
        }

        backfill.backfill_validation_for_call(call, dry_run=False, as_of_date=date(2024, 12, 31))

        payload = mock_write.call_args[0][0]
        assert payload["actual_direction_t5"] == "NEUTRAL"
        assert payload["correct_t5"] is False  # NEUTRAL is not CORRECT
        # Brier: p=0.8, y=0.5 -> (0.8-0.5)^2 = 0.09
        assert payload["brier_score_t5"] == pytest.approx(0.09, abs=1e-6)

    @patch.object(writer, "get_historical_price_for_date")
    @patch.object(writer, "get_validation_log_entry")
    @patch.object(writer, "write_validation_row")
    def test_bearish_wrong_direction(
        self,
        mock_write: MagicMock,
        mock_get_val: MagicMock,
        mock_get_price: MagicMock,
    ) -> None:
        """BEARISH call where price goes UP → WRONG outcome."""
        call_date = date(2024, 1, 2)
        t5 = date(2024, 1, 9)

        s0, s5 = 100.0, 103.0  # Strong up move

        def _price_side(pair: str, date_str: str) -> dict[str, Any] | None:
            d = date.fromisoformat(date_str)
            if d == call_date:
                return {"date": call_date.isoformat(), "pair": pair, "close": s0}
            if d == t5:
                return {"date": t5.isoformat(), "pair": pair, "close": s5}
            return None

        mock_get_price.side_effect = _price_side
        mock_get_val.return_value = None

        call: dict[str, Any] = {
            "id": 9999,
            "date": call_date.isoformat(),
            "pair": "EURUSD",
            "regime": "CARRY_NEGATIVE",
            "rate_signal": "BEARISH",
            "confidence": 0.60,
        }

        backfill.backfill_validation_for_call(call, dry_run=False, as_of_date=date(2024, 12, 31))

        payload = mock_write.call_args[0][0]
        assert payload["actual_direction_t5"] == "UP"
        assert payload["correct_t5"] is False
        assert payload["correct_5d"] is False
        # Brier: p=0.6, y=0.0 -> (0.6-0)^2 = 0.36
        assert payload["brier_score_t5"] == pytest.approx(0.36, abs=1e-6)

    @patch.object(writer, "get_historical_price_for_date")
    @patch.object(writer, "get_validation_log_entry")
    @patch.object(writer, "write_validation_row")
    def test_dry_run_no_write(
        self,
        mock_write: MagicMock,
        mock_get_val: MagicMock,
        mock_get_price: MagicMock,
    ) -> None:
        """``dry_run=True`` must compute but not write."""
        call_date = date(2024, 1, 2)
        t5 = date(2024, 1, 9)

        s0, s5 = 100.0, 102.0

        def _price_side(pair: str, date_str: str) -> dict[str, Any] | None:
            d = date.fromisoformat(date_str)
            if d == call_date:
                return {"date": call_date.isoformat(), "pair": pair, "close": s0}
            if d == t5:
                return {"date": t5.isoformat(), "pair": pair, "close": s5}
            return None

        mock_get_price.side_effect = _price_side
        mock_get_val.return_value = None

        call: dict[str, Any] = {
            "id": 9999,
            "date": call_date.isoformat(),
            "pair": "EURUSD",
            "regime": "CARRY_POSITIVE",
            "rate_signal": "BULLISH",
            "confidence": 0.80,
        }

        result = backfill.backfill_validation_for_call(
            call, dry_run=True, as_of_date=date(2024, 12, 31)
        )

        assert result is True
        mock_write.assert_not_called()
