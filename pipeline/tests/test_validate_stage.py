"""ValidateStage net-correctness tests."""

from __future__ import annotations

import datetime

from src.staged.contracts import IngestionSnapshot
from src.staged.fakes import FakeWriterPort
from src.staged.stages.validate_stage import ValidateStage
from src.types import RegimeCall, SpotBar
from src.validation.calculator import compute_horizon_metrics
from src.validation.calendar import add_trading_days


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


def test_validate_stage_net_correctness_differs_from_gross() -> None:
    """ValidateStage must use cost-adjusted net correctness, not gross correct."""
    call_date = datetime.date(2026, 4, 1)
    as_of = add_trading_days(call_date, 5)
    t5_date = as_of
    s0 = 1.0000
    sh = 1.00051  # 5.1 bps gross UP; net 4.9 bps NEUTRAL after EUR cost

    snapshot = IngestionSnapshot(
        date=as_of,
        spots={
            "EURUSD": (
                _spot_bar("EURUSD", call_date, s0),
                _spot_bar("EURUSD", t5_date, sh),
            )
        },
        yields={},
        cot_rows=[],
        cross_asset={},
        macro={},
        dqs_score=1.0,
        stress_level="GREEN",
    )

    writer = FakeWriterPort()
    writer.write_regime_call(
        RegimeCall(
            pair="EURUSD",
            date=call_date,
            regime="TEST",
            confidence=0.5,
            signal_composite=0.0,
            rate_signal="NEUTRAL",
            primary_driver="rate",
            predicted_direction="NEUTRAL",
            directional_bias="NEUTRAL",
        )
    )

    rows = ValidateStage(writer).run(as_of, ["EURUSD"], snapshot=snapshot)
    assert len(rows) == 1
    row = rows[0]
    assert row["correct_t5"] is False
    assert row["correct_net_t5"] is True
    assert row["correct_net_t5"] != row["correct_t5"]


def test_validate_stage_matches_calculator_golden_vector() -> None:
    """ValidateStage and calculator produce identical metrics for the same inputs."""
    call_date = datetime.date(2026, 4, 1)
    as_of = add_trading_days(call_date, 5)
    s0 = 1.0000
    sh = 1.00003
    predicted = "BULLISH"
    confidence = 0.5

    expected = compute_horizon_metrics(s0, sh, predicted, confidence, "EURUSD")
    assert expected is not None

    snapshot = IngestionSnapshot(
        date=as_of,
        spots={
            "EURUSD": (
                _spot_bar("EURUSD", call_date, s0),
                _spot_bar("EURUSD", as_of, sh),
            )
        },
        yields={},
        cot_rows=[],
        cross_asset={},
        macro={},
        dqs_score=1.0,
        stress_level="GREEN",
    )

    writer = FakeWriterPort()
    writer.write_regime_call(
        RegimeCall(
            pair="EURUSD",
            date=call_date,
            regime="TEST",
            confidence=confidence,
            signal_composite=0.0,
            rate_signal=predicted,
            primary_driver="rate",
            predicted_direction=predicted,
            directional_bias="LONG",
        )
    )

    rows = ValidateStage(writer).run(as_of, ["EURUSD"], snapshot=snapshot)
    row = rows[0]
    assert row["correct_t5"] == expected.correct
    assert row["correct_net_t5"] == expected.correct_net
    assert row["log_return_t5_bps"] == expected.log_return_bps
    assert row["log_return_net_bps_t5"] == expected.log_return_net_bps
