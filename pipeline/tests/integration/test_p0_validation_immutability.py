"""P0-T1+T2 integration test: validation engine wiring + immutability guards.

Mocks the Supabase writer layer so no live database is required.
"""

from __future__ import annotations

import math
from contextlib import ExitStack
from datetime import date
from typing import Any
from unittest.mock import patch

import pytest

from src.validation.engine import run_validation


@pytest.fixture
def _writer_mock() -> Any:
    """Return a callable that patches all writer functions used by run_validation."""

    def _make(
        regime_calls: list[dict[str, Any]] | None = None,
        spots: dict[str, float] | None = None,
        existing_validation: dict[str, Any] | None = None,
    ) -> tuple[list[Any], list[dict[str, Any]]]:
        regime_calls = regime_calls or []
        spots = spots or {}
        captured: list[dict[str, Any]] = []

        def _get_historical_regime_calls(
            pair: str, limit: int = 5000
        ) -> list[dict[str, Any]]:
            return [r for r in regime_calls if r.get("pair") == pair]

        def _get_signal_for_pair_date(
            pair: str, date_str: str
        ) -> dict[str, Any] | None:
            key = f"{pair}:{date_str}"
            spot = spots.get(key)
            if spot is not None:
                return {"spot": spot}
            return None

        def _get_validation_log_entry(
            call_date: date, pair: str
        ) -> dict[str, Any] | None:
            return existing_validation

        def _write_validation_row(row: dict[str, Any]) -> None:
            captured.append(dict(row))

        patches = [
            patch(
                "src.validation.engine.writer.get_historical_regime_calls",
                _get_historical_regime_calls,
            ),
            patch(
                "src.validation.engine.writer.get_signal_for_pair_date",
                _get_signal_for_pair_date,
            ),
            patch(
                "src.validation.engine.writer.get_validation_log_entry",
                _get_validation_log_entry,
            ),
            patch(
                "src.validation.engine.writer.write_validation_row",
                _write_validation_row,
            ),
            patch(
                "src.validation.engine.load_universe",
                return_value={
                    "EURUSD": {"class": "FX"},
                    "USDJPY": {"class": "FX"},
                    "USDINR": {"class": "FX"},
                },
            ),
        ]
        return patches, captured

    return _make


def test_validation_engine_computes_t5_and_t20_separately(_writer_mock: Any) -> None:
    """T+5 and T+20 metrics must coexist in the same row without overwriting."""
    call_date = date(2026, 5, 1)
    as_of = date(2026, 5, 30)

    regime_calls = [
        {
            "id": 42,
            "pair": "EURUSD",
            "date": call_date.isoformat(),
            "regime": "NEUTRAL",
            "rate_signal": "BULLISH",
            "confidence": 0.75,
            "signal_composite": 0.3,
        }
    ]

    # Spot prices: s0=1.0700, t5=1.0721 (+21 pips, ~19.6 bps),
    # t20=1.0750 (+50 pips, ~46.5 bps)
    spots = {
        "EURUSD:2026-05-01": 1.0700,
        "EURUSD:2026-05-08": 1.0721,
        "EURUSD:2026-05-29": 1.0750,
    }

    patches, captured = _writer_mock(regime_calls=regime_calls, spots=spots)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run_validation(as_of_date=as_of)

    assert len(captured) == 1
    row = captured[0]

    # T+5 assertions
    assert row.get("log_return_t5_bps") is not None
    expected_t5_bps = 10_000.0 * math.log(1.0721 / 1.0700)
    assert abs(row["log_return_t5_bps"] - expected_t5_bps) < 1e-6
    assert row.get("correct_t5") is True  # BULLISH + UP
    assert row.get("brier_score_t5") is not None
    assert abs(row["brier_score_t5"] - (0.75 - 1.0) ** 2) < 1e-9
    assert row.get("actual_direction_t5") == "UP"

    # T+20 assertions
    assert row.get("log_return_t20_bps") is not None
    expected_t20_bps = 10_000.0 * math.log(1.0750 / 1.0700)
    assert abs(row["log_return_t20_bps"] - expected_t20_bps) < 1e-6
    assert row.get("correct_t20") is True
    assert row.get("brier_score_t20") is not None
    assert abs(row["brier_score_t20"] - (0.75 - 1.0) ** 2) < 1e-9
    assert row.get("actual_direction_t20") == "UP"

    # They must be different values
    assert row["log_return_t5_bps"] != row["log_return_t20_bps"]

    # Legacy columns populated too
    assert row.get("actual_return_5d") == pytest.approx(
        expected_t5_bps / 10_000.0, rel=1e-6
    )
    assert row.get("actual_return_20d") == pytest.approx(
        expected_t20_bps / 10_000.0, rel=1e-6
    )

    # call_id passed through
    assert row.get("call_id") == 42


def test_validation_engine_skips_t20_when_not_ready(_writer_mock: Any) -> None:
    """If as_of_date is before T+20, only T+5 should be populated."""
    call_date = date(2026, 5, 1)
    as_of = date(2026, 5, 8)  # Exactly T+5, not T+20

    regime_calls = [
        {
            "id": 43,
            "pair": "USDJPY",
            "date": call_date.isoformat(),
            "regime": "NEUTRAL",
            "rate_signal": "BEARISH",
            "confidence": 0.60,
            "signal_composite": -0.2,
        }
    ]

    spots = {
        "USDJPY:2026-05-01": 150.00,
        "USDJPY:2026-05-08": 149.85,
    }

    patches, captured = _writer_mock(regime_calls=regime_calls, spots=spots)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run_validation(as_of_date=as_of)

    assert len(captured) == 1
    row = captured[0]

    # T+5 should exist
    assert row.get("log_return_t5_bps") is not None
    assert row.get("correct_t5") is True  # BEARISH + DOWN

    # T+20 should NOT exist
    assert row.get("log_return_t20_bps") is None
    assert row.get("correct_t20") is None
    assert row.get("brier_score_t20") is None


def test_validation_engine_does_not_overwrite_existing_t5(_writer_mock: Any) -> None:
    """If T+5 data already exists in the row, re-run must not overwrite it."""
    call_date = date(2026, 5, 1)
    as_of = date(2026, 5, 30)

    regime_calls = [
        {
            "id": 44,
            "pair": "USDINR",
            "date": call_date.isoformat(),
            "regime": "NEUTRAL",
            "rate_signal": "NEUTRAL",
            "confidence": 0.0,
            "signal_composite": 0.0,
        }
    ]

    # Pre-existing T+5 data
    existing_validation = {
        "log_return_t5_bps": 12.34,
        "correct_t5": True,
        "brier_score_t5": 0.25,
        "actual_direction_t5": "UP",
        "actual_return_5d": 0.001234,
        "correct_5d": True,
        "brier_5d": 0.25,
    }

    spots = {
        "USDINR:2026-05-01": 83.50,
        "USDINR:2026-05-08": 83.55,
        "USDINR:2026-05-29": 83.60,
    }

    patches, captured = _writer_mock(
        regime_calls=regime_calls,
        spots=spots,
        existing_validation=existing_validation,
    )
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run_validation(as_of_date=as_of)

    assert len(captured) == 1
    row = captured[0]

    # T+5 must be carried forward unchanged
    assert row["log_return_t5_bps"] == 12.34
    assert row["correct_t5"] is True
    assert row["brier_score_t5"] == 0.25

    # T+20 should be freshly computed
    assert row.get("log_return_t20_bps") is not None
    assert row.get("correct_t20") is not None
