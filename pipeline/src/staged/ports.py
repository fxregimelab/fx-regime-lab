"""External ports (abstract interfaces) for the staged pipeline.

Production implementations adapt the existing fetchers, database writer, and
Slack client. Tests inject fakes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from src.types import RegimeCall, SignalRow

from .contracts import IngestionSnapshot, StageHealth


class FetcherPort(ABC):
    """Port for fetching all market and macro inputs for a single date."""

    @abstractmethod
    async def fetch(self, as_of: date) -> IngestionSnapshot:
        """Return an immutable snapshot of all fetched inputs for ``as_of``."""
        ...


class WriterPort(ABC):
    """Port for persisting regime calls and validation rows."""

    @abstractmethod
    def archive_price_observations(
        self,
        observations: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        """Append provider observations and return their durable receipt."""
        ...

    @abstractmethod
    def read_published_calls(
        self,
        pair: str,
        *,
        limit: int | None,
    ) -> Sequence[Mapping[str, Any]]:
        """Return persisted calls with their durable ``call_id`` values."""
        ...

    @abstractmethod
    def read_validation_entry(
        self,
        call_id: int | str,
    ) -> Mapping[str, Any] | None:
        """Return the current evaluation for one durable published-call id."""
        ...

    @abstractmethod
    def get_publication_signal_for_call(
        self,
        call_id: int,
    ) -> Mapping[str, Any] | None:
        """Return the immutable signal evidence for one published call."""
        ...

    @abstractmethod
    def get_exact_historical_price_for_date(
        self,
        pair: str,
        date_str: str,
    ) -> Mapping[str, Any] | None:
        """Return the stored historical close for exactly one pair and date."""
        ...

    @abstractmethod
    def publish_regime_call(
        self,
        call: RegimeCall,
        signal_row: SignalRow,
        *,
        correlation_id: str | None = None,
    ) -> int | str | None:
        """Atomically persist a call and its exact signal evidence."""
        ...

    @abstractmethod
    def write_regime_call(
        self,
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int | str | None:
        """Persist a regime call. Returns the persisted row id, if available."""
        ...

    @abstractmethod
    def write_signal_row(self, row: SignalRow) -> None:
        """Persist the signal inputs and quality notes used for one call."""
        ...

    @abstractmethod
    def write_validation_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        """Persist one or more validation rows."""
        ...


class AlertPort(ABC):
    """Port for pipeline alerts and success heartbeats."""

    @abstractmethod
    def send_heartbeat(
        self,
        as_of: date,
        *,
        pairs_processed: int,
        regime_calls_count: int,
        dqs_score: float,
    ) -> None:
        """Send a daily success heartbeat."""
        ...

    @abstractmethod
    def send_success(self, call: RegimeCall) -> None:
        """Send a success alert for a published regime call."""
        ...

    @abstractmethod
    def send_status(
        self,
        as_of: date,
        health: StageHealth,
        *,
        pair: str | None = None,
    ) -> None:
        """Send an explicit notice for a degraded or failed stage."""
        ...

    @abstractmethod
    def send_low_dqs(
        self,
        as_of: date,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        """Send a low data-quality-score alert."""
        ...
