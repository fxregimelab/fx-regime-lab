"""Failure ordering and status evidence for actual staged publication/flow code."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from src.staged import orchestrator as flows
from src.staged.contracts import StageHealth, combine_stage_health
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.staged.stages import PublishStage, RegimeStage, SignalStage
from src.types import RegimeCall, SignalRow
from tests.fixtures.eurusd_snapshot import make_recorded_eurusd_snapshot


@pytest.fixture(autouse=True)
def direct_task_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run real task functions; existing flow tests separately exercise Prefect."""
    for name in (
        "_ingestion_task",
        "_signal_task",
        "_regime_task",
        "_publish_task",
        "_validate_task",
    ):
        monkeypatch.setattr(flows, name, getattr(flows, name).fn)


def publication_inputs() -> tuple[SignalRow, RegimeCall]:
    result = SignalStage().run("EURUSD", make_recorded_eurusd_snapshot())
    return result.signal_row, RegimeStage().run("EURUSD", result)


def test_health_merge_keeps_failed_status_and_input_details() -> None:
    degraded = StageHealth("IngestionStage", "DEGRADED", missing_fields=["cot"], notes=["stale"])
    failed = StageHealth("SignalStage", "FAILED", missing_fields=["cot", "spot"])
    result = combine_stage_health("Run", degraded, failed, StageHealth("PublishStage", "OK"))
    assert result.status == "FAILED"
    assert result.missing_fields == ["cot", "spot"]
    assert result.notes == ["IngestionStage:DEGRADED", "SignalStage:FAILED", "stale"]
    assert degraded.missing_fields == ["cot"]


def test_healthy_publication_completes_atomic_write_before_alerting() -> None:
    signal, call = publication_inputs()
    events: list[str] = []

    class OrderedWriter(FakeWriterPort):
        def publish_regime_call(
            self,
            call: RegimeCall,
            signal_row: SignalRow,
            **kwargs: Any,
        ) -> int | str | None:
            events.append("publish_started")
            result = super().publish_regime_call(call, signal_row, **kwargs)
            events.append("publish_returned")
            return result

    class OrderedAlert(FakeAlertPort):
        def send_success(self, call: RegimeCall) -> None:
            events.append("alert")
            super().send_success(call)

    writer, alert = OrderedWriter(), OrderedAlert()
    output = asyncio.run(
        PublishStage(writer, alert).run(
            "EURUSD",
            call,
            signal_row=signal,
            upstream_health=(StageHealth("Inputs", "OK"),),
        )
    )
    assert events == ["publish_started", "publish_returned", "alert"]
    assert writer.signal_rows[0].data_quality_notes == signal.data_quality_notes
    assert output.health.status == "OK"
    assert alert.successes == [call] and not alert.statuses
    assert output.stage_health[-1] == StageHealth("PublicationWrite", "OK")


@pytest.mark.parametrize("score", [None, float("nan"), -0.1, 1.1, 0.6])
def test_unavailable_or_low_quality_never_uses_success_channel(score: float | None) -> None:
    signal, call = publication_inputs()
    call = replace(call, data_quality_score=score)
    writer, alert = FakeWriterPort(), FakeAlertPort()
    output = asyncio.run(
        PublishStage(writer, alert).run(
            "EURUSD",
            call,
            signal_row=signal,
            upstream_health=(StageHealth("Inputs", "OK"),),
        )
    )
    assert output.health.status == "DEGRADED"
    assert len(writer.signal_rows) == len(writer.regime_calls) == 1
    assert not alert.successes
    assert alert.statuses[0]["health"].status == "DEGRADED"


