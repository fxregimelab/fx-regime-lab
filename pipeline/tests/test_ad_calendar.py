"""Calendar coverage must be affirmative evidence, not an empty-list shortcut."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.paper import calendar as calendar_policy
from src.paper.calendar import (
    CalendarEvent,
    CalendarPayload,
    CoverageReceipt,
    collect_calendar,
    entry_blackout,
)
from src.paper.config import FRAMEWORK_VERSION, PLAYBOOK_VERSION
from src.paper.contracts import ContractError, Coverage, Pair

NOW = datetime(2026, 10, 19, 9, tzinfo=UTC)
LOOKBACK = calendar_policy.CALENDAR_LOOKBACK
LOOKAHEAD = calendar_policy.CALENDAR_LOOKAHEAD
WINDOW_START = NOW - LOOKBACK
WINDOW_END = NOW + LOOKAHEAD


class CalendarFake:
    """Honest collector: it returns only the events released in the window it was asked for."""

    source_id = "registered-calendar"

    def __init__(self, payload: CalendarPayload) -> None:
        self.payload = payload
        self.calls = 0
        self.requested: tuple[datetime, datetime] | None = None

    def read_window(
        self, start: datetime, end: datetime, currencies: tuple[str, ...]
    ) -> CalendarPayload:
        assert start < end
        assert currencies == ("EUR", "USD")
        self.calls += 1
        self.requested = (start, end)
        events = tuple(
            event for event in self.payload.events if start <= event.release_at <= end
        )
        return CalendarPayload(self.payload.receipt, events)


class RogueCalendarFake(CalendarFake):
    """Misbehaving collector: it ignores the requested window and returns extra events."""

    def read_window(
        self, start: datetime, end: datetime, currencies: tuple[str, ...]
    ) -> CalendarPayload:
        super().read_window(start, end, currencies)
        return self.payload


def receipt(**changes: Any) -> CoverageReceipt:
    base = CoverageReceipt(
        "registered-calendar", ("EUR", "USD"), WINDOW_START, WINDOW_END, NOW, Coverage.verified,
    )
    return replace(base, **changes)


def collect(payload: CalendarPayload) -> CalendarPayload:
    return collect_calendar(
        CalendarFake(payload), registered_sources=frozenset({"registered-calendar"}),
        pair=Pair.EURUSD, decision_at=NOW,
    )


def collect_rogue(payload: CalendarPayload) -> CalendarPayload:
    return collect_calendar(
        RogueCalendarFake(payload), registered_sources=frozenset({"registered-calendar"}),
        pair=Pair.EURUSD, decision_at=NOW,
    )


def red_event(event_id: str, release_at: datetime) -> CalendarEvent:
    return CalendarEvent(event_id, "USD", release_at, "red", NOW - timedelta(days=1), NOW)


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


def test_source_is_asked_for_the_exact_decided_window() -> None:
    source = CalendarFake(CalendarPayload(receipt(), ()))
    collect_calendar(source, registered_sources=frozenset({"registered-calendar"}),
                     pair=Pair.EURUSD, decision_at=NOW)
    assert source.requested == (NOW - timedelta(hours=2), NOW + timedelta(hours=24))


def test_decided_two_hour_policy_is_the_pinned_policy() -> None:
    assert calendar_policy.CALENDAR_LOOKBACK == timedelta(hours=2)
    assert calendar_policy.CALENDAR_LOOKAHEAD == timedelta(hours=24)
    assert calendar_policy.CALENDAR_BLACKOUT_BEFORE == timedelta(hours=2)
    assert calendar_policy.CALENDAR_BLACKOUT_AFTER == timedelta(hours=2)


def test_calendar_policy_is_pinned_to_the_framework_and_playbook_versions() -> None:
    version = calendar_policy.CALENDAR_POLICY_VERSION
    assert version.startswith("ad-calendar-blackout/2h-symmetric/")
    assert f"playbook-{PLAYBOOK_VERSION}" in version
    assert f"framework-{FRAMEWORK_VERSION}" in version


def test_collection_window_is_never_narrower_than_the_blackout_span() -> None:
    assert calendar_policy.CALENDAR_LOOKBACK >= calendar_policy.CALENDAR_BLACKOUT_BEFORE


def test_receipt_window_mismatch_names_the_policy_window() -> None:
    with pytest.raises(ContractError) as mismatch:
        collect(CalendarPayload(receipt(window_start=NOW), ()))
    assert "t-2h..t+24h" in mismatch.value.detail


def test_red_release_ninety_minutes_prior_is_observable_and_blocks() -> None:
    event = red_event("event-prior", NOW - timedelta(minutes=90))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert len(payload.events) == 1, "the release must be inside the collected window"
    assert entry_blackout(payload, decision_at=NOW) is True


def test_red_release_ninety_minutes_ahead_blocks_under_the_two_hour_rule() -> None:
    event = red_event("event-ahead", NOW + timedelta(minutes=90))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert len(payload.events) == 1
    assert entry_blackout(payload, decision_at=NOW) is True


@pytest.mark.parametrize("minutes,blocked", [
    (-120, True), (-119, True), (-1, True), (0, True), (1, True), (119, True), (120, True),
    (-121, False), (121, False),
])
def test_red_event_blackout_within_two_hours_of_the_release(
    minutes: int, blocked: bool
) -> None:
    event = red_event("event-1", NOW + timedelta(minutes=minutes))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert entry_blackout(payload, decision_at=NOW) is blocked


def test_blackout_past_edge_is_the_first_instant_of_the_collected_window() -> None:
    event = red_event("event-past-edge", NOW - timedelta(hours=2))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert len(payload.events) == 1
    assert entry_blackout(payload, decision_at=NOW) is True


def test_release_one_second_before_the_window_start_is_not_collected() -> None:
    event = red_event("event-just-before", NOW - timedelta(hours=2, seconds=1))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert payload.events == ()
    assert not entry_blackout(payload, decision_at=NOW)


def test_blackout_future_edge_two_hours_ahead_still_blocks() -> None:
    event = red_event("event-future-edge", NOW + timedelta(hours=2))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert len(payload.events) == 1
    assert entry_blackout(payload, decision_at=NOW) is True


def test_release_one_minute_past_the_future_edge_does_not_block() -> None:
    event = red_event("event-just-after", NOW + timedelta(hours=2, minutes=1))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert len(payload.events) == 1
    assert not entry_blackout(payload, decision_at=NOW)


def test_window_end_edge_is_observable_but_does_not_block() -> None:
    event = red_event("event-window-end", NOW + timedelta(hours=24))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert len(payload.events) == 1
    assert not entry_blackout(payload, decision_at=NOW)


def test_release_after_the_window_end_is_not_collected() -> None:
    event = red_event("event-after-window", NOW + timedelta(hours=24, minutes=1))
    payload = collect(CalendarPayload(receipt(), (event,)))
    assert payload.events == ()
    assert not entry_blackout(payload, decision_at=NOW)


@pytest.mark.parametrize("release_at", [
    NOW - timedelta(hours=3),
    NOW + timedelta(hours=24, minutes=1),
])
def test_source_returning_an_event_outside_the_requested_window_blocks(
    release_at: datetime,
) -> None:
    event = red_event("event-outside", release_at)
    with pytest.raises(ContractError):
        collect_rogue(CalendarPayload(receipt(), (event,)))


def test_entry_blackout_requires_coverage_of_the_blocking_span() -> None:
    narrow = CalendarPayload(receipt(window_end=NOW + timedelta(hours=1)), ())
    with pytest.raises(ContractError):
        entry_blackout(narrow, decision_at=NOW)


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
