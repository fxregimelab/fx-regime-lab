"""Authored synthetic evidence only; these tests do not prove database read visibility."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import UTC, datetime, timedelta
from itertools import permutations
from typing import Any

import pytest

from src.research.fpi_capture import build_fpi_capture
from src.research.fpi_observation import FPI_OBSERVATION_VERSION, build_fpi_observation
from src.research.fpi_selection import (
    FpiDecisionSnapshot,
    FpiParsedDay,
    FpiParseResult,
    FpiQualificationEvent,
    FpiSelectionPolicy,
    select_fpi,
)
from tests.test_fpi_observation import _fpi_fixture

T0 = datetime(2026, 9, 25, 12, tzinfo=UTC)
P1 = hashlib.sha256(b"synthetic parser artifact + dependencies/config 1").hexdigest()
P2 = hashlib.sha256(b"synthetic parser artifact + dependencies/config 2").hexdigest()
LATEST = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"
MONTHLY = LATEST.replace("Latest", "Monthly")


def policy(**changes: Any) -> FpiSelectionPolicy:
    return replace(
        FpiSelectionPolicy((P1, P2), 3, 40, 20, 10, "fpi-v1", "research-v1", "5D", "a" * 64),
        **changes,
    )


def parsed(
    minute: int = 0,
    shift: int = 0,
    *,
    day: int = 25,
    end: int | None = None,
    source: str = LATEST,
    parser: str = P1,
    recorded: int | None = None,
    days: tuple[int, ...] | None = None,
) -> FpiParseResult:
    end = minute + 1 if end is None else end
    capture = build_fpi_capture(
        body=f"synthetic value {shift}".encode(),
        source_url=source,
        requested_at=T0 + timedelta(minutes=minute),
        retrieved_at=T0 + timedelta(minutes=end),
        http_status=200,
    )
    values = []
    for report_day in days or (day,):
        observation = build_fpi_observation(**_fpi_fixture(report_day, shift=shift))
        values.append(
            FpiParsedDay(
                observation.document_json,
                hashlib.sha256(f"USD evidence {shift}".encode()).hexdigest(),
            )
        )
    return FpiParseResult(
        capture,
        parser,
        FPI_OBSERVATION_VERSION,
        T0 + timedelta(minutes=end if recorded is None else recorded),
        tuple(values),
    )


def accept(parse: FpiParseResult, index: int = 0, **changes: Any) -> FpiQualificationEvent:
    return replace(
        FpiQualificationEvent(
            "membership",
            parse.membership_id(parse.days[index]),
            "ACCEPT",
            parse.recorded_at,
            "research qualification",
            "synthetic-evidence",
        ),
        **changes,
    )


def snapshot(
    parses: tuple[FpiParseResult, ...],
    events: tuple[FpiQualificationEvent, ...] | None = None,
    *,
    rules: FpiSelectionPolicy | None = None,
    at: datetime = T0 + timedelta(hours=1),
    ordered: bool = True,
) -> FpiDecisionSnapshot:
    rules = rules or policy()
    if events is None:
        events = tuple(accept(parse, i) for parse in parses for i in range(len(parse.days)))
    return FpiDecisionSnapshot(
        "synthetic-decision",
        at,
        rules.policy_sha256,
        parses,
        events,
        tuple(p.capture.capture_sha256 for p in parses) if ordered else (),
    )


def test_reversion_snapshots_and_every_input_permutation() -> None:
    a, b, again = parsed(0), parsed(2, 1), parsed(4)
    assert a.days[0].value_sha256 == again.days[0].value_sha256
    assert a.capture.capture_sha256 != again.capture.capture_sha256
    for records, expected in (((a,), a), ((a, b), b), ((a, b, again), again)):
        selections = [select_fpi(snapshot(order), policy()) for order in permutations(records)]
        assert all(result == selections[0] for result in selections)
        current = selections[0].current
        assert current is not None
        assert current.membership_ids == (expected.membership_id(expected.days[0]),)
    original = snapshot((a, b, again))
    retried = snapshot((a, b, again, again))
    assert original == retried
    assert select_fpi(original, policy()) == select_fpi(retried, policy())


def test_visibility_is_exact_membership_not_timestamp_inference() -> None:
    capture = parsed(0, recorded=3)
    qualification = accept(capture, recorded_at=T0 + timedelta(minutes=5))
    earlier = snapshot((), at=T0 + timedelta(minutes=1))
    unqualified = snapshot((capture,), (), at=T0 + timedelta(minutes=4))
    later = snapshot((capture,), (qualification,), at=T0 + timedelta(minutes=5))
    assert select_fpi(earlier, policy()).status == "NO_OBSERVATIONS"
    assert select_fpi(unqualified, policy()).status == "UNQUALIFIED"
    assert select_fpi(later, policy()).current is not None
    assert earlier.parses == ()
    assert qualification.recorded_at > capture.recorded_at
    with pytest.raises(ValueError, match="future"):
        replace(earlier, parses=(capture,))
    with pytest.raises(ValueError, match="future"):
        replace(unqualified, events=(qualification,))


def test_late_import_cannot_rewrite_replay_or_supersede_newer_capture() -> None:
    old = parsed(0, recorded=30)
    new = parsed(2, 1)
    saved = snapshot((new,))
    before = select_fpi(saved, policy())
    future = select_fpi(snapshot((new, old)), policy())
    assert future.current == before.current
    assert select_fpi(saved, policy()) == before
    assert future.input_set_sha256 != before.input_set_sha256
    assert select_fpi(snapshot((old, new), ordered=False), policy()).status == "CONFLICT"


def test_overlapping_and_out_of_order_responses_conflict_until_new_occurrence() -> None:
    slow, fast = parsed(0, end=4), parsed(1, 1, end=2)
    for order in permutations((slow, fast)):
        result = select_fpi(snapshot(order), policy())
        assert result.status == "CONFLICT"
        assert result.current is None
    final = parsed(5, 2)
    for order in permutations((slow, fast, final)):
        assert (
            select_fpi(snapshot(order), policy()).current
            == select_fpi(snapshot((final,)), policy()).current
        )


def test_touching_intervals_do_not_establish_strict_order() -> None:
    assert select_fpi(snapshot((parsed(0, end=1), parsed(1, 1))), policy()).status == "CONFLICT"


def test_endpoint_disagreement_and_agreement_preserve_memberships() -> None:
    latest, monthly = parsed(0), parsed(2, 1, source=MONTHLY)
    for order in permutations((latest, monthly)):
        assert select_fpi(snapshot(order), policy()).status == "CONFLICT"
    same = parsed(2, source=MONTHLY)
    result = select_fpi(snapshot((latest, same)), policy())
    assert result.current is not None and len(result.current.membership_ids) == 2
    priority = policy(source_rule="LATEST", source_rationale="Explicit synthetic priority")
    chosen = select_fpi(snapshot((latest, monthly), rules=priority), priority)
    assert chosen.current is not None
    assert chosen.current.value_sha256 == latest.days[0].value_sha256
    assert chosen.current.reasons == ("POLICY_SOURCE_PRIORITY",)


def test_newest_date_conflict_never_silently_falls_back() -> None:
    older = parsed(day=24)
    result = select_fpi(snapshot((older, parsed(2), parsed(4, 1, source=MONTHLY))), policy())
    assert result.status == "CONFLICT" and result.current is None


def test_parser_correction_requires_qualification_and_resolution() -> None:
    old = parsed()
    corrected = replace(
        parsed(0, 1), capture=old.capture, parser_sha256=P2, recorded_at=T0 + timedelta(minutes=3)
    )
    initial = snapshot((old, corrected), (accept(old),))
    assert select_fpi(initial, policy()).current == select_fpi(snapshot((old,)), policy()).current
    both = snapshot((old, corrected))
    assert select_fpi(both, policy()).status == "CONFLICT"
    previous = accept(old)
    withdraw = replace(
        previous,
        action="WITHDRAW",
        prior_event_id=previous.event_id,
        recorded_at=T0 + timedelta(minutes=4),
    )
    fixed = snapshot((old, corrected), (previous, withdraw, accept(corrected)))
    assert (
        select_fpi(fixed, policy()).current == select_fpi(snapshot((corrected,)), policy()).current
    )
    assert select_fpi(initial, policy()).current == select_fpi(snapshot((old,)), policy()).current
    incompatible = replace(corrected, parser_sha256=P1)
    with pytest.raises(ValueError, match="Contradictory"):
        snapshot((old, incompatible))
    failed = replace(old, parser_sha256=P2, days=(), failure_reason="UNRECOGNIZED_TABLE")
    result = select_fpi(snapshot((old, failed)), policy())
    assert result.current is not None and result.parse_diagnostics == (
        (failed.parse_id, "UNRECOGNIZED_TABLE"),
    )


def test_explicit_resolution_binds_complete_candidate_basis() -> None:
    a, b = parsed(), parsed(0, 1)
    chosen = b.membership_id(b.days[0])
    resolution = FpiQualificationEvent(
        "date",
        "2026-09-25",
        "RESOLVE",
        T0 + timedelta(minutes=8),
        "reviewed conflict",
        "synthetic-review",
        chosen_membership_id=chosen,
        basis_membership_ids=(chosen, a.membership_id(a.days[0])),
    )
    events = (accept(a), accept(b), resolution)
    result = select_fpi(snapshot((a, b), events), policy())
    assert result.current is not None and result.current.membership_ids == (chosen,)
    assert result.current.reasons == ("EXPLICIT_RESOLUTION",)
    third = parsed(10, 2)
    stale = select_fpi(snapshot((a, b, third), (*events, accept(third))), policy())
    assert stale.status == "CONFLICT" and stale.excluded_dates[-1].reasons == ("STALE_RESOLUTION",)


@pytest.mark.parametrize("scope", ["membership", "value", "parser"])
def test_withdrawal_scopes_reinstatement_and_prior_replay(scope: str) -> None:
    old, new = parsed(), parsed(2, 1)
    saved = snapshot((old, new))
    before = select_fpi(saved, policy())
    target = {
        "membership": new.membership_id(new.days[0]),
        "value": new.days[0].value_sha256,
        "parser": P1,
    }[scope]
    predecessor = accept(new).event_id if scope == "membership" else None
    withdrawn = FpiQualificationEvent(
        scope,
        target,
        "WITHDRAW",
        T0 + timedelta(minutes=5),
        "invalid evidence",
        "synthetic-withdrawal",
        predecessor,
    )
    blocked = replace(saved, events=(*saved.events, withdrawn))
    result = select_fpi(blocked, policy())
    assert result.status == "WITHDRAWN" and result.current is None
    restored = replace(
        withdrawn,
        action="ACCEPT",
        prior_event_id=withdrawn.event_id,
        recorded_at=T0 + timedelta(minutes=6),
    )
    assert (
        select_fpi(replace(blocked, events=(*blocked.events, restored)), policy()).current
        == before.current
    )
    assert select_fpi(saved, policy()) == before


def test_membership_withdrawal_does_not_block_new_capture_of_same_value() -> None:
    first, second = parsed(), parsed(2)
    initial = accept(first)
    withdrawal = replace(
        initial,
        action="WITHDRAW",
        prior_event_id=initial.event_id,
        recorded_at=T0 + timedelta(minutes=4),
    )
    result = select_fpi(snapshot((first, second), (initial, withdrawal, accept(second))), policy())
    assert result.current is not None
    assert result.current.membership_ids == (second.membership_id(second.days[0]),)


def test_only_explicit_policy_allows_older_withdrawal_fallback() -> None:
    first, second = parsed(), parsed(2, 1)
    qualification = accept(second)
    withdrawn = replace(
        qualification,
        action="WITHDRAW",
        prior_event_id=qualification.event_id,
        recorded_at=T0 + timedelta(minutes=5),
    )
    evidence = snapshot((first, second), (accept(first), qualification, withdrawn))
    assert select_fpi(evidence, policy()).current is None
    rules = policy(allow_withdrawal_fallback=True)
    result = select_fpi(replace(evidence, policy_sha256=rules.policy_sha256), rules)
    assert result.current is not None and result.current.value_sha256 == first.days[0].value_sha256
    assert result.current.reasons == ("POLICY_WITHDRAWAL_FALLBACK",)


def test_complete_monthly_result_or_failure_never_partial() -> None:
    whole = parsed(days=tuple(range(15, 26)), source=MONTHLY)
    assert len(whole.days) == 11
    assert select_fpi(snapshot((whole,)), policy()).status == "AVAILABLE"
    with pytest.raises(ValueError, match="partial"):
        replace(whole, failure_reason="BAD_DATE")
    with pytest.raises(ValueError, match="Duplicate"):
        replace(whole, days=(*whole.days, whole.days[0]))
    broken = json.loads(whole.days[0].document_json)
    broken["total"]["net_cr"] = "0.00"
    with pytest.raises(ValueError, match="INR"):
        FpiParsedDay(json.dumps(broken), "0" * 64)
    failed = replace(whole, days=(), failure_reason="BAD_DATE")
    result = select_fpi(snapshot((failed,)), policy())
    assert result.status == "NO_OBSERVATIONS" and result.current is None
    assert failed.capture == whole.capture


def test_retry_deduplication_and_competing_transition_predecessors() -> None:
    parse = parsed()
    original = accept(parse)
    withdrawn = replace(
        original,
        action="WITHDRAW",
        prior_event_id=original.event_id,
        recorded_at=T0 + timedelta(minutes=5),
    )
    quarantine = replace(withdrawn, action="QUARANTINE")
    one = snapshot((parse,), (original, withdrawn))
    assert one == snapshot((parse, parse), (withdrawn, original, original, withdrawn))
    with pytest.raises(ValueError, match="transition conflict"):
        snapshot((parse,), (original, withdrawn, quarantine))
    with pytest.raises(ValueError, match="predecessor"):
        snapshot((parse,), (withdrawn,))
    with pytest.raises(ValueError, match="transition conflict"):
        snapshot((parse,), (original, replace(original, reason="changed retry")))


@pytest.mark.parametrize(
    "changes",
    [
        {"max_history_age_days": 30},
        {"max_current_age_days": 2},
        {"history_window": 10},
        {"minimum_history": 11},
        {"source_rule": "MONTHLY", "source_rationale": "explicit test"},
        {"parser_allowlist": (P1,)},
        {"definition_allowlist": ("other-definition",)},
        {"allow_withdrawal_fallback": True},
        {"feature_version": "fpi-v2"},
        {"model_version": "research-v2"},
        {"prediction_horizon": "20D"},
        {"selector_sha256": "b" * 64},
    ],
)
def test_whole_policy_changes_identity(changes: dict[str, Any]) -> None:
    base = policy()
    changed = policy(**changes)
    assert changed.policy_sha256 != base.policy_sha256
    evidence = snapshot((parsed(),))
    with pytest.raises(ValueError, match="different frozen policy"):
        select_fpi(evidence, changed)
    assert (
        select_fpi(replace(evidence, policy_sha256=changed.policy_sha256), changed).selection_sha256
        != select_fpi(evidence, base).selection_sha256
    )


def test_history_unique_earlier_dates_age_window_and_coverage() -> None:
    whole = parsed(days=tuple(range(1, 26)))
    repeated = parsed(2, day=24)
    rules = policy(history_window=10)
    evidence = snapshot((whole, repeated), rules=rules)
    result = select_fpi(evidence, rules)
    assert result.status == "AVAILABLE"
    assert [item.reporting_date.day for item in result.history] == list(range(15, 25))
    assert result.current is not None and result.current.reporting_date not in {
        item.reporting_date for item in result.history
    }
    assert {item.status for item in result.excluded_dates} == {"OUTSIDE_WINDOW"}
    rules = policy(max_history_age_days=3)
    result = select_fpi(replace(evidence, policy_sha256=rules.policy_sha256), rules)
    assert result.status == "INSUFFICIENT_HISTORY" and len(result.history) == 3
    assert {item.status for item in result.excluded_dates} == {"STALE"}


def test_missing_required_history_date_changes_coverage() -> None:
    complete = parsed(days=tuple(range(15, 26)))
    assert select_fpi(snapshot((complete,)), policy()).status == "AVAILABLE"
    missing = replace(complete, days=complete.days[1:])
    assert select_fpi(snapshot((missing,)), policy()).status == "INSUFFICIENT_HISTORY"


def test_ist_age_boundary_and_stale_missingness() -> None:
    capture = parsed(day=24)
    rules = policy(max_current_age_days=1)
    before = snapshot((capture,), rules=rules, at=datetime(2026, 9, 25, 18, 29, 59, tzinfo=UTC))
    after = replace(before, decision_at=datetime(2026, 9, 25, 18, 30, tzinfo=UTC))
    assert select_fpi(before, rules).current is not None
    result = select_fpi(after, rules)
    assert result.status == "STALE" and result.current is None


def test_bare_cutoff_missing_snapshot_and_deterministic_repeatability() -> None:
    rules = policy()
    assert select_fpi(None, rules).status == "VISIBILITY_UNPROVEN"
    with pytest.raises(ValueError, match="not timestamp"):
        select_fpi(T0, rules)  # type: ignore[arg-type]
    evidence = snapshot((parsed(days=(23, 24, 25)),))
    assert select_fpi(evidence, rules) == select_fpi(evidence, rules)


def test_unqualified_latest_capture_is_missing_not_older_or_zero() -> None:
    a, b = parsed(), parsed(2, 1)
    result = select_fpi(snapshot((a, b), (accept(a),)), policy())
    assert result.status == "UNQUALIFIED" and result.current is None
    assert result.excluded_dates[-1].net_hundredths_cr is None


def test_parser_allowlist_is_applied_before_selection() -> None:
    evidence = snapshot((parsed(parser=P2),))
    rules = policy(parser_allowlist=(P1,))
    result = select_fpi(replace(evidence, policy_sha256=rules.policy_sha256), rules)
    assert result.status == "POLICY_EXCLUDED" and result.current is None


def test_frozen_objects_detached_hashes_and_source_evidence_identity() -> None:
    parse = parsed()
    with pytest.raises(FrozenInstanceError):
        parse.parser_sha256 = P2  # type: ignore[misc]
    changed_day = replace(parse.days[0], source_evidence_sha256="f" * 64)
    assert changed_day.value_sha256 == parse.days[0].value_sha256
    changed = replace(parse, days=(changed_day,))
    assert changed.membership_id(changed_day) != parse.membership_id(parse.days[0])
    with pytest.raises(ValueError, match="Contradictory"):
        snapshot((parse, changed))


@pytest.mark.parametrize(
    "case",
    [
        "naive",
        "early_parse",
        "early_qualification",
        "unknown_target",
        "unknown_order",
        "mutable_days",
        "mutable_events",
        "bad_hash",
        "future_day",
        "failure_with_days",
        "negative_age",
        "bool_age",
        "invalid_window",
        "duplicate_allowlist",
        "unknown_start",
    ],
)
def test_invalid_assertions_rejected(case: str) -> None:
    parse = parsed()
    with pytest.raises(ValueError):
        if case == "naive":
            replace(parse, recorded_at=T0.replace(tzinfo=None))
        elif case == "early_parse":
            replace(parse, recorded_at=T0)
        elif case == "early_qualification":
            snapshot((parse,), (accept(parse, recorded_at=T0),))
        elif case == "unknown_target":
            snapshot((parse,), (replace(accept(parse), target="f" * 64),))
        elif case == "unknown_order":
            replace(snapshot((parse,)), ordered_capture_ids=("f" * 64,))
        elif case == "mutable_days":
            replace(parse, days=list(parse.days))  # type: ignore[arg-type]
        elif case == "mutable_events":
            replace(snapshot((parse,)), events=[])  # type: ignore[arg-type]
        elif case == "bad_hash":
            replace(parse, parser_sha256="label-v1")
        elif case == "future_day":
            parsed(day=26)
        elif case == "failure_with_days":
            replace(parse, failure_reason="BROKEN")
        elif case == "negative_age":
            policy(max_history_age_days=-1)
        elif case == "bool_age":
            policy(max_current_age_days=True)
        elif case == "invalid_window":
            policy(history_window=1)
        elif case == "duplicate_allowlist":
            policy(parser_allowlist=(P1, P1))
        else:
            build_fpi_capture(
                body=b"unknown start",
                source_url=LATEST,
                requested_at=None,  # type: ignore[arg-type]
                retrieved_at=T0,
                http_status=200,
            )


@pytest.mark.parametrize("state", ["unqualified", "later_accept", "withdrawn", "scope_block"])
def test_resolution_cannot_activate_from_later_qualification(state: str) -> None:
    parse = parsed()
    accepted = accept(parse)
    chosen = accepted.target
    resolution = FpiQualificationEvent(
        "date",
        "2026-09-25",
        "RESOLVE",
        T0 + timedelta(minutes=5),
        "review",
        "evidence",
        chosen_membership_id=chosen,
        basis_membership_ids=(chosen,),
    )
    events: tuple[FpiQualificationEvent, ...]
    if state == "unqualified":
        events = (resolution,)
    elif state == "later_accept":
        events = (replace(accepted, recorded_at=T0 + timedelta(minutes=6)), resolution)
    elif state == "withdrawn":
        withdrawal = replace(
            accepted,
            action="WITHDRAW",
            prior_event_id=accepted.event_id,
            recorded_at=T0 + timedelta(minutes=3),
        )
        reinstatement = replace(
            accepted, prior_event_id=withdrawal.event_id, recorded_at=T0 + timedelta(minutes=6)
        )
        events = (accepted, withdrawal, resolution, reinstatement)
    else:
        block = FpiQualificationEvent(
            "parser", P1, "WITHDRAW", T0 + timedelta(minutes=3), "block", "evidence"
        )
        events = (accepted, block, resolution)
    with pytest.raises(ValueError, match="not qualified at resolution"):
        snapshot((parse,), events)


@pytest.mark.parametrize("status", [201, 204, 206, 301, 404, 500])
def test_only_complete_http_200_can_have_successful_parse(status: int) -> None:
    original = parsed()
    capture = build_fpi_capture(
        body=b"synthetic",
        source_url=LATEST,
        requested_at=T0,
        retrieved_at=T0 + timedelta(minutes=1),
        http_status=status,
    )
    with pytest.raises(ValueError, match="HTTP 200"):
        replace(original, capture=capture)
    failure = replace(original, capture=capture, days=(), failure_reason="HTTP_RESPONSE")
    assert failure.capture == capture


def test_definition_cannot_relabel_retained_canonical_value() -> None:
    with pytest.raises(ValueError, match="definition"):
        replace(parsed(), definition_version="relabelled-v2")


def test_selection_fingerprint_commits_to_complete_returned_content() -> None:
    result = select_fpi(snapshot((parsed(days=tuple(range(1, 26))),)), policy())
    content = asdict(result)
    expected = content.pop("selection_sha256")
    encoded = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=lambda day: day.isoformat(),
    )
    assert hashlib.sha256(encoded.encode("ascii")).hexdigest() == expected
    for key in ("current", "history", "excluded_dates", "parse_diagnostics"):
        tampered = dict(content)
        tampered[key] = "changed"
        changed = json.dumps(
            tampered,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=lambda day: day.isoformat(),
        )
        assert hashlib.sha256(changed.encode("ascii")).hexdigest() != expected


@pytest.mark.parametrize("kind", ["parses", "events", "order", "allowlist", "basis", "days"])
def test_record_counts_are_bounded_before_large_work(kind: str) -> None:
    parse = parsed()
    event = accept(parse)
    with pytest.raises(ValueError):
        if kind == "parses":
            snapshot((parse,) * 2049)
        elif kind == "events":
            snapshot((parse,), (event,) * 20001)
        elif kind == "order":
            replace(snapshot((parse,)), ordered_capture_ids=(parse.capture.capture_sha256,) * 2049)
        elif kind == "allowlist":
            policy(parser_allowlist=tuple(f"{i:064x}" for i in range(65)))
        elif kind == "basis":
            replace(event, basis_membership_ids=(event.target,) * 4097)
        else:
            replace(parse, days=(parse.days[0],) * 32)


def test_long_qualification_chain_replays_without_recursion_or_quadratic_walk() -> None:
    parse = parsed()
    events = [accept(parse)]
    for index in range(1, 1001):
        events.append(
            replace(
                events[-1],
                prior_event_id=events[-1].event_id,
                action="ACCEPT" if index % 2 == 0 else "WITHDRAW",
                reason=f"synthetic transition {index}",
            )
        )
    evidence = snapshot((parse,), tuple(reversed(events)))
    assert select_fpi(evidence, policy()).current is not None


def test_measured_zero_requires_complete_reconciled_zero_document() -> None:
    fixture = _fpi_fixture(25)
    for category in fixture["categories"].values():
        for route in category["routes"].values():
            route["purchases_cr"] = route["sales_cr"]
            route["net_cr"] = "0"
        category["subtotal"]["purchases_cr"] = category["subtotal"]["sales_cr"]
        category["subtotal"]["net_cr"] = "0"
    fixture["total"]["purchases_cr"] = fixture["total"]["sales_cr"]
    fixture["total"]["net_cr"] = "0"
    value = build_fpi_observation(**fixture)
    parse = replace(parsed(), days=(FpiParsedDay(value.document_json, "a" * 64),))
    result = select_fpi(snapshot((parse,)), policy())
    assert result.current is not None and result.current.net_hundredths_cr == 0
    assert select_fpi(snapshot((parse,), ()), policy()).current is None


def test_same_total_different_components_still_conflict() -> None:
    baseline = parsed()
    document = build_fpi_observation(**_fpi_fixture(25, shift=1, offset=True)).document_json
    altered = replace(parsed(0, 1), days=(FpiParsedDay(document, "b" * 64),))
    assert altered.days[0].net_hundredths_cr == baseline.days[0].net_hundredths_cr
    assert altered.days[0].value_sha256 != baseline.days[0].value_sha256
    assert select_fpi(snapshot((baseline, altered)), policy()).status == "CONFLICT"


def test_new_download_of_old_reporting_date_does_not_replace_newest_date() -> None:
    recent, late_old = parsed(day=25), parsed(5, 2, day=24)
    result = select_fpi(snapshot((recent, late_old)), policy())
    assert result.current is not None and result.current.reporting_date.day == 25
    assert result.history[0].reporting_date.day == 24


def test_qualification_fork_from_same_predecessor_never_picks_by_hash() -> None:
    parse = parsed()
    original = accept(parse)
    withdraw = replace(original, action="WITHDRAW", prior_event_id=original.event_id)
    accept_again = replace(original, reason="accept again", prior_event_id=original.event_id)
    for order in permutations((original, withdraw, accept_again)):
        with pytest.raises(ValueError, match="transition conflict"):
            snapshot((parse,), order)


def test_parser_scope_withdrawal_blocks_all_capture_occurrences() -> None:
    first, second = parsed(), parsed(2)
    withdrawal = FpiQualificationEvent(
        "parser", P1, "WITHDRAW", T0 + timedelta(minutes=5), "parser defect", "evidence"
    )
    result = select_fpi(
        snapshot((first, second), (accept(first), accept(second), withdrawal)), policy()
    )
    assert result.current is None and result.status == "WITHDRAWN"


def test_value_scope_withdrawal_blocks_same_value_across_parsers() -> None:
    first, second = parsed(), parsed(2, parser=P2)
    withdrawal = FpiQualificationEvent(
        "value",
        first.days[0].value_sha256,
        "WITHDRAW",
        T0 + timedelta(minutes=5),
        "invalid value",
        "evidence",
    )
    result = select_fpi(
        snapshot((first, second), (accept(first), accept(second), withdrawal)), policy()
    )
    assert result.current is None and result.status == "WITHDRAWN"


def test_withdrawn_resolution_target_stays_unavailable_without_older_fallback() -> None:
    first, second = parsed(), parsed(0, 1)
    chosen = second.membership_id(second.days[0])
    resolution = FpiQualificationEvent(
        "date",
        "2026-09-25",
        "RESOLVE",
        T0 + timedelta(minutes=5),
        "review",
        "evidence",
        chosen_membership_id=chosen,
        basis_membership_ids=(first.membership_id(first.days[0]), chosen),
    )
    withdrawal = replace(
        accept(second),
        action="WITHDRAW",
        prior_event_id=accept(second).event_id,
        recorded_at=T0 + timedelta(minutes=6),
    )
    result = select_fpi(
        snapshot((first, second), (accept(first), accept(second), resolution, withdrawal)), policy()
    )
    assert result.current is None and result.status == "WITHDRAWN"


@pytest.mark.parametrize("change", [{"minimum_history": 9}, {"max_history_age_days": 2}])
def test_original_research_history_floor_cannot_be_weakened(change: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        policy(**change)


def test_capture_body_decoded_once_per_selection_not_per_reporting_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parses = tuple(parsed(minute * 2, minute, days=tuple(range(1, 26))) for minute in range(20))
    # Keep decision later than all request/qualification intervals.
    evidence = snapshot(parses)
    captured_documents = {parse.capture.document_json for parse in parses}
    original_loads = json.loads
    counts = dict.fromkeys(captured_documents, 0)

    def counted_loads(document: str, *args: Any, **kwargs: Any) -> Any:
        if document in counts:
            counts[document] += 1
        return original_loads(document, *args, **kwargs)

    monkeypatch.setattr(json, "loads", counted_loads)
    result = select_fpi(evidence, policy())
    assert result.status == "AVAILABLE" and result.current is not None
    assert result.current.value_sha256 == parses[-1].days[-1].value_sha256
    assert set(counts.values()) == {1}
