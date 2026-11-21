"""Authored synthetic qualification evidence; no order/read/execution authentication."""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone
from itertools import permutations, product
from typing import Any

import pytest

from src.research import fpi_qualification as model
from src.research.fpi_qualification import (
    FpiQualificationCommand as Command,
)
from src.research.fpi_qualification import (
    FpiQualificationEventV2 as Event,
)
from src.research.fpi_qualification import (
    FpiQualificationHead as Head,
)
from src.research.fpi_qualification import (
    FpiQualificationMember as Member,
)
from src.research.fpi_qualification import (
    FpiQualificationView as View,
)
from src.research.fpi_qualification import (
    FpiResolutionWitness as Witness,
)
from src.research.fpi_qualification import (
    date_resolution,
    evaluate_fpi_qualification,
    member_qualification,
)
from src.research.fpi_qualification import (
    decode_fpi_qualification_command as decode_command,
)
from src.research.fpi_qualification import (
    decode_fpi_qualification_event as decode_event,
)

DAY = date(2026, 9, 25)
NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def member(label: str = "A", **changes: Any) -> Member:
    return replace(Member(digest(label), digest("value"), digest("parser"), DAY), **changes)


def event(
    scope: str = "membership",
    target: str | None = None,
    action: str = "ACCEPT",
    ordinal: int = 1,
    prior: Event | None = None,
    **changes: Any,
) -> Event:
    command = Command(
        scope,
        target or member().membership_id,
        action,
        "SYNTHETIC",
        digest("evidence"),
        prior.event_id if prior else None,
    )
    return replace(Event(command, ordinal, NOW), **changes)


def heads_for(members: tuple[Member, ...], events: tuple[Event, ...]) -> tuple[Head, ...]:
    targets: set[tuple[str, str]] = set()
    for item in members:
        targets.update(
            (
                ("membership", item.membership_id),
                ("value", item.value_sha256),
                ("parser", item.parser_sha256),
                ("date", item.reporting_date.isoformat()),
            )
        )
    latest: dict[tuple[str, str], Event] = {}
    for qualification_event in events:
        key = qualification_event.command.scope, qualification_event.command.target
        if key not in latest or qualification_event.event_ordinal > latest[key].event_ordinal:
            latest[key] = qualification_event
    return tuple(
        Head(*key, latest[key].event_id if key in latest else None) for key in sorted(targets)
    )


def view(events: tuple[Event, ...] = (), members: tuple[Member, ...] | None = None) -> View:
    members = (member(),) if members is None else members
    return View(members, heads_for(members, events), events)


def resolution(
    accepted: Event,
    ordinal: int = 2,
    *,
    chosen: Member | None = None,
    basis: tuple[str, ...] | None = None,
    **changes: Any,
) -> Event:
    chosen = chosen or member()
    witness = Witness(
        (
            Head("membership", chosen.membership_id, accepted.event_id),
            Head("value", chosen.value_sha256, None),
            Head("parser", chosen.parser_sha256, None),
        )
    )
    command = Command(
        "date",
        chosen.reporting_date.isoformat(),
        "RESOLVE",
        "SYNTHETIC",
        digest("resolve"),
        chosen_membership_id=chosen.membership_id,
        basis_membership_ids=basis or (chosen.membership_id,),
    )
    return replace(Event(command, ordinal, NOW, witness), **changes)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def independent_view_document(value: View) -> str:
    return canonical(
        {
            "version": "fpi-qualification-view-v2",
            "members": [
                {
                    "membership_id": m.membership_id,
                    "value_sha256": m.value_sha256,
                    "parser_sha256": m.parser_sha256,
                    "reporting_date": m.reporting_date.isoformat(),
                }
                for m in sorted(value.members, key=lambda m: m.membership_id)
            ],
            "heads": [
                {"scope": h.scope, "target": h.target, "event_id": h.event_id}
                for h in sorted(value.heads, key=lambda h: (h.scope, h.target))
            ],
            "events": [
                json.loads(e.document_json) for e in sorted(value.events, key=lambda e: e.event_id)
            ],
        }
    )


