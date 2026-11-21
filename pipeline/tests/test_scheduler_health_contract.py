"""Exercise scheduled execution, failures and actual overnight status boundaries."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from src import config
from src.db import writer
from src.scheduler import overnight_check as overnight
from src.scheduler import run_pipeline as pipeline
from src.staged.contracts import StageHealth
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from tests.test_run_pipeline_flags import _sample_v2_output
from tests.test_run_pipeline_flags import patched_pipeline as _pipeline_fixture
from tests.test_staged_multi_pair import _make_multi_pair_snapshot

_SCHEDULED_FLOW = pipeline.run_pipeline
_V2_LIVE = pipeline._run_v2_live_pipeline


@pytest.fixture(name="patched_pipeline")
def scheduler_ports(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    return cast(dict[str, MagicMock], cast(Any, _pipeline_fixture).__wrapped__(monkeypatch))


@pytest.fixture(autouse=True)
def flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", False)
    monkeypatch.setattr(config, "SHADOW_V2", False)


def test_configured_entrypoint_runs_required_stages_in_order(
    patched_pipeline: dict[str, MagicMock],
) -> None:
    deployment = yaml.safe_load((Path(__file__).parents[1] / "prefect.yaml").read_text())
    entry = deployment["deployments"][0]["entrypoint"]
    assert entry == "src/scheduler/run_pipeline.py:run_pipeline"
    module_path, name = entry.split(":")
    entrypoint = getattr(
        importlib.import_module(module_path.removesuffix(".py").replace("/", ".")), name
    )
    events: list[str] = []
    original = patched_pipeline["run_daily"].return_value

    async def daily(*args: Any, **kwargs: Any) -> Any:
        events.extend(["publication", "validation"])
        return original

    patched_pipeline["run_daily"].side_effect = daily

    def overnight_result(**kwargs: Any) -> StageHealth:
        events.append("overnight")
        return StageHealth("overnight_check", "OK")

    def aggregate_result(**kwargs: Any) -> list[object]:
        events.append("aggregate")
        return [object()]

    patched_pipeline["run_overnight_check"].side_effect = overnight_result
    patched_pipeline["run_aggregate_stats"].side_effect = aggregate_result
    patched_pipeline["write_pipeline_run"].side_effect = lambda row: events.append("health")
    patched_pipeline["send_success_heartbeat"].side_effect = lambda **kw: events.append("heartbeat")
    result = entrypoint("2026-05-20")
    assert result.status == "OK"
    assert events == ["publication", "validation", "overnight", "aggregate", "health", "heartbeat"]
    patched_pipeline["send_success_heartbeat"].assert_called_once_with(
        date_str="2026-05-20", pairs_processed=3, regime_calls_count=3, dqs_score=0.95
    )
    patched_pipeline["run_aggregate_stats"].assert_called_once_with(as_of_date=date(2026, 5, 20))
    row = patched_pipeline["write_pipeline_run"].call_args.args[0]
    assert row["validation_stats_computed"] is True and row["status"] == "HEALTHY"
    assert row["ai_briefs_generated"] is None


@pytest.mark.parametrize(
    "broken", ["run_daily", "run_overnight_check", "run_aggregate_stats", "write_pipeline_run"]
)
def test_required_failure_survives_diagnostic_failures(
    broken: str, patched_pipeline: dict[str, MagicMock]
) -> None:
    error = RuntimeError("original stage error")
    patched_pipeline[broken].side_effect = error
    patched_pipeline["write_pipeline_error"].side_effect = ConnectionError("diagnostic failed")
    patched_pipeline["ProductionAlertPort"].return_value.send_status.side_effect = ConnectionError(
        "notice failed"
    )
    with pytest.raises(RuntimeError) as raised:
        pipeline.run_pipeline("2026-05-20")
    assert raised.value is error
    patched_pipeline["send_success_heartbeat"].assert_not_called()
    if broken != "write_pipeline_run":
        row = patched_pipeline["write_pipeline_run"].call_args.args[0]
        assert row["status"] == "FAILED"
        assert row["steps_failed"]
        if broken == "run_daily":
            assert row["regime_calls_count"] is None


@pytest.mark.parametrize("dqs", [None, float("nan"), float("inf"), -0.1, 1.1, 0.0, 0.6])
def test_missing_or_invalid_quality_is_never_replaced_with_one(
    dqs: float | None, patched_pipeline: dict[str, MagicMock]
) -> None:
    original = patched_pipeline["run_daily"].return_value
    patched_pipeline["run_daily"].return_value = replace(original, dqs_score=dqs)
    result = pipeline.run_pipeline("2026-05-20")
    assert result.status == "DEGRADED"
    patched_pipeline["send_success_heartbeat"].assert_not_called()
    row = patched_pipeline["write_pipeline_run"].call_args.args[0]
    assert row["dqs_score"] == (dqs if dqs in (0.0, 0.6) else None)
    assert row["status"] == "DEGRADED"


def test_v2_degradation_and_missing_pair_quality_survive_wrapper(
    patched_pipeline: dict[str, MagicMock], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", True)
    output = _sample_v2_output()
    pair_output = output.outputs["EURUSD"]
    output.outputs["EURUSD"] = replace(
        pair_output,
        regime_call=replace(pair_output.regime_call, data_quality_score=None),
        health=StageHealth("SignalStage", "DEGRADED", notes=["rate_history_unavailable"]),
    )
    patched_pipeline["_run_v2_live_pipeline"].return_value = output
    result = pipeline.run_pipeline("2026-05-20")
    assert result.status == "DEGRADED" and "rate_history_unavailable" in result.notes
    assert patched_pipeline["write_pipeline_run"].call_args.args[0]["dqs_score"] is None
    patched_pipeline["send_success_heartbeat"].assert_not_called()


def test_missing_pair_is_reported_with_actual_count(patched_pipeline: dict[str, MagicMock]) -> None:
    original = patched_pipeline["run_daily"].return_value
    patched_pipeline["run_daily"].return_value = replace(original, published_pairs=("EURUSD",))
    result = pipeline.run_pipeline("2026-05-20")
    assert result.status == "DEGRADED" and result.missing_fields == ["USDINR", "USDJPY"]
    assert patched_pipeline["write_pipeline_run"].call_args.args[0]["regime_calls_count"] == 1
    patched_pipeline["send_success_heartbeat"].assert_not_called()


@pytest.mark.parametrize("defect", ["date", "validation", "extra_pair", "duplicate_pair", "failed"])
def test_invalid_return_contract_cannot_be_accepted(
    defect: str, patched_pipeline: dict[str, MagicMock]
) -> None:
    original = patched_pipeline["run_daily"].return_value
    choices: dict[str, dict[str, Any]] = {
        "date": {"date": "2026-05-19"},
        "validation": {"stage_health": ()},
        "extra_pair": {"published_pairs": ("EURUSD", "GBPUSD")},
        "duplicate_pair": {"published_pairs": ("EURUSD", "EURUSD")},
        "failed": {"health": StageHealth("SignalStage", "FAILED")},
    }
    changes = choices[defect]
    patched_pipeline["run_daily"].return_value = replace(original, **changes)
    with pytest.raises(RuntimeError):
        pipeline.run_pipeline("2026-05-20")
    patched_pipeline["send_success_heartbeat"].assert_not_called()
    patched_pipeline["run_aggregate_stats"].assert_not_called()


@pytest.mark.parametrize("mode", ["exception", "divergence"])
def test_shadow_problem_is_visible_but_live_stages_continue(
    mode: str, patched_pipeline: dict[str, MagicMock], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "SHADOW_V2", True)
    monkeypatch.setattr(pipeline, "_get_v1_outputs_for_date", lambda value: ({}, {}))
    shadow = (
        AsyncMock(side_effect=RuntimeError("shadow failed"))
        if mode == "exception"
        else AsyncMock(return_value=MagicMock(equivalent=False))
    )
    monkeypatch.setattr(pipeline, "run_shadow_comparison", shadow)
    result = pipeline.run_pipeline("2026-05-20")
    assert result.status == "DEGRADED"
    patched_pipeline["run_aggregate_stats"].assert_called_once()
    patched_pipeline["send_success_heartbeat"].assert_not_called()
    assert any(
        row["stage_name"] == "shadow_v2"
        for row in patched_pipeline["write_pipeline_run"].call_args.args[0]["errors"]
    )


def test_no_aggregates_is_degraded(patched_pipeline: dict[str, MagicMock]) -> None:
    patched_pipeline["run_aggregate_stats"].return_value = []
    result = pipeline.run_pipeline("2026-05-20")
    assert "no_aggregate_rows" in result.notes
    assert (
        patched_pipeline["write_pipeline_run"].call_args.args[0]["validation_stats_computed"]
        is False
    )
    patched_pipeline["send_success_heartbeat"].assert_not_called()


@pytest.mark.parametrize("staged", [False, True])
def test_completed_validation_with_missing_outcomes_reaches_aggregate_and_health(
    staged: bool, patched_pipeline: dict[str, MagicMock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", staged)
    scan = StageHealth("ValidateStage", "DEGRADED", notes=[
        "validation_scan_completed", "missing_horizons=2",
    ])
    source = "_run_v2_live_pipeline" if staged else "run_daily"
    output = patched_pipeline[source].return_value
    patched_pipeline[source].return_value = replace(output, stage_health=(scan,))
    result = pipeline.run_pipeline("2026-05-20")
    assert result.status == "DEGRADED" and "missing_horizons=2" in result.notes
    patched_pipeline["run_aggregate_stats"].assert_called_once()
    patched_pipeline["run_overnight_check"].assert_called_once()
    patched_pipeline["send_success_heartbeat"].assert_not_called()
    record = patched_pipeline["write_pipeline_run"].call_args.args[0]
    assert record["status"] == "DEGRADED" and record["validation_stats_computed"]
    assert "validation" in record["steps_completed"]
    assert any("missing_horizons=2" in report["notes"] for report in record["errors"])


@pytest.mark.parametrize("reports", [
    (StageHealth("ValidateStage", "OK"),),
    (StageHealth("ValidateStage", "DEGRADED", notes=["validation_not_run"]),),
    (StageHealth("ValidateStage", "FAILED", notes=["validation_scan_completed"]),),
    (StageHealth("ValidateStage", "DEGRADED", notes=[
        "validation_scan_completed", "validation_not_run",
    ]),),
    (StageHealth("ValidateStage", "OK", notes=["validation_scan_completed"]),) * 2,
])
def test_wrapper_rejects_unsupported_validation_success(
    reports: tuple[StageHealth, ...], patched_pipeline: dict[str, MagicMock],
) -> None:
    original = patched_pipeline["run_daily"].return_value
    patched_pipeline["run_daily"].return_value = replace(original, stage_health=reports)
    with pytest.raises(RuntimeError):
        pipeline.run_pipeline("2026-05-20")
    patched_pipeline["run_aggregate_stats"].assert_not_called()
    patched_pipeline["send_success_heartbeat"].assert_not_called()


def test_v2_wrapper_suppresses_premature_run_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    staged = AsyncMock(return_value=_sample_v2_output())
    monkeypatch.setattr(pipeline, "run_multi_pair_flow", staged)
    asyncio.run(pipeline._run_v2_live_pipeline("2026-05-20", "correlation"))
    assert staged.call_args.kwargs["send_run_status"] is False


@pytest.fixture
def overnight_ports(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    mocks = {
        name: MagicMock()
        for name in ["fetch_proxy_basket", "_write_state", "_set_all_latest_cards_offline"]
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(overnight, name, mock)
    monkeypatch.setattr(overnight, "load_universe", lambda: {})
    monkeypatch.setattr(
        overnight, "_read_state", lambda: {"consecutive_failures": 0, "invalidation_streak": {}}
    )
    mocks["fetch_proxy_basket"].return_value = overnight.ProxyBasket(
        {p: 1.0 for p in ("EURUSD", "USDJPY", "USDINR")}, 20.0, 100.0
    )
    for name in [
        "get_signal_for_pair_date",
        "get_latest_desk_open_card",
        "update_desk_open_card_flags",
        "update_desk_open_card_telemetry_audit",
    ]:
        mocks[name] = MagicMock()
        monkeypatch.setattr(writer, name, mocks[name])
    mocks["get_signal_for_pair_date"].return_value = {
        "date": date.today().isoformat(),
        "spot": 1.0,
        "realized_vol_20d": 1.0,
        "cross_asset_vix": 20.0,
    }
    mocks["get_latest_desk_open_card"].return_value = {"date": date.today().isoformat()}
    return mocks


def test_overnight_actual_success_reports_three_checked_pairs(
    overnight_ports: dict[str, MagicMock],
) -> None:
    result = overnight.run_overnight_check()
    assert result.status == "OK"
    assert overnight_ports["update_desk_open_card_flags"].call_count == 3


def test_overnight_fetch_error_reaches_scheduler(overnight_ports: dict[str, MagicMock]) -> None:
    error = ConnectionError("source unavailable")
    overnight_ports["fetch_proxy_basket"].side_effect = error
    overnight_ports["_write_state"].side_effect = OSError("state unavailable")
    with pytest.raises(ConnectionError) as raised:
        overnight.run_overnight_check()
    assert raised.value is error
    overnight_ports["update_desk_open_card_flags"].assert_not_called()


@pytest.mark.parametrize("defect", ["missing_signal", "old_card", "nonfinite"])
def test_overnight_skipped_pairs_are_degraded(
    defect: str, overnight_ports: dict[str, MagicMock]
) -> None:
    if defect == "missing_signal":
        overnight_ports["get_signal_for_pair_date"].return_value = None
    elif defect == "old_card":
        overnight_ports["get_latest_desk_open_card"].return_value = {"date": "2000-01-01"}
    else:
        overnight_ports["get_signal_for_pair_date"].return_value["spot"] = float("nan")
    result = overnight.run_overnight_check()
    assert result.status == "DEGRADED" and len(result.missing_fields) == 3
    overnight_ports["update_desk_open_card_flags"].assert_not_called()


def test_historical_run_cannot_use_current_overnight_prices(
    overnight_ports: dict[str, MagicMock],
) -> None:
    result = overnight.run_overnight_check(as_of=date.today() - timedelta(days=1))
    assert result.status == "DEGRADED"
    overnight_ports["fetch_proxy_basket"].assert_not_called()


def test_health_writer_uses_single_upsert_without_deleting_previous_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", lambda: client)
    writer.write_pipeline_run({"date": "2026-05-20", "status": "DEGRADED"})
    table = client.table.return_value
    table.upsert.assert_called_once_with(
        {"date": "2026-05-20", "status": "DEGRADED"}, on_conflict="date"
    )
    table.delete.assert_not_called()
    table.insert.assert_not_called()
    error = ConnectionError("upsert unavailable")
    table.upsert.return_value.execute.side_effect = error
    with pytest.raises(ConnectionError) as raised:
        writer.write_pipeline_run({"date": "2026-05-20", "status": "HEALTHY"})
    assert raised.value is error
    table.delete.assert_not_called()


@pytest.mark.parametrize("invalid", ["", "2026-05-20junk", "2026-02-30"])
def test_invalid_health_date_does_not_reach_database(
    invalid: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", client)
    with pytest.raises(ValueError):
        writer.write_pipeline_run({"date": invalid})
    client.assert_not_called()


@pytest.mark.parametrize("aggregate_fails", [False, True])
def test_actual_prefect_wrapper_and_staged_flow_share_completion_boundary(
    aggregate_fails: bool,
    patched_pipeline: dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", True)
    monkeypatch.setenv("PREFECT_API_URL", "")
    snapshot = _make_multi_pair_snapshot()
    fake_writer, fake_alert = FakeWriterPort(), FakeAlertPort()
    monkeypatch.setattr(pipeline, "_run_v2_live_pipeline", _V2_LIVE)
    monkeypatch.setattr(pipeline, "ProductionFetcherPort", lambda: FakeFetcherPort(snapshot))
    monkeypatch.setattr(pipeline, "ProductionWriterPort", lambda: fake_writer)
    monkeypatch.setattr(pipeline, "ProductionAlertPort", lambda: fake_alert)
    if aggregate_fails:
        patched_pipeline["run_aggregate_stats"].side_effect = RuntimeError("aggregate failed")
        with pytest.raises(RuntimeError, match="aggregate failed"):
            _SCHEDULED_FLOW(snapshot.date.isoformat())
        assert fake_alert.statuses[-1]["health"].status == "FAILED"
    else:
        result = _SCHEDULED_FLOW(snapshot.date.isoformat())
        assert result.status == "DEGRADED"
        assert fake_alert.statuses[-1]["health"].stage_name == "DailyPipeline"
    assert len(fake_writer.signal_rows) == len(fake_writer.regime_calls) == 3
    # Three pair notices and one final wrapper notice; no inner run completion.
    assert len(fake_alert.statuses) == 4
    assert not fake_alert.heartbeats and not fake_alert.successes
    patched_pipeline["send_success_heartbeat"].assert_not_called()
