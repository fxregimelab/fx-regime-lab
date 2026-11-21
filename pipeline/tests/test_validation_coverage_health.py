"""Coverage health keeps mature validation gaps visible."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from src.db import writer
from src.validation import engine
from src.validation.calculator import EVALUATION_VERSION
from src.validation.calendar import add_trading_days
from src.validation.coverage import ValidationRunResult

CALL_DATE = date(2026, 1, 2)
T5_DATE = add_trading_days(CALL_DATE, 5)
T20_DATE = add_trading_days(CALL_DATE, 20)
UNIVERSE = {
    "EURUSD": {"class": "FX"},
    "USDJPY": {"class": "FX"},
    "USDINR": {"class": "FX"},
}


def _call(**changes: Any) -> dict[str, Any]:
    call: dict[str, Any] = {
        "id": 1,
        "date": CALL_DATE.isoformat(),
        "pair": "EURUSD",
        "regime": "TRENDING",
        "predicted_direction": "BULLISH",
        "confidence": 0.7,
    }
    call.update(changes)
    return call


def _entry() -> dict[str, Any]:
    return {"pair": "EURUSD", "date": CALL_DATE.isoformat(), "spot": 1.0}


def _evidence(price_date: date, price: float) -> dict[str, Any]:
    return {
        "kind": "historical_close",
        "pair": "EURUSD",
        "date": price_date.isoformat(),
        "price": price,
        "source": "historical_prices.close",
    }


def _completed_record() -> dict[str, Any]:
    return {
        "call_id": 1,
        "evaluation_version": EVALUATION_VERSION,
        "entry_price_evidence": {
            "kind": "publication_signal",
            "pair": "EURUSD",
            "date": CALL_DATE.isoformat(),
            "price": 1.0,
            "source": "publication_evidence.signal_payload.spot",
            "call_id": 1,
        },
        "log_return_t5_bps": 10.0,
        "price_evidence_t5": _evidence(T5_DATE, 1.001),
        "log_return_t20_bps": 20.0,
        "price_evidence_t20": _evidence(T20_DATE, 1.002),
    }


def _history_for(
    call_rows: list[dict[str, Any]],
) -> Callable[[str, int | None], list[dict[str, Any]]]:
    def history(pair: str, limit: int | None) -> list[dict[str, Any]]:
        assert limit is None
        return call_rows if pair == "EURUSD" else []

    return history


def test_live_report_exposes_missing_mature_t20(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    monkeypatch.setattr(writer, "get_publication_signal_for_call", lambda call_id: _entry())
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda pair, target: (
            {"pair": pair, "date": target, "close": 1.01}
            if target == T5_DATE.isoformat()
            else None
        ),
    )
    monkeypatch.setattr(writer, "write_validation_row", captured.append)

    report = engine.run_validation(T20_DATE)

    assert report.rows == captured
    assert report.scanned_calls == 1
    assert report.due_horizons == 2
    assert report.completed_horizons == 1
    assert report.missing_horizons == 1
    assert report.invalid_calls == 0
    assert report.healthy is False
    assert "validation_scan_completed" in report.notes
    assert "missing_horizons=1" in report.notes


def test_fully_completed_record_counts_without_reader_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: _completed_record())
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda *args: pytest.fail("completed call must not read entry evidence"),
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda *args: pytest.fail("completed call must not read endpoint evidence"),
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda *args: pytest.fail("completed call must not be rewritten"),
    )

    report = engine.run_validation(T20_DATE)

    assert report.rows == []
    assert report.due_horizons == 2
    assert report.completed_horizons == 2
    assert report.missing_horizons == 0
    assert report.invalid_calls == 0
    assert report.healthy is True


def test_invalid_completed_record_cannot_look_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _completed_record()
    invalid["price_evidence_t20"] = {
        **_evidence(T20_DATE, 1.002),
        "pair": "USDJPY",
    }
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: invalid)
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda *args: pytest.fail("invalid completed record must fail closed"),
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda *args: pytest.fail("invalid completed record must fail closed"),
    )

    report = engine.run_validation(T20_DATE)

    assert report.invalid_calls == 1
    assert report.due_horizons == 2
    assert report.completed_horizons == 0
    assert report.missing_horizons == 2
    assert report.healthy is False


@pytest.mark.parametrize("invalid_id", [True, "1", 0])
def test_completed_record_requires_an_actual_positive_integer_id(
    monkeypatch: pytest.MonkeyPatch,
    invalid_id: Any,
) -> None:
    invalid = _completed_record()
    invalid["call_id"] = invalid_id
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: invalid)

    report = engine.run_validation(T20_DATE)

    assert report.due_horizons == 2
    assert report.completed_horizons == 0
    assert report.invalid_calls == 1
    assert report.healthy is False


def test_completed_entry_evidence_requires_an_actual_integer_call_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _completed_record()
    invalid["entry_price_evidence"]["call_id"] = True
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: invalid)

    report = engine.run_validation(T20_DATE)

    assert report.completed_horizons == 0
    assert report.invalid_calls == 1
    assert report.healthy is False


def test_completed_return_overflow_degrades_as_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _completed_record()
    invalid["log_return_t5_bps"] = 10**10_000
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: invalid)

    report = engine.run_validation(T20_DATE)

    assert report.completed_horizons == 0
    assert report.invalid_calls == 1
    assert report.healthy is False


def test_invalid_timestamp_call_is_scanned_and_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        _history_for([_call(date="2026-01-02T00:00:00Z")]),
    )
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda *args: pytest.fail("invalid call must stop before ledger reads"),
    )

    report = engine.run_validation(T20_DATE)

    assert report.scanned_calls == 1
    assert report.invalid_calls == 1
    assert report.due_horizons == 0
    assert report.healthy is False
    assert "no_mature_horizons" in report.notes


def test_duplicate_call_ids_fail_closed_without_double_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        _history_for([_call(), _call()]),
    )
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda *args: pytest.fail("duplicate identities must stop before ledger reads"),
    )

    report = engine.run_validation(T20_DATE)

    assert report.scanned_calls == 2
    assert report.due_horizons == 4
    assert report.completed_horizons == 0
    assert report.invalid_calls == 2
    assert report.healthy is False


def test_missing_locked_pair_definition_degrades_an_empty_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: {"EURUSD": {"class": "FX"}})
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([]))

    report = engine.run_validation(T20_DATE)

    assert report.scanned_calls == 0
    assert report.invalid_calls == 0
    assert report.healthy is False
    assert "no_mature_horizons" in report.notes
    assert "missing_pair_definitions=USDJPY,USDINR" in report.notes


def test_future_call_is_invalid_instead_of_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        _history_for([_call(date="2026-02-02")]),
    )
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda *args: pytest.fail("future call must stop before ledger reads"),
    )

    report = engine.run_validation(CALL_DATE)

    assert report.scanned_calls == 1
    assert report.due_horizons == 0
    assert report.completed_horizons == 0
    assert report.invalid_calls == 1
    assert report.healthy is False
    assert "future_call_dates_present" in report.notes


def test_future_completed_horizon_invalidates_existing_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda call_id: _completed_record(),
    )
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda *args: pytest.fail("future completion must fail before evidence reads"),
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda *args: pytest.fail("future completion must fail before evidence reads"),
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda *args: pytest.fail("future completion must not be rewritten"),
    )

    report = engine.run_validation(T5_DATE)

    assert report.due_horizons == 1
    assert report.completed_horizons == 0
    assert report.missing_horizons == 1
    assert report.invalid_calls == 1
    assert report.healthy is False


def test_current_record_without_structural_evidence_is_degraded_not_rewritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incomplete_record = {
        "call_id": 1,
        "evaluation_version": EVALUATION_VERSION,
        "log_return_t5_bps": 10.0,
    }
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_call",
        lambda call_id: incomplete_record,
    )
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda *args: pytest.fail("invalid current record must fail closed"),
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda *args: pytest.fail("invalid current record must fail closed"),
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda *args: pytest.fail("invalid current record must not be rewritten"),
    )

    report = engine.run_validation(T5_DATE)

    assert report.due_horizons == 1
    assert report.completed_horizons == 0
    assert report.missing_horizons == 1
    assert report.invalid_calls == 1
    assert report.healthy is False


def test_persistence_error_propagates_without_a_healthy_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "load_universe", lambda: UNIVERSE)
    monkeypatch.setattr(writer, "get_historical_regime_calls", _history_for([_call()]))
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    monkeypatch.setattr(writer, "get_publication_signal_for_call", lambda call_id: _entry())
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda pair, target: {"pair": pair, "date": target, "close": 1.01},
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda row: (_ for _ in ()).throw(RuntimeError("ledger unavailable")),
    )

    with pytest.raises(RuntimeError, match="ledger unavailable"):
        engine.run_validation(T5_DATE)


@pytest.mark.parametrize(
    "changes",
    [
        {"scanned_calls": -1},
        {"due_horizons": 1.0},
        {"invalid_calls": True},
        {"scanned_calls": 1, "due_horizons": 3},
        {"scanned_calls": 1, "due_horizons": 1, "completed_horizons": 2},
        {"scanned_calls": 1, "invalid_calls": 2},
    ],
)
def test_inconsistent_counters_cannot_report_healthy(changes: dict[str, Any]) -> None:
    report = ValidationRunResult()
    for name, value in changes.items():
        setattr(report, name, value)

    assert report.healthy is False
