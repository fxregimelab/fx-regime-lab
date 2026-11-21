"""Prepare provider observations without inventing final closes or old vintages."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from src.core.spot_history import LOCKED_PAIRS, strict_date
from src.types import SpotBar

_PROVIDERS = frozenset(("polygon", "alphavantage", "yahoo"))
_METADATA_KEYS = frozenset(
    (
        "date_label_policy",
        "response_ticker",
        "response_status",
        "request_id",
        "adjusted",
        "raw_timestamp_ms",
        "provider_timezone",
        "last_refreshed",
        "from_symbol",
        "to_symbol",
        "index_timezone",
        "raw_index",
    )
)


@dataclass(frozen=True)
class PriceArchiveBatch:
    observations: tuple[dict[str, Any], ...]
    missing_metadata_count: int = 0
    invalid_count: int = 0
    future_count: int = 0
    unknown_session_count: int = 0


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Observation timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _observation(bar: SpotBar, pair: str, cutoff: datetime) -> dict[str, Any]:
    day = strict_date(bar.date)
    if pair not in LOCKED_PAIRS or bar.pair != pair or bar.provider not in _PROVIDERS:
        raise ValueError("Invalid observation identity")
    if not isinstance(bar.instrument, str) or not bar.instrument.strip():
        raise ValueError("Missing provider instrument")
    values: dict[str, float] = {}
    for key in ("open", "high", "low", "close", "volume"):
        raw = getattr(bar, key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("Observation values must be numbers")
        value = float(raw)
        if not math.isfinite(value) or (value < 0 if key == "volume" else value <= 0):
            raise ValueError("Invalid price or volume")
        values[key] = value
    if (
        not values["low"]
        <= min(values["open"], values["close"])
        <= max(values["open"], values["close"])
        <= values["high"]
    ):
        raise ValueError("Inconsistent OHLC")
    receipt = _instant(bar.retrieved_at)
    if receipt > cutoff:
        raise ValueError("Retrieval is after the archive cutoff")
    times = {
        key: _instant(value) if value is not None else None
        for key, value in (
            ("provider_timestamp", bar.provider_timestamp),
            ("window_start", bar.window_start),
            ("window_end", bar.window_end),
        )
    }
    provider_time, start, end = (
        times[key] for key in ("provider_timestamp", "window_start", "window_end")
    )
    if provider_time is not None and provider_time > receipt:
        raise ValueError("Provider timestamp follows retrieval")
    if (start is None) != (end is None):
        raise ValueError("Incomplete observation window")
    if start is not None and end is not None and (end <= start or start > receipt):
        raise ValueError("Invalid observation window")
    if (
        not isinstance(bar.provider_metadata, dict)
        or not set(bar.provider_metadata) <= _METADATA_KEYS
    ):
        raise ValueError("Unexpected provider metadata")
    for value in bar.provider_metadata.values():
        if value is not None and not isinstance(value, (str, bool, int, float)):
            raise ValueError("Provider metadata must contain scalars")
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError("Nonfinite provider metadata")
    optional: dict[str, str | None] = {}
    for key in ("session_timezone", "session_definition", "volume_source", "volume_instrument"):
        value = getattr(bar, key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Optional metadata must be a nonblank string")
        optional[key] = value
    return {
        "pair": pair,
        "date": day.isoformat(),
        **values,
        "provider": bar.provider,
        "instrument": bar.instrument,
        "retrieved_at": receipt.isoformat(),
        **{key: value.isoformat() if value is not None else None for key, value in times.items()},
        **optional,
        "provider_metadata": dict(bar.provider_metadata),
    }


def prepare_price_observations(
    spots: Mapping[str, Sequence[SpotBar]],
    *,
    as_of: date,
    cutoff: datetime,
) -> PriceArchiveBatch:
    """Return detached JSON rows and explicit reasons for incomplete evidence.

    Revisions and repeated dates are retained. This archive is not the unique
    daily series used by inference or validation.
    """
    day = strict_date(as_of, field="as_of")
    instant = _instant(cutoff)
    observations: list[dict[str, Any]] = []
    missing = invalid = future = unknown = 0
    for pair, bars in spots.items():
        for bar in bars:
            if not isinstance(bar, SpotBar):
                invalid += 1
                continue
            try:
                if strict_date(bar.date) > day:
                    future += 1
                    continue
                if bar.provider is None or bar.instrument is None or bar.retrieved_at is None:
                    missing += 1
                    continue
                row = _observation(bar, pair, instant)
            except (ValueError, TypeError, OverflowError):
                invalid += 1
                continue
            observations.append(row)
            if any(
                row[key] is None
                for key in (
                    "session_timezone",
                    "session_definition",
                    "window_start",
                    "window_end",
                )
            ):
                unknown += 1
    return PriceArchiveBatch(tuple(observations), missing, invalid, future, unknown)
