"""Tests for the staged pipeline external ports."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.types import RegimeCall


def test_fetcher_port_can_be_subclassed() -> None:
    """FetcherPort defines a narrow async fetch method that can be implemented."""

    class FakeFetcher(FetcherPort):
        async def fetch(self, as_of: date) -> IngestionSnapshot:
            return IngestionSnapshot(
                date=as_of,
                spots={},
                yields={},
                cot_rows=[],
                cross_asset={},
                health=StageHealth("IngestionStage", "OK"),
            )

    fetcher: FetcherPort = FakeFetcher()
    snapshot = asyncio.run(fetcher.fetch(date(2026, 5, 20)))

    assert snapshot.date == date(2026, 5, 20)


def test_fetcher_port_is_abstract() -> None:
    """FetcherPort cannot be instantiated without implementing fetch."""

    with pytest.raises(TypeError):
        FetcherPort()  # type: ignore[abstract]


def test_writer_port_can_be_subclassed() -> None:
    """WriterPort defines narrow write methods that can be implemented."""

    class FakeWriter(WriterPort):
        def __init__(self) -> None:
            self.calls: list[RegimeCall] = []
            self.validation_rows: list[Mapping[str, Any]] = []

        def write_regime_call(
            self,
            call: RegimeCall,
            *,
            correlation_id: str | None = None,
            write_hash: str | None = None,
        ) -> int | str | None:
            self.calls.append(call)
            return len(self.calls)

        def write_validation_rows(
            self,
            rows: Sequence[Mapping[str, Any]],
        ) -> None:
            self.validation_rows.extend(rows)

        def get_regime_calls(self, pair: str, *, limit: int = 100) -> list[RegimeCall]:
            return [c for c in self.calls if c.pair == pair][-limit:]

    writer = FakeWriter()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )
    call_id = writer.write_regime_call(call, correlation_id="abc-123")
    writer.write_validation_rows([{"pair": "EURUSD", "date": "2026-05-20"}])

    assert call_id == 1
    assert writer.calls == [call]
    assert writer.validation_rows == [{"pair": "EURUSD", "date": "2026-05-20"}]


def test_alert_port_can_be_subclassed() -> None:
    """AlertPort defines narrow alert methods that can be implemented."""

    class FakeAlert(AlertPort):
        def __init__(self) -> None:
            self.heartbeats: list[dict[str, Any]] = []
            self.successes: list[RegimeCall] = []
            self.low_dqs: list[dict[str, Any]] = []

        def send_heartbeat(
            self,
            as_of: date,
            *,
            pairs_processed: int,
            regime_calls_count: int,
            dqs_score: float,
        ) -> None:
            self.heartbeats.append(
                {
                    "as_of": as_of,
                    "pairs_processed": pairs_processed,
                    "regime_calls_count": regime_calls_count,
                    "dqs_score": dqs_score,
                }
            )

        def send_success(self, call: RegimeCall) -> None:
            self.successes.append(call)

        def send_low_dqs(
            self,
            as_of: date,
            dqs_score: float,
            stale_sources: list[str],
        ) -> None:
            self.low_dqs.append(
                {
                    "as_of": as_of,
                    "dqs_score": dqs_score,
                    "stale_sources": stale_sources,
                }
            )

    alert = FakeAlert()
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
    assert alert.heartbeats[0]["pairs_processed"] == 3
    assert alert.low_dqs[0]["stale_sources"] == ["cot"]
