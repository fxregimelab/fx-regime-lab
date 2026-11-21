"""Atomic writer requests and preservation of original publication evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core import regime_persist
from src.db import writer
from src.staged.stages import RegimeStage, SignalStage
from src.types import RegimeCall, SignalRow
from tests.fixtures.eurusd_snapshot import make_recorded_eurusd_snapshot


def publication() -> tuple[RegimeCall, SignalRow]:
    result = SignalStage().run("EURUSD", make_recorded_eurusd_snapshot())
    return RegimeStage().run("EURUSD", result), result.signal_row


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock()
    fake.rpc.return_value.execute.return_value = SimpleNamespace(data=71)
    monkeypatch.setattr(writer, "_client", lambda: fake)
    return fake


def test_complete_publication_uses_one_rpc_and_preserves_signal_fields(client: MagicMock) -> None:
    call, signal = publication()
    signal.risk_reversal_source = "synthetic_proxy"
    signal.data_quality_notes = ["rate_history_unavailable"]
    assert writer.publish_regime_call(call, signal, correlation_id="attempt-1") == 71
    name, request = client.rpc.call_args.args
    assert name == "append_regime_publication"
    assert request["p_call"]["predicted_direction"] == call.predicted_direction
    assert request["p_call"]["correlation_id"] == "attempt-1"
    assert request["p_signal"]["data_quality_notes"] == ["rate_history_unavailable"]
    assert request["p_signal"]["risk_reversal_source"] == "synthetic_proxy"
    signal.data_quality_notes.append("later_mutation")
    assert request["p_signal"]["data_quality_notes"] == ["rate_history_unavailable"]
    client.rpc.assert_called_once()
    client.table.assert_not_called()


@pytest.mark.parametrize(
    "defect",
    ["pair", "date", "source", "model", "strategy", "direction", "nan", "predecessor", "rationale"],
)
def test_invalid_publication_stops_before_any_io(defect: str, client: MagicMock) -> None:
    call, signal = publication()
    kwargs: dict[str, Any] = {}
    if defect == "pair":
        call = replace(call, pair="GBPUSD")
    elif defect == "date":
        signal = replace(signal, date=signal.date - timedelta(days=1))
    elif defect == "source":
        call = replace(call, data_source="unknown")
    elif defect == "model":
        call = replace(call, model_version=None)
    elif defect == "strategy":
        call = replace(call, strategy_version=" ")
    elif defect == "direction":
        call = replace(call, predicted_direction=None)
    elif defect == "nan":
        signal = replace(signal, spot=float("nan"))
    elif defect == "predecessor":
        kwargs["supersedes_call_id"] = True
    else:
        kwargs["rationale"] = {"call_id": 12, "date": call.date.isoformat(), "pair": call.pair}
    with pytest.raises(ValueError):
        writer.publish_regime_call(call, signal, **kwargs)
    client.rpc.assert_not_called()
    client.table.assert_not_called()


@pytest.mark.parametrize("receipt", [None, False, "71", 0, -1, [], {}])
def test_invalid_rpc_receipt_cannot_claim_publication(receipt: Any, client: MagicMock) -> None:
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=receipt)
    call, signal = publication()
    with pytest.raises(RuntimeError, match="durable integer"):
        writer.publish_regime_call(call, signal)
    client.table.assert_not_called()


def test_rpc_failure_propagates_without_nonatomic_fallback(client: MagicMock) -> None:
    error = RuntimeError("publication conflict")
    client.rpc.return_value.execute.side_effect = error
    call, signal = publication()
    with pytest.raises(RuntimeError) as raised:
        writer.publish_regime_call(call, signal)
    assert raised.value is error
    client.table.assert_not_called()


def test_unbound_call_and_force_purge_are_rejected_before_io(client: MagicMock) -> None:
    call, _ = publication()
    with pytest.raises(RuntimeError, match="signal evidence"):
        writer.write_regime_call(call)
    for force in (False, True):
        with pytest.raises(RuntimeError, match="originals cannot be purged"):
            writer.delete_pipeline_data_for_date(call.date.isoformat(), force=force)
    client.table.assert_not_called()
    client.rpc.assert_not_called()


def test_bulk_preflights_entire_batch_before_first_write(monkeypatch: pytest.MonkeyPatch) -> None:
    call, signal = publication()
    call = replace(call, data_source="backtest", model_version="replay-v3")
    publish = MagicMock()
    monkeypatch.setattr(writer, "publish_regime_call", publish)
    bad = replace(call, data_source="live", date=call.date + timedelta(days=1))
    with pytest.raises(ValueError, match="backtest"):
        writer.bulk_write_backfill_results(
            "EURUSD", [(signal, call), (replace(signal, date=bad.date), bad)]
        )
    publish.assert_not_called()
    with pytest.raises(ValueError, match="duplicate"):
        writer.bulk_write_backfill_results("EURUSD", [(signal, call), (signal, call)])
    publish.assert_not_called()


def test_bulk_appends_via_atomic_boundary_and_failed_prefix_can_be_retried(
    monkeypatch: pytest.MonkeyPatch, client: MagicMock
) -> None:
    call, signal = publication()
    call = replace(call, data_source="backtest", model_version="replay-v3")
    next_call = replace(call, date=call.date + timedelta(days=1))
    rows = [(signal, call), (replace(signal, date=next_call.date), next_call)]
    publish = MagicMock(side_effect=[71, ConnectionError("second write failed")])
    monkeypatch.setattr(writer, "publish_regime_call", publish)
    with pytest.raises(ConnectionError):
        writer.bulk_write_backfill_results("EURUSD", rows)
    assert publish.call_count == 2
    publish.reset_mock(side_effect=True)
    publish.side_effect = [71, 72]
    writer.bulk_write_backfill_results("EURUSD", rows)
    assert [args.args[0].date for args in publish.call_args_list] == [call.date, next_call.date]
    client.table.assert_not_called()


def test_core_builds_rationale_before_one_atomic_write_and_keeps_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call, signal = publication()
    call = replace(
        call,
        data_source="backtest",
        model_version="replay-v3",
        strategy_version="test-v3",
        data_quality_score=0.43,
    )
    signal.volume_rvol = 999.0
    publish = MagicMock(return_value=71)
    monkeypatch.setattr(writer, "publish_regime_call", publish)
    assert regime_persist.persist_regime_call(call, signal, correlation_id="trace") == 71
    publish.assert_called_once()
    assert call.data_source == "backtest" and call.strategy_version == "test-v3"
    rationale = publish.call_args.kwargs["rationale"]
    assert "DQS=0.43" in rationale["confidence_explanation"]
    assert "999" not in rationale["confidence_explanation"]
    assert "not a calibrated probability" in rationale["confidence_explanation"]
    assert rationale["call_id"] is None


def test_retrospective_rationale_never_overwrites_existing_content(client: MagicMock) -> None:
    row = {"call_id": 71, "date": "2026-05-20", "pair": "EURUSD", "layer1_reasoning": "original"}
    query = client.table.return_value
    query.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[dict(row)]
    )
    writer.write_call_rationale([dict(row)])
    query.insert.assert_not_called()
    with pytest.raises(ValueError, match="immutable"):
        writer.write_call_rationale([{**row, "layer1_reasoning": "retrospective rewrite"}])
    query.upsert.assert_not_called()
    query.update.assert_not_called()


def test_missing_retrospective_rationale_is_inserted_without_mutating_existing_rows(
    client: MagicMock,
) -> None:
    query = client.table.return_value
    query.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=[])
    row = {
        "call_id": 71,
        "date": "2026-05-20",
        "pair": "EURUSD",
        "confidence_explanation": "Retrospective explanation",
    }
    writer.write_call_rationale([row])
    query.insert.assert_called_once_with(row)
    query.upsert.assert_not_called()
