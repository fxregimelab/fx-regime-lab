from __future__ import annotations

import math
from copy import deepcopy
from datetime import date, datetime
from typing import Any

import pytest

from src.db import writer
from src.validation import engine
from src.validation.calculator import EVALUATION_VERSION
from src.validation.evaluator import evaluate_call


def _call(call_id: int = 1, *, spot_date: str = "2026-01-02") -> dict[str, Any]:
    return {
        "id": call_id,
        "date": spot_date,
        "pair": "EURUSD",
        "regime": "TRENDING",
        "predicted_direction": "BULLISH",
        "confidence": 0.8,
        "strategy_version": "v2",
        "model_version": f"model-{call_id}",
        "data_source": "live",
    }


def _entry(call_id: int, price: float) -> dict[str, Any]:
    return {"pair": "EURUSD", "date": "2026-01-02", "spot": price, "call_id": call_id}


def _close(target: date, price: float, *, pair: str = "EURUSD") -> dict[str, Any]:
    return {"pair": pair, "date": target.isoformat(), "close": price}


def _entry_evidence(call_id: int, price: float) -> dict[str, Any]:
    return {
        "kind": "publication_signal",
        "pair": "EURUSD",
        "date": "2026-01-02",
        "price": price,
        "source": "publication_evidence.signal_payload.spot",
        "call_id": call_id,
    }


def _price_evidence(target: date, price: float) -> dict[str, Any]:
    return {
        "kind": "historical_close",
        "pair": "EURUSD",
        "date": target.isoformat(),
        "price": price,
        "source": "historical_prices.close",
    }


def _t5_fields(target: date, price: float) -> dict[str, Any]:
    return {
        "log_return_t5_bps": 10.0,
        "correct_t5": True,
        "brier_score_t5": 0.04,
        "actual_direction_t5": "UP",
        "actual_return_5d": 0.001,
        "correct_5d": True,
        "brier_5d": 0.04,
        "log_return_net_bps_t5": 9.8,
        "correct_net_t5": True,
        "cost_bps_t5": 0.2,
        "price_evidence_t5": _price_evidence(target, price),
    }


def test_two_same_date_model_snapshots_score_from_their_own_entries_and_not_mutable_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = [_call(1), _call(2)]
    entries = {1: _entry(1, 1.2), 2: _entry(2, 0.8)}
    captured: list[dict[str, Any]] = []
    t5 = date(2026, 1, 9)

    monkeypatch.setattr(engine, "load_universe", lambda: {"EURUSD": {"class": "FX"}})
    monkeypatch.setattr(writer, "get_historical_regime_calls", lambda pair, limit: calls)
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    monkeypatch.setattr(writer, "get_publication_signal_for_call", entries.__getitem__)
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda pair, target: _close(date.fromisoformat(target), 1.0),
    )
    monkeypatch.setattr(
        writer,
        "get_signal_for_pair_date",
        lambda *args: pytest.fail("mutable signals must never supply validation entry prices"),
    )
    monkeypatch.setattr(writer, "write_validation_row", captured.append)

    engine.run_validation(t5)

    assert [row["call_id"] for row in captured] == [1, 2]
    assert captured[0]["log_return_t5_bps"] == pytest.approx(10_000 * math.log(1 / 1.2))
    assert captured[1]["log_return_t5_bps"] == pytest.approx(10_000 * math.log(1 / 0.8))
    assert captured[0]["log_return_t5_bps"] < 0 < captured[1]["log_return_t5_bps"]
    assert captured[0]["entry_price_evidence"]["price"] == 1.2
    assert captured[1]["entry_price_evidence"]["price"] == 0.8


@pytest.mark.parametrize(
    "entry",
    [
        None,
        {"pair": "USDJPY", "date": "2026-01-02", "spot": 1.0},
        {"pair": "EURUSD", "date": "2026-01-03", "spot": 1.0},
        {"pair": "EURUSD", "date": "2026-01-02", "spot": True},
        {"pair": "EURUSD", "date": "2026-01-02", "spot": float("nan")},
    ],
)
def test_missing_or_invalid_original_publication_evidence_cannot_score(
    entry: dict[str, Any] | None,
) -> None:
    assert (
        evaluate_call(
            _call(),
            date(2026, 1, 9),
            None,
            read_entry=lambda call_id: entry,
            read_price=lambda pair, target: _close(target, 1.1),
        )
        is None
    )