def test_failed_upstream_and_wrong_identity_prevent_all_writes() -> None:
    signal, call = publication_inputs()
    for row, health in (
        (signal, StageHealth("SignalStage", "FAILED")),
        (replace(signal, pair="USDJPY"), StageHealth("SignalStage", "OK")),
        (replace(signal, date=signal.date - timedelta(days=1)), StageHealth("SignalStage", "OK")),
    ):
        writer, alert = FakeWriterPort(), FakeAlertPort()
        with pytest.raises(ValueError):
            asyncio.run(
                PublishStage(writer, alert).run(
                    "EURUSD",
                    call,
                    signal_row=row,
                    upstream_health=(health,),
                )
            )
        assert not writer.signal_rows and not writer.regime_calls and not alert.successes


def test_failed_atomic_write_leaves_no_half_write_or_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal, call = publication_inputs()
    writer, alert = FakeWriterPort(), FakeAlertPort()

    def fail_write(*args: Any, **kwargs: Any) -> int:
        raise RuntimeError("atomic publication failed")

    monkeypatch.setattr(writer, "publish_regime_call", fail_write)
    with pytest.raises(RuntimeError, match="atomic publication failed"):
        asyncio.run(
            PublishStage(writer, alert).run(
                "EURUSD",
                call,
                signal_row=signal,
                upstream_health=(StageHealth("Inputs", "OK"),),
            )
        )
    assert not writer.regime_calls and not writer.signal_rows
    assert not alert.successes and not alert.statuses


