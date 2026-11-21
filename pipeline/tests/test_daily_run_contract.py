"""Legacy daily orchestration must expose publication and validation truth."""

from __future__ import annotations

import ast
import asyncio
import inspect
import textwrap
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.db import writer as db_writer
from src.fetchers.buffer_keys import KEY_FX_SPOT
from src.scheduler import orchestrator
from src.scheduler.contracts import DailyRunOutput
from src.staged.contracts import StageHealth
from src.types import RegimeCall, SignalRow, SpotBar
from src.validation.coverage import ValidationRunResult

RUN_DATE = date(2026, 9, 26)
TEST_PAIRS = ("EURUSD", "USDJPY", "USDINR")


def _finalize(
    monkeypatch: pytest.MonkeyPatch,
    *,
    published_pairs: tuple[str, ...] = TEST_PAIRS,
    dqs_score: float | None = 0.95,
    stress_red: bool = False,
    signal_quality_notes: tuple[str, ...] = (),
) -> DailyRunOutput:
    monkeypatch.setattr(
        orchestrator,
        "run_validation",
        lambda *, as_of_date: ValidationRunResult(),
    )
    return orchestrator._finalize_daily_run(
        date_str=RUN_DATE.isoformat(),
        run_as_of=RUN_DATE,
        published_pairs=published_pairs,
        dqs_score=dqs_score,
        stress_red=stress_red,
        signal_quality_notes=signal_quality_notes,
        archive_health=StageHealth("PriceArchiveStage", "OK"),
    )


def test_validation_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_validation(*, as_of_date: date) -> None:
        assert as_of_date == RUN_DATE
        raise RuntimeError("validation unavailable")

    monkeypatch.setattr(orchestrator, "run_validation", fail_validation)

    with pytest.raises(RuntimeError, match="validation unavailable"):
        orchestrator._finalize_daily_run(
            date_str=RUN_DATE.isoformat(),
            run_as_of=RUN_DATE,
            published_pairs=TEST_PAIRS,
            dqs_score=0.95,
            stress_red=False,
            signal_quality_notes=(),
        )


def test_incomplete_withheld_invalid_quality_and_signal_notes_are_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _finalize(
        monkeypatch,
        published_pairs=(TEST_PAIRS[0],),
        dqs_score=float("nan"),
        stress_red=True,
        signal_quality_notes=("rate_inputs_unqualified", "rate_history_unavailable"),
    )

    assert output.health.status == "DEGRADED"
    assert output.published_pairs == (TEST_PAIRS[0],)
    signal, dqs, archive, publication, validation = output.stage_health
    assert signal.status == "DEGRADED"
    assert signal.notes == ["rate_inputs_unqualified", "rate_history_unavailable"]
    assert dqs.status == "DEGRADED"
    assert dqs.missing_fields == ["valid_dqs_score"]
    assert archive.status == "OK"
    assert publication.status == "DEGRADED"
    assert publication.missing_fields == list(TEST_PAIRS[1:])
    assert publication.notes == ["stress_withholding"]
    assert validation.status == "OK"


def test_healthy_synthetic_control_records_validation_and_no_healthy_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validation_dates: list[date] = []
    low_dqs_alerts: list[str] = []
    def healthy_validation(*, as_of_date: date) -> ValidationRunResult:
        validation_dates.append(as_of_date)
        return ValidationRunResult()

    monkeypatch.setattr(orchestrator, "run_validation", healthy_validation)
    monkeypatch.setattr(
        orchestrator,
        "alert_on_low_dqs",
        lambda *args, **kwargs: low_dqs_alerts.append("sent"),
    )

    output = orchestrator._finalize_daily_run(
        date_str=RUN_DATE.isoformat(),
        run_as_of=RUN_DATE,
        published_pairs=TEST_PAIRS,
        dqs_score=0.95,
        stress_red=False,
        signal_quality_notes=(),
        archive_health=StageHealth("PriceArchiveStage", "OK"),
    )

    assert output == DailyRunOutput(
        date=RUN_DATE.isoformat(),
        published_pairs=TEST_PAIRS,
        dqs_score=0.95,
        health=output.health,
        stage_health=output.stage_health,
    )
    assert output.health.status == "OK"
    assert [report.status for report in output.stage_health] == [
        "OK",
        "OK",
        "OK",
        "OK",
        "OK",
    ]
    assert output.stage_health[-1].stage_name == "ValidateStage"
    assert "validation_scan_completed" in output.stage_health[-1].notes
    assert validation_dates == [RUN_DATE]
    assert low_dqs_alerts == []
    assert not hasattr(orchestrator, "send_success_heartbeat")