@pytest.mark.parametrize(
    "row",
    [
        {"pair": "USDJPY", "date": "2026-01-09", "close": 1.1},
        {"pair": "EURUSD", "date": "2026-01-08", "close": 1.1},
        {"pair": "EURUSD", "date": "2026-01-09", "close": False},
        {"pair": "EURUSD", "date": "2026-01-09", "close": float("inf")},
    ],
)
def test_wrong_or_nonfinite_endpoint_identity_cannot_score(row: dict[str, Any]) -> None:
    assert (
        evaluate_call(
            _call(),
            date(2026, 1, 9),
            None,
            read_entry=lambda call_id: _entry(call_id, 1.0),
            read_price=lambda pair, target: row,
        )
        is None
    )


def test_partial_completion_freezes_t5_and_evidence_then_adds_t20() -> None:
    t5 = date(2026, 1, 9)
    t20 = date(2026, 1, 30)
    existing = {
        "call_id": 1,
        "evaluation_version": EVALUATION_VERSION,
        "entry_price_evidence": _entry_evidence(1, 1.0),
        **_t5_fields(t5, 1.001),
    }
    original = deepcopy(existing)
    entry_reads: list[int] = []
    price_reads: list[date] = []

    def unexpected_entry(call_id: int) -> dict[str, Any] | None:
        entry_reads.append(call_id)
        return None

    def read_price(pair: str, target: date) -> dict[str, Any]:
        price_reads.append(target)
        return _close(target, 1.02)

    row = evaluate_call(
        _call(),
        t20,
        existing,
        read_entry=unexpected_entry,
        read_price=read_price,
    )

    assert row is not None
    assert entry_reads == []
    assert price_reads == [t20]
    assert row["log_return_t5_bps"] == 10.0
    assert row["price_evidence_t5"] == original["price_evidence_t5"]
    assert row["entry_price_evidence"] == original["entry_price_evidence"]
    row["price_evidence_t5"]["price"] = 99.0
    assert existing == original
    assert row["price_evidence_t20"] == _price_evidence(t20, 1.02)


def test_complete_retry_and_not_yet_due_call_do_not_read_prices() -> None:
    def fail(*args: Any) -> Any:
        pytest.fail("completed or immature calls must not read evidence")

    complete = {
        "call_id": 1,
        "evaluation_version": EVALUATION_VERSION,
        "log_return_t5_bps": 1.0,
        "log_return_t20_bps": 2.0,
    }
    assert (
        evaluate_call(_call(), date(2026, 1, 30), complete, read_entry=fail, read_price=fail)
        is None
    )
    assert evaluate_call(_call(), date(2026, 1, 8), None, read_entry=fail, read_price=fail) is None


@pytest.mark.parametrize("reader_name", ["entry", "price"])
@pytest.mark.parametrize("error_type", [ValueError, RuntimeError])
def test_reader_errors_propagate(reader_name: str, error_type: type[Exception]) -> None:
    def fail(*args: Any) -> Any:
        raise error_type("reader failed")

    with pytest.raises(error_type, match="reader failed"):
        evaluate_call(
            _call(),
            date(2026, 1, 9),
            None,
            read_entry=fail if reader_name == "entry" else lambda call_id: _entry(call_id, 1.0),
            read_price=fail if reader_name == "price" else lambda pair, target: _close(target, 1.1),
        )


def test_timestamp_call_date_and_mismatched_ids_fail_closed() -> None:
    def fail(*args: Any) -> Any:
        pytest.fail("invalid call must not read evidence")

    timestamped = {**_call(), "date": datetime(2026, 1, 2, 12, 0)}
    mismatched = {**_call(), "call_id": 2}
    assert (
        evaluate_call(timestamped, date(2026, 1, 9), None, read_entry=fail, read_price=fail) is None
    )
    assert (
        evaluate_call(mismatched, date(2026, 1, 9), None, read_entry=fail, read_price=fail) is None
    )
