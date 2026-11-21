"""Persistence must fail closed; PostgreSQL owns atomic horizon completion."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.db import writer
from src.validation.calculator import EVALUATION_VERSION


def test_writer_uses_one_transaction_rpc(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", lambda: client)
    row = {"call_id": 42, "pair": "EURUSD", "call_date": "2026-05-01"}
    writer.write_validation_row(row)
    client.rpc.assert_called_once_with("append_validation_evaluation", {
        "p_payload": {**row, "evaluation_version": EVALUATION_VERSION}
    })
    client.rpc.return_value.execute.assert_called_once_with()
    client.table.assert_not_called()
    assert "evaluation_version" not in row


@pytest.mark.parametrize("row", [
    {}, {"call_id": None}, {"call_id": True}, {"call_id": ""},
    {"call_id": 42, "evaluation_version": "legacy-unversioned"},
])
def test_invalid_identity_or_version_rejected_before_io(
    monkeypatch: pytest.MonkeyPatch, row: dict[str, object]
) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", lambda: client)
    with pytest.raises(ValueError):
        writer.write_validation_row(row)
    client.rpc.assert_not_called()
    client.table.assert_not_called()


def test_rpc_failure_propagates_without_lossy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("schema not migrated")
    monkeypatch.setattr(writer, "_client", lambda: client)
    with pytest.raises(RuntimeError, match="schema not migrated"):
        writer.write_validation_row({"call_id": 42})
    client.table.assert_not_called()


def test_read_filters_current_evaluation_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.maybe_single.return_value.execute.return_value.data = None
    monkeypatch.setattr(writer, "_client", lambda: client)
    assert writer.get_validation_log_for_call(42) is None
    assert ("evaluation_version", EVALUATION_VERSION) in [c.args for c in query.eq.call_args_list]


def test_read_failure_does_not_reinterpret_legacy_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.table.return_value.select.side_effect = RuntimeError("missing evaluation_version")
    monkeypatch.setattr(writer, "_client", lambda: client)
    with pytest.raises(RuntimeError, match="missing evaluation_version"):
        writer.get_validation_log_for_call(42)


def test_exact_call_lookup_has_no_date_limit_or_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value = query
    query.maybe_single.return_value.execute.return_value.data = {"call_id": 42}
    monkeypatch.setattr(writer, "_client", lambda: client)
    assert writer.get_validation_log_for_call(42) == {"call_id": 42}
    assert [c.args for c in query.eq.call_args_list] == [
        ("call_id", 42), ("evaluation_version", EVALUATION_VERSION), ("is_superseded", False)]
    query.limit.assert_not_called()
    query.maybe_single.return_value.execute.side_effect = RuntimeError("duplicate current identity")
    with pytest.raises(RuntimeError, match="duplicate current identity"):
        writer.get_validation_log_for_call(42)


def test_aggregate_reader_never_mixes_legacy_evaluations(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.lte.return_value = query
    query.execute.return_value.data = []
    monkeypatch.setattr(writer, "_client", lambda: client)
    assert writer.get_validation_log_for_stats() == []
    assert ("evaluation_version", EVALUATION_VERSION) in [c.args for c in query.eq.call_args_list]
    query.order.assert_called_once_with("id")
    client.table.assert_called_once_with("validation_observations")
    assert ("population_version", "published-calls-v1") in [c.args for c in query.eq.call_args_list]


def test_stats_reader_anchors_window_and_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value
    for method in ("eq", "order", "range", "lte", "gte"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [SimpleNamespace(data=[{"id": i} for i in range(1000)]),
                                 SimpleNamespace(data=[{"id": 1000}])]
    monkeypatch.setattr(writer, "_client", lambda: client)
    rows = writer.get_validation_log_for_stats("EURUSD", 90, date(2026, 9, 1))
    assert len(rows) == 1001
    query.lte.assert_called_once_with("date", "2026-09-01")
    query.gte.assert_called_once_with("date", "2026-06-04")
    assert [c.args for c in query.range.call_args_list] == [(0, 999), (1000, 1999)]


@pytest.mark.parametrize("change", [
    {"population_version": None}, {"data_source": None}, {"model_version": " "},
    {"window_days": -1},
    {"window_days": True}, {"window_days": 1.5},
])
def test_snapshot_rejects_ambiguous_cohort_before_io(
    monkeypatch: pytest.MonkeyPatch, change: dict[str, object]
) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", lambda: client)
    row = {"data_source": "live", "strategy_version": "v2", "model_version": "2.0-live",
           "population_version": "published-calls-v1",
           "evaluation_version": EVALUATION_VERSION, "window_days": 0, **change}
    with pytest.raises(ValueError):
        writer.write_validation_stats(row)
    client.table.assert_not_called()


def test_snapshot_conflict_key_preserves_other_cohorts(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", lambda: client)
    row = {"data_source": "live", "strategy_version": "v2", "model_version": "2.0-live",
           "population_version": "published-calls-v1",
           "evaluation_version": EVALUATION_VERSION, "window_days": 0}
    writer.write_validation_stats(row)
    client.table.return_value.upsert.assert_called_once_with(
        row, on_conflict=(
            "as_of_date,pair,data_source,strategy_version,"
            "model_version,evaluation_version,window_days,population_version"
        )
    )
