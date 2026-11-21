"""Tests for the staged pipeline fake ports."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import date

import pytest

from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.types import RegimeCall, SignalRow
from src.validation.calculator import EVALUATION_VERSION


def _signal_row(
    *,
    spot: float = 1.08,
    notes: list[str] | None = None,
) -> SignalRow:
    return SignalRow(
        pair="EURUSD",
        date=date(2026, 5, 20),
        rate_diff_2y=1.25,
        rate_diff_10y=1.1,
        cot_percentile=0.7,
        realized_vol_20d=0.08,
        realized_vol_5d=0.09,
        implied_vol_30d=0.1,
        spot=spot,
        day_change=0.002,
        day_change_pct=0.2,
        cross_asset_vix=18.0,
        cross_asset_dxy=104.0,
        cross_asset_oil=72.0,
        cross_asset_us10y=4.2,
        cross_asset_gold=2_600.0,
        cross_asset_copper=4.1,
        cross_asset_stoxx=510.0,
        oi_delta=50,
        risk_reversal_25d=-0.4,
        risk_reversal_source="market",
        data_quality_notes=notes,
    )


def test_fake_fetcher_returns_configured_snapshot() -> None:
    """FakeFetcherPort returns the snapshot provided at construction."""

    snapshot = IngestionSnapshot(
        date=date(2026, 5, 20),
        spots={},
        yields={"us_10y": 4.5},
        cot_rows=[],
        cross_asset={},
        health=StageHealth("IngestionStage", "DEGRADED", missing_fields=["cot"]),
    )
    fetcher = FakeFetcherPort(snapshot)

    result = asyncio.run(fetcher.fetch(date(2026, 5, 20)))

    assert result is snapshot
    assert fetcher.calls == [date(2026, 5, 20)]


def test_fake_fetcher_returns_empty_snapshot_by_default() -> None:
    """FakeFetcherPort returns an empty snapshot when none is configured."""

    fetcher = FakeFetcherPort()

    result = asyncio.run(fetcher.fetch(date(2026, 5, 20)))

    assert result.date == date(2026, 5, 20)
    assert result.spots == {}
    assert result.health.status == "OK"


def test_fake_archive_is_detached_retry_idempotent_and_does_not_seed_prices() -> None:
    writer = FakeWriterPort()
    observation = {
        "pair": "EURUSD",
        "date": "2026-05-20",
        "open": 1,
        "high": 1.1,
        "low": 0.9,
        "close": 1.05,
        "volume": 0,
        "provider": "polygon",
        "instrument": "C:EURUSD",
        "retrieved_at": "2026-05-20T12:00:00+00:00",
    }

    first = writer.archive_price_observations([observation])
    observation["close"] = 9.0
    repeated = writer.archive_price_observations([{**writer.price_observations[0]}])

    assert first == {"observation_ids": [1], "inserted_count": 1, "existing_count": 0}
    assert repeated == {"observation_ids": [1], "inserted_count": 0, "existing_count": 1}
    assert writer.price_observations[0]["close"] == 1.05
    assert writer.get_exact_historical_price_for_date("EURUSD", "2026-05-20") is None


def test_fake_writer_requires_explicit_exact_price_and_publication_evidence() -> None:
    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BULLISH",
        predicted_direction="BULLISH",
        model_version="model-a",
    )
    call_id = writer.publish_regime_call(call, _signal_row())

    assert isinstance(call_id, int)
    evidence = writer.get_publication_signal_for_call(call_id)
    assert evidence is not None
    assert evidence["spot"] == 1.08
    assert writer.get_exact_historical_price_for_date(
        "EURUSD", "2026-05-27"
    ) is None

    writer.seed_historical_price("EURUSD", date(2026, 5, 27), 1.09)
    assert writer.get_exact_historical_price_for_date(
        "EURUSD", "2026-05-27"
    ) == {"pair": "EURUSD", "date": "2026-05-27", "close": 1.09}
    assert writer.get_exact_historical_price_for_date(
        "EURUSD", "2026-05-28"
    ) is None


def test_fake_writer_records_regime_call_and_validation_rows() -> None:
    """FakeWriterPort records all writes and exposes them for assertions."""

    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )

    call_id = writer.write_regime_call(call, correlation_id="abc")
    writer.write_validation_rows([{"pair": "EURUSD", "date": "2026-05-20"}])

    assert call_id == 1
    assert writer.regime_calls == [(call, {"correlation_id": "abc", "write_hash": None})]
    assert writer.validation_rows == [{"pair": "EURUSD", "date": "2026-05-20"}]
    assert writer.read_published_calls("EURUSD", limit=10) == [
        {
            "call_id": 1,
            "date": date(2026, 5, 20),
            "pair": "EURUSD",
            "regime": "NEUTRAL",
            "predicted_direction": None,
            "confidence": 0.6,
            "strategy_version": "v2",
            "model_version": None,
            "data_source": "live",
        }
    ]
    assert writer.read_validation_entry(1) is None


def test_fake_writer_assigns_incrementing_ids() -> None:
    """FakeWriterPort returns incrementing integer ids for regime calls."""

    writer = FakeWriterPort()
    call1 = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )
    call2 = RegimeCall(
        pair="USDJPY",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )

    id1 = writer.write_regime_call(call1)
    id2 = writer.write_regime_call(call2)

    assert id1 == 1
    assert id2 == 2


def test_fake_writer_reuses_persisted_id_and_reads_latest_evaluation() -> None:
    """Retries keep the original fake id and evaluation lookup returns the latest row."""

    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BEARISH",
        predicted_direction="BULLISH",
    )

    first_id = writer.write_regime_call(call)
    repeated_id = writer.write_regime_call(call)
    writer.write_validation_rows(
        [
            {
                "call_id": first_id,
                "call_date": "2026-05-20",
                "pair": "EURUSD",
                "evaluation_version": EVALUATION_VERSION,
                "v": 1,
            },
            {
                "call_id": first_id,
                "call_date": "2026-05-20",
                "pair": "EURUSD",
                "evaluation_version": EVALUATION_VERSION,
                "v": 2,
            },
        ]
    )

    assert first_id == repeated_id == 1
    assert writer.read_published_calls("EURUSD", limit=10)[0]["call_id"] == 1
    evaluation = writer.read_validation_entry(1)
    assert evaluation is not None
    assert evaluation["v"] == 2
    assert writer.read_published_calls("EURUSD", limit=None)[0]["call_id"] == 1


def test_fake_writer_upserts_detached_signal_row_snapshot() -> None:
    """Signal retries replace the pair/date snapshot without losing quality notes."""

    writer = FakeWriterPort()
    first_notes = ["COT unavailable"]
    first = _signal_row(notes=first_notes)
    writer.write_signal_row(first)
    first_notes.append("mutated after write")

    replacement_notes = ["COT published late", "implied vol fallback"]
    replacement = _signal_row(spot=1.081, notes=replacement_notes)
    writer.write_signal_row(replacement)
    replacement_notes.append("mutated after replacement")

    assert len(writer.signal_rows) == 1
    stored = writer.signal_rows[0]
    assert stored is not replacement
    assert stored.spot == 1.081
    assert stored.risk_reversal_source == "market"
    assert stored.data_quality_notes == ["COT published late", "implied vol fallback"]


def test_fake_atomic_publication_detaches_call_and_signal_and_reuses_exact_id() -> None:
    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BEARISH",
        predicted_direction="BULLISH",
        model_version="2.0-live",
    )
    notes = ["COT published late"]
    signal = _signal_row(notes=notes)

    first_id = writer.publish_regime_call(call, signal, correlation_id="corr-1")
    repeated_id = writer.publish_regime_call(call, signal, correlation_id="corr-2")

    assert first_id == repeated_id == 1
    assert len(writer.regime_calls) == len(writer.signal_rows) == 1
    call.regime = "MUTATED"
    notes.append("mutated after publication")
    assert writer.regime_calls[0][0].regime == "RISK_ON"
    assert writer.signal_rows[0].data_quality_notes == ["COT published late"]


@pytest.mark.parametrize("changed", ["call", "signal"])
def test_fake_atomic_publication_rejects_conflict_without_partial_mutation(
    changed: str,
) -> None:
    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BEARISH",
        predicted_direction="BULLISH",
        model_version="2.0-live",
    )
    signal = _signal_row(notes=["original"])
    writer.publish_regime_call(call, signal)
    conflicting_call = replace(call, confidence=0.8) if changed == "call" else call
    conflicting_signal = replace(signal, spot=1.09) if changed == "signal" else signal

    with pytest.raises(ValueError, match="Conflicting publication"):
        writer.publish_regime_call(conflicting_call, conflicting_signal)

    assert len(writer.regime_calls) == len(writer.signal_rows) == 1
    assert writer.regime_calls[0][0].confidence == 0.7
    assert writer.signal_rows[0].spot == 1.08


def test_fake_atomic_publication_keeps_versions_independent() -> None:
    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BEARISH",
        predicted_direction="BULLISH",
        model_version="2.0-live",
    )
    signal = _signal_row(notes=["same evidence"])

    assert writer.publish_regime_call(call, signal) == 1
    assert writer.publish_regime_call(replace(call, model_version="2.1-live"), signal) == 2
    assert len(writer.regime_calls) == len(writer.signal_rows) == 2


def test_fake_atomic_publication_rejects_identity_and_provenance_errors() -> None:
    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BEARISH",
        predicted_direction="BULLISH",
        model_version="2.0-live",
    )
    signal = _signal_row()

    with pytest.raises(ValueError, match="identity must match"):
        writer.publish_regime_call(call, replace(signal, pair="USDJPY"))
    with pytest.raises(ValueError, match="nonempty"):
        writer.publish_regime_call(replace(call, model_version=None), signal)
    with pytest.raises(ValueError, match="live or backtest"):
        writer.publish_regime_call(replace(call, data_source="synthetic"), signal)
    with pytest.raises(ValueError, match="locked universe"):
        writer.publish_regime_call(
            replace(call, pair="GBPUSD"),
            replace(signal, pair="GBPUSD"),
        )
    assert not writer.regime_calls and not writer.signal_rows


def test_fake_atomic_publication_cannot_adopt_legacy_call_without_evidence() -> None:
    writer = FakeWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="RISK_ON",
        confidence=0.7,
        signal_composite=0.4,
        rate_signal="BEARISH",
        predicted_direction="BULLISH",
        model_version="2.0-live",
    )
    writer.write_regime_call(call)

    with pytest.raises(ValueError, match="no publication evidence"):
        writer.publish_regime_call(call, _signal_row())
    assert len(writer.regime_calls) == 1
    assert writer.signal_rows == []


def test_fake_alert_port_records_all_alerts() -> None:
    """FakeAlertPort records heartbeats, successes, and low-DQS alerts."""

    alert = FakeAlertPort()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )

    alert.send_success(call)
    alert.send_heartbeat(
        date(2026, 5, 20),
        pairs_processed=3,
        regime_calls_count=3,
        dqs_score=0.95,
    )
    alert.send_low_dqs(date(2026, 5, 20), 0.55, ["cot"])

    assert alert.successes == [call]
    assert alert.heartbeats == [
        {
            "as_of": date(2026, 5, 20),
            "pairs_processed": 3,
            "regime_calls_count": 3,
            "dqs_score": 0.95,
        }
    ]
    assert alert.low_dqs_alerts == [
        {
            "as_of": date(2026, 5, 20),
            "dqs_score": 0.55,
            "stale_sources": ["cot"],
        }
    ]


def test_fake_alert_records_only_non_ok_statuses() -> None:
    """Status notices retain pair and health details and reject healthy status."""

    alert = FakeAlertPort()
    degraded = StageHealth(
        "SignalStage",
        "DEGRADED",
        missing_fields=["cot_percentile"],
        notes=["COT source lagged"],
    )
    failed = StageHealth(
        "PublishStage",
        "FAILED",
        missing_fields=["regime_call"],
        notes=["publication did not complete"],
    )

    alert.send_status(date(2026, 5, 20), degraded, pair="EURUSD")
    alert.send_status(date(2026, 5, 20), failed)

    assert alert.statuses == [
        {"as_of": date(2026, 5, 20), "health": degraded, "pair": "EURUSD"},
        {"as_of": date(2026, 5, 20), "health": failed, "pair": None},
    ]
    assert alert.heartbeats == []
    assert alert.successes == []
    with pytest.raises(ValueError, match="only DEGRADED or FAILED"):
        alert.send_status(date(2026, 5, 20), StageHealth("PublishStage", "OK"))


def test_fake_alert_port_is_silent() -> None:
    """FakeAlertPort does not raise or mutate external state."""

    alert = FakeAlertPort()

    alert.send_success(
        RegimeCall(
            pair="EURUSD",
            date=date(2026, 5, 20),
            regime="NEUTRAL",
            confidence=0.6,
            signal_composite=0.1,
            rate_signal="NEUTRAL",
        )
    )

    assert len(alert.successes) == 1
