"""Live validation visits the complete call backlog without mutable prices."""

from datetime import date
from typing import Any

import pytest

from src.db import writer
from src.validation import engine
from src.validation.calculator import EVALUATION_VERSION


def _configure_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda call_id: {"pair": "EURUSD", "date": "2026-01-02", "spot": 100.0},
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda pair, target: {"pair": pair, "date": target, "close": 101.0},
    )


def test_engine_revisits_calls_older_than_latest_thirty(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = [
        {
            "id": i,
            "date": "2026-01-02",
            "pair": "EURUSD",
            "regime": "TRENDING",
            "predicted_direction": "BULLISH",
            "confidence": 0.7,
        }
        for i in range(1, 42)
    ]
    limits: list[int | None] = []

    def history(pair: str, limit: int | None = 5000) -> list[dict[str, Any]]:
        limits.append(limit)
        return calls

    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(engine, "load_universe", lambda: {"EURUSD": {"class": "FX"}})
    monkeypatch.setattr(writer, "get_historical_regime_calls", history)
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    _configure_evidence(monkeypatch)
    monkeypatch.setattr(writer, "write_validation_row", captured.append)

    engine.run_validation(date(2026, 2, 2))

    assert limits == [None]
    assert len(captured) == 41
    assert {row["call_id"] for row in captured} == set(range(1, 42))


def test_completed_calls_do_not_require_evidence_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: {"EURUSD": {"class": "FX"}})
    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        lambda pair, limit: [
            {
                "id": "1",
                "date": "2026-01-02",
                "pair": "EURUSD",
                "predicted_direction": "NEUTRAL",
            }
        ],
    )
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda call_id: {
            "call_id": 1,
            "evaluation_version": EVALUATION_VERSION,
            "log_return_t5_bps": 0.0,
            "log_return_t20_bps": 0.0,
        },
    )
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda *args: pytest.fail("no entry read"),
    )
    monkeypatch.setattr(
        writer, "get_exact_historical_price_for_date", lambda *args: pytest.fail("no price read")
    )
    monkeypatch.setattr(writer, "write_validation_row", lambda *args: pytest.fail("no rewrite"))

    engine.run_validation(date(2026, 2, 2))


def test_database_read_errors_propagate_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: {"EURUSD": {"class": "FX"}})
    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        lambda pair, limit: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    with pytest.raises(RuntimeError, match="database unavailable"):
        engine.run_validation(date(2026, 2, 2))


def test_engine_rejects_wrong_pair_returned_by_pair_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: {"EURUSD": {"class": "FX"}})
    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        lambda pair, limit: [
            {
                "id": 1,
                "date": "2026-01-02",
                "pair": "USDJPY",
                "predicted_direction": "BULLISH",
                "confidence": 0.7,
            }
        ],
    )
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda *args: pytest.fail("wrong-pair call must stop"),
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda *args: pytest.fail("wrong-pair call must stop"),
    )

    engine.run_validation(date(2026, 2, 2))
