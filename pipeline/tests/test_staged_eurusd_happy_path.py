"""End-to-end EUR/USD happy path through the staged pipeline with fake ports."""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Sequence

import pytest

from src.staged.contracts import IngestionSnapshot
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.staged.stages import (
    IngestionStage,
    PublishStage,
    RegimeStage,
    SignalStage,
    ValidateStage,
)
from src.types import CotRow, RegimeCall, SpotBar


def _spot_bar(pair: str, d: datetime.date, close: float) -> SpotBar:
    return SpotBar(
        date=d,
        pair=pair,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000.0,
    )


def _trading_date_range(start: datetime.date, days: int) -> list[datetime.date]:
    """Return ``days`` trading dates (Mon-Fri) starting from ``start``."""

    dates: list[datetime.date] = []
    current = start
    while len(dates) < days:
        if current.weekday() < 5:
            dates.append(current)
        current += datetime.timedelta(days=1)
    return dates


def _make_eurusd_snapshot() -> IngestionSnapshot:
    """Rich EUR/USD snapshot with enough history for signal math."""

    as_of = datetime.date(2026, 5, 20)
    # 40 trading days of spots ending on as_of
    start = datetime.date(2026, 3, 30)
    dates = _trading_date_range(start, 40)
    base = 1.0800
    bars = tuple(
        _spot_bar("EURUSD", d, round(base + i * 0.0005, 4))
        for i, d in enumerate(dates)
    )

    # 10 weekly COT reports leading up to as_of
    cot_rows: list[CotRow] = []
    cot_start = datetime.date(2026, 3, 17)
    for i in range(10):
        report_date = cot_start + datetime.timedelta(weeks=i)
        cot_rows.append(
            CotRow(
                date=report_date,
                pair="EURUSD",
                net_long=10_000 + i * 500,
                open_interest=50_000 + i * 1_000,
                asset_mgr_net=6_000 + i * 300,
                lev_money_net=-2_000 - i * 100,
            )
        )

    return IngestionSnapshot(
        date=as_of,
        spots={"EURUSD": bars},
        yields={
            "DGS2": 4.0,
            "ECBDFR": 2.0,
            "us_10y": 4.5,
            "de_10y": 2.5,
            "T10YIE": 2.0,
        },
        cot_rows=cot_rows,
        cross_asset={
            "vix": 18.0,
            "dxy": 104.0,
            "oil": 75.0,
            "gold": 2000.0,
            "copper": 4.0,
            "stoxx": 4500.0,
        },
        macro={
            "ecb_balance_sheet": 7000.0,
            "bund_btp_spread": 1.5,
        },
        dqs_score=0.95,
        stress_level="GREEN",
    )


def _make_prior_calls() -> Sequence[RegimeCall]:
    """A prior EUR/USD BULLISH call to exercise T+5/T+20 validation."""

    call_date = datetime.date(2026, 4, 20)
    return [
        RegimeCall(
            pair="EURUSD",
            date=call_date,
            regime="RISK_OFF_DOLLAR_BID",
            confidence=0.65,
            signal_composite=0.8,
            rate_signal="BULLISH",
            primary_driver="rate",
            predicted_direction="BULLISH",
            directional_bias="LONG",
        )
    ]


def test_eurusd_happy_path_with_fake_ports() -> None:
    """Run the full EUR/USD pipeline end-to-end with fake external ports."""

    pair = "EURUSD"
    snapshot = _make_eurusd_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    # Seed a prior call so ValidateStage has something to evaluate.
    for call in _make_prior_calls():
        writer.write_regime_call(call)

    ingestion = IngestionStage(fetcher)
    signal_stage = SignalStage()
    regime_stage = RegimeStage()
    publish_stage = PublishStage(writer, alert, correlation_id="test-correlation")
    validate_stage = ValidateStage(writer)

    # Act: run the pipeline
    ingested = asyncio.run(ingestion.run(snapshot.date))
    signal_result = signal_stage.run(pair, ingested)
    regime_call = regime_stage.run(pair, signal_result)
    publish_output = asyncio.run(publish_stage.run(pair, regime_call))
    validation_rows = validate_stage.run(
        snapshot.date,
        [pair],
        snapshot=snapshot,
    )

    # Assert: ingestion
    assert ingested.date == snapshot.date
    assert ingested.health.stage_name == "IngestionStage"
    assert fetcher.calls == [snapshot.date]

    # Assert: signal stage produced a result with Layer 1/2/3
    assert signal_result.pair == pair
    assert signal_result.date == snapshot.date
    assert signal_result.signal_row.pair == pair
    assert signal_result.signal_row.spot is not None
    assert signal_result.layer1["regime"] != ""
    assert signal_result.layer2["directional_bias"] in ("LONG", "SHORT", "NEUTRAL")
    assert signal_result.layer3["entry_timing"] in ("ENTER", "WAIT")
    assert signal_result.health.stage_name == "SignalStage"

    # Assert: regime stage produced a RegimeCall
    assert regime_call.pair == pair
    assert regime_call.date == snapshot.date
    assert regime_call.regime == signal_result.layer1["regime"]
    assert regime_call.confidence == pytest.approx(signal_result.confidence, abs=1e-9)
    assert regime_call.signal_composite == pytest.approx(signal_result.composite, abs=1e-9)
    assert regime_call.rate_signal == signal_result.rate_direction
    assert regime_call.predicted_direction in ("BULLISH", "BEARISH", "NEUTRAL")
    assert regime_call.directional_bias == signal_result.layer2["directional_bias"]
    assert regime_call.entry_timing == signal_result.layer3["entry_timing"]
    assert regime_call.position_size == signal_result.layer3["position_size"]
    assert regime_call.data_quality_score == 0.95
    assert regime_call.special_signal_label == "Bund-BTP + ECB BS"
    assert regime_call.regime_category is not None

    # Assert: publish stage wrote and alerted
    assert publish_output.pair == pair
    assert publish_output.date == snapshot.date
    assert publish_output.regime_call == regime_call
    assert "wrote_regime_call:2" in publish_output.alerts_sent
    assert "success_alert" in publish_output.alerts_sent
    assert len(writer.regime_calls) == 2
    assert writer.regime_calls[-1][0] == regime_call
    assert writer.regime_calls[-1][1]["correlation_id"] == "test-correlation"
    assert len(alert.successes) == 1
    assert alert.successes[0] == regime_call

    # Assert: validation produced rows for the prior call
    assert len(validation_rows) >= 1
    eur_validations = [r for r in validation_rows if r["pair"] == pair]
    assert len(eur_validations) >= 1
    row = eur_validations[0]
    assert row["predicted_direction"] == "BULLISH"
    assert row["predicted_regime"] == "RISK_OFF_DOLLAR_BID"
    assert "log_return_t5_bps" in row
    assert "correct_t5" in row
    assert "brier_score_t5" in row
    assert "log_return_t20_bps" in row
    assert "correct_t20" in row
    assert "brier_score_t20" in row
    assert len(writer.validation_rows) >= 1

    # Assert: StageHealth propagated through the pipeline
    assert ingested.health.status == "OK"
    assert signal_result.health.status in ("OK", "DEGRADED")
    assert publish_output.health.status == "OK"
