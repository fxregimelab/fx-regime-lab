"""Source evidence for a yield observation and point-in-time qualification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from src.signals.rate_inputs import (
    CONFIGURED_RATE_SOURCES,
    SOURCE_DEFINITIONS,
    RateInstrument,
    finite_rate,
    two_year_spread,
)


@dataclass(frozen=True)
class RateObservation:
    source_id: str
    instrument: RateInstrument | None
    observed_on: date | None
    available_at: datetime | None
    retrieved_at: datetime | None
    vintage: str | None
    value: float | None
    unit: str | None
    missing_reason: str | None = None
    provider_realtime_start: str | None = None
    provider_realtime_end: str | None = None


def qualified_rate_value(
    observation: RateObservation | None,
    *,
    source_id: str,
    decision_at: datetime | None,
    max_age: timedelta = timedelta(days=5),
    definitions: Mapping[str, RateInstrument] = SOURCE_DEFINITIONS,
) -> float | None:
    """Require witnessed availability and a known vintage before a rate is used."""
    if observation is None or decision_at is None or decision_at.tzinfo is None:
        return None
    if observation.source_id != source_id or observation.instrument != definitions.get(source_id):
        return None
    if observation.unit != "percent" or observation.missing_reason is not None:
        return None
    value = finite_rate(observation.value)
    available = observation.available_at
    retrieved = observation.retrieved_at
    if (
        value is None
        or observation.observed_on is None
        or available is None
        or available.tzinfo is None
        or retrieved is None
        or retrieved.tzinfo is None
        or not observation.vintage
    ):
        return None
    cutoff = decision_at.astimezone(UTC)
    release = available.astimezone(UTC)
    receipt = retrieved.astimezone(UTC)
    if release > cutoff or receipt < release or receipt > cutoff:
        return None
    if release.date() < observation.observed_on:
        return None
    if observation.observed_on > cutoff.date() or cutoff.date() - observation.observed_on > max_age:
        return None
    return value


def qualified_two_year_spread(
    pair: str,
    observations: Mapping[str, RateObservation],
    *,
    decision_at: datetime | None,
    source_ids: tuple[str | None, str | None] | None = None,
    definitions: Mapping[str, RateInstrument] = SOURCE_DEFINITIONS,
) -> float | None:
    """Keep the accepted pair orientation and matched-instrument check."""
    ids = source_ids if source_ids is not None else CONFIGURED_RATE_SOURCES.get(pair)
    if ids is None or any(source_id is None for source_id in ids):
        return None
    values: dict[str, float | None] = {}
    for source_id in ids:
        assert source_id is not None
        observation = observations.get(source_id)
        if observation is None or observation.instrument != definitions.get(source_id):
            return None
        values[source_id] = qualified_rate_value(
            observation,
            source_id=source_id,
            decision_at=decision_at,
            definitions=definitions,
        )
    return two_year_spread(pair, values, ids, definitions=definitions)
