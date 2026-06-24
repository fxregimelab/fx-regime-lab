"""Production WriterPort adapter wrapping the existing database writer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.db import writer as writer_module
from src.staged.ports import WriterPort
from src.types import RegimeCall

__all__ = ["ProductionWriterPort", "writer_module"]


class ProductionWriterPort(WriterPort):
    """Persist regime calls and validation rows via ``src.db.writer``."""

    def write_regime_call(
        self,
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int | str | None:
        return writer_module.write_regime_call(
            call,
            correlation_id=correlation_id,
            write_hash=write_hash,
        )

    def write_validation_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        for row in rows:
            writer_module.write_validation_row(row)
