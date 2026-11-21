"""Coverage accounting for live and staged validation scans."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from src.validation.calculator import (
    EVALUATION_VERSION,
    normalize_predicted_direction,
    validate_price,
    validate_probability,
)
from src.validation.calendar import add_trading_days
from src.validation.evaluator import evaluate_call, normalize_call_id

ReadExisting = Callable[[int], Mapping[str, Any] | None]
ReadEntry = Callable[[int], Mapping[str, Any] | None]
ReadPrice = Callable[[str, date], Mapping[str, Any] | None]
PersistRows = Callable[[Sequence[Mapping[str, Any]]], None]


@dataclass
class ValidationRunResult:
    """Rows written and coverage health for one complete published-call scan."""

    rows: list[dict[str, Any]] = field(default_factory=list)
    scanned_calls: int = 0
    due_horizons: int = 0
    completed_horizons: int = 0
    invalid_calls: int = 0
    _limitations: list[str] = field(default_factory=list, init=False, repr=False)

    @property
    def missing_horizons(self) -> int:
        return max(0, self.due_horizons - self.completed_horizons)

    @property
    def healthy(self) -> bool:
        counters = (
            self.scanned_calls,
            self.due_horizons,
            self.completed_horizons,
            self.invalid_calls,
        )
        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in counters
        ):
            return False
        if (
            self.completed_horizons > self.due_horizons
            or self.due_horizons > self.scanned_calls * 2
            or self.invalid_calls > self.scanned_calls
        ):
            return False
        return (
            self.invalid_calls == 0
            and self.missing_horizons == 0
            and not self._limitations
        )

    @property
    def notes(self) -> list[str]:
        notes = [
            "validation_scan_completed",
            f"scanned_calls={self.scanned_calls}",
            f"due_horizons={self.due_horizons}",
            f"completed_horizons={self.completed_horizons}",
            f"missing_horizons={self.missing_horizons}",
            f"invalid_calls={self.invalid_calls}",
        ]
        if self.due_horizons == 0:
            notes.append("no_mature_horizons")
        if self.missing_horizons:
            notes.append("missing_mature_horizons")
        if self.invalid_calls:
            notes.append("invalid_calls_present")
        return [*notes, *self._limitations]

    def add_limitation(self, note: str) -> None:
        """Add a stable explanation for coverage outside the returned population."""
        if note not in self._limitations:
            self._limitations.append(note)


def _strict_date(raw: Any, label: str) -> date:
    if isinstance(raw, datetime):
        raise ValueError(f"{label} must be an ISO calendar date without a time")
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str) or len(raw) != 10:
        raise ValueError(f"{label} must be an ISO calendar date")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO calendar date") from exc
    if parsed.isoformat() != raw:
        raise ValueError(f"{label} must be an ISO calendar date")
    return parsed


def _finite_number(raw: Any, label: str) -> float:
    if raw is None or isinstance(raw, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        value = float(raw)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def _positive_int(raw: Any, label: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return raw


def _validate_call(
    call: Mapping[str, Any], expected_pair: str, as_of: date
) -> tuple[int, str, date, tuple[str, ...]]:
    call_id = normalize_call_id(call)
    if call.get("pair") != expected_pair or expected_pair not in {
        "EURUSD",
        "USDJPY",
        "USDINR",
    }:
        raise ValueError("published call pair does not match requested pair")
    call_date = _strict_date(call.get("date"), "call date")
    if call_date > as_of:
        raise ValueError("call date cannot be after the validation date")
    predicted = normalize_predicted_direction(call.get("predicted_direction"))
    confidence = call.get("confidence")
    if confidence is not None:
        validate_probability(confidence)
    if predicted != "NEUTRAL" and confidence is None:
        raise ValueError("confidence is required for a directional call")
    due = tuple(
        horizon
        for horizon, days in (("t5", 5), ("t20", 20))
        if as_of >= add_trading_days(call_date, days)
    )
    return call_id, expected_pair, call_date, due


def _validate_evidence(
    raw: Any,
    *,
    expected_keys: set[str],
    kind: str,
    pair: str,
    evidence_date: date,
    source: str,
    call_id: int | None = None,
) -> None:
    if not isinstance(raw, Mapping) or set(raw) != expected_keys:
        raise ValueError("validation evidence has unexpected fields")
    if (
        raw.get("kind") != kind
        or raw.get("pair") != pair
        or _strict_date(raw.get("date"), "evidence date") != evidence_date
        or raw.get("source") != source
        or (
            call_id is not None
            and _positive_int(raw.get("call_id"), "evidence call_id") != call_id
        )
    ):
        raise ValueError("validation evidence identity does not match the call")
    validate_price(raw.get("price"), "evidence price")


def _completed_horizons(
    row: Mapping[str, Any] | None,
    *,
    call_id: int,
    pair: str,
    call_date: date,
    mature_horizons: Collection[str],
) -> set[str]:
    if row is None:
        return set()
    if (
        _positive_int(row.get("call_id"), "evaluation call_id") != call_id
        or row.get("evaluation_version") != EVALUATION_VERSION
    ):
        raise ValueError("existing evaluation identity or version does not match")

    completed = {
        horizon
        for horizon in ("t5", "t20")
        if row.get(f"log_return_{horizon}_bps") is not None
    }
    if completed - set(mature_horizons):
        raise ValueError("existing evaluation contains an immature horizon")
    if not completed:
        return set()
    _validate_evidence(
        row.get("entry_price_evidence"),
        expected_keys={"kind", "pair", "date", "price", "source", "call_id"},
        kind="publication_signal",
        pair=pair,
        evidence_date=call_date,
        source="publication_evidence.signal_payload.spot",
        call_id=call_id,
    )
    for horizon in completed:
        _finite_number(row.get(f"log_return_{horizon}_bps"), f"{horizon} return")
        days = 5 if horizon == "t5" else 20
        _validate_evidence(
            row.get(f"price_evidence_{horizon}"),
            expected_keys={"kind", "pair", "date", "price", "source"},
            kind="historical_close",
            pair=pair,
            evidence_date=add_trading_days(call_date, days),
            source="historical_prices.close",
        )
    return completed


def evaluate_validation_population(
    populations: Iterable[tuple[str, Sequence[Mapping[str, Any]]]],
    as_of: date,
    *,
    read_existing: ReadExisting,
    read_entry: ReadEntry,
    read_price: ReadPrice,
    persist_rows: PersistRows,
) -> ValidationRunResult:
    """Evaluate a complete published population and retain its honest denominator."""

    evaluation_date = _strict_date(as_of, "as_of")
    records = [
        (pair, call)
        for pair, calls in populations
        for call in calls
    ]
    result = ValidationRunResult(scanned_calls=len(records))

    identities: list[int | None] = []
    for _pair, call in records:
        try:
            identities.append(normalize_call_id(call))
        except (TypeError, ValueError):
            identities.append(None)
    duplicate_ids = {
        call_id
        for call_id, count in Counter(identities).items()
        if call_id is not None and count > 1
    }

    pending_rows: list[dict[str, Any]] = []
    for (expected_pair, call), identity in zip(records, identities, strict=True):
        try:
            call_id, pair, call_date, due = _validate_call(
                call, expected_pair, evaluation_date
            )
        except (TypeError, ValueError) as exc:
            result.invalid_calls += 1
            if str(exc) == "call date cannot be after the validation date":
                result.add_limitation("future_call_dates_present")
            continue
        result.due_horizons += len(due)
        if identity in duplicate_ids:
            result.invalid_calls += 1
            continue

        existing = read_existing(call_id)
        try:
            completed_before = _completed_horizons(
                existing,
                call_id=call_id,
                pair=pair,
                call_date=call_date,
                mature_horizons=due,
            )
        except (TypeError, ValueError):
            result.invalid_calls += 1
            continue

        row = evaluate_call(
            call,
            evaluation_date,
            existing,
            read_entry=read_entry,
            read_price=read_price,
        )
        final_row = row if row is not None else existing
        try:
            completed_after = _completed_horizons(
                final_row,
                call_id=call_id,
                pair=pair,
                call_date=call_date,
                mature_horizons=due,
            )
        except (TypeError, ValueError):
            result.invalid_calls += 1
            continue
        result.completed_horizons += len(set(due) & completed_after)
        if row is not None and completed_after != completed_before:
            pending_rows.append(row)

    if pending_rows:
        persist_rows(pending_rows)
        result.rows.extend(pending_rows)
    return result
