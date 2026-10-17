"""AD-T06 spec bundle loader and evidence-only acknowledgment.

The suite pins the runtime spec-gate contract from spec 01 section 8 and the
runtime prompt roles in spec 06 sections 4-7: exact rule-document bytes are
digested, mandatory clause headings are extracted deterministically, role
excerpts are bounded, and an acknowledgment can only ever be evidence that a
model saw a bundle digest and clause set. No acknowledgment key, value,
duplicate, waiver, permission or unknown clause can widen authority.

Behavior tests build small fixture documents under ``tmp_path`` with the real
heading text; one content-pinning test loads the actual rule bundle.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from src.paper.contracts import ContractError
from src.paper.spec_bundle import (
    BUNDLE_SOURCES,
    MANDATORY_CLAUSES,
    MAX_BUNDLE_BYTES,
    MAX_EXCERPT_BYTES,
    RESEARCH_ANALYST,
    RESEARCH_VERIFIER,
    RUNTIME_ROLES,
    STRATEGY_SCIENTIST,
    ClauseAnchor,
    SpecBundle,
    load_spec_bundle,
    required_excerpts_for,
    validate_acknowledgment,
)

TS = "2026-10-18T12:00:00Z"

# Exact visible heading text from the two rule documents. Extraction is
# anchored on these strings; the real-bundle test below detects rule-doc drift.
BANNED = "5. Explicitly banned (no exceptions)"
SPEC_GATE = "6. The spec-gate (read-before-trade)"
ADAPTATION = "7. Adaptation rules (how the desk learns)"
OPERATOR_SCORE = "8. Operator score (penalty/reward for the executing AI)"
HONESTY = "9. Honesty clause"
STANDING = "0. Standing rules (never violated)"
HARD_GATES = "Hard gates (all 5 must pass or the candidate is skipped — grade C)"
MANAGEMENT = "3. Trade management policy (exact mechanics)"
RESEARCH = "6. News & research protocol (research packet)"
MEASUREMENT = "8. Measurement & model-improvement loop"

_BODIES: Mapping[str, str] = {
    BANNED: "FIXTURE-BANNED",
    SPEC_GATE: "FIXTURE-SPEC-GATE",
    ADAPTATION: "FIXTURE-ADAPTATION",
    OPERATOR_SCORE: "FIXTURE-OPERATOR-SCORE",
    HONESTY: "FIXTURE-HONESTY",
    STANDING: "FIXTURE-STANDING",
    HARD_GATES: "FIXTURE-HARD-GATES",
    MANAGEMENT: "FIXTURE-MANAGEMENT",
    RESEARCH: "FIXTURE-RESEARCH",
    MEASUREMENT: "FIXTURE-MEASUREMENT",
}

# The hard gates are a real subsection of this parent in the playbook; the
# fixture reproduces that nesting so ``## 0`` extraction cannot swallow it.
_CONFIDENCE_PARENT = "2. Confidence engine — 14 binary checks"
# Inserted after the hard-gate subsection so extraction can be proven to stop
# at the next same-or-higher heading instead of swallowing the whole document.
_SCORED_HEADING = "### Scored checks (1 point each, Y/N with evidence line)"
_SCORED_MARKER = "FIXTURE-SCORED-MUST-NOT-BE-EXTRACTED"


def _anchors_for(relpath: str) -> tuple[ClauseAnchor, ...]:
    ordered: list[ClauseAnchor] = []
    for role in RUNTIME_ROLES:
        for anchor in MANDATORY_CLAUSES[role]:
            if anchor.relpath == relpath and anchor not in ordered:
                ordered.append(anchor)
    return tuple(ordered)


def _render(
    anchors: Sequence[ClauseAnchor],
    *,
    omit: Sequence[str] = (),
    bodies: Mapping[str, str] | None = None,
) -> str:
    body_map = dict(_BODIES)
    if bodies is not None:
        body_map.update(bodies)
    lines = ["# Fixture rule document", ""]
    for anchor in anchors:
        if anchor.heading in omit:
            continue
        if anchor.heading == HARD_GATES:
            lines.extend([f"## {_CONFIDENCE_PARENT}", ""])
        level = 3 if anchor.heading == HARD_GATES else 2
        lines.extend([f"{'#' * level} {anchor.heading}", body_map[anchor.heading], ""])
        if anchor.heading == HARD_GATES:
            lines.extend([_SCORED_HEADING, _SCORED_MARKER, ""])
    return "\n".join(lines)


def _framework(
    *, omit: Sequence[str] = (), bodies: Mapping[str, str] | None = None
) -> str:
    return _render(_anchors_for(BUNDLE_SOURCES[0]), omit=omit, bodies=bodies)


def _playbook(
    *, omit: Sequence[str] = (), bodies: Mapping[str, str] | None = None
) -> str:
    return _render(_anchors_for(BUNDLE_SOURCES[1]), omit=omit, bodies=bodies)


def _write_fixture(
    root: Path,
    *,
    framework: str | None = None,
    playbook: str | None = None,
) -> Path:
    documents = (
        (BUNDLE_SOURCES[0], _framework() if framework is None else framework),
        (BUNDLE_SOURCES[1], _playbook() if playbook is None else playbook),
    )
    for relpath, text in documents:
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    return root


def _ack(
    bundle: SpecBundle,
    role: str,
    *,
    clauses: Sequence[str] | None = None,
    acknowledged_at: object = TS,
    **extra: object,
) -> dict[str, object]:
    if clauses is None:
        clauses = [anchor.clause_id for anchor in MANDATORY_CLAUSES[role]]
    payload: dict[str, object] = {
        "bundle_digest": bundle.bundle_digest,
        "role": role,
        "acknowledged_at": acknowledged_at,
        "clauses": list(clauses),
    }
    payload.update(extra)
    return payload


def _error(call: Callable[[], object]) -> ContractError:
    with pytest.raises(ContractError) as excinfo:
        call()
    return excinfo.value


# ``validate_acknowledgment`` is annotated ``-> None``; view it as returning an
# object only to prove at runtime that the result really is ``None``.
_validate_as_object = cast(
    Callable[[SpecBundle, Mapping[str, object]], object], validate_acknowledgment
)


def test_changed_markdown_invalidates_acknowledgment(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    acknowledgment = _ack(bundle, RESEARCH_ANALYST)
    assert _validate_as_object(bundle, acknowledgment) is None

    target = root / BUNDLE_SOURCES[1]
    target.write_bytes(target.read_bytes() + b"\nrevised rule text\n")
    reloaded = load_spec_bundle(root)

    assert reloaded.bundle_digest != bundle.bundle_digest
    error = _error(lambda: validate_acknowledgment(reloaded, acknowledgment))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    # The old bundle no longer describes the bytes on disk either.
    stale = _error(lambda: required_excerpts_for(bundle, RESEARCH_ANALYST, root))
    assert stale.code == "SPEC_UNACKNOWLEDGED"


def test_missing_required_clause_raises(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path, playbook=_playbook(omit=(RESEARCH,)))
    bundle = load_spec_bundle(root)

    error = _error(lambda: required_excerpts_for(bundle, RESEARCH_ANALYST, root))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    assert RESEARCH in error.detail
    # Clause requirements are role-specific: the scientist does not need it.
    packet = required_excerpts_for(bundle, STRATEGY_SCIENTIST, root)
    assert RESEARCH not in packet.text


def test_mismatched_bundle_acknowledgment_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    acknowledgment = _ack(bundle, RESEARCH_ANALYST)
    acknowledgment["bundle_digest"] = "0" * 64

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "SPEC_UNACKNOWLEDGED"


def test_oversized_bundle_rejected(tmp_path: Path) -> None:
    oversized = "# Fixture\n\n" + ("x" * (MAX_BUNDLE_BYTES + 1)) + "\n"
    root = _write_fixture(tmp_path, framework=oversized)

    error = _error(lambda: load_spec_bundle(root))
    assert error.code == "INVALID_SCHEMA"
    assert str(MAX_BUNDLE_BYTES) in error.detail


@pytest.mark.parametrize("marker", ["{{", "TBD:"])
def test_unresolved_marker_rejected(tmp_path: Path, marker: str) -> None:
    root = _write_fixture(
        tmp_path, framework=_framework() + f"\nunresolved {marker} placeholder\n"
    )

    error = _error(lambda: load_spec_bundle(root))
    assert error.code == "INVALID_SCHEMA"
    assert marker in error.detail


@pytest.mark.parametrize("key", ["waive", "waiver", "permission", "unlock"])
def test_model_acknowledgment_cannot_waive_rule(tmp_path: Path, key: str) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    acknowledgment = _ack(bundle, RESEARCH_ANALYST)
    acknowledgment[key] = ["playbook.standing_rules"] if key.startswith("waiv") else True

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "INVALID_SCHEMA"
    assert key in error.detail


def test_ack_missing_clause_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    required = [anchor.clause_id for anchor in MANDATORY_CLAUSES[RESEARCH_ANALYST]]
    acknowledgment = _ack(bundle, RESEARCH_ANALYST, clauses=required[:-1])

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    assert required[-1] in error.detail


def test_ack_wrong_role_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    acknowledgment = _ack(bundle, "executor", clauses=())

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    assert "executor" in error.detail


def test_ack_cross_role_clauses_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    scientist_ids = [anchor.clause_id for anchor in MANDATORY_CLAUSES[STRATEGY_SCIENTIST]]
    acknowledgment = _ack(bundle, RESEARCH_ANALYST, clauses=scientist_ids)

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    assert "missing" in error.detail


def test_acknowledgment_is_evidence_only(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    acknowledgment = _ack(bundle, RESEARCH_VERIFIER)
    before = dict(acknowledgment)

    assert _validate_as_object(bundle, acknowledgment) is None
    assert _validate_as_object(bundle, acknowledgment) is None
    assert acknowledgment == before
    assert load_spec_bundle(root) == bundle
    # No authority-shaped result is exposed: the function only returns None.
    assert _validate_as_object(bundle, acknowledgment) is None


@pytest.mark.parametrize("role", RUNTIME_ROLES)
def test_excerpt_contains_every_mandatory_clause(tmp_path: Path, role: str) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    packet = required_excerpts_for(bundle, role, root)
    required = tuple(anchor.clause_id for anchor in MANDATORY_CLAUSES[role])

    assert packet.role == role
    assert packet.bundle_digest == bundle.bundle_digest
    assert packet.clauses == required
    for anchor in MANDATORY_CLAUSES[role]:
        assert anchor.clause_id in packet.text
        assert _BODIES[anchor.heading] in packet.text
    assert packet.total_bytes == len(packet.text.encode("utf-8"))
    assert packet.total_bytes <= MAX_EXCERPT_BYTES


def test_excerpt_stops_at_next_same_or_higher_heading(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    packet = required_excerpts_for(bundle, RESEARCH_ANALYST, root)

    assert _BODIES[HARD_GATES] in packet.text
    assert _SCORED_MARKER not in packet.text
    assert _BODIES[MANAGEMENT] not in packet.text


def test_oversized_excerpt_rejected(tmp_path: Path) -> None:
    root = _write_fixture(
        tmp_path,
        framework=_framework(bodies={HONESTY: "X" * (MAX_EXCERPT_BYTES + 1)}),
    )
    bundle = load_spec_bundle(root)

    error = _error(lambda: required_excerpts_for(bundle, RESEARCH_ANALYST, root))
    assert error.code == "INVALID_SCHEMA"
    assert str(MAX_EXCERPT_BYTES) in error.detail


def test_deterministic_loads(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    first = load_spec_bundle(root)
    second = load_spec_bundle(root)

    assert first == second
    assert first.bundle_digest == second.bundle_digest
    assert len(first.bundle_digest) == 64
    assert tuple(file.relpath for file in first.files) == BUNDLE_SOURCES
    assert first.total_bytes == sum(file.size for file in first.files)


def test_bundle_dataclasses_are_frozen(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    packet = required_excerpts_for(bundle, RESEARCH_ANALYST, root)

    with pytest.raises(FrozenInstanceError):
        setattr(bundle, "total_bytes", 1)
    with pytest.raises(FrozenInstanceError):
        setattr(bundle.files[0], "size", 1)
    with pytest.raises(FrozenInstanceError):
        setattr(packet, "role", "executor")


def test_ack_non_mapping_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    payload = cast(Mapping[str, object], ["not", "a", "mapping"])

    error = _error(lambda: validate_acknowledgment(bundle, payload))
    assert error.code == "INVALID_SCHEMA"


@pytest.mark.parametrize(
    "timestamp",
    ["2026-10-18T12:00:00", "2026-10-18T12:00:00+00:00", "2026-10-18 12:00:00Z"],
)
def test_ack_naive_or_non_z_timestamp_rejected(
    tmp_path: Path, timestamp: str
) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    acknowledgment = _ack(bundle, RESEARCH_ANALYST, acknowledged_at=timestamp)

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "INVALID_SCHEMA"


def test_ack_duplicate_clause_ids_cover_exact_set(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    required = [anchor.clause_id for anchor in MANDATORY_CLAUSES[RESEARCH_ANALYST]]

    duplicated = [*required, required[0]]
    assert _validate_as_object(
        bundle, _ack(bundle, RESEARCH_ANALYST, clauses=duplicated)
    ) is None

    missing = [*required[:-1], required[0]]
    error = _error(
        lambda: validate_acknowledgment(
            bundle, _ack(bundle, RESEARCH_ANALYST, clauses=missing)
        )
    )
    assert error.code == "SPEC_UNACKNOWLEDGED"


def test_ack_extra_clause_id_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)
    required = [anchor.clause_id for anchor in MANDATORY_CLAUSES[RESEARCH_ANALYST]]
    acknowledgment = _ack(
        bundle, RESEARCH_ANALYST, clauses=[*required, "framework.invented"]
    )

    error = _error(lambda: validate_acknowledgment(bundle, acknowledgment))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    assert "unexpected" in error.detail


def test_ack_missing_key_and_wrong_types_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)

    missing = _ack(bundle, RESEARCH_ANALYST)
    del missing["clauses"]
    assert _error(lambda: validate_acknowledgment(bundle, missing)).code == "INVALID_SCHEMA"

    wrong = _ack(bundle, RESEARCH_ANALYST)
    wrong["bundle_digest"] = 123
    assert _error(lambda: validate_acknowledgment(bundle, wrong)).code == "INVALID_SCHEMA"

    unknown = _ack(bundle, RESEARCH_ANALYST, notes="extra")
    assert _error(lambda: validate_acknowledgment(bundle, unknown)).code == "INVALID_SCHEMA"


def test_missing_source_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    (root / BUNDLE_SOURCES[0]).unlink()

    error = _error(lambda: load_spec_bundle(root))
    assert error.code == "SPEC_UNACKNOWLEDGED"
    assert BUNDLE_SOURCES[0] in error.detail


def test_unknown_role_excerpt_rejected(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)
    bundle = load_spec_bundle(root)

    error = _error(lambda: required_excerpts_for(bundle, "executor", root))
    assert error.code == "INVALID_SCHEMA"
    assert "executor" in error.detail


# Content pinning: update DELIBERATELY when either rule document changes.
# The digest covers the ordered (relpath, sha256) pairs, not the file mtimes.
REAL_BUNDLE_DIGEST = "b0803715b04f0d7ac10094b227e7e580062bb92b4dec3c3d5551dab08c3b2014"


def test_real_bundle_digest_pinned() -> None:
    bundle = load_spec_bundle()
    assert bundle.bundle_digest == REAL_BUNDLE_DIGEST
    assert tuple(file.relpath for file in bundle.files) == BUNDLE_SOURCES
    assert bundle.total_bytes == sum(file.size for file in bundle.files)

    for role in RUNTIME_ROLES:
        packet = required_excerpts_for(bundle, role)
        required = tuple(anchor.clause_id for anchor in MANDATORY_CLAUSES[role])
        assert packet.clauses == required
        for clause_id in required:
            assert clause_id in packet.text
        assert packet.total_bytes == len(packet.text.encode("utf-8"))
        assert packet.total_bytes <= MAX_EXCERPT_BYTES