def test_reproduces_v1_tied_clock_limitation_without_changing_v1() -> None:
    from src.research.fpi_selection import FpiQualificationEvent
    from tests.test_fpi_selection import T0, accept, parsed, snapshot

    source = parsed()
    accepted = accept(source, recorded_at=T0 + timedelta(minutes=4))
    chosen = source.membership_id(source.days[0])
    resolved = FpiQualificationEvent(
        "date",
        DAY.isoformat(),
        "RESOLVE",
        T0 + timedelta(minutes=5),
        "synthetic",
        "synthetic",
        chosen_membership_id=chosen,
        basis_membership_ids=(chosen,),
    )
    snapshot((source,), (accepted, resolved))
    withdrawal = replace(
        accepted,
        action="WITHDRAW",
        recorded_at=resolved.recorded_at,
        prior_event_id=accepted.event_id,
    )
    for ordering in permutations((accepted, resolved, withdrawal)):
        with pytest.raises(ValueError, match="not qualified at resolution time"):
            snapshot((source,), ordering)


@pytest.mark.parametrize("decreasing", [False, True])
def test_ordinal_order_survives_tied_or_decreasing_clocks_and_permutations(
    decreasing: bool,
) -> None:
    accepted = event()
    resolved = resolution(accepted, recorded_at=NOW - timedelta(days=int(decreasing)))
    withdrawn = event(
        action="WITHDRAW",
        ordinal=3,
        prior=accepted,
        recorded_at=NOW - timedelta(days=2 * int(decreasing)),
    )
    original = view((accepted, resolved))
    assert date_resolution(original, DAY) == ("RESOLVED", member().membership_id)
    new = view((accepted, resolved, withdrawn))
    assert member_qualification(new, member().membership_id) == "WITHDRAWN"
    assert date_resolution(new, DAY) == ("TARGET_UNQUALIFIED", None)
    for ordering in permutations(new.events):
        for heads in permutations(new.heads):
            assert View(new.members, heads, ordering) == new
    assert date_resolution(original, DAY) == ("RESOLVED", member().membership_id)
    assert original.view_sha256 != new.view_sha256


def test_command_and_event_canonical_hash_domains_and_normalization() -> None:
    accepted = event(recorded_at=NOW.astimezone(timezone(timedelta(hours=5, minutes=30))))
    assert accepted.recorded_at is NOW or accepted.recorded_at == NOW
    assert decode_command(accepted.command.document_json) == accepted.command
    assert decode_event(accepted.document_json) == accepted
    assert accepted.command.command_id == digest(accepted.command.document_json)
    assert accepted.event_id == digest(accepted.document_json)
    assert set(json.loads(accepted.command.document_json)) == {
        "version",
        "scope",
        "target",
        "action",
        "reason_code",
        "evidence_sha256",
        "expected_prior_event_id",
        "chosen_membership_id",
        "basis_membership_ids",
    }
    assert set(json.loads(accepted.document_json)) == {
        "version",
        "command",
        "command_id",
        "event_ordinal",
        "recorded_at",
        "witness",
    }
    values = tuple(sorted((digest("A"), digest("B"))))
    command = Command(
        "date",
        DAY.isoformat(),
        "RESOLVE",
        "A",
        digest("proof"),
        chosen_membership_id=values[0],
        basis_membership_ids=values[::-1],
    )
    assert command.basis_membership_ids == values
    with pytest.raises(FrozenInstanceError):
        accepted.event_ordinal = 2  # type: ignore[misc]
    micro = replace(accepted, recorded_at=NOW.replace(microsecond=1000))
    assert ".001000+00:00" in micro.document_json
    assert decode_event(micro.document_json) == micro
    assert ".000000" not in accepted.document_json


@pytest.mark.parametrize(
    "field,value",
    [
        ("reason_code", "ANOTHER"),
        ("evidence_sha256", digest("other")),
        ("target", digest("other")),
        ("action", "QUARANTINE"),
        ("expected_prior_event_id", digest("prior")),
    ],
)
def test_command_changes_bind_both_identities(field: str, value: Any) -> None:
    old = event()
    new = replace(old, command=replace(old.command, **{field: value}))
    assert new.command.command_id != old.command.command_id
    assert new.event_id != old.event_id


def test_resolution_basis_time_ordinal_and_witness_are_hashed() -> None:
    accepted = event()
    resolved = resolution(accepted)
    alternative = replace(
        resolved.command, basis_membership_ids=(member().membership_id, digest("B"))
    )
    assert resolved.witness is not None
    witness = Witness(
        tuple(
            replace(h, event_id=digest("past")) if h.scope == "value" else h
            for h in resolved.witness.heads
        )
    )
    variants = (
        replace(resolved, command=alternative),
        replace(resolved, witness=witness),
        replace(resolved, event_ordinal=3),
        replace(resolved, recorded_at=NOW + timedelta(1)),
    )
    assert len({resolved.event_id, *(item.event_id for item in variants)}) == 5


