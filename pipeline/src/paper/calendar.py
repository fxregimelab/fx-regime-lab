"""Authoritative calendar coverage and entry blackout (AD-T08 slice).

Fail-closed coverage for the red-event blackout authority:

- Only sources explicitly registered for runtime use are contacted; an
  unregistered source is rejected before any read (no scraped fallbacks).
- A verified *empty* calendar is legitimate evidence ("no qualifying events"),
  while any non-verified status, stale fetch, window/currency mismatch or
  malformed event blocks entry.
- Revisions are retained for evidence; the latest revision per event id
  determines the release time used for blackout math.
- Source data is inert input; nothing here executes or trusts its text.

This module never fetches by itself — a registered collector transport supplies
the raw window. Live entitlement for that transport is a separate provisioning
fact; its absence stays a blocker rather than being faked here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from src.paper.contracts import ContractError, Coverage, Pair

_RED_BLACKOUT_BEFORE = timedelta(minutes=15)
_RED_BLACKOUT_AFTER = timedelta(hours=2)
_COVERAGE_LOOKBACK = timedelta(minutes=15)
_COVERAGE_LOOKAHEAD = timedelta(hours=24)
_MAX_FETCH_AGE = timedelta(minutes=5)
_IMPACT_TIERS = frozenset({"red", "amber", "green"})

_PAIR_CURRENCIES: dict[Pair, tuple[str, ...]] = {
    Pair.EURUSD: ("EUR", "USD"),
    Pair.USDJPY: ("USD", "JPY"),
}

_DIGEST_LEN = 64


def _aware_utc(name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: timezone-aware datetime required")
    if value.utcoffset() != timedelta(0):
        raise ContractError("INVALID_SCHEMA", f"{name}: only UTC datetimes are accepted")
    return value


def _non_empty(name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string required")
    return value


@dataclass(frozen=True)
class CoverageReceipt:
    """Affirmative coverage proof supplied by one registered collector."""

    source_id: str
    currencies: tuple[str, ...]
    window_start: datetime
    window_end: datetime
    fetched_at: datetime
    status: Coverage

    def __post_init__(self) -> None:
        _non_empty("CoverageReceipt.source_id", self.source_id)
        if type(self.currencies) is not tuple or not self.currencies:
            raise ContractError("INVALID_SCHEMA", "CoverageReceipt.currencies: tuple required")
        for currency in self.currencies:
            _non_empty("CoverageReceipt.currencies", currency)
        _aware_utc("CoverageReceipt.window_start", self.window_start)
        _aware_utc("CoverageReceipt.window_end", self.window_end)
        _aware_utc("CoverageReceipt.fetched_at", self.fetched_at)
        if not isinstance(self.status, Coverage):
            raise ContractError("INVALID_SCHEMA", "CoverageReceipt.status: Coverage required")


@dataclass(frozen=True)
class CalendarEvent:
    """One authoritative calendar event; the latest revision per id wins."""

    event_id: str
    currency: str
    release_at: datetime
    impact: str
    published_at: datetime
    available_at: datetime
    revision: int = 1

    def __post_init__(self) -> None:
        _non_empty("CalendarEvent.event_id", self.event_id)
        _non_empty("CalendarEvent.currency", self.currency)
        _aware_utc("CalendarEvent.release_at", self.release_at)
        _aware_utc("CalendarEvent.published_at", self.published_at)
        _aware_utc("CalendarEvent.available_at", self.available_at)
        if type(self.impact) is not str or self.impact not in _IMPACT_TIERS:
            raise ContractError("CALENDAR_UNKNOWN", f"CalendarEvent.impact: {self.impact!r}")
        if type(self.revision) is not int or self.revision < 1:
            raise ContractError("INVALID_SCHEMA", "CalendarEvent.revision: positive int required")


@dataclass(frozen=True)
class CalendarPayload:
    """Window result: one coverage receipt plus zero or more events."""

    receipt: CoverageReceipt
    events: tuple[CalendarEvent, ...] = ()


class CalendarSource(Protocol):
    """Registered collector transport; supplies one already-fetched window."""

    source_id: str

    def read_window(
        self, start: datetime, end: datetime, currencies: tuple[str, ...]
    ) -> CalendarPayload: ...


def _validate_event(event: CalendarEvent, decision_at: datetime) -> None:
    _aware_utc("CalendarEvent.release_at", event.release_at)
    _aware_utc("CalendarEvent.published_at", event.published_at)
    _aware_utc("CalendarEvent.available_at", event.available_at)
    if event.published_at > event.available_at:
        raise ContractError("INVALID_SCHEMA", "CalendarEvent: published after available")
    if event.available_at > decision_at:
        raise ContractError("INVALID_SCHEMA", "CalendarEvent: not yet available at decision")


def _validate_receipt_shape(receipt: CoverageReceipt, decision_at: datetime) -> None:
    _aware_utc("CoverageReceipt.window_start", receipt.window_start)
    _aware_utc("CoverageReceipt.window_end", receipt.window_end)
    fetched_at = _aware_utc("CoverageReceipt.fetched_at", receipt.fetched_at)
    if fetched_at > decision_at:
        raise ContractError("SOURCE_STALE", "coverage receipt fetched in the future")
    if decision_at - fetched_at > _MAX_FETCH_AGE:
        raise ContractError("SOURCE_STALE", "coverage refresh older than 5 minutes")


def collect_calendar(
    source: CalendarSource,
    *,
    registered_sources: frozenset[str],
    pair: Pair,
    decision_at: datetime,
) -> CalendarPayload:
    """Collect and validate one calendar window; fail closed on weak coverage."""
    _aware_utc("decision_at", decision_at)
    source_id = getattr(source, "source_id", None)
    if type(source_id) is not str or source_id not in registered_sources:
        raise ContractError("SOURCE_INCOMPLETE", f"calendar source {source_id!r} is not registered")

    currencies = _PAIR_CURRENCIES[pair]
    start = decision_at - _COVERAGE_LOOKBACK
    end = decision_at + _COVERAGE_LOOKAHEAD
    payload = source.read_window(start, end, currencies)
    if not isinstance(payload, CalendarPayload):
        raise ContractError("INVALID_SCHEMA", "calendar source must return a CalendarPayload")

    receipt = payload.receipt
    _validate_receipt_shape(receipt, decision_at)
    if receipt.source_id != source_id:
        raise ContractError("SOURCE_INCOMPLETE", "receipt/source identity mismatch")
    if receipt.currencies != currencies:
        raise ContractError("SOURCE_INCOMPLETE", "receipt currencies do not cover the pair")
    if receipt.window_start != start or receipt.window_end != end:
        raise ContractError("SOURCE_INCOMPLETE", "receipt window does not match t-15min..t+24h")
    if receipt.status is not Coverage.verified:
        raise ContractError("SOURCE_INCOMPLETE", f"calendar coverage status {receipt.status!r}")

    seen: set[tuple[str, int]] = set()
    for event in payload.events:
        if not isinstance(event, CalendarEvent):
            raise ContractError("INVALID_SCHEMA", "calendar payload contains a non-event")
        _validate_event(event, decision_at)
        if event.currency not in receipt.currencies:
            raise ContractError("SOURCE_INCOMPLETE", "event currency outside covered set")
        key = (event.event_id, event.revision)
        if key in seen:
            raise ContractError("CONFLICT", f"duplicate calendar event {event.event_id!r}")
        seen.add(key)
    return payload


def entry_blackout(payload: CalendarPayload, *, decision_at: datetime) -> bool:
    """True when a red release blocks new entries at ``decision_at``.

    Blackout rule: no entry from 15 minutes before a red release until 2 hours
    after it. The latest revision per event id is the authoritative release
    time; superseded revisions remain archived as evidence only.
    """
    _aware_utc("decision_at", decision_at)
    receipt = payload.receipt
    _validate_receipt_shape(receipt, decision_at)
    if receipt.status is not Coverage.verified:
        raise ContractError("SOURCE_INCOMPLETE", f"calendar coverage status {receipt.status!r}")
    if not receipt.window_start <= decision_at <= receipt.window_end:
        raise ContractError("SOURCE_INCOMPLETE", "decision outside the covered calendar window")

    latest: dict[str, CalendarEvent] = {}
    for event in payload.events:
        _validate_event(event, decision_at)
        current = latest.get(event.event_id)
        if current is None or event.revision > current.revision:
            latest[event.event_id] = event
    for event in latest.values():
        if event.impact != "red":
            continue
        if event.release_at - _RED_BLACKOUT_BEFORE <= decision_at <= (
            event.release_at + _RED_BLACKOUT_AFTER
        ):
            return True
    return False
