"""Single-call replay uses the same frozen evaluator as live validation."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

import pytest

from src.backfill import validation_backfill as backfill
from src.db import writer
from src.validation.calculator import EVALUATION_VERSION


def _call() -> dict[str, Any]:
    return {
        "id": 9999,
        "date": "2024-01-02",
        "pair": "EURUSD",
        "regime": "CARRY_POSITIVE",
        "predicted_direction": "BULLISH",
        "confidence": 0.8,
    }


def _entry_evidence() -> dict[str, Any]:
    return {
        "kind": "publication_signal",
        "pair": "EURUSD",
        "date": "2024-01-02",
        "price": 100.0,
        "source": "publication_evidence.signal_payload.spot",
        "call_id": 9999,
    }


def test_single_replay_writes_both_mature_horizons_with_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prices = {"2024-01-09": 102.0, "2024-01-30": 105.0}
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda call_id: {"pair": "EURUSD", "date": "2024-01-02", "spot": 100.0},
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda pair, target: {"pair": pair, "date": target, "close": prices[target]},
    )
    monkeypatch.setattr(writer, "write_validation_row", captured.append)

    assert backfill.backfill_validation_for_call(_call(), as_of_date=date(2024, 1, 30)) is True

    assert len(captured) == 1
    row = captured[0]
    assert row["evaluation_version"] == EVALUATION_VERSION
    assert row["entry_price_evidence"] == _entry_evidence()
    assert row["price_evidence_t5"]["price"] == 102.0
    assert row["price_evidence_t20"]["price"] == 105.0
    assert row["correct_t5"] is row["correct_t20"] is True


def test_single_replay_dry_run_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda call_id: {"pair": "EURUSD", "date": "2024-01-02", "spot": 100.0},
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        lambda pair, target: {"pair": pair, "date": target, "close": 102.0},
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda row: pytest.fail("dry run wrote"),
    )

    assert (
        backfill.backfill_validation_for_call(_call(), dry_run=True, as_of_date=date(2024, 1, 9))
        is True
    )


def test_single_replay_preserves_completed_t5_and_reads_only_t20(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    t5_evidence = {
        "kind": "historical_close",
        "pair": "EURUSD",
        "date": "2024-01-09",
        "price": 101.0,
        "source": "historical_prices.close",
    }
    existing = {
        "call_id": 9999,
        "evaluation_version": EVALUATION_VERSION,
        "entry_price_evidence": _entry_evidence(),
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
        "price_evidence_t5": t5_evidence,
    }
    original = deepcopy(existing)
    requested: list[str] = []
    captured: list[dict[str, Any]] = []

    def read_price(pair: str, target: str) -> dict[str, Any]:
        requested.append(target)
        return {"pair": pair, "date": target, "close": 105.0}

    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: existing)
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda call_id: pytest.fail("entry refetched"),
    )
    monkeypatch.setattr(
        writer,
        "get_exact_historical_price_for_date",
        read_price,
    )
    monkeypatch.setattr(writer, "write_validation_row", captured.append)

    assert backfill.backfill_validation_for_call(_call(), as_of_date=date(2024, 1, 30)) is True

    assert requested == ["2024-01-30"]
    assert captured[0]["log_return_t5_bps"] == 10.0
    assert captured[0]["price_evidence_t5"] == t5_evidence
    assert existing == original