def test_persist_records_only_matching_call_with_durable_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call = cast(
        RegimeCall,
        SimpleNamespace(pair=TEST_PAIRS[0], date=RUN_DATE),
    )
    signal = cast(
        SignalRow,
        SimpleNamespace(pair=TEST_PAIRS[0], date=RUN_DATE),
    )
    writes: list[tuple[Any, Any, str | None]] = []

    def persist(
        persisted_call: RegimeCall,
        signals: SignalRow,
        *,
        correlation_id: str | None,
    ) -> str:
        writes.append((persisted_call, signals, correlation_id))
        return "durable-42"

    monkeypatch.setattr(orchestrator, "persist_regime_call", persist)
    published: list[str] = []

    call_id = orchestrator._persist_daily_regime_call(
        call=call,
        signal_row=signal,
        requested_date=RUN_DATE,
        published_pairs=published,
        correlation_id="run-1",
    )

    assert call_id == "durable-42"
    assert published == [TEST_PAIRS[0]]
    assert writes == [(call, signal, "run-1")]


@pytest.mark.parametrize("durable_id", [None, "", 0, -1, False])
def test_persist_does_not_claim_invalid_durable_id(
    monkeypatch: pytest.MonkeyPatch,
    durable_id: object,
) -> None:
    call = cast(RegimeCall, SimpleNamespace(pair=TEST_PAIRS[0], date=RUN_DATE))
    signal = cast(SignalRow, SimpleNamespace(pair=TEST_PAIRS[0], date=RUN_DATE))
    monkeypatch.setattr(orchestrator, "persist_regime_call", lambda *args, **kwargs: durable_id)
    published: list[str] = []

    with pytest.raises(RuntimeError, match="no durable row id"):
        orchestrator._persist_daily_regime_call(
            call=call,
            signal_row=signal,
            requested_date=RUN_DATE,
            published_pairs=published,
            correlation_id=None,
        )

    assert published == []


def test_persist_rejects_wrong_date_before_writing(monkeypatch: pytest.MonkeyPatch) -> None:
    call = cast(RegimeCall, SimpleNamespace(pair=TEST_PAIRS[0], date=date(2026, 9, 25)))
    signal = cast(SignalRow, SimpleNamespace(pair=TEST_PAIRS[0], date=date(2026, 9, 25)))
    writes: list[str] = []
    monkeypatch.setattr(
        orchestrator,
        "persist_regime_call",
        lambda *args, **kwargs: writes.append("write"),
    )

    with pytest.raises(ValueError, match="does not match requested date"):
        orchestrator._persist_daily_regime_call(
            call=call,
            signal_row=signal,
            requested_date=RUN_DATE,
            published_pairs=[],
            correlation_id=None,
        )

    assert writes == []


def test_duplicate_is_rejected_before_writer_call(monkeypatch: pytest.MonkeyPatch) -> None:
    call = cast(RegimeCall, SimpleNamespace(pair=TEST_PAIRS[0], date=RUN_DATE))
    signal = cast(SignalRow, SimpleNamespace(pair=TEST_PAIRS[0], date=RUN_DATE))
    writes: list[str] = []
    monkeypatch.setattr(
        orchestrator,
        "persist_regime_call",
        lambda *args, **kwargs: writes.append("write"),
    )

    with pytest.raises(RuntimeError, match="Duplicate publication"):
        orchestrator._persist_daily_regime_call(
            call=call,
            signal_row=signal,
            requested_date=RUN_DATE,
            published_pairs=[TEST_PAIRS[0]],
            correlation_id=None,
        )

    assert writes == []


def test_finalize_rejects_pair_outside_locked_universe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(orchestrator, "run_validation", lambda *, as_of_date: None)

    with pytest.raises(ValueError, match="outside the locked universe"):
        orchestrator._finalize_daily_run(
            date_str=RUN_DATE.isoformat(),
            run_as_of=RUN_DATE,
            published_pairs=(*TEST_PAIRS, "GBPUSD"),
            dqs_score=0.95,
            stress_red=False,
            signal_quality_notes=(),
        )