@pytest.mark.parametrize("scope", ["membership", "value", "parser"])
@pytest.mark.parametrize("action", ["ACCEPT", "WITHDRAW", "QUARANTINE"])
def test_each_scope_action(scope: str, action: str) -> None:
    m = member()
    target = {"membership": m.membership_id, "value": m.value_sha256, "parser": m.parser_sha256}[
        scope
    ]
    current = view((event(scope, target, action),))
    expected = {
        "ACCEPT": "ACCEPTED" if scope == "membership" else "UNQUALIFIED",
        "WITHDRAW": "WITHDRAWN",
        "QUARANTINE": "QUARANTINED",
    }[action]
    assert member_qualification(current, m.membership_id) == expected


def test_all_scope_block_combinations_and_individual_clearing() -> None:
    m = member()
    for actions in product((None, "ACCEPT", "WITHDRAW", "QUARANTINE"), repeat=3):
        targets = (
            ("membership", m.membership_id),
            ("value", m.value_sha256),
            ("parser", m.parser_sha256),
        )
        events = tuple(
            event(*target, action, i + 1)
            for i, (target, action) in enumerate(zip(targets, actions, strict=True))
            if action is not None
        )
        expected = (
            "QUARANTINED"
            if "QUARANTINE" in actions
            else (
                "WITHDRAWN"
                if "WITHDRAW" in actions
                else ("ACCEPTED" if actions[0] == "ACCEPT" else "UNQUALIFIED")
            )
        )
        assert member_qualification(view(events), m.membership_id) == expected
    accepted = event()
    blocked = event("parser", m.parser_sha256, "WITHDRAW", 2)
    quarantine = event("value", m.value_sha256, "QUARANTINE", 3)
    clear_parser = event("parser", m.parser_sha256, "ACCEPT", 4, blocked)
    assert (
        member_qualification(view((accepted, clear_parser, quarantine)), m.membership_id)
        == "QUARANTINED"
    )
    clear_value = event("value", m.value_sha256, "ACCEPT", 5, quarantine)
    assert (
        member_qualification(view((accepted, clear_parser, clear_value)), m.membership_id)
        == "ACCEPTED"
    )


def test_explicit_reinstatement_restores_unchanged_resolution() -> None:
    accepted = event()
    resolved = resolution(accepted)
    withdrawn = event(action="WITHDRAW", ordinal=3, prior=accepted)
    reinstated = event(ordinal=4, prior=withdrawn)
    # The withdrawal ancestor is intentionally absent from this compact witness.
    current = view((accepted, resolved, reinstated))
    assert date_resolution(current, DAY) == ("RESOLVED", member().membership_id)


@pytest.mark.parametrize("scope", ["membership", "value", "parser"])
@pytest.mark.parametrize("block", ["WITHDRAW", "QUARANTINE"])
def test_blocked_historical_witness_rejects_despite_present_accept(scope: str, block: str) -> None:
    m = member()
    accepted = event()
    target = {"membership": m.membership_id, "value": m.value_sha256, "parser": m.parser_sha256}[
        scope
    ]
    blocked = event(scope, target, block, 2, accepted if scope == "membership" else None)
    resolved = resolution(accepted, 3)
    assert resolved.witness is not None
    witness = Witness(
        tuple(
            replace(h, event_id=blocked.event_id) if h.scope == scope else h
            for h in resolved.witness.heads
        )
    )
    resolved = replace(resolved, witness=witness)
    reinstated = event(scope, target, "ACCEPT", 4, blocked)
    events = (
        (blocked, resolved, reinstated)
        if scope == "membership"
        else (accepted, blocked, resolved, reinstated)
    )
    with pytest.raises(ValueError, match="Witness"):
        view(events)


def test_witness_absence_and_outdated_heads_contradict_available_history() -> None:
    accepted = event()
    value = event("value", member().value_sha256, "ACCEPT", 2)
    resolved = resolution(accepted, 3)
    with pytest.raises(ValueError, match="absence"):
        view((accepted, value, resolved))
    replaced_accept = event(ordinal=2, prior=accepted)
    with pytest.raises(ValueError, match="latest earlier"):
        view((accepted, replaced_accept, resolved))
    good = replace(
        resolved,
        witness=Witness(
            (
                Head("membership", member().membership_id, accepted.event_id),
                Head("parser", member().parser_sha256, None),
                Head("value", member().value_sha256, value.event_id),
            )
        ),
    )
    assert date_resolution(view((accepted, value, good)), DAY)[0] == "RESOLVED"


