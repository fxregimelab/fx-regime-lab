"""Production FetcherPort adapter wrapping the existing async fetcher engine."""

from __future__ import annotations

import datetime
from typing import Any

from src.core.ingestion_snapshot import IngestionSnapshot as CoreIngestionSnapshot
from src.fetchers.async_engine import build_master_buffer
from src.staged.contracts import IngestionSnapshot, StageHealth, StageStatus
from src.staged.ports import FetcherPort
from src.types import SpotBar


class ProductionFetcherPort(FetcherPort):
    """Fetch a full-market snapshot using the legacy async fetcher engine.

    The legacy ``build_master_buffer`` is date-agnostic; this adapter treats
    ``as_of`` as the target snapshot date and lets the core
    ``IngestionSnapshot.from_buffer`` coerce fetched rows to that date.
    """

    def __init__(
        self,
        *,
        spot_lookback_days: int = 120,
        yield_lookback_days: int = 5,
        macro: dict[str, Any] | None = None,
        dqs_score: float | None = None,
        stress_level: str | None = None,
    ) -> None:
        self._spot_lookback_days = spot_lookback_days
        self._yield_lookback_days = yield_lookback_days
        self._macro = macro
        self._dqs_score = dqs_score
        self._stress_level = stress_level

    async def fetch(self, as_of: datetime.date) -> IngestionSnapshot:
        buffer = await build_master_buffer(
            spot_lookback_days=self._spot_lookback_days,
            yield_lookback_days=self._yield_lookback_days,
        )

        core = CoreIngestionSnapshot.from_buffer(
            as_of,
            buffer,
            macro=self._macro,
            dqs_score=self._dqs_score,
            stress_level=self._stress_level,
        )

        return _map_core_to_staged(core)


def _map_core_to_staged(core: CoreIngestionSnapshot) -> IngestionSnapshot:
    """Convert the core ingestion snapshot to the staged pipeline contract.

    Critical inputs (spots and yields) are required for a usable snapshot.
    Their absence raises ``ValueError`` so the flow fails fast rather than
    publishing a degraded regime call on missing market data.
    """

    missing_fields: list[str] = []

    if not core.spots:
        missing_fields.append("spots")
    if not core.yields:
        missing_fields.append("yields")
    if not core.cot_rows:
        missing_fields.append("cot")
    if not any(v is not None for v in core.cross_asset.values()):
        missing_fields.append("cross_asset")

    critical_missing = [f for f in missing_fields if f in ("spots", "yields")]
    if critical_missing:
        raise ValueError(
            f"Critical ingestion inputs missing: {', '.join(critical_missing)}"
        )

    status: StageStatus = "OK" if not missing_fields else "DEGRADED"

    # Preserve tuple sequences if already present, otherwise coerce.
    spots: dict[str, tuple[SpotBar, ...]] = {}
    for pair, bars in core.spots.items():
        spots[pair] = tuple(bars)

    return IngestionSnapshot(
        date=core.date,
        spots=spots,
        yields=dict(core.yields),
        cot_rows=list(core.cot_rows),
        cross_asset=dict(core.cross_asset),
        macro=core.macro,
        dqs_score=core.dqs_score,
        stress_level=core.stress_level,
        health=StageHealth("IngestionStage", status, missing_fields=missing_fields),
    )
