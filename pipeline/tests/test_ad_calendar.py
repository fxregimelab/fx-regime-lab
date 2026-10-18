"""Calendar coverage must be affirmative evidence, not an empty-list shortcut."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.paper.calendar import (
    CalendarEvent,
    CalendarPayload,
    CoverageReceipt,
    collect_calendar,
    entry_blackout,
)
from src.paper.contracts import ContractError, Coverage, Pair

NOW = datetime(2026, 10, 19, 9, tzinfo=UTC)


class CalendarFake:
    source_id = "registered-calendar"

    def __init__(self, payload: CalendarPayload) -> None:
        self.payload = payload
        self.calls = 0

    def read_window(
        self, start: datetime, end: datetime, currencies: tuple[str, ...]
    ) -> CalendarPayload:
        assert start == NOW - timedelta(minutes=15)
        assert end == NOW + timedelta(hours=24)
        assert currencies == ("EUR", "USD")
        self.calls += 1
        return self.payload


def receipt(**changes: Any) -> CoverageReceipt:
    base = CoverageReceipt(
        "registered-calendar", ("EUR", "USD"), NOW - timedelta(minutes=15),
        NOW + timedelta(hours=24), NOW, Coverage.verified,
    )
    return replace(base, **changes)


def collect(payload: CalendarPayload) -> CalendarPayload:
    return collect_calendar(
        CalendarFake(payload), registered_sources=frozenset({"registered-calendar"}),
        pair=Pair.EURUSD, decision_at=NOW,
    )


def test_verified_empty_calendar_is_distinct_from_failed_coverage() -> None:
    result = collect(CalendarPayload(receipt(), ()))
    assert result.receipt.status is Coverage.verified
    assert not entry_blackout(result, decision_at=NOW)
    with pytest.raises(ContractError):
        collect(CalendarPayload(receipt(status=Coverage.unavailable), ()))


@pytest.mark.parametrize("changes", [
    {"currencies": ("USD",)},
    {"window_start": NOW},
    {"window_end": NOW + timedelta(hours=23)},
    {"fetched_at": NOW - timedelta(minutes=5, seconds=1)},
    {"fetched_at": NOW + timedelta(seconds=1)},
    {"source_id": "different-source"},
    {"fetched_at": NOW.replace(tzinfo=None)},
])
def test_incomplete_stale_future_or_mismatched_receipt_blocks(changes: dict[str, Any]) -> None:
    with pytest.raises(ContractError):
        collect(CalendarPayload(receipt(**changes), ()))


def test_unregistered_source_is_never_contacted() -> None:
    source = CalendarFake(CalendarPayload(receipt(), ()))
    with pytest.raises(ContractError):
        collect_calendar(source, registered_sources=frozenset(), pair=Pair.EURUSD,
                         decision_at=NOW)
    assert source.calls == 0


@pytest.mark.parametrize("minutes,blocked", [(-121, False), (-120, True),
                                            (0, True), (15, True), (16, False)])
def test_red_event_blackout_before_and_after_release(minutes: int, blocked: bool) -> None:
    event = CalendarEvent("event-1", "USD", NOW + timedelta(minutes=minutes),
                          "red", NOW - timedelta(days=1), NOW)
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert entry_blackout(payload, decision_at=NOW) is blocked


@pytest.mark.parametrize("changes", [
    {"impact": "unknown"}, {"available_at": NOW + timedelta(seconds=1)},
    {"published_at": NOW + timedelta(seconds=1)}, {"currency": ""},
    {"revision": True}, {"event_id": ""},
])
def test_bad_or_unavailable_events_block(changes: dict[str, Any]) -> None:
    event = CalendarEvent("event-1", "USD", NOW, "red", NOW, NOW)
    with pytest.raises(ContractError):
        collect(CalendarPayload(receipt(), (replace(event, **changes),)))


def test_revisions_are_retained_and_latest_available_release_is_used() -> None:
    old = CalendarEvent("release", "USD", NOW, "red", NOW - timedelta(days=1),
                        NOW - timedelta(minutes=1))
    new = replace(old, release_at=NOW + timedelta(hours=3), available_at=NOW, revision=2)
    payload = collect(CalendarPayload(receipt(), (old, new)))
    assert len(payload.events) == 2
    assert not entry_blackout(payload, decision_at=NOW)
    with pytest.raises(ContractError):
        collect(CalendarPayload(receipt(), (new, new)))


def test_expired_calendar_cannot_be_reused_for_later_entry() -> None:
    payload = collect(CalendarPayload(receipt(), ()))
    with pytest.raises(ContractError):
        entry_blackout(payload, decision_at=NOW + timedelta(minutes=6))