def test_new_candidates_make_resolution_stale_including_same_value_and_alternate_parser() -> None:
    accepted = event()
    resolved = resolution(accepted)
    variants = (
        member("B"),
        member("B", parser_sha256=digest("parser2")),
        member("B", value_sha256=digest("value2")),
    )
    for other in variants:
        for ordering in permutations((member(), other)):
            current = view((accepted, resolved), ordering)
            assert date_resolution(current, DAY) == ("STALE_RESOLUTION", None)
            assert member_qualification(current, other.membership_id) == "UNQUALIFIED"
    extra_date = member("B", reporting_date=DAY - timedelta(1), value_sha256=digest("dated-value"))
    assert date_resolution(view((accepted, resolved), (member(), extra_date)), DAY)[0] == "RESOLVED"


def test_empty_universe_absence_and_unknown_queries() -> None:
    empty = view(members=())
    assert empty == View((), (), ())
    assert empty.view_sha256 == digest(independent_view_document(empty))
    current = view()
    assert member_qualification(current, member().membership_id) == "UNQUALIFIED"
    assert date_resolution(current, DAY) == ("NO_RESOLUTION", None)
    for supplied in (empty, current):
        with pytest.raises(ValueError, match="Unknown"):
            member_qualification(supplied, digest("unknown"))
        with pytest.raises(ValueError, match="Unknown"):
            date_resolution(supplied, DAY - timedelta(1))
    with pytest.raises(ValueError):
        date_resolution(current, NOW)
    with pytest.raises(ValueError):
        View((), (Head("membership", member().membership_id, None),), ())


@pytest.mark.parametrize(
    "mode", ["missing", "extra", "duplicate", "wrong_target", "false_absence", "missing_event"]
)
def test_heads_are_an_explicit_exact_complete_set(mode: str) -> None:
    accepted = event()
    original = view((accepted,))
    heads, events = original.heads, original.events
    if mode == "missing":
        heads = heads[1:]
    elif mode == "extra":
        heads += (Head("membership", digest("extra"), None),)
    elif mode == "duplicate":
        heads += (heads[0],)
    elif mode == "wrong_target":
        heads = tuple(
            replace(h, event_id=accepted.event_id) if h.scope == "parser" else h for h in heads
        )
    elif mode == "false_absence":
        heads = tuple(replace(h, event_id=None) if h.scope == "membership" else h for h in heads)
    else:
        events = ()
    with pytest.raises(ValueError):
        View(original.members, heads, events)


def test_duplicate_metadata_events_commands_ordinals_and_forks_reject() -> None:
    accepted = event()
    with pytest.raises(ValueError, match="Duplicate membership"):
        view(members=(member(), member()))
    with pytest.raises(ValueError, match="Duplicate membership"):
        view(members=(member(), member(value_sha256=digest("contradiction"))))
    variants = (
        accepted,
        replace(accepted, event_ordinal=2),
        event("value", member().value_sha256, ordinal=1),
        event(action="WITHDRAW", ordinal=2),
        event(action="QUARANTINE", ordinal=2, prior=accepted),
    )
    for other in variants[:4]:
        with pytest.raises(ValueError):
            view((accepted, other))
    branch1 = event(action="WITHDRAW", ordinal=3, prior=accepted)
    with pytest.raises(ValueError, match="Forked"):
        view((accepted, variants[4], branch1))


def test_predecessors_may_be_absent_but_present_ones_must_be_same_target_and_earlier() -> None:
    accepted = replace(
        event(ordinal=2**63 - 1),
        command=replace(event().command, expected_prior_event_id=digest("old")),
    )
    assert member_qualification(view((accepted,)), member().membership_id) == "ACCEPTED"
    other = event("value", member().value_sha256, ordinal=1)
    wrong = replace(
        event(ordinal=2), command=replace(event().command, expected_prior_event_id=other.event_id)
    )
    with pytest.raises(ValueError, match="predecessor"):
        view((other, wrong))
    future = event(ordinal=4)
    backwards = event(action="WITHDRAW", ordinal=3, prior=future)
    with pytest.raises(ValueError, match="predecessor"):
        view((future, backwards))


def test_unrelated_ancestry_is_rejected_and_current_head_must_be_latest() -> None:
    accepted = event()
    withdrawn = event(action="WITHDRAW", ordinal=2, prior=accepted)
    with pytest.raises(ValueError, match="exactly current"):
        view((accepted, withdrawn))
    original = view((accepted,))
    with pytest.raises(ValueError, match="not latest"):
        View(original.members, original.heads, (accepted, withdrawn))
    assert member_qualification(view((withdrawn,)), member().membership_id) == "WITHDRAWN"


