"""IngestionStage: date-scoped fetch of all market and macro inputs."""

from __future__ import annotations

from datetime import date

from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.ports import FetcherPort


class IngestionStage:
    """Fetch one immutable snapshot for ``as_of`` via the injected fetcher port."""

    def __init__(self, fetcher: FetcherPort) -> None:
        self.fetcher = fetcher

    async def run(self, as_of: date) -> IngestionSnapshot:
        """Return the fetched snapshot, preserving any health report from the fetcher."""

        snapshot = await self.fetcher.fetch(as_of)
        if snapshot.health.stage_name != "IngestionStage":
            snapshot = IngestionSnapshot(
                date=snapshot.date,
                spots=snapshot.spots,
                yields=snapshot.yields,
                cot_rows=snapshot.cot_rows,
                cross_asset=snapshot.cross_asset,
                macro=snapshot.macro,
                dqs_score=snapshot.dqs_score,
                stress_level=snapshot.stress_level,
                health=StageHealth(
                    stage_name="IngestionStage",
                    status=snapshot.health.status,
                    missing_fields=list(snapshot.health.missing_fields),
                    derived_fields=list(snapshot.health.derived_fields),
                    notes=list(snapshot.health.notes),
                ),
            )
        return snapshot
