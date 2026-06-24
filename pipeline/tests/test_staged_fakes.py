"""Tests for the staged pipeline fake ports."""

from __future__ import annotations

import asyncio
from datetime import date

from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.types import RegimeCall


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
