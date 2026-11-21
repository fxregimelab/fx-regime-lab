"""Validate prior calls through the shared immutable-evidence evaluator."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from src.staged.contracts import IngestionSnapshot
from src.staged.ports import WriterPort
from src.validation.coverage import ValidationRunResult, evaluate_validation_population


class ValidateStage:
    """Evaluate published calls from exact durable entry and endpoint evidence."""

    def __init__(self, writer: WriterPort) -> None:
        self.writer = writer

    def run(
        self,
        as_of: date,
        pairs: Sequence[str],
        *,
        snapshot: IngestionSnapshot,
    ) -> list[dict[str, Any]]:
        """Evaluate all published calls without reading ingestion snapshot prices."""

        return self.run_with_report(as_of, pairs, snapshot=snapshot).rows

    def run_with_report(
        self,
        as_of: date,
        pairs: Sequence[str],
        *,
        snapshot: IngestionSnapshot,
    ) -> ValidationRunResult:
        """Evaluate all published calls and report mature-horizon coverage."""

        del snapshot
        populations = [
            (pair, self.writer.read_published_calls(pair, limit=None)) for pair in pairs
        ]
        return evaluate_validation_population(
            populations,
            as_of,
            read_existing=self.writer.read_validation_entry,
            read_entry=self.writer.get_publication_signal_for_call,
            read_price=lambda requested_pair, target_date: (
                self.writer.get_exact_historical_price_for_date(
                    requested_pair,
                    target_date.isoformat(),
                )
            ),
            persist_rows=self.writer.write_validation_rows,
        )
