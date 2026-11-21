"""Causal validation and selection for spot-price histories."""

from __future__ import annotations

import datetime
import math
import re
from collections.abc import Sequence

from src.types import SpotBar

LOCKED_PAIRS = frozenset(("EURUSD", "USDJPY", "USDINR"))
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class SpotHistoryError(ValueError):
    """The supplied spot history is unsafe for point-in-time inference."""


def strict_date(value: object, *, field: str = "date") -> datetime.date:
    """Return an exact calendar date and reject timestamps or truncated strings."""

    if type(value) is datetime.date:
        return value
    if not isinstance(value, str) or _ISO_DATE.fullmatch(value) is None:
        raise SpotHistoryError(f"{field} must be an exact YYYY-MM-DD date")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise SpotHistoryError(f"{field} must be a valid YYYY-MM-DD date") from exc


def select_spot_history(
    bars: Sequence[SpotBar],
    *,
    pair: str,
    as_of: datetime.date,
) -> tuple[SpotBar, ...]:
    """Validate, de-duplicate, order and causally fence one pair's history.

    The returned objects are the original ``SpotBar`` instances. This keeps
    provider metadata attached to each observation while excluding every bar
    after ``as_of``. Exact duplicate rows collapse to one observation;
    conflicting rows for the same date fail closed.
    """

    if pair not in LOCKED_PAIRS:
        raise SpotHistoryError(f"Spot pair {pair!r} is outside the locked universe")
    cutoff = strict_date(as_of, field="as_of")

    by_date: dict[datetime.date, SpotBar] = {}
    for bar in bars:
        if not isinstance(bar, SpotBar):
            raise SpotHistoryError(f"Spot history for {pair} contains a non-SpotBar row")
        observed = strict_date(bar.date, field="bar.date")
        if bar.pair != pair:
            raise SpotHistoryError(
                f"Spot history key {pair} contains a row for {bar.pair!r}"
            )
        _validate_values(bar, pair=pair, observed=observed)
        if observed > cutoff:
            continue

        prior = by_date.get(observed)
        if prior is None:
            by_date[observed] = bar
        elif prior != bar:
            raise SpotHistoryError(
                f"Conflicting {pair} spot rows for {observed.isoformat()}"
            )

    return tuple(by_date[observed] for observed in sorted(by_date))


def _validate_values(
    bar: SpotBar,
    *,
    pair: str,
    observed: datetime.date,
) -> None:
    values: dict[str, float] = {}
    for name in ("open", "high", "low", "close"):
        raw = getattr(bar, name)
        if isinstance(raw, bool):
            raise SpotHistoryError(_invalid_value_message(pair, observed, name))
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise SpotHistoryError(_invalid_value_message(pair, observed, name)) from exc
        if not math.isfinite(value) or value <= 0:
            raise SpotHistoryError(_invalid_value_message(pair, observed, name))
        values[name] = value

    volume_raw = bar.volume
    if isinstance(volume_raw, bool):
        raise SpotHistoryError(_invalid_value_message(pair, observed, "volume"))
    try:
        volume = float(volume_raw)
    except (TypeError, ValueError) as exc:
        raise SpotHistoryError(_invalid_value_message(pair, observed, "volume")) from exc
    if not math.isfinite(volume) or volume < 0:
        raise SpotHistoryError(_invalid_value_message(pair, observed, "volume"))

    if (
        values["high"] < max(values["open"], values["low"], values["close"])
        or values["low"] > min(values["open"], values["high"], values["close"])
    ):
        raise SpotHistoryError(
            f"Inconsistent OHLC values for {pair} on {observed.isoformat()}"
        )


def _invalid_value_message(
    pair: str, observed: datetime.date, field: str
) -> str:
    return f"Invalid {field} for {pair} on {observed.isoformat()}"
