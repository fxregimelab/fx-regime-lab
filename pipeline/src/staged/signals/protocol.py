"""SignalFamily protocol for staged pipeline signal computation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.staged.contracts import IngestionSnapshot
from src.staged.signals.types import FamilyOutput


@runtime_checkable
class SignalFamily(Protocol):
    """Compute one signal family slice from an ingestion snapshot."""

    def compute(self, pair: str, snapshot: IngestionSnapshot) -> FamilyOutput:
        """Return a partial FamilyOutput containing this family's slice."""
