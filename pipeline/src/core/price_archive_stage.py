"""Archive one fetched price snapshot before downstream publication."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from src.core.price_archive import prepare_price_observations
from src.types import SpotBar

_RPC_BATCH_LIMIT = 5000


class PriceObservationWriter(Protocol):
    """Narrow write boundary used by both daily orchestrators."""

    def archive_price_observations(
        self,
        observations: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class PriceArchiveStageResult:
    """Receipt and completeness evidence for one date-scoped archive stage."""

    archived_count: int
    inserted_count: int
    existing_count: int
    batch_count: int
    missing_metadata_count: int
    invalid_count: int
    future_count: int
    unknown_session_count: int

    @property
    def degraded(self) -> bool:
        return (
            self.archived_count == 0
            or self.missing_metadata_count > 0
            or self.invalid_count > 0
            or self.future_count > 0
            or self.unknown_session_count > 0
        )

    @property
    def missing_fields(self) -> tuple[str, ...]:
        if self.archived_count == 0:
            return ("price_observations",)
        return ()

    @property
    def notes(self) -> tuple[str, ...]:
        notes: list[str] = []
        for name, count in (
            ("missing_metadata", self.missing_metadata_count),
            ("invalid_observations", self.invalid_count),
            ("future_observations", self.future_count),
            ("unknown_session_windows", self.unknown_session_count),
        ):
            if count:
                notes.append(f"{name}:{count}")
        if self.archived_count == 0:
            notes.append("price_observations_unavailable")
        # A complete archive receipt is evidence of storage only. It does not
        # establish that a provider bar is the market's canonical final close.
        notes.append("canonical_close_unverified")
        return tuple(notes)


def archive_price_snapshot(
    spots: Mapping[str, Sequence[SpotBar]],
    *,
    as_of: date,
    cutoff: datetime,
    writer: PriceObservationWriter,
) -> PriceArchiveStageResult:
    """Prepare, chunk, and archive all valid observations in one snapshot.

    Each RPC stays within the database limit. A failure from any chunk is
    allowed to propagate so publication cannot continue without a confirmed
    archive receipt. Batches above the limit are durable per chunk rather than
    atomic across the whole snapshot.
    """

    prepared = prepare_price_observations(spots, as_of=as_of, cutoff=cutoff)
    inserted = existing = batches = 0
    observations = prepared.observations
    for start in range(0, len(observations), _RPC_BATCH_LIMIT):
        chunk = observations[start : start + _RPC_BATCH_LIMIT]
        receipt = writer.archive_price_observations(chunk)
        chunk_inserted = receipt.get("inserted_count")
        chunk_existing = receipt.get("existing_count")
        ids = receipt.get("observation_ids")
        if (
            type(chunk_inserted) is not int
            or type(chunk_existing) is not int
            or not isinstance(ids, list)
            or len(ids) != len(chunk)
            or any(type(observation_id) is not int or observation_id <= 0 for observation_id in ids)
            or chunk_inserted < 0
            or chunk_existing < 0
            or chunk_inserted + chunk_existing != len(chunk)
            or chunk_inserted > len(set(ids))
        ):
            raise RuntimeError("Price observation archive returned an invalid receipt")
        inserted += chunk_inserted
        existing += chunk_existing
        batches += 1

    return PriceArchiveStageResult(
        archived_count=len(observations),
        inserted_count=inserted,
        existing_count=existing,
        batch_count=batches,
        missing_metadata_count=prepared.missing_metadata_count,
        invalid_count=prepared.invalid_count,
        future_count=prepared.future_count,
        unknown_session_count=prepared.unknown_session_count,
    )
