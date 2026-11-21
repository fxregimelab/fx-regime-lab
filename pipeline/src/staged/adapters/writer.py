"""Production WriterPort adapter wrapping the existing database writer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.core import regime_persist as regime_persist_module
from src.db import writer as writer_module
from src.staged.ports import WriterPort
from src.types import RegimeCall, SignalRow

__all__ = ["ProductionWriterPort", "regime_persist_module", "writer_module"]


class ProductionWriterPort(WriterPort):
    """Persist regime calls and validation rows via ``src.db.writer``."""

    def archive_price_observations(
        self,
        observations: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        return writer_module.archive_price_observations(observations)

    def read_published_calls(
        self,
        pair: str,
        *,
        limit: int | None,
    ) -> Sequence[Mapping[str, Any]]:
        rows = writer_module.get_historical_regime_calls(pair, limit=limit)
        return [{**row, "call_id": row.get("id")} for row in rows]

    def read_validation_entry(
        self,
        call_id: int | str,
    ) -> Mapping[str, Any] | None:
        return writer_module.get_validation_log_for_call(call_id)

    def get_publication_signal_for_call(
        self,
        call_id: int,
    ) -> Mapping[str, Any] | None:
        return writer_module.get_publication_signal_for_call(call_id)

    def get_exact_historical_price_for_date(
        self,
        pair: str,
        date_str: str,
    ) -> Mapping[str, Any] | None:
        return writer_module.get_exact_historical_price_for_date(pair, date_str)

    def publish_regime_call(
        self,
        call: RegimeCall,
        signal_row: SignalRow,
        *,
        correlation_id: str | None = None,
    ) -> int | str | None:
        """Delegate the complete publication to the shared atomic boundary."""

        return regime_persist_module.persist_regime_call(
            call,
            signals=signal_row,
            correlation_id=correlation_id,
        )

    def write_regime_call(
        self,
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int | str | None:
        del call, correlation_id, write_hash
        raise RuntimeError("Use publish_regime_call with signal evidence")

    def write_signal_row(self, row: SignalRow) -> None:
        writer_module.write_signal_row(row)

    def write_validation_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        for row in rows:
            writer_module.write_validation_row(row)
