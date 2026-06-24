"""Fake implementations of the staged pipeline external ports.

These fakes record every call and return minimal canned data so that stage
logic can be unit tested without touching real external services.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from src.types import RegimeCall

from .contracts import IngestionSnapshot
from .ports import AlertPort, FetcherPort, WriterPort


class FakeFetcherPort(FetcherPort):
    """In-memory fetcher that returns a configured snapshot or an empty one."""

    def __init__(self, snapshot: IngestionSnapshot | None = None) -> None:
        self.snapshot = snapshot
        self.calls: list[date] = []

    async def fetch(self, as_of: date) -> IngestionSnapshot:
        """Return the configured snapshot, or an empty OK snapshot."""

        self.calls.append(as_of)
        if self.snapshot is not None:
            return self.snapshot
        return IngestionSnapshot(
            date=as_of,
            spots={},
            yields={},
            cot_rows=[],
            cross_asset={},
        )


class FakeWriterPort(WriterPort):
    """In-memory writer that records regime calls and validation rows."""

    def __init__(self) -> None:
        self.regime_calls: list[tuple[RegimeCall, dict[str, Any]]] = []
        self.validation_rows: list[Mapping[str, Any]] = []

    def write_regime_call(
        self,
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int | str | None:
        """Record the call and return a synthetic integer id."""

        self.regime_calls.append(
            (call, {"correlation_id": correlation_id, "write_hash": write_hash})
        )
        return len(self.regime_calls)

    def write_validation_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        """Record validation rows in order."""

        self.validation_rows.extend(rows)


class FakeAlertPort(AlertPort):
    """In-memory alert port that records every alert for inspection."""

    def __init__(self) -> None:
        self.heartbeats: list[dict[str, Any]] = []
        self.successes: list[RegimeCall] = []
        self.low_dqs_alerts: list[dict[str, Any]] = []

    def send_heartbeat(
        self,
        as_of: date,
        *,
        pairs_processed: int,
        regime_calls_count: int,
        dqs_score: float,
    ) -> None:
        """Record a heartbeat."""

        self.heartbeats.append(
            {
                "as_of": as_of,
                "pairs_processed": pairs_processed,
                "regime_calls_count": regime_calls_count,
                "dqs_score": dqs_score,
            }
        )

    def send_success(self, call: RegimeCall) -> None:
        """Record a success alert."""

        self.successes.append(call)

    def send_low_dqs(
        self,
        as_of: date,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        """Record a low-DQS alert."""

        self.low_dqs_alerts.append(
            {
                "as_of": as_of,
                "dqs_score": dqs_score,
                "stale_sources": stale_sources,
            }
        )