def test_actual_run_daily_calls_contract_helpers_without_swallowing_finalizer() -> None:
    flow_source = textwrap.dedent(inspect.getsource(orchestrator.run_daily.fn))
    tree = ast.parse(flow_source)

    helper_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "_persist_daily_regime_call" in helper_calls
    assert "_finalize_daily_run" in helper_calls

    swallowed_calls = {
        node.func.id
        for try_node in (node for node in ast.walk(tree) if isinstance(node, ast.Try))
        for node in ast.walk(try_node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "_finalize_daily_run" not in swallowed_calls


def test_actual_run_daily_archives_before_any_publication() -> None:
    flow_source = textwrap.dedent(inspect.getsource(orchestrator.run_daily.fn))
    tree = ast.parse(flow_source)
    archive_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "archive_price_snapshot"
    ]
    publication_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_persist_daily_regime_call"
    ]

    assert len(archive_lines) == 1
    assert publication_lines
    assert archive_lines[0] < min(publication_lines)


def test_archive_failure_stops_legacy_run_before_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = datetime.now(UTC).date()
    retrieved_at = datetime.now(UTC)
    bar = SpotBar(
        date=today,
        pair="EURUSD",
        open=1.08,
        high=1.09,
        low=1.07,
        close=1.085,
        volume=1_000_000.0,
        provider="polygon",
        instrument="C:EURUSD",
        retrieved_at=retrieved_at,
        provider_timestamp=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
    )
    buffer = {KEY_FX_SPOT: {"EURUSD": (bar,)}}
    publications: list[str] = []

    async def fetched_buffer() -> dict[str, Any]:
        return buffer

    monkeypatch.setattr(orchestrator, "_require_pipeline_runtime_env", lambda: None)
    monkeypatch.setattr(orchestrator, "load_universe", lambda: {})
    monkeypatch.setattr(orchestrator, "build_master_buffer_task", fetched_buffer)
    monkeypatch.setattr(
        orchestrator,
        "validate_ingestion_buffer",
        lambda raw, *, universe: SimpleNamespace(telemetry_status="ONLINE", buffer=raw),
    )
    monkeypatch.setattr(
        orchestrator,
        "compute_dqs",
        lambda *args, **kwargs: SimpleNamespace(
            score=0.95,
            rates_freshness=1.0,
            spots_freshness=1.0,
            cot_freshness=1.0,
            commodities_freshness=1.0,
            cross_asset_freshness=1.0,
            critical_penalty_applied=False,
            spot_observation_date=today,
            cot_observation_date=today,
        ),
    )
    monkeypatch.setattr(orchestrator, "_log_dqs_band", lambda score: None)
    monkeypatch.setattr(
        db_writer,
        "archive_price_observations",
        lambda observations: (_ for _ in ()).throw(RuntimeError("archive unavailable")),
    )
    monkeypatch.setattr(
        orchestrator,
        "_persist_daily_regime_call",
        lambda **kwargs: publications.append("publish"),
    )

    with pytest.raises(RuntimeError, match="archive unavailable"):
        asyncio.run(orchestrator.run_daily.fn(today.isoformat()))

    assert publications == []


def test_live_daily_run_rejects_historical_date_before_runtime_or_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        orchestrator,
        "_require_pipeline_runtime_env",
        lambda: calls.append("env"),
    )
    monkeypatch.setattr(
        orchestrator,
        "build_master_buffer_task",
        lambda: calls.append("fetch"),
    )
    historical = datetime.now(UTC).date() - timedelta(days=1)

    with pytest.raises(ValueError, match="current UTC date"):
        asyncio.run(orchestrator.run_daily.fn(historical.isoformat()))

    assert calls == []


def test_live_daily_run_rejects_timestamp_without_truncating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        orchestrator,
        "_require_pipeline_runtime_env",
        lambda: calls.append("env"),
    )
    today = datetime.now(UTC).date().isoformat()

    with pytest.raises(ValueError, match="exact YYYY-MM-DD"):
        asyncio.run(orchestrator.run_daily.fn(f"{today}T00:00:00Z"))

    assert calls == []