@pytest.mark.parametrize("mode", ["wrong_value", "wrong_parser", "future", "missing", "other_date"])
def test_resolution_context_is_checked(mode: str) -> None:
    accepted = event()
    resolved = resolution(accepted)
    members: tuple[Member, ...] = (member(),)
    events: tuple[Event, ...] = (accepted, resolved)
    assert resolved.witness is not None
    if mode in ("wrong_value", "wrong_parser"):
        scope = mode.removeprefix("wrong_")
        witness = Witness(
            tuple(
                replace(h, target=digest("other")) if h.scope == scope else h
                for h in resolved.witness.heads
            )
        )
        events = (accepted, replace(resolved, witness=witness))
    elif mode == "future":
        accepted = replace(accepted, event_ordinal=3)
        events = (accepted, resolution(accepted))
    elif mode == "missing":
        events = (resolved,)
    else:
        other = member(
            "other", reporting_date=DAY - timedelta(1), value_sha256=digest("dated-value")
        )
        members = (member(), other)
        events = (
            accepted,
            replace(
                resolved,
                command=replace(
                    resolved.command,
                    basis_membership_ids=(member().membership_id, other.membership_id),
                ),
            ),
        )
    with pytest.raises(ValueError):
        view(events, members)


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope", True),
        ("scope", "other"),
        ("target", "a" * 63),
        ("target", "A" * 64),
        ("action", False),
        ("action", "RESOLVE"),
        ("reason_code", "lower"),
        ("reason_code", "A" * 65),
        ("reason_code", "A\x00"),
        ("reason_code", "A\ud800"),
        ("reason_code", 1),
        ("evidence_sha256", None),
        ("expected_prior_event_id", True),
        ("chosen_membership_id", digest("A")),
        ("basis_membership_ids", []),
        ("basis_membership_ids", (digest("A"),)),
    ],
)
def test_strict_command_primitives(field: str, value: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        replace(event().command, **{field: value})


@pytest.mark.parametrize("value", [True, False, 0, -1, 2**63, 1.0, "1", None])
def test_strict_event_ordinal(value: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        replace(event(), event_ordinal=value)


@pytest.mark.parametrize(
    "value", ["2026-9-25", "0000-01-01", "10000-01-01", "2026-02-30", True, DAY, "20260925"]
)
def test_strict_date_targets(value: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        Head("date", value, None)


def test_endpoint_dates_aware_time_and_member_types() -> None:
    for day in (date.min, date.max):
        assert Head("date", day.isoformat(), None).target == day.isoformat()
        assert member(reporting_date=day).reporting_date == day
    for bad in (NOW, "2026-09-25", True):
        with pytest.raises(ValueError):
            member(reporting_date=bad)
    bad_times: tuple[Any, ...] = (
        NOW.replace(tzinfo=None),
        DAY,
        "2026-09-27",
        True,
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
    )
    for bad_time in bad_times:
        with pytest.raises(ValueError):
            replace(event(), recorded_at=bad_time)


@pytest.mark.parametrize("decoder,source", [(decode_command, "command"), (decode_event, "event")])
@pytest.mark.parametrize(
    "mode",
    [
        "extra",
        "missing",
        "spaces",
        "duplicate",
        "nan",
        "infinity",
        "nul",
        "surrogate",
        "unicode",
        "oversize",
        "deep",
        "array",
        "bytes",
        "bad_json",
    ],
)
def test_decoder_rejects_malformed_documents_without_leaking_input(
    decoder: Any, source: str, mode: str
) -> None:
    original = event().command.document_json if source == "command" else event().document_json
    document = json.loads(original)
    if mode == "extra":
        document["private_secret"] = "DO_NOT_LEAK"
        text = canonical(document)
    elif mode == "missing":
        document.pop("version")
        text = canonical(document)
    elif mode == "spaces":
        text = " " + original
    elif mode == "duplicate":
        text = '{"version":"DO_NOT_LEAK",' + original[1:]
    elif mode in ("nan", "infinity"):
        text = original[:-1] + ',"private_secret":' + ("NaN" if mode == "nan" else "Infinity") + "}"
    elif mode in ("nul", "surrogate", "unicode"):
        document["version"] = {"nul": "\x00", "surrogate": "\ud800", "unicode": "é"}[mode]
        text = json.dumps(document, ensure_ascii=mode != "unicode")
    elif mode == "oversize":
        text = " " * (300_001 if source == "command" else 400_001)
    elif mode == "deep":
        text = "[" * 10000 + '"DO_NOT_LEAK"' + "]" * 10000
    elif mode == "array":
        text = "[]"
    elif mode == "bytes":
        text = original.encode()  # type: ignore[assignment]
    else:
        text = '{"DO_NOT_LEAK":'
    with pytest.raises((ValueError, TypeError)) as error:
        decoder(text)
    assert "DO_NOT_LEAK" not in str(error.value)
    assert len(str(error.value)) < 150


def test_decoder_rejects_noncanonical_basis_timestamp_and_forged_id() -> None:
    accepted = event()
    resolved = resolution(accepted, basis=(member().membership_id, digest("B")))
    command = json.loads(resolved.command.document_json)
    command["basis_membership_ids"].reverse()
    with pytest.raises(ValueError, match="Noncanonical"):
        decode_command(canonical(command))
    for timestamp in (
        "2026-09-27T12:00:00Z",
        "2026-09-27T12:00:00.000000+00:00",
        "2026-09-27T17:30:00+05:30",
        "2026-09-27T12:00:00.1+00:00",
    ):
        document = json.loads(accepted.document_json)
        document["recorded_at"] = timestamp
        with pytest.raises(ValueError, match="Noncanonical"):
            decode_event(canonical(document))
    document = json.loads(accepted.document_json)
    document["command_id"] = digest("forged")
    with pytest.raises(ValueError, match="identity"):
        decode_event(canonical(document))


@pytest.mark.parametrize(
    "mode",
    [
        "member",
        "head",
        "command",
        "command_cache",
        "event",
        "event_cache",
        "witness",
        "tuple",
        "incomplete",
    ],
)
def test_forged_nested_frozen_objects_are_revalidated(mode: str) -> None:
    accepted = event()
    resolved = resolution(accepted)
    current = view((accepted, resolved))
    if mode == "member":
        object.__setattr__(current.members[0], "value_sha256", True)
    elif mode == "head":
        object.__setattr__(current.heads[0], "event_id", False)
    elif mode == "command":
        object.__setattr__(current.events[0].command, "action", "FORGED")
    elif mode == "command_cache":
        object.__setattr__(current.events[0].command, "document_json", "{}")
    elif mode == "event":
        object.__setattr__(current.events[0], "event_ordinal", True)
    elif mode == "event_cache":
        object.__setattr__(current.events[0], "event_id", digest("fake"))
    elif mode == "witness":
        saved = next(e for e in current.events if e.witness is not None)
        object.__setattr__(saved.witness, "heads", list(saved.witness.heads))  # type: ignore[union-attr]
    elif mode == "tuple":
        object.__setattr__(current, "events", list(current.events))
    else:
        object.__delattr__(current.events[0], "event_ordinal")
    with pytest.raises((ValueError, TypeError)):
        View(current.members, current.heads, current.events)
    with pytest.raises((ValueError, TypeError)):
        member_qualification(current, member().membership_id)


def test_outer_boundaries_do_not_retain_mutable_aliases() -> None:
    accepted = event()
    original_member = member()
    source_heads = heads_for((original_member,), (accepted,))
    current = View((original_member,), source_heads, (accepted,))
    original_hash = current.view_sha256
    object.__setattr__(original_member, "membership_id", digest("changed"))
    object.__setattr__(accepted.command, "action", "WITHDRAW")
    object.__setattr__(source_heads[0], "event_id", digest("changed"))
    assert current.view_sha256 == original_hash
    assert member_qualification(current, member().membership_id) == "ACCEPTED"


def test_tuple_count_and_basis_boundaries() -> None:
    basis = tuple(digest(str(i)) for i in range(4096))
    command = Command(
        "date",
        DAY.isoformat(),
        "RESOLVE",
        "A",
        digest("e"),
        chosen_membership_id=basis[0],
        basis_membership_ids=basis,
    )
    assert decode_command(command.document_json) == command
    with pytest.raises(ValueError):
        replace(command, basis_membership_ids=(*basis, digest("overflow")))
    with pytest.raises(ValueError):
        replace(command, basis_membership_ids=(basis[0], basis[0]))
    with pytest.raises(ValueError):
        replace(command, basis_membership_ids=())
    with pytest.raises(ValueError):
        replace(command, chosen_membership_id=digest("not in basis"))
    for field_name, maximum in (("members", 20000), ("heads", 100000), ("events", 100000)):
        inputs: dict[str, Any] = {"members": (), "heads": (), "events": ()}
        inputs[field_name] = (None,) * (maximum + 1)
        with pytest.raises(ValueError, match="bounded exact tuple"):
            View(**inputs)
        inputs[field_name] = []
        with pytest.raises(ValueError, match="bounded exact tuple"):
            View(**inputs)


def test_member_count_limit_accepts_full_twenty_thousand_without_history() -> None:
    members = tuple(member(str(index)) for index in range(20000))
    current = view(members=members)
    assert len(current.members) == 20000
    assert len(current.heads) == 20003
    assert current.view_sha256 == digest(independent_view_document(current))


def test_exact_canonical_byte_budget_rejects_before_later_reconstruction(monkeypatch: Any) -> None:
    accepted = event()
    resolved = resolution(accepted)
    current = view((accepted, resolved))
    document = independent_view_document(current)
    assert current.view_sha256 == digest(document)
    monkeypatch.setattr(model, "_MAX_VIEW_BYTES", len(document))
    assert view((accepted, resolved)) == current
    monkeypatch.setattr(model, "_MAX_VIEW_BYTES", len(document) - 1)
    with pytest.raises(ValueError, match="canonical byte limit"):
        view((accepted, resolved))
    monkeypatch.setattr(model, "_MAX_VIEW_BYTES", 1)
    forged = object.__new__(Event)
    with pytest.raises(ValueError, match="canonical byte limit"):
        View((member(),), current.heads, (forged,))


def test_codec_byte_budget_endpoints(monkeypatch: Any) -> None:
    accepted = event()
    for attribute, document, decoder in (
        ("_MAX_COMMAND_BYTES", accepted.command.document_json, decode_command),
        ("_MAX_EVENT_BYTES", accepted.document_json, decode_event),
    ):
        with monkeypatch.context() as patch:
            patch.setattr(model, attribute, len(document))
            decoder(document)
            patch.setattr(model, attribute, len(document) - 1)
            with pytest.raises(ValueError):
                decoder(document)


def test_long_history_ordinals_need_only_compact_references() -> None:
    old = replace(
        event(ordinal=2**63 - 3),
        command=replace(event().command, expected_prior_event_id=digest("millionth")),
    )
    resolved = resolution(old, ordinal=2**63 - 2)
    blocked = event(action="WITHDRAW", ordinal=2**63 - 1, prior=old)
    current = view((old, resolved, blocked))
    assert len(current.events) == 3
    assert date_resolution(current, DAY) == ("TARGET_UNQUALIFIED", None)


def test_value_hash_cannot_claim_two_reporting_dates() -> None:
    other = member("other", reporting_date=DAY - timedelta(1))
    with pytest.raises(ValueError, match="different reporting dates"):
        view(members=(member(), other))


def test_batch_evaluation_reconstructs_once_and_binds_exact_result(monkeypatch: Any) -> None:
    accepted = event()
    resolved = resolution(accepted)
    current = view((accepted, resolved))
    calls = 0
    original = model._validated_view

    def tracked(value: View) -> View:
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(model, "_validated_view", tracked)
    result = evaluate_fpi_qualification(current)
    assert calls == 1
    assert result.member_states == ((member().membership_id, "ACCEPTED"),)
    assert result.date_resolutions == ((DAY, "RESOLVED", member().membership_id),)
    assert result.result_sha256 == digest(
        canonical(
            {
                "version": "fpi-qualification-evaluation-v2",
                "view_sha256": current.view_sha256,
                "member_states": result.member_states,
                "date_resolutions": ((DAY.isoformat(), "RESOLVED", member().membership_id),),
            }
        )
    )
    assert replace(result, view_sha256=digest("another")).result_sha256 != result.result_sha256
    with pytest.raises(ValueError):
        replace(result, member_states=((member().membership_id, "WITHDRAWN"),))
    with pytest.raises(ValueError):
        replace(result, date_resolutions=((DAY, "TARGET_UNQUALIFIED", member().membership_id),))
    with pytest.raises(FrozenInstanceError):
        result.view_sha256 = digest("forged")  # type: ignore[misc]


def test_large_batch_is_one_reconstruction_and_one_evaluation_per_member(monkeypatch: Any) -> None:
    members = tuple(
        member(
            str(i),
            reporting_date=DAY + timedelta(days=i % 100),
            value_sha256=digest("day-" + str(i % 100)),
        )
        for i in range(20000)
    )
    current = view(members=members)
    counts = {"view": 0, "member": 0}
    original_view, original_qualification = model._validated_view, model._qualification

    def tracked_view(value: View) -> View:
        counts["view"] += 1
        return original_view(value)

    def tracked_member(value: Member, heads: dict[tuple[str, str], str]) -> str:
        counts["member"] += 1
        return original_qualification(value, heads)

    monkeypatch.setattr(model, "_validated_view", tracked_view)
    monkeypatch.setattr(model, "_qualification", tracked_member)
    result = evaluate_fpi_qualification(current)
    assert counts == {"view": 1, "member": 20000}
    assert len(result.member_states) == 20000
    assert len(result.date_resolutions) == 100
    assert all(state == "UNQUALIFIED" for _, state in result.member_states)
    assert all(
        state == "NO_RESOLUTION" and chosen is None for _, state, chosen in result.date_resolutions
    )


def test_actual_sixteen_megabyte_limit_stops_before_remaining_events(monkeypatch: Any) -> None:
    members = tuple(member(str(index)) for index in range(20000))
    events = tuple(event(target=m.membership_id, ordinal=i + 1) for i, m in enumerate(members))
    heads = heads_for(members, events)
    copies = 0
    original = model._copy_event

    def tracked(value: Event) -> Event:
        nonlocal copies
        copies += 1
        return original(value)

    monkeypatch.setattr(model, "_copy_event", tracked)
    assert model._MAX_VIEW_BYTES == 16000000
    with pytest.raises(ValueError, match="canonical byte limit"):
        View(members, heads, events)
    assert 0 < copies < len(events)


def test_many_dates_share_compact_historical_parser_witnesses(monkeypatch: Any) -> None:
    members = tuple(
        member(
            str(index),
            value_sha256=digest("dated" + str(index)),
            reporting_date=DAY + timedelta(days=index),
        )
        for index in range(250)
    )
    events: list[Event] = []
    prior_parser = None
    for index, m in enumerate(members):
        accepted = event(target=m.membership_id, ordinal=3 * index + 1)
        parser = event("parser", m.parser_sha256, ordinal=3 * index + 2, prior=prior_parser)
        resolved = resolution(accepted, 3 * index + 3, chosen=m)
        assert resolved.witness is not None
        resolved = replace(
            resolved,
            witness=Witness(
                tuple(
                    replace(h, event_id=parser.event_id) if h.scope == "parser" else h
                    for h in resolved.witness.heads
                )
            ),
        )
        events.extend((accepted, parser, resolved))
        prior_parser = parser
    lookups = 0
    original = bisect_left

    def tracked(values: list[int], ordinal: int) -> int:
        nonlocal lookups
        lookups += 1
        return original(values, ordinal)

    monkeypatch.setattr(model, "bisect_left", tracked)
    current = view(tuple(events), members)
    assert lookups == 3 * len(members)
    result = evaluate_fpi_qualification(current)
    assert lookups == 6 * len(members)
    assert len(result.date_resolutions) == len(members)
    assert all(state == "RESOLVED" for _, state, _ in result.date_resolutions)


@pytest.mark.parametrize(
    "member_rows,date_rows",
    [
        ([], ()),
        (((digest("A"), "UNKNOWN"),), ()),
        (((digest("A"), "ACCEPTED"), (digest("A"), "ACCEPTED")), ()),
        (((digest("A"),),), ()),
        (([digest("A"), "ACCEPTED"],), ()),
        ((), ((NOW, "NO_RESOLUTION", None),)),
        ((), ((DAY, "UNKNOWN", None),)),
        ((), ((DAY, "NO_RESOLUTION", None), (DAY, "NO_RESOLUTION", None))),
        ((), ((DAY, "RESOLVED", digest("missing")),)),
        ((), ((DAY, "NO_RESOLUTION"),)),
    ],
)
def test_evaluation_result_has_strict_bounded_rows(member_rows: Any, date_rows: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        model.FpiQualificationEvaluation(digest("view"), member_rows, date_rows)


def test_evaluation_result_canonicalizes_only_row_order() -> None:
    rows = ((digest("B"), "UNQUALIFIED"), (digest("A"), "ACCEPTED"))
    dates = ((DAY + timedelta(1), "NO_RESOLUTION", None), (DAY, "RESOLVED", digest("A")))
    original = model.FpiQualificationEvaluation(digest("view"), rows, dates)
    assert original == model.FpiQualificationEvaluation(digest("view"), rows[::-1], dates[::-1])
    assert original.member_states == tuple(sorted(rows))
    assert original.date_resolutions == tuple(sorted(dates))
