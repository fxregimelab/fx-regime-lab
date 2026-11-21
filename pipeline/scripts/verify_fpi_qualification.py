"""Independent sequential oracle for compact qualification state; no I/O evidence claim."""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.research import fpi_qualification as q  # noqa: E402


def _reference_hash(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _reference_state(
    member: q.FpiQualificationMember, actions: dict[tuple[str, str], str]
) -> str:
    """This oracle uses sequentially applied actions, never the compact event graph."""
    observed = (
        actions.get(("membership", member.membership_id)),
        actions.get(("value", member.value_sha256)),
        actions.get(("parser", member.parser_sha256)),
    )
    if "QUARANTINE" in observed:
        return "QUARANTINED"
    if "WITHDRAW" in observed:
        return "WITHDRAWN"
    return "ACCEPTED" if observed[0] == "ACCEPT" else "UNQUALIFIED"


def _reference_run(seed: int) -> tuple[int, int]:
    rng = random.Random(seed)
    members = tuple(
        q.FpiQualificationMember(
            _reference_hash(f"member-{index}"),
            _reference_hash(f"value-{index // 2}-{index % 2}"),
            _reference_hash(f"parser-{index % 2}"),
            date(2026, 9, 20 + index // 2),
        )
        for index in range(6)
    )
    required = {
        key
        for member in members
        for key in (
            ("membership", member.membership_id),
            ("value", member.value_sha256),
            ("parser", member.parser_sha256),
            ("date", member.reporting_date.isoformat()),
        )
    }
    heads: dict[tuple[str, str], str | None] = dict.fromkeys(required)
    events: dict[str, q.FpiQualificationEventV2] = {}
    actions: dict[tuple[str, str], str] = {}
    resolutions: dict[date, tuple[str, tuple[str, ...]]] = {}
    ordinal = 0
    compared = 0
    resolution_checks = 0

    def append(scope: str, target: str, action: str, chosen: str | None = None) -> None:
        nonlocal ordinal
        ordinal += 1
        basis: tuple[str, ...] = ()
        witness = None
        if scope == "date":
            basis = tuple(
                sorted(m.membership_id for m in members if m.reporting_date.isoformat() == target)
            )
            selected = next(m for m in members if m.membership_id == chosen)
            witness = q.FpiResolutionWitness(
                tuple(
                    q.FpiQualificationHead(kind, identity, heads[(kind, identity)])
                    for kind, identity in (
                        ("membership", selected.membership_id),
                        ("value", selected.value_sha256),
                        ("parser", selected.parser_sha256),
                    )
                )
            )
            assert chosen is not None
            resolutions[selected.reporting_date] = (chosen, basis)
        command = q.FpiQualificationCommand(
            scope,
            target,
            action,
            "REFERENCE_PROBE",
            _reference_hash("authored synthetic evidence only"),
            heads[(scope, target)],
            chosen,
            basis,
        )
        # Equal and decreasing clocks deliberately disagree with causal order.
        event = q.FpiQualificationEventV2(
            command,
            ordinal,
            datetime(2026, 9, 27, 12, tzinfo=UTC) - timedelta(seconds=ordinal // 3),
            witness,
        )
        events[event.event_id] = event
        heads[(scope, target)] = event.event_id
        if scope != "date":
            actions[(scope, target)] = action

    def compare() -> None:
        nonlocal compared, resolution_checks
        retained = {identity for identity in heads.values() if identity is not None}
        for identity in tuple(retained):
            event = events[identity]
            if event.witness is not None:
                retained.update(
                    head.event_id for head in event.witness.heads if head.event_id is not None
                )
        compact_members = list(members)
        compact_heads = [q.FpiQualificationHead(*key, value) for key, value in heads.items()]
        compact_events = [events[identity] for identity in retained]
        view = q.FpiQualificationView(
            tuple(compact_members), tuple(compact_heads), tuple(compact_events)
        )
        evaluation = q.evaluate_fpi_qualification(view)
        assert evaluation.view_sha256 == view.view_sha256
        result_document = json.dumps(
            {
                "version": "fpi-qualification-evaluation-v2",
                "view_sha256": view.view_sha256,
                "member_states": evaluation.member_states,
                "date_resolutions": [
                    (day.isoformat(), status, chosen)
                    for day, status, chosen in evaluation.date_resolutions
                ],
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        assert evaluation.result_sha256 == _reference_hash(result_document)
        member_results = dict(evaluation.member_states)
        date_results = {
            day: (status, chosen) for day, status, chosen in evaluation.date_resolutions
        }
        assert set(member_results) == {member.membership_id for member in members}
        assert set(date_results) == {member.reporting_date for member in members}
        for member in members:
            expected = _reference_state(member, actions)
            assert member_results[member.membership_id] == expected, (
                "sequential qualification mismatch",
                seed,
                ordinal,
                expected,
            )
            if seed == 0 and member == members[0]:
                assert q.member_qualification(view, member.membership_id) == expected, (
                    "sequential scalar qualification mismatch",
                    ordinal,
                )
            compared += 1
        for reporting_date in sorted({m.reporting_date for m in members}):
            expected_resolution: tuple[str, str | None] = ("NO_RESOLUTION", None)
            if reporting_date in resolutions:
                chosen, saved_basis = resolutions[reporting_date]
                current_basis = tuple(
                    sorted(m.membership_id for m in members if m.reporting_date == reporting_date)
                )
                selected = next(m for m in members if m.membership_id == chosen)
                if saved_basis != current_basis:
                    expected_resolution = ("STALE_RESOLUTION", None)
                elif _reference_state(selected, actions) != "ACCEPTED":
                    expected_resolution = ("TARGET_UNQUALIFIED", None)
                else:
                    expected_resolution = ("RESOLVED", chosen)
            assert date_results[reporting_date] == expected_resolution, (
                "sequential resolution mismatch",
                seed,
                ordinal,
                expected_resolution,
            )
            if seed == 0 and reporting_date == members[0].reporting_date:
                assert q.date_resolution(view, reporting_date) == expected_resolution, (
                    "sequential scalar resolution mismatch",
                    ordinal,
                )
            resolution_checks += 1
        rng.shuffle(compact_members)
        rng.shuffle(compact_heads)
        rng.shuffle(compact_events)
        permuted = q.FpiQualificationView(
            tuple(compact_members), tuple(compact_heads), tuple(compact_events)
        )
        assert permuted.view_sha256 == view.view_sha256, "Input order changed view identity"

    compare()
    # Guaranteed historical resolution followed by withdrawal and reinstatement.
    for member in members:
        append("membership", member.membership_id, "ACCEPT")
    append("date", members[0].reporting_date.isoformat(), "RESOLVE", members[0].membership_id)
    compare()
    append("membership", members[0].membership_id, "WITHDRAW")
    compare()
    append("membership", members[0].membership_id, "ACCEPT")
    compare()
    for _ in range(32):
        member = rng.choice(members)
        if rng.randrange(4) == 0 and _reference_state(member, actions) == "ACCEPTED":
            append("date", member.reporting_date.isoformat(), "RESOLVE", member.membership_id)
        else:
            scope, target = rng.choice(
                (
                    ("membership", member.membership_id),
                    ("value", member.value_sha256),
                    ("parser", member.parser_sha256),
                )
            )
            append(scope, target, rng.choice(("ACCEPT", "WITHDRAW", "QUARANTINE")))
        compare()
    # A newly retained candidate makes a prior same-date resolution stale.
    extra = q.FpiQualificationMember(
        _reference_hash("late member"),
        _reference_hash("late value"),
        members[0].parser_sha256,
        members[0].reporting_date,
    )
    members += (extra,)
    heads[("membership", extra.membership_id)] = None
    heads[("value", extra.value_sha256)] = None
    compare()
    return compared, resolution_checks


def verify_fpi_qualification_reference() -> None:
    totals = [_reference_run(seed) for seed in range(40)]
    for name, value in (
        ("member_qualification", "ACCEPTED"),
        ("date_resolution", ("NO_RESOLUTION", None)),
    ):
        detected = False
        with patch.object(q, name, return_value=value):
            try:
                _reference_run(0)
            except AssertionError as exc:
                assert str(exc).startswith("('sequential "), "Unexpected negative-control failure"
                detected = True
        assert detected, f"Broken {name} escaped the independent oracle"
    correct_batch = q.evaluate_fpi_qualification

    def wrong_batch(view: q.FpiQualificationView) -> q.FpiQualificationEvaluation:
        result = correct_batch(view)
        return replace(
            result,
            member_states=tuple((identity, "ACCEPTED") for identity, _ in result.member_states),
        )

    with patch.object(q, "evaluate_fpi_qualification", side_effect=wrong_batch):
        try:
            _reference_run(0)
        except AssertionError as exc:
            assert str(exc).startswith("('sequential qualification mismatch'")
        else:
            raise AssertionError("Broken bulk evaluator escaped the independent oracle")
    print(
        "Independent comparisons:",
        sum(item[0] for item in totals),
        "membership states;",
        sum(item[1] for item in totals),
        "date resolutions; 40 seeds; three wrong-evaluator controls detected",
    )
    print("FPI_QUALIFICATION_REFERENCE_VERIFIED")


if __name__ == "__main__":
    verify_fpi_qualification_reference()
