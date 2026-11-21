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

from src.validation.calculator import EVALUATION_VERSION
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
            pair: str, limit: int | None = 5000
        ) -> list[dict[str, Any]]:
            return [r for r in regime_calls if r.get("pair") == pair]

        def _get_publication_signal_for_call(call_id: int) -> dict[str, Any] | None:
            call = next((row for row in regime_calls if row.get("id") == call_id), None)
            if call is None:
                return None
            pair = str(call["pair"])
            date_str = str(call["date"])
            key = f"{pair}:{date_str}"
            spot = spots.get(key)
            if spot is not None:
                return {"pair": pair, "date": date_str, "spot": spot}
            return None

        def _get_exact_historical_price_for_date(pair: str, date_str: str) -> dict[str, Any] | None:
            spot = spots.get(f"{pair}:{date_str}")
            return None if spot is None else {"pair": pair, "date": date_str, "close": spot}

        def _get_validation_log_for_call(call_id: int | str) -> dict[str, Any] | None:
            return existing_validation

        def _write_validation_row(row: dict[str, Any]) -> None:
            captured.append(dict(row))

        patches = [
            patch(
                "src.validation.engine.writer.get_historical_regime_calls",
                _get_historical_regime_calls,
            ),
            patch(
                "src.validation.engine.writer.get_publication_signal_for_call",
                _get_publication_signal_for_call,
            ),
            patch(
                "src.validation.engine.writer.get_exact_historical_price_for_date",
                _get_exact_historical_price_for_date,
            ),
            patch(
                "src.validation.engine.writer.get_validation_log_for_call",
                _get_validation_log_for_call,
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
            "predicted_direction": "BULLISH",
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
    assert row.get("actual_return_5d") == pytest.approx(expected_t5_bps / 10_000.0, rel=1e-6)
    assert row.get("actual_return_20d") == pytest.approx(expected_t20_bps / 10_000.0, rel=1e-6)

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
            "predicted_direction": "BEARISH",
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
            "predicted_direction": "BULLISH",
            "confidence": 0.70,
            "signal_composite": 0.0,
        }
    ]

    # Pre-existing T+5 data
    existing_validation = {
        "call_id": 44,
        "evaluation_version": EVALUATION_VERSION,
        "entry_price_evidence": {
            "kind": "publication_signal",
            "pair": "USDINR",
            "date": "2026-05-01",
            "price": 83.50,
            "source": "publication_evidence.signal_payload.spot",
            "call_id": 44,
        },
        "log_return_t5_bps": 12.34,
        "correct_t5": True,
        "brier_score_t5": 0.25,
        "actual_direction_t5": "UP",
        "actual_return_5d": 0.001234,
        "correct_5d": True,
        "brier_5d": 0.25,
        "log_return_net_bps_t5": 2.34,
        "correct_net_t5": True,
        "cost_bps_t5": 10.0,
        "price_evidence_t5": {
            "kind": "historical_close",
            "pair": "USDINR",
            "date": "2026-05-08",
            "price": 83.55,
            "source": "historical_prices.close",
        },
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
    assert row["log_return_net_bps_t5"] == 2.34
    assert row["correct_net_t5"] is True
    assert row["cost_bps_t5"] == 10.0

    # T+20 should be freshly computed
    assert row.get("log_return_t20_bps") is not None
    assert row.get("correct_t20") is not None


def test_validation_engine_scores_published_direction_not_rate_component(
    _writer_mock: Any,
) -> None:
    call_date = date(2026, 5, 1)
    regime_calls = [
        {
            "id": 45,
            "pair": "EURUSD",
            "date": call_date.isoformat(),
            "regime": "RISK_ON",
            "predicted_direction": "BEARISH",
            "rate_signal": "BULLISH",
            "confidence": 0.8,
        }
    ]
    spots = {
        "EURUSD:2026-05-01": 1.0,
        "EURUSD:2026-05-08": 0.99,
    }

    patches, captured = _writer_mock(regime_calls=regime_calls, spots=spots)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run_validation(as_of_date=date(2026, 5, 8))

    assert captured[0]["predicted_direction"] == "BEARISH"
    assert captured[0]["correct_t5"] is True


def test_validation_engine_skips_missing_published_direction(_writer_mock: Any) -> None:
    call_date = date(2026, 5, 1)
    regime_calls = [
        {
            "id": 46,
            "pair": "EURUSD",
            "date": call_date.isoformat(),
            "rate_signal": "BULLISH",
            "confidence": 0.8,
        }
    ]
    spots = {
        "EURUSD:2026-05-01": 1.0,
        "EURUSD:2026-05-08": 1.01,
    }

    patches, captured = _writer_mock(regime_calls=regime_calls, spots=spots)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run_validation(as_of_date=date(2026, 5, 8))

    assert captured == []


def test_validation_engine_fails_closed_on_ambiguous_existing_call(
    _writer_mock: Any,
) -> None:
    call_date = date(2026, 5, 1)
    calls = [
        {
            "id": 47,
            "pair": "EURUSD",
            "date": call_date.isoformat(),
            "predicted_direction": "BULLISH",
            "confidence": 0.8,
        }
    ]
    spots = {
        "EURUSD:2026-05-01": 1.0,
        "EURUSD:2026-05-08": 1.01,
    }
    patches, captured = _writer_mock(
        regime_calls=calls,
        spots=spots,
        existing_validation={"call_id": 999, "log_return_t5_bps": 12.0},
    )
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run_validation(as_of_date=date(2026, 5, 8))

    assert captured == []
