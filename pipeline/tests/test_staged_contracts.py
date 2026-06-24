"""Tests for the staged pipeline cross-stage contracts."""

from __future__ import annotations

from datetime import date

import pytest

from src.staged.contracts import IngestionSnapshot, PublishOutput, SignalPipelineResult, StageHealth
from src.types import (
    CotRow,
    Layer1GateOutput,
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    RegimeCall,
    SignalRow,
    SpotBar,
)


def test_stage_health_defaults() -> None:
    """StageHealth can be constructed with sensible defaults."""

    health = StageHealth(stage_name="TestStage", status="OK")

    assert health.stage_name == "TestStage"
    assert health.status == "OK"
    assert health.missing_fields == []
    assert health.derived_fields == []
    assert health.notes == []


def test_stage_health_is_frozen() -> None:
    """StageHealth instances are immutable."""

    health = StageHealth(stage_name="TestStage", status="OK")

    with pytest.raises(AttributeError):
        health.status = "FAILED"  # type: ignore[misc]


def test_ingestion_snapshot_defaults() -> None:
    """IngestionSnapshot can be constructed with a default OK health report."""

    as_of = date(2026, 5, 20)
    snapshot = IngestionSnapshot(
        date=as_of,
        spots={},
        yields={},
        cot_rows=[],
        cross_asset={},
    )

    assert snapshot.date == as_of
    assert snapshot.spots == {}
    assert snapshot.yields == {}
    assert snapshot.cot_rows == []
    assert snapshot.cross_asset == {}
    assert snapshot.macro is None
    assert snapshot.dqs_score is None
    assert snapshot.stress_level is None
    assert snapshot.health == StageHealth("IngestionStage", "OK")


def test_ingestion_snapshot_is_frozen() -> None:
    """IngestionSnapshot instances are immutable."""

    snapshot = IngestionSnapshot(
        date=date(2026, 5, 20),
        spots={},
        yields={},
        cot_rows=[],
        cross_asset={},
    )

    with pytest.raises(AttributeError):
        snapshot.dqs_score = 0.9  # type: ignore[misc]


def _make_spot_bar() -> SpotBar:
    return SpotBar(
        date=date(2026, 5, 20),
        pair="EURUSD",
        open=1.08,
        high=1.09,
        low=1.07,
        close=1.085,
    )


def _make_cot_row() -> CotRow:
    return CotRow(
        date=date(2026, 5, 20),
        pair="EURUSD",
        net_long=1000,
        open_interest=5000,
    )


def _minimal_signal_row() -> SignalRow:
    return SignalRow(
        pair="EURUSD",
        date=date(2026, 5, 20),
        rate_diff_2y=None,
        rate_diff_10y=None,
        cot_percentile=None,
        realized_vol_20d=None,
        realized_vol_5d=None,
        implied_vol_30d=None,
        spot=None,
        day_change=None,
        day_change_pct=None,
        cross_asset_vix=None,
        cross_asset_dxy=None,
        cross_asset_oil=None,
        cross_asset_us10y=None,
        cross_asset_gold=None,
        cross_asset_copper=None,
        cross_asset_stoxx=None,
        oi_delta=None,
    )


def test_ingestion_snapshot_carries_typed_data() -> None:
    """IngestionSnapshot preserves typed spot bars and COT rows."""

    bar = _make_spot_bar()
    cot = _make_cot_row()
    snapshot = IngestionSnapshot(
        date=date(2026, 5, 20),
        spots={"EURUSD": (bar,)},
        yields={"us_10y": 4.5},
        cot_rows=[cot],
        cross_asset={"vix": 15.0},
        macro={"ecb_balance_sheet": 5000.0},
        dqs_score=0.95,
        stress_level="LOW",
    )

    assert snapshot.spots["EURUSD"] == (bar,)
    assert snapshot.cot_rows == [cot]
    assert snapshot.yields["us_10y"] == 4.5
    assert snapshot.cross_asset["vix"] == 15.0
    assert snapshot.macro == {"ecb_balance_sheet": 5000.0}
    assert snapshot.dqs_score == 0.95
    assert snapshot.stress_level == "LOW"


def test_signal_pipeline_result_is_frozen() -> None:
    """SignalPipelineResult instances are immutable."""

    signal_row = _minimal_signal_row()
    layer1: Layer1GateOutput = {
        "regime": "NEUTRAL",
        "invalidated": False,
        "z_rate": 0.1,
        "m_rate": 0.1,
        "delta_pi": 0.0,
        "d_spot": 0.0,
        "stale_fields": [],
        "raw_regime": "NEUTRAL",
    }
    layer2: Layer2DirectionalOutput = {
        "positioning_percentile": 0.5,
        "crowd_flag": False,
        "crowd_penalty": 0.0,
        "crowd_veto": False,
        "conviction_multiplier": 1.0,
        "conviction": 3,
        "directional_bias": "LONG",
        "rate_positioning_clash": False,
    }
    layer3: Layer3ExecutionOutput = {
        "entry_timing": "ENTER",
        "position_size": "FULL",
        "stop_level": None,
        "realized_vol_rank": 0.5,
        "skew_alignment": 0,
        "skew_reversal_flag": False,
        "risk_reversal_z": None,
        "adr": None,
        "mie_proxy": None,
        "stop_buffer": None,
    }
    result = SignalPipelineResult(
        pair="EURUSD",
        date=date(2026, 5, 20),
        signal_row=signal_row,
        layer1=layer1,
        layer2=layer2,
        layer3=layer3,
        health=StageHealth("SignalStage", "OK"),
    )

    assert result.pair == "EURUSD"
    assert result.signal_row == signal_row
    assert result.layer1 == layer1
    with pytest.raises(AttributeError):
        result.pair = "USDJPY"  # type: ignore[misc]


def test_publish_output_is_frozen() -> None:
    """PublishOutput instances are immutable."""

    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )
    output = PublishOutput(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime_call=call,
        brief_markdown=None,
        desk_card=None,
        alerts_sent=[],
        health=StageHealth("PublishStage", "OK"),
    )

    assert output.regime_call == call
    assert output.alerts_sent == []
    with pytest.raises(AttributeError):
        output.brief_markdown = "updated"  # type: ignore[misc]
