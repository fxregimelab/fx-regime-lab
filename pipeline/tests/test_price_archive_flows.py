"""Daily flows must archive provider observations before publication."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pytest

from src.core.price_archive_stage import archive_price_snapshot
from src.staged import orchestrator as flows
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.types import RegimeCall, SignalRow, SpotBar
from src.validation.coverage import ValidationRunResult
from tests.fixtures.eurusd_snapshot import make_recorded_eurusd_snapshot

DAY = date(2026, 2, 20)
RECEIPT = datetime(2026, 2, 20, 23, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flows._archive_price_task, "retry_delay_seconds", 0, raising=False)


def _recorded_bar(
    *,
    session_known: bool = True,
    close: float = 1.08,
) -> SpotBar:
    start = datetime.combine(DAY, time.min, tzinfo=UTC)
    return SpotBar(
        date=DAY,
        pair="EURUSD",
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000.0,
        provider="polygon",
        instrument="C:EURUSD",
        retrieved_at=RECEIPT,
        provider_timestamp=start,
        session_timezone="UTC" if session_known else None,
        session_definition="provider_daily_window" if session_known else None,
        window_start=start if session_known else None,
        window_end=start + timedelta(days=1) if session_known else None,
        provider_metadata={"response_ticker": "C:EURUSD"},
    )


def _snapshot_with_recorded_metadata() -> Any:
    snapshot = make_recorded_eurusd_snapshot()
    receipt = datetime.combine(snapshot.date, time(23), tzinfo=UTC)
    bars = tuple(
        replace(
            bar,
            provider="polygon",
            instrument="C:EURUSD",
            retrieved_at=receipt,
            provider_timestamp=datetime.combine(bar.date, time.min, tzinfo=UTC),
            session_timezone="UTC",
            session_definition="provider_daily_window",
            window_start=datetime.combine(bar.date, time.min, tzinfo=UTC),
            window_end=datetime.combine(bar.date, time.min, tzinfo=UTC)
            + timedelta(days=1),
            provider_metadata={"response_ticker": "C:EURUSD"},
        )
        for bar in snapshot.spots["EURUSD"]
        if bar.date <= snapshot.date
    )
    return replace(snapshot, spots={"EURUSD": bars})


def test_archive_keeps_valid_rows_and_reports_incomplete_evidence() -> None:
    writer = FakeWriterPort()
    missing = replace(_recorded_bar(), provider=None)

    result = archive_price_snapshot(
        {"EURUSD": (_recorded_bar(session_known=False), missing)},
        as_of=DAY,
        cutoff=RECEIPT,
        writer=writer,
    )

    assert result.archived_count == 1
    assert result.missing_metadata_count == 1
    assert result.unknown_session_count == 1
    assert result.degraded
    assert len(writer.price_observations) == 1
    assert writer.get_exact_historical_price_for_date("EURUSD", DAY.isoformat()) is None


def test_archive_chunks_above_rpc_limit_without_losing_retry_ids() -> None:
    writer = FakeWriterPort()
    result = archive_price_snapshot(
        {"EURUSD": tuple(_recorded_bar() for _ in range(5001))},
        as_of=DAY,
        cutoff=RECEIPT,
        writer=writer,
    )

    assert [len(batch) for batch in writer.archive_calls] == [5000, 1]
    assert result.archived_count == 5001
    assert result.batch_count == 2
    assert result.inserted_count == 1
    assert result.existing_count == 5000


@pytest.mark.parametrize("invalid_id", [0, -1, True, "1"])
def test_archive_rejects_receipts_without_positive_integer_ids(invalid_id: Any) -> None:
    class InvalidReceiptWriter(FakeWriterPort):
        def archive_price_observations(self, observations: Any) -> Any:
            return {
                "observation_ids": [invalid_id for _ in observations],
                "inserted_count": len(observations),
                "existing_count": 0,
            }

    with pytest.raises(RuntimeError, match="invalid receipt"):
        archive_price_snapshot(
            {"EURUSD": (_recorded_bar(),)},
            as_of=DAY,
            cutoff=RECEIPT,
            writer=InvalidReceiptWriter(),
        )


def test_archive_rejects_receipt_claiming_more_inserts_than_distinct_ids() -> None:
    class ImpossibleCountWriter(FakeWriterPort):
        def archive_price_observations(self, observations: Any) -> Any:
            assert len(observations) == 2
            return {
                "observation_ids": [17, 17],
                "inserted_count": 2,
                "existing_count": 0,
            }

    with pytest.raises(RuntimeError, match="invalid receipt"):
        archive_price_snapshot(
            {"EURUSD": (_recorded_bar(), _recorded_bar(close=1.09))},
            as_of=DAY,
            cutoff=RECEIPT,
            writer=ImpossibleCountWriter(),
        )


def test_validation_health_keeps_completed_marker_when_outcomes_are_missing() -> None:
    result = ValidationRunResult(
        scanned_calls=1,
        due_horizons=2,
        completed_horizons=1,
    )

    health = flows._validation_health(result)

    assert health.status == "DEGRADED"
    assert health.missing_fields == ["mature_validation_outcomes"]
    assert health.notes == result.notes
    assert "validation_scan_completed" in health.notes


def test_validation_health_rejects_untyped_report_without_completion_marker() -> None:
    health = flows._validation_health(None)

    assert health.status == "DEGRADED"
    assert health.missing_fields == ["validation_report"]
    assert "validation_scan_completed" not in health.notes


def test_single_flow_archives_before_publication_and_preserves_archive_health() -> None:
    events: list[str] = []

    class OrderedWriter(FakeWriterPort):
        def archive_price_observations(self, observations: Any) -> Any:
            events.append("archive")
            return super().archive_price_observations(observations)

        def publish_regime_call(
            self,
            call: RegimeCall,
            signal_row: SignalRow,
            *,
            correlation_id: str | None = None,
        ) -> int | str | None:
            events.append("publish")
            return super().publish_regime_call(
                call,
                signal_row,
                correlation_id=correlation_id,
            )

    snapshot = _snapshot_with_recorded_metadata()
    writer = OrderedWriter()
    output = asyncio.run(
        flows.run_single_pair_flow.fn(
            "EURUSD",
            snapshot.date,
            fetcher=FakeFetcherPort(snapshot),
            writer=writer,
            alert=FakeAlertPort(),
        )
    )

    assert events == ["archive", "publish"]
    archive_health = next(
        health for health in output.stage_health if health.stage_name == "PriceArchiveStage"
    )
    assert archive_health.status == "OK"
    assert "canonical_close_unverified" in archive_health.notes


def test_archive_writer_failure_stops_before_publication() -> None:
    class FailingArchiveWriter(FakeWriterPort):
        def archive_price_observations(self, observations: Any) -> Any:
            del observations
            raise RuntimeError("archive unavailable")

    snapshot = _snapshot_with_recorded_metadata()
    writer = FailingArchiveWriter()
    alert = FakeAlertPort()

    with pytest.raises(RuntimeError, match="archive unavailable"):
        asyncio.run(
            flows.run_single_pair_flow.fn(
                "EURUSD",
                snapshot.date,
                fetcher=FakeFetcherPort(snapshot),
                writer=writer,
                alert=alert,
            )
        )

    assert not writer.regime_calls and not writer.signal_rows
    assert alert.statuses[-1]["health"].stage_name == "PriceArchiveStage"


def test_missing_archive_metadata_degrades_published_output() -> None:
    snapshot = make_recorded_eurusd_snapshot()
    writer = FakeWriterPort()
    output = asyncio.run(
        flows.run_single_pair_flow.fn(
            "EURUSD",
            snapshot.date,
            fetcher=FakeFetcherPort(snapshot),
            writer=writer,
            alert=FakeAlertPort(),
        )
    )

    archive_health = next(
        health for health in output.stage_health if health.stage_name == "PriceArchiveStage"
    )
    assert archive_health.status == "DEGRADED"
    assert archive_health.missing_fields == ["price_observations"]
    assert any(note.startswith("missing_metadata:") for note in archive_health.notes)
    assert len(writer.regime_calls) == 1
    assert writer.archive_calls == []
