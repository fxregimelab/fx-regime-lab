"""Staged validation uses the shared exact-price evidence contract."""

from __future__ import annotations

import math
from datetime import date

import pytest

from src.staged.contracts import IngestionSnapshot
from src.staged.fakes import FakeWriterPort
from src.staged.stages.validate_stage import ValidateStage
from src.types import RegimeCall, SignalRow
from src.validation.calculator import EVALUATION_VERSION, calculate_horizon
from src.validation.calendar import add_trading_days

CALL_DATE = date(2025, 1, 6)
T5_DATE = add_trading_days(CALL_DATE, 5)
T20_DATE = add_trading_days(CALL_DATE, 20)


def _snapshot(as_of: date) -> IngestionSnapshot:
    return IngestionSnapshot(
        date=as_of,
        spots={},
        yields={},
        cot_rows=[],
        cross_asset={},
    )


def _signal(pair: str, call_date: date, spot: float) -> SignalRow:
    return SignalRow(
        pair=pair,
        date=call_date,
        rate_diff_2y=None,
        rate_diff_10y=None,
        cot_percentile=None,
        realized_vol_20d=None,
        realized_vol_5d=None,
        implied_vol_30d=None,
        spot=spot,
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


def _publish(
    writer: FakeWriterPort,
    *,
    pair: str = "EURUSD",
    call_date: date = CALL_DATE,
    spot: float = 1.0,
    predicted: str | None = "BULLISH",
    confidence: float = 0.8,
    model_version: str = "model-a",
) -> int:
    call_id = writer.publish_regime_call(
        RegimeCall(
            pair=pair,
            date=call_date,
            regime="TEST_REGIME",
            confidence=confidence,
            signal_composite=0.4,
            rate_signal="BEARISH",
            predicted_direction=predicted,
            model_version=model_version,
        ),
        _signal(pair, call_date, spot),
    )
    assert isinstance(call_id, int)
    return call_id


@pytest.mark.parametrize(
    ("pair", "predicted", "entry", "move_bps"),
    [
        ("EURUSD", "BULLISH", 1.0, 12.0),
        ("EURUSD", "BEARISH", 1.0, -12.0),
        ("EURUSD", "BULLISH", 1.0, 2.0),
        ("USDINR", "BEARISH", 80.0, -8.0),
    ],
)
def test_staged_horizon_matches_shared_calculator(
    pair: str,
    predicted: str,
    entry: float,
    move_bps: float,
) -> None:
    writer = FakeWriterPort()
    call_id = _publish(writer, pair=pair, predicted=predicted, spot=entry)
    endpoint = entry * math.exp(move_bps / 10_000.0)
    writer.seed_historical_price(pair, T5_DATE, endpoint)

    rows = ValidateStage(writer).run(T5_DATE, [pair], snapshot=_snapshot(T5_DATE))

    expected = calculate_horizon(entry, endpoint, predicted, 0.8, pair)
    assert len(rows) == 1
    row = rows[0]
    assert row["call_id"] == call_id
    assert row["evaluation_version"] == EVALUATION_VERSION
    assert row["log_return_t5_bps"] == pytest.approx(expected["log_return_bps"])
    assert row["log_return_net_bps_t5"] == pytest.approx(
        expected["log_return_net_bps"]
    )
    assert row["correct_t5"] is expected["correct"]
    assert row["price_evidence_t5"] == {
        "kind": "historical_close",
        "pair": pair,
        "date": T5_DATE.isoformat(),
        "price": endpoint,
        "source": "historical_prices.close",
    }


def test_same_date_versions_use_their_own_publication_entry() -> None:
    writer = FakeWriterPort()
    first_id = _publish(writer, spot=1.0, model_version="model-a")
    second_id = _publish(writer, spot=2.0, model_version="model-b")
    writer.seed_historical_price("EURUSD", T5_DATE, 1.1)

    rows = ValidateStage(writer).run(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    )

    assert [row["call_id"] for row in rows] == [first_id, second_id]
    assert rows[0]["entry_price_evidence"]["price"] == 1.0
    assert rows[1]["entry_price_evidence"]["price"] == 2.0
    assert rows[0]["log_return_t5_bps"] > 0
    assert rows[1]["log_return_t5_bps"] < 0


def test_partial_evidence_completion_freezes_t5_and_adds_t20() -> None:
    writer = FakeWriterPort()
    _publish(writer, spot=1.0)
    writer.seed_historical_price("EURUSD", T5_DATE, 1.01)

    first = ValidateStage(writer).run(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    )[0]
    frozen_t5 = {
        key: value
        for key, value in first.items()
        if key.endswith("t5") or key.endswith("5d")
    }

    writer.seed_historical_price("EURUSD", T5_DATE, 9.99)
    writer.seed_historical_price("EURUSD", T20_DATE, 0.99)
    completed = ValidateStage(writer).run(
        T20_DATE, ["EURUSD"], snapshot=_snapshot(T20_DATE)
    )[0]

    assert {
        key: value
        for key, value in completed.items()
        if key.endswith("t5") or key.endswith("5d")
    } == frozen_t5
    assert completed["entry_price_evidence"] == first["entry_price_evidence"]
    assert completed["price_evidence_t20"]["price"] == 0.99
    assert ("EURUSD", T5_DATE) not in writer.historical_price_reads[1:]


def test_completed_retry_does_not_refetch_entry_or_prices() -> None:
    writer = FakeWriterPort()
    _publish(writer)
    writer.seed_historical_price("EURUSD", T5_DATE, 1.01)
    writer.seed_historical_price("EURUSD", T20_DATE, 1.02)
    stage = ValidateStage(writer)
    assert len(stage.run(T20_DATE, ["EURUSD"], snapshot=_snapshot(T20_DATE))) == 1
    reads_before = (
        list(writer.publication_signal_reads),
        list(writer.historical_price_reads),
    )

    report = stage.run_with_report(
        T20_DATE, ["EURUSD"], snapshot=_snapshot(T20_DATE)
    )
    assert report.rows == []
    assert report.scanned_calls == 1
    assert report.due_horizons == 2
    assert report.completed_horizons == 2
    assert report.healthy is True
    assert "validation_scan_completed" in report.notes
    assert writer.publication_signal_reads == reads_before[0]
    assert writer.historical_price_reads == reads_before[1]


def test_legacy_call_without_publication_evidence_stays_unavailable() -> None:
    writer = FakeWriterPort()
    legacy_id = writer.write_regime_call(
        RegimeCall(
            pair="EURUSD",
            date=CALL_DATE,
            regime="LEGACY",
            confidence=0.8,
            signal_composite=0.4,
            rate_signal="BULLISH",
            predicted_direction="BULLISH",
        )
    )
    writer.seed_historical_price("EURUSD", T5_DATE, 1.01)

    report = ValidateStage(writer).run_with_report(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    )
    assert report.rows == []
    assert report.scanned_calls == 1
    assert report.due_horizons == 1
    assert report.completed_horizons == 0
    assert report.missing_horizons == 1
    assert report.invalid_calls == 0
    assert report.healthy is False
    assert writer.publication_signal_reads == [legacy_id]
    assert writer.historical_price_reads == []


def test_old_backlog_is_independent_of_ingestion_snapshot_window() -> None:
    writer = FakeWriterPort()
    old_date = date(2020, 1, 6)
    old_t5 = add_trading_days(old_date, 5)
    call_id = _publish(writer, call_date=old_date, spot=1.1)
    writer.seed_historical_price("EURUSD", old_t5, 1.2)
    recent_snapshot = _snapshot(date(2026, 9, 27))

    rows = ValidateStage(writer).run(
        date(2026, 9, 27), ["EURUSD"], snapshot=recent_snapshot
    )

    assert [row["call_id"] for row in rows] == [call_id]
    assert rows[0]["entry_price_evidence"]["date"] == old_date.isoformat()
    assert rows[0]["price_evidence_t5"]["date"] == old_t5.isoformat()


def test_missing_exact_endpoint_is_not_substituted() -> None:
    writer = FakeWriterPort()
    _publish(writer)
    writer.seed_historical_price("EURUSD", add_trading_days(CALL_DATE, 6), 1.01)

    report = ValidateStage(writer).run_with_report(
        add_trading_days(CALL_DATE, 6),
        ["EURUSD"],
        snapshot=_snapshot(add_trading_days(CALL_DATE, 6)),
    )
    assert report.rows == []
    assert report.due_horizons == 1
    assert report.completed_horizons == 0
    assert report.missing_horizons == 1
    assert report.healthy is False
    assert writer.historical_price_reads == [("EURUSD", T5_DATE)]


def test_neutral_call_keeps_null_accuracy_scores() -> None:
    writer = FakeWriterPort()
    _publish(writer, predicted="NEUTRAL")
    writer.seed_historical_price("EURUSD", T5_DATE, 1.01)

    row = ValidateStage(writer).run(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    )[0]

    assert row["correct_t5"] is None
    assert row["correct_net_t5"] is None
    assert row["brier_score_t5"] is None

    report = ValidateStage(writer).run_with_report(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    )
    assert report.due_horizons == 1
    assert report.completed_horizons == 1
    assert report.missing_horizons == 0
    assert report.healthy is True


def test_immature_call_returns_before_evidence_reads() -> None:
    writer = FakeWriterPort()
    _publish(writer)
    as_of = date(2025, 1, 10)

    assert ValidateStage(writer).run(
        as_of, ["EURUSD"], snapshot=_snapshot(as_of)
    ) == []
    assert writer.publication_signal_reads == []
    assert writer.historical_price_reads == []


def test_old_v1_evaluation_coexists_with_new_current_evaluation() -> None:
    writer = FakeWriterPort()
    call_id = _publish(writer)
    writer.write_validation_rows(
        [{"call_id": call_id, "evaluation_version": "published-direction-v1"}]
    )
    writer.seed_historical_price("EURUSD", T5_DATE, 1.01)

    rows = ValidateStage(writer).run(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    )

    assert len(rows) == 1
    assert rows[0]["evaluation_version"] == EVALUATION_VERSION
    assert writer.validation_rows[0]["evaluation_version"] == "published-direction-v1"
    assert writer.read_validation_entry(call_id) == rows[0]


def test_validation_requests_complete_published_history() -> None:
    class CompleteHistoryWriter(FakeWriterPort):
        observed_limit: int | None = 5000

        def read_published_calls(
            self, pair: str, *, limit: int | None
        ) -> list[dict[str, object]]:
            self.observed_limit = limit
            return [dict(row) for row in super().read_published_calls(pair, limit=limit)]

    writer = CompleteHistoryWriter()
    _publish(writer)
    writer.seed_historical_price("EURUSD", T5_DATE, 1.01)

    assert len(
        ValidateStage(writer).run(
            T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
        )
    ) == 1
    assert writer.observed_limit is None


def test_requested_pair_mismatch_cannot_score() -> None:
    class MismatchedPairWriter(FakeWriterPort):
        def read_published_calls(
            self, pair: str, *, limit: int | None
        ) -> list[dict[str, object]]:
            rows = [dict(row) for row in super().read_published_calls(pair, limit=limit)]
            rows[0]["pair"] = "USDJPY"
            return rows

    writer = MismatchedPairWriter()
    _publish(writer)
    writer.seed_historical_price("USDJPY", T5_DATE, 150.0)

    assert ValidateStage(writer).run(
        T5_DATE, ["EURUSD"], snapshot=_snapshot(T5_DATE)
    ) == []
    assert writer.publication_signal_reads == []
    assert writer.historical_price_reads == []