@pytest.mark.parametrize("receipt", [None, "", False, 0])
def test_missing_call_receipt_cannot_claim_publication(
    receipt: int | str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal, call = publication_inputs()
    writer, alert = FakeWriterPort(), FakeAlertPort()
    monkeypatch.setattr(writer, "publish_regime_call", lambda *args, **kwargs: receipt)
    with pytest.raises(RuntimeError, match="durable row id"):
        asyncio.run(
            PublishStage(writer, alert).run(
                "EURUSD",
                call,
                signal_row=signal,
                upstream_health=(StageHealth("Inputs", "OK"),),
            )
        )
    assert not alert.successes and not alert.statuses


def test_single_flow_preserves_degraded_source_details_and_writes_signal() -> None:
    snapshot = replace(
        make_recorded_eurusd_snapshot(),
        health=StageHealth(
            "IngestionStage",
            "DEGRADED",
            missing_fields=["cot"],
            notes=["source_delayed"],
        ),
    )
    writer, alert = FakeWriterPort(), FakeAlertPort()
    output = asyncio.run(
        flows.run_single_pair_flow.fn(
            "EURUSD",
            snapshot.date,
            fetcher=FakeFetcherPort(snapshot),
            writer=writer,
            alert=alert,
        )
    )
    assert output.health.status == "DEGRADED"
    assert "cot" in output.health.missing_fields
    assert "source_delayed" in output.health.notes
    assert "rate_history_unavailable" in output.health.notes
    assert len(writer.signal_rows) == len(writer.regime_calls) == 1
    assert not alert.successes and not alert.heartbeats


@pytest.mark.parametrize("failure", ["status", "date"])
def test_failed_or_mismatched_ingestion_stops_single_flow(failure: str) -> None:
    original = make_recorded_eurusd_snapshot()
    snapshot = (
        replace(original, health=StageHealth("IngestionStage", "FAILED"))
        if failure == "status"
        else replace(original, date=original.date - timedelta(days=1))
    )
    writer, alert = FakeWriterPort(), FakeAlertPort()
    with pytest.raises(ValueError):
        asyncio.run(
            flows.run_single_pair_flow.fn(
                "EURUSD",
                original.date,
                fetcher=FakeFetcherPort(snapshot),
                writer=writer,
                alert=alert,
            )
        )
    assert not writer.signal_rows and not writer.regime_calls
    assert alert.statuses[-1]["health"].status == "FAILED"
    assert alert.statuses[-1]["health"].stage_name == "IngestionStage"


def test_validation_failure_cannot_send_daily_success(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = make_recorded_eurusd_snapshot()
    writer, alert = FakeWriterPort(), FakeAlertPort()

    def fail_validation(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("validation unavailable")

    monkeypatch.setattr(flows, "_validate_task", fail_validation)
    with pytest.raises(RuntimeError, match="validation unavailable"):
        asyncio.run(
            flows.run_multi_pair_flow.fn(
                snapshot.date,
                pairs=["EURUSD"],
                fetcher=FakeFetcherPort(snapshot),
                writer=writer,
                alert=alert,
            )
        )
    assert len(writer.regime_calls) == 1
    assert not alert.heartbeats
    assert alert.statuses[-1]["health"] == StageHealth(
        "ValidateStage",
        "FAILED",
        notes=["RuntimeError"],
    )


def test_skipped_validation_is_reported_as_incomplete() -> None:
    snapshot = make_recorded_eurusd_snapshot()
    alert = FakeAlertPort()
    output = asyncio.run(
        flows.run_multi_pair_flow.fn(
            snapshot.date,
            pairs=["EURUSD"],
            fetcher=FakeFetcherPort(snapshot),
            writer=FakeWriterPort(),
            alert=alert,
            run_validation=False,
        )
    )
    assert output.health.status == "DEGRADED"
    assert "validation_not_run" in output.health.notes
    assert output.stage_health[-1].stage_name == "ValidateStage"
    assert not alert.heartbeats


def test_failed_signal_stage_stops_before_any_write(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = make_recorded_eurusd_snapshot()
    result = replace(
        SignalStage().run("EURUSD", snapshot), health=StageHealth("SignalStage", "FAILED")
    )
    monkeypatch.setattr(flows, "_signal_task", lambda *args: result)
    writer, alert = FakeWriterPort(), FakeAlertPort()
    with pytest.raises(ValueError, match="Signal stage reported FAILED"):
        asyncio.run(
            flows.run_single_pair_flow.fn(
                "EURUSD",
                snapshot.date,
                fetcher=FakeFetcherPort(snapshot),
                writer=writer,
                alert=alert,
            )
        )
    assert not writer.signal_rows and not writer.regime_calls
    assert alert.statuses[-1]["health"].stage_name == "SignalStage"


def test_publication_failure_is_reported_without_masking_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = make_recorded_eurusd_snapshot()
    writer, alert = FakeWriterPort(), FakeAlertPort()

    def fail_write(*args: Any, **kwargs: Any) -> int:
        raise RuntimeError("write unavailable")

    def fail_notice(*args: Any, **kwargs: Any) -> None:
        raise ConnectionError("notification unavailable")

    monkeypatch.setattr(writer, "publish_regime_call", fail_write)
    monkeypatch.setattr(alert, "send_status", fail_notice)
    with pytest.raises(RuntimeError, match="write unavailable"):
        asyncio.run(
            flows.run_single_pair_flow.fn(
                "EURUSD",
                snapshot.date,
                fetcher=FakeFetcherPort(snapshot),
                writer=writer,
                alert=alert,
            )
        )
    assert not alert.successes and not alert.heartbeats


@pytest.mark.parametrize("pairs", [[], ["EURUSD", "EURUSD"]])
def test_empty_or_duplicate_pair_requests_cannot_report_completion(pairs: list[str]) -> None:
    snapshot = make_recorded_eurusd_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    alert = FakeAlertPort()
    with pytest.raises(ValueError, match="nonempty and unique"):
        asyncio.run(
            flows.run_multi_pair_flow.fn(
                snapshot.date,
                pairs=pairs,
                fetcher=fetcher,
                writer=FakeWriterPort(),
                alert=alert,
            )
        )
    assert not fetcher.calls and not alert.heartbeats


def test_publication_requires_explicit_stage_evidence() -> None:
    signal, call = publication_inputs()
    writer, alert = FakeWriterPort(), FakeAlertPort()
    with pytest.raises(ValueError, match="stage health evidence"):
        asyncio.run(
            PublishStage(writer, alert).run(
                "EURUSD",
                call,
                signal_row=signal,
                upstream_health=(),
            )
        )
    assert not writer.signal_rows and not writer.regime_calls
