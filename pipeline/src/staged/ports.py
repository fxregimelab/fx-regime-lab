"""External ports (abstract interfaces) for the staged pipeline.

Production implementations adapt the existing fetchers, database writer, and
Slack client. Tests inject fakes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from src.types import RegimeCall

from .contracts import IngestionSnapshot


class FetcherPort(ABC):
    """Port for fetching all market and macro inputs for a single date."""

    @abstractmethod
    async def fetch(self, as_of: date) -> IngestionSnapshot:
        """Return an immutable snapshot of all fetched inputs for ``as_of``."""
        ...


class WriterPort(ABC):
    """Port for persisting regime calls and validation rows."""

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
    def write_validation_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        """Persist one or more validation rows."""
        ...

    @abstractmethod
    def get_regime_calls(self, pair: str, *, limit: int = 100) -> list[RegimeCall]:
        """Return prior regime calls for ``pair`` ordered by date ascending."""
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
    def send_low_dqs(
        self,
        as_of: date,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        """Send a low data-quality-score alert."""
        ...
