"""Tests for the USE_V2_PIPELINE and SHADOW_V2 feature flags in run_pipeline."""

from __future__ import annotations

import datetime
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src import config
from src.scheduler.contracts import DailyRunOutput
from src.staged.contracts import MultiPairRunOutput, PublishOutput, StageHealth
from src.types import RegimeCall


def _sample_regime_call() -> RegimeCall:
    return RegimeCall(
        pair="EURUSD",
        date=datetime.date(2026, 5, 20),
        regime="RALLY",
        confidence=0.72,
        signal_composite=0.35,
        rate_signal="BULLISH",
        primary_driver="rates",
        entry_timing="ENTER",
        position_size="FULL",
        stop_level=1.06,
        data_quality_score=0.95,
        stress_level="GREEN",
        predicted_direction="UP",
        directional_bias="BULLISH",
        conviction=3,
        cot_signal="BULLISH",
        vol_signal="NEUTRAL",
        oi_signal="NEUTRAL",
        rr_signal=None,
        special_signal_value=0.0,
        special_signal_label=None,
        regime_category="TREND",
        model_version="v2.0",
    )


def _sample_publish_output() -> PublishOutput:
    return PublishOutput(
        pair="EURUSD",
        date=datetime.date(2026, 5, 20),
        regime_call=_sample_regime_call(),
        brief_markdown="brief",
        desk_card=None,
        alerts_sent=[],
    )


def _sample_v2_output() -> MultiPairRunOutput:
    return MultiPairRunOutput(
        date=datetime.date(2026, 5, 20),
        outputs={
            pair: replace(
                _sample_publish_output(),
                pair=pair,
                regime_call=replace(_sample_regime_call(), pair=pair),
            )
            for pair in ("EURUSD", "USDJPY", "USDINR")
        },
        validation_rows=[],
        health=StageHealth("MultiPairRun", "OK"),
        pairs_processed=3,
        regime_calls_count=3,
        stage_health=(StageHealth("ValidateStage", "OK", notes=["validation_scan_completed"]),),
    )


@pytest.fixture
def patched_pipeline(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Patch all downstream steps so run_pipeline can be exercised in isolation."""

    monkeypatch.setattr(
        "src.scheduler.run_pipeline.run_pipeline",
        __import__("src.scheduler.run_pipeline", fromlist=["run_pipeline"]).run_pipeline.fn,
    )
    mocks: dict[str, MagicMock] = {
        "run_daily": AsyncMock(
            return_value=DailyRunOutput(
                "2026-05-20",
                ("EURUSD", "USDJPY", "USDINR"),
                0.95,
                StageHealth("DailyRun", "OK"),
                (StageHealth("ValidateStage", "OK", notes=["validation_scan_completed"]),),
            )
        ),
        "_run_v2_live_pipeline": AsyncMock(return_value=_sample_v2_output()),
        "run_overnight_check": MagicMock(return_value=StageHealth("overnight_check", "OK")),
        "run_aggregate_stats": MagicMock(return_value=[object()]),
        "check_accuracy_alerts": MagicMock(return_value=[]),
        "send_success_heartbeat": MagicMock(),
        "ProductionAlertPort": MagicMock(),
        "write_pipeline_run": MagicMock(),
        "write_pipeline_error": MagicMock(),
    }

    monkeypatch.setattr("src.scheduler.run_pipeline.run_daily", mocks["run_daily"])
    monkeypatch.setattr(
        "src.scheduler.run_pipeline._run_v2_live_pipeline",
        mocks["_run_v2_live_pipeline"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.run_overnight_check",
        mocks["run_overnight_check"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.run_aggregate_stats",
        mocks["run_aggregate_stats"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.check_accuracy_alerts",
        mocks["check_accuracy_alerts"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.send_success_heartbeat",
        mocks["send_success_heartbeat"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.ProductionAlertPort",
        mocks["ProductionAlertPort"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.write_pipeline_run",
        mocks["write_pipeline_run"],
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.write_pipeline_error",
        mocks["write_pipeline_error"],
    )
    return mocks


def test_run_pipeline_defaults_to_v1(
    patched_pipeline: dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", False)
    monkeypatch.setattr(config, "SHADOW_V2", False)

    from src.scheduler.run_pipeline import run_pipeline

    run_pipeline("2026-05-20")

    patched_pipeline["run_daily"].assert_called_once()
    patched_pipeline["_run_v2_live_pipeline"].assert_not_called()
    patched_pipeline["run_overnight_check"].assert_called_once()
    patched_pipeline["run_aggregate_stats"].assert_called_once()
    patched_pipeline["send_success_heartbeat"].assert_called_once()


def test_run_pipeline_uses_v2_when_flag_set(
    patched_pipeline: dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", True)
    monkeypatch.setattr(config, "SHADOW_V2", False)

    from src.scheduler.run_pipeline import run_pipeline

    run_pipeline("2026-05-20")

    patched_pipeline["run_daily"].assert_not_called()
    patched_pipeline["_run_v2_live_pipeline"].assert_called_once()
    patched_pipeline["run_overnight_check"].assert_called_once()
    patched_pipeline["run_aggregate_stats"].assert_called_once()
    patched_pipeline["send_success_heartbeat"].assert_called_once()


def test_run_pipeline_runs_shadow_v2_alongside_v1(
    patched_pipeline: dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "USE_V2_PIPELINE", False)
    monkeypatch.setattr(config, "SHADOW_V2", True)

    shadow_mock = AsyncMock(return_value=MagicMock(equivalent=True, comparisons={}))
    get_v1_mock = MagicMock(return_value=({}, {}))
    monkeypatch.setattr(
        "src.scheduler.run_pipeline.run_shadow_comparison",
        shadow_mock,
    )
    monkeypatch.setattr(
        "src.scheduler.run_pipeline._get_v1_outputs_for_date",
        get_v1_mock,
    )

    from src.scheduler.run_pipeline import run_pipeline

    run_pipeline("2026-05-20")

    patched_pipeline["run_daily"].assert_called_once()
    patched_pipeline["_run_v2_live_pipeline"].assert_not_called()
    get_v1_mock.assert_called_once_with("2026-05-20")
    shadow_mock.assert_called_once()
    patched_pipeline["run_overnight_check"].assert_called_once()
