"""Database reads must not substitute component votes for published calls."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.db import writer


def _query(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]) -> MagicMock:
    query = MagicMock()
    for method in ("select", "eq", "order", "range", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    client = MagicMock()
    client.table.return_value = query
    monkeypatch.setattr(writer, "_client", lambda: client)
    return query


def test_live_read_includes_published_prediction(monkeypatch: pytest.MonkeyPatch) -> None:
    query = _query(monkeypatch, [{"id": 1, "predicted_direction": "BEARISH"}])
    rows = writer.get_historical_regime_calls("EURUSD", limit=30)
    assert "predicted_direction" in query.select.call_args.args[0].split(",")
    assert rows[0]["predicted_direction"] == "BEARISH"


def test_historical_calls_all_pages_preserve_oldest_first(monkeypatch: pytest.MonkeyPatch) -> None:
    query = _query(monkeypatch, [])
    query.execute.side_effect = [
        SimpleNamespace(data=[{"id": i} for i in range(1001, 1, -1)]),
        SimpleNamespace(data=[{"id": 1}]),
    ]
    rows = writer.get_historical_regime_calls("EURUSD", limit=None)
    assert len(rows) == 1001
    assert rows[0]["id"] == 1 and rows[-1]["id"] == 1001
    assert [call.args for call in query.range.call_args_list] == [(0, 999), (1000, 1999)]


def test_historical_limit_is_total_across_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    query = _query(monkeypatch, [])
    query.execute.side_effect = [SimpleNamespace(data=[{"id": i} for i in range(1000)]),
                                 SimpleNamespace(data=[{"id": i} for i in range(50)])]
    assert len(writer.get_historical_regime_calls("EURUSD", limit=1050)) == 1050
    assert [call.args for call in query.range.call_args_list] == [(0, 999), (1000, 1049)]


def test_backfill_revisits_t5_only_call_and_completed_abstention_is_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = [
        {"id": 1, "date": "2026-05-01", "pair": "EURUSD"},
        {"id": 2, "date": "2026-05-04", "pair": "EURUSD"},
    ]
    query = _query(monkeypatch, calls)
    evaluations = {
        1: {"call_id": 1, "log_return_t5_bps": 10},
        2: {
            "call_id": 2, "log_return_t5_bps": 0, "log_return_t20_bps": 0,
            "brier_score_t5": None, "brier_score_t20": None,
        },
    }
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: evaluations[call_id])
    assert writer.get_unvalidated_regime_calls() == [calls[0]]
    assert "predicted_direction" in query.select.call_args.args[0].split(",")


def test_backfill_limit_applies_after_completed_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = [
        {"id": 1, "date": "2026-05-01", "pair": "EURUSD"},
        {"id": 2, "date": "2026-05-04", "pair": "EURUSD"},
    ]
    _query(monkeypatch, calls)
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: (
        {"call_id": 1, "log_return_t5_bps": 10, "log_return_t20_bps": 20}
        if call_id == 1 else None
    ))
    assert writer.get_unvalidated_regime_calls(limit=1) == [calls[1]]


def test_backfill_does_not_reuse_another_calls_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = [{"id": 2, "date": "2026-05-01", "pair": "EURUSD"}]
    _query(monkeypatch, calls)
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: {
        "call_id": 1, "log_return_t5_bps": 10, "log_return_t20_bps": 20,
    })
    assert writer.get_unvalidated_regime_calls() == calls


def test_backfill_paginates_past_supabase_default(monkeypatch: pytest.MonkeyPatch) -> None:
    first_page = [
        {"id": i, "date": "2026-05-01", "pair": "EURUSD"} for i in range(1000)
    ]
    last = {"id": 1000, "date": "2026-05-04", "pair": "EURUSD"}
    query = _query(monkeypatch, [])
    query.execute.side_effect = [SimpleNamespace(data=first_page), SimpleNamespace(data=[last])]
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda call_id: None)
    rows = writer.get_unvalidated_regime_calls()
    assert len(rows) == 1001
    assert rows[-1] == last
    assert query.range.call_args_list[1].args == (1000, 1999)
