"""Production WriterPort adapter wrapping the existing database writer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from src.db import writer as writer_module
from src.staged.ports import WriterPort
from src.types import RegimeCall

__all__ = ["ProductionWriterPort", "writer_module"]


def _row_to_regime_call(row: Mapping[str, Any]) -> RegimeCall:
    """Convert a Supabase regime_calls row into a ``RegimeCall``."""

    raw_date = row.get("date")
    if isinstance(raw_date, date):
        call_date = raw_date
    elif isinstance(raw_date, str):
        call_date = date.fromisoformat(raw_date[:10])
    else:
        raise ValueError(f"Unexpected date type in regime_calls row: {type(raw_date)}")

    return RegimeCall(
        pair=str(row["pair"]),
        date=call_date,
        regime=str(row.get("regime") or ""),
        confidence=float(row.get("confidence") or 0.0),
        signal_composite=float(row.get("signal_composite") or 0.0),
        rate_signal=str(row.get("rate_signal") or ""),
        primary_driver=(
            str(row.get("primary_driver")) if row.get("primary_driver") else None
        ),
        predicted_direction=(
            str(row.get("predicted_direction"))
            if row.get("predicted_direction")
            else None
        ),
    )


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

    def get_regime_calls(self, pair: str, *, limit: int = 100) -> list[RegimeCall]:
        rows = writer_module.get_historical_regime_calls(pair, limit=limit)
        return [_row_to_regime_call(row) for row in rows]
