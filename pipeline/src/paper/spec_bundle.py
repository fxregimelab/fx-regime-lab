"""AD-T06 runtime spec bundle: exact bytes, mandatory clauses, evidence-only ack.

The runtime prompt contracts in spec 06 define four model roles, named here by
their prompt labels:

- ``research_analyst`` — "unprivileged private DEMO research analyst" (§4);
- ``research_verifier`` — "research verifier, not trade approver" (§5);
- ``strategy_scientist`` — "bounded strategy scientist" (§6);
- ``postmortem_writer`` — "evidence-based postmortem writer" (§7).

Each role receives a bounded excerpt of the two rule documents
(``BUNDLE_SOURCES``) anchored on real headings. The clause selection carries the
mandatory runtime-context concepts of spec 06 §1: demo-only operation, the
fixed execution universe, "model cannot trade or change policy", unknown→wait
(hard gates), "facts must cite snapshot fields" (research packet), and the
target is reporting-only (honesty clause). Deterministic gates enforce these
rules; this module only reproduces their text.

``validate_acknowledgment`` is STRICTLY EVIDENCE ONLY. It checks that a model
returned the loaded bundle digest, its own runtime role, a strict UTC
timestamp and the exact mandatory clause-id set. It never grants permission,
never waives a rule, never unlocks execution and has no side effects. No API in
this module returns authority; runtime gates must consult protected policy and
broker state independently of any acknowledgment.

Fail-closed codes: ``SPEC_UNACKNOWLEDGED`` for a missing/unreadable or changed
source, a missing mandatory heading, a mismatched digest/role/clause set;
``INVALID_SCHEMA`` for oversized content, unresolved placeholders, malformed
acknowledgment payloads and unknown roles. Loading is pure filesystem read:
no DB, broker, network, AI or production client is touched.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType

from src.paper.contracts import ContractError

# Rule documents relative to the repository root; order is part of the digest.
BUNDLE_SOURCES: tuple[str, ...] = (
    "docs/DESK_STRATEGY_FRAMEWORK.md",
    "docs/DESK_TRADING_PLAYBOOK.md",
)

DEFAULT_ROOT = Path(__file__).resolve().parents[3]

MAX_BUNDLE_BYTES = 512 * 1024
MAX_EXCERPT_BYTES = 24 * 1024

# Shipped rule text must not contain unrendered template or authoring markers.
# ``{{`` is deliberately broad: any doubled brace in prose is a template leak.
UNRESOLVED_MARKERS: tuple[str, ...] = ("{{", "TBD:", "TODO:", "FIXME:")

RESEARCH_ANALYST = "research_analyst"
RESEARCH_VERIFIER = "research_verifier"
STRATEGY_SCIENTIST = "strategy_scientist"
POSTMORTEM_WRITER = "postmortem_writer"

_FRAMEWORK = BUNDLE_SOURCES[0]
_PLAYBOOK = BUNDLE_SOURCES[1]
_ZERO_OFFSET = timedelta(0)
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]*(?:```|~~~)")
_EXPECTED_ACK_KEYS = frozenset({"bundle_digest", "role", "acknowledged_at", "clauses"})
_FORBIDDEN_ACK_FRAGMENTS = ("waiv", "permission", "unlock", "grant", "authorit")


@dataclass(frozen=True)
class ClauseAnchor:
    """One mandatory clause: stable id plus the exact heading that carries it."""

    clause_id: str
    relpath: str
    heading: str


@dataclass(frozen=True)
class SpecFile:
    """One digested rule document."""

    relpath: str
    digest: str
    size: int


@dataclass(frozen=True)
class SpecBundle:
    """Exact rule-document bundle; the digest covers ordered path/hash pairs."""

    bundle_digest: str
    files: tuple[SpecFile, ...]
    total_bytes: int


@dataclass(frozen=True)
class ExcerptPacket:
    """Bounded per-role excerpt; clause ids are embedded in ``text``."""

    role: str
    bundle_digest: str
    clauses: tuple[str, ...]
    text: str
    total_bytes: int


# Clause selection per runtime role. Headings are the real visible heading text
# (without leading '#'); the real-bundle test detects rule-document drift.
MANDATORY_CLAUSES: Mapping[str, tuple[ClauseAnchor, ...]] = MappingProxyType(
    {
        RESEARCH_ANALYST: (
            ClauseAnchor(
                "playbook.standing_rules",
                _PLAYBOOK,
                "0. Standing rules (never violated)",
            ),
            ClauseAnchor(
                "playbook.hard_gates",
                _PLAYBOOK,
                "Hard gates (all 5 must pass or the candidate is skipped — grade C)",
            ),
            ClauseAnchor(
                "framework.banned_actions",
                _FRAMEWORK,
                "5. Explicitly banned (no exceptions)",
            ),
            ClauseAnchor(
                "framework.spec_gate",
                _FRAMEWORK,
                "6. The spec-gate (read-before-trade)",
            ),
            ClauseAnchor(
                "playbook.research_protocol",
                _PLAYBOOK,
                "6. News & research protocol (research packet)",
            ),
            ClauseAnchor(
                "framework.honesty_clause",
                _FRAMEWORK,
                "9. Honesty clause",
            ),
        ),
        RESEARCH_VERIFIER: (
            ClauseAnchor(
                "playbook.standing_rules",
                _PLAYBOOK,
                "0. Standing rules (never violated)",
            ),
            ClauseAnchor(
                "playbook.hard_gates",
                _PLAYBOOK,
                "Hard gates (all 5 must pass or the candidate is skipped — grade C)",
            ),
            ClauseAnchor(
                "framework.banned_actions",
                _FRAMEWORK,
                "5. Explicitly banned (no exceptions)",
            ),
            ClauseAnchor(
                "framework.spec_gate",
                _FRAMEWORK,
                "6. The spec-gate (read-before-trade)",
            ),
            ClauseAnchor(
                "playbook.research_protocol",
                _PLAYBOOK,
                "6. News & research protocol (research packet)",
            ),
            ClauseAnchor(
                "framework.honesty_clause",
                _FRAMEWORK,
                "9. Honesty clause",
            ),
        ),
        STRATEGY_SCIENTIST: (
            ClauseAnchor(
                "playbook.standing_rules",
                _PLAYBOOK,
                "0. Standing rules (never violated)",
            ),
            ClauseAnchor(
                "framework.banned_actions",
                _FRAMEWORK,
                "5. Explicitly banned (no exceptions)",
            ),
            ClauseAnchor(
                "framework.spec_gate",
                _FRAMEWORK,
                "6. The spec-gate (read-before-trade)",
            ),
            ClauseAnchor(
                "framework.adaptation_rules",
                _FRAMEWORK,
                "7. Adaptation rules (how the desk learns)",
            ),
            ClauseAnchor(
                "framework.operator_score",
                _FRAMEWORK,
                "8. Operator score (penalty/reward for the executing AI)",
            ),
            ClauseAnchor(
                "framework.honesty_clause",
                _FRAMEWORK,
                "9. Honesty clause",
            ),
            ClauseAnchor(
                "playbook.measurement_loop",
                _PLAYBOOK,
                "8. Measurement & model-improvement loop",
            ),
        ),
        POSTMORTEM_WRITER: (
            ClauseAnchor(
                "playbook.standing_rules",
                _PLAYBOOK,
                "0. Standing rules (never violated)",
            ),
            ClauseAnchor(
                "framework.banned_actions",
                _FRAMEWORK,
                "5. Explicitly banned (no exceptions)",
            ),
            ClauseAnchor(
                "framework.spec_gate",
                _FRAMEWORK,
                "6. The spec-gate (read-before-trade)",
            ),
            ClauseAnchor(
                "playbook.management_policy",
                _PLAYBOOK,
                "3. Trade management policy (exact mechanics)",
            ),
            ClauseAnchor(
                "framework.operator_score",
                _FRAMEWORK,
                "8. Operator score (penalty/reward for the executing AI)",
            ),
            ClauseAnchor(
                "framework.honesty_clause",
                _FRAMEWORK,
                "9. Honesty clause",
            ),
            ClauseAnchor(
                "playbook.measurement_loop",
                _PLAYBOOK,
                "8. Measurement & model-improvement loop",
            ),
        ),
    }
)

RUNTIME_ROLES: tuple[str, ...] = tuple(MANDATORY_CLAUSES)


@dataclass(frozen=True)
class _Heading:
    index: int
    level: int
    text: str


def _read_source(root: Path, relpath: str) -> bytes:
    try:
        return (root / relpath).read_bytes()
    except OSError as error:
        raise ContractError(
            "SPEC_UNACKNOWLEDGED", f"{relpath}: spec source unreadable ({error})"
        ) from None


def _decode(relpath: str, raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(
            "INVALID_SCHEMA", f"{relpath}: rule document is not UTF-8 ({error})"
        ) from None


def _scan_markers(relpath: str, text: str) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for marker in UNRESOLVED_MARKERS:
            if marker in line:
                raise ContractError(
                    "INVALID_SCHEMA",
                    f"{relpath}:{line_number}: unresolved placeholder marker {marker!r}",
                )


def _bundle_digest(files: Sequence[SpecFile]) -> str:
    """SHA-256 over canonical JSON of ordered ``(relpath, sha256)`` pairs."""
    document = [[file.relpath, file.digest] for file in files]
    payload = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _checked_bundle(bundle: object) -> SpecBundle:
    if not isinstance(bundle, SpecBundle):
        raise ContractError("INVALID_SCHEMA", "bundle: SpecBundle required")
    if tuple(file.relpath for file in bundle.files) != BUNDLE_SOURCES:
        raise ContractError(
            "INVALID_SCHEMA", "bundle: file set does not match the frozen BUNDLE_SOURCES"
        )
    if bundle.total_bytes != sum(file.size for file in bundle.files):
        raise ContractError("INVALID_SCHEMA", "bundle: total_bytes disagrees with file sizes")
    if bundle.bundle_digest != _bundle_digest(bundle.files):
        raise ContractError("INVALID_SCHEMA", "bundle: bundle_digest is not self-consistent")
    return bundle


def load_spec_bundle(root: Path = DEFAULT_ROOT) -> SpecBundle:
    """Digest the exact bytes of every rule document in ``BUNDLE_SOURCES``.

    Raises ``SPEC_UNACKNOWLEDGED`` when a source is missing or unreadable and
    ``INVALID_SCHEMA`` when the bundle is oversized or contains an unresolved
    placeholder marker. Order is fixed; ``bundle_digest`` is independent of
    filesystem metadata.
    """
    base = Path(root)
    files: list[SpecFile] = []
    for relpath in BUNDLE_SOURCES:
        raw = _read_source(base, relpath)
        if not raw:
            raise ContractError("INVALID_SCHEMA", f"{relpath}: rule document is empty")
        _scan_markers(relpath, _decode(relpath, raw))
        files.append(
            SpecFile(
                relpath=relpath,
                digest=hashlib.sha256(raw).hexdigest(),
                size=len(raw),
            )
        )
    total_bytes = sum(file.size for file in files)
    if total_bytes > MAX_BUNDLE_BYTES:
        raise ContractError(
            "INVALID_SCHEMA",
            f"spec bundle is {total_bytes} bytes; limit is {MAX_BUNDLE_BYTES}",
        )
    frozen = tuple(files)
    return SpecBundle(
        bundle_digest=_bundle_digest(frozen),
        files=frozen,
        total_bytes=total_bytes,
    )


def _parse_headings(lines: Sequence[str]) -> tuple[_Heading, ...]:
    """Return ATX headings outside fenced code blocks, preserving line order."""
    headings: list[_Heading] = []
    in_fence = False
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        if _FENCE_RE.match(content):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING_RE.match(content)
        if match is not None:
            headings.append(
                _Heading(index=index, level=len(match.group(1)), text=match.group(2).strip())
            )
    return tuple(headings)


def _section(text: str, relpath: str, heading: str) -> str:
    """Extract a heading line through the next same-or-higher-level heading."""
    lines = text.splitlines(keepends=True)
    headings = _parse_headings(lines)
    matches = [candidate for candidate in headings if candidate.text == heading]
    if not matches:
        raise ContractError(
            "SPEC_UNACKNOWLEDGED",
            f"{relpath}: mandatory clause heading not found: {heading!r}",
        )
    if len(matches) > 1:
        raise ContractError(
            "INVALID_SCHEMA",
            f"{relpath}: mandatory clause heading is ambiguous: {heading!r}",
        )
    target = matches[0]
    end = len(lines)
    for candidate in headings:
        if candidate.index > target.index and candidate.level <= target.level:
            end = candidate.index
            break
    return "".join(lines[target.index:end])


def required_excerpts_for(
    bundle: SpecBundle, role: str, root: Path = DEFAULT_ROOT
) -> ExcerptPacket:
    """Return the bounded mandatory-clause packet for one runtime role.

    The packet text embeds every clause id and the exact anchored section bytes.
    A missing heading, a source changed after the bundle digest was taken, or an
    unreadable source is ``SPEC_UNACKNOWLEDGED``; an oversized role selection or
    an unknown role is ``INVALID_SCHEMA``.
    """
    checked = _checked_bundle(bundle)
    if type(role) is not str or role not in MANDATORY_CLAUSES:
        raise ContractError(
            "INVALID_SCHEMA",
            f"unknown runtime role {role!r}; supported roles: {list(RUNTIME_ROLES)!r}",
        )
    anchors = MANDATORY_CLAUSES[role]
    base = Path(root)
    digests = {file.relpath: file.digest for file in checked.files}
    documents: dict[str, str] = {}
    for relpath in BUNDLE_SOURCES:
        raw = _read_source(base, relpath)
        if hashlib.sha256(raw).hexdigest() != digests[relpath]:
            raise ContractError(
                "SPEC_UNACKNOWLEDGED",
                f"{relpath}: content changed after bundle load; reload and re-acknowledge",
            )
        documents[relpath] = _decode(relpath, raw)

    parts = [
        "# Spec bundle excerpt\n",
        f"# bundle_digest: {checked.bundle_digest}\n",
        f"# role: {role}\n\n",
    ]
    clause_ids: list[str] = []
    for anchor in anchors:
        section = _section(documents[anchor.relpath], anchor.relpath, anchor.heading)
        parts.extend(
            (
                f"[BEGIN MANDATORY CLAUSE {anchor.clause_id}]\n",
                f"source: {anchor.relpath} :: {anchor.heading}\n",
                section,
                "\n[END MANDATORY CLAUSE "
                f"{anchor.clause_id}]\n\n",
            )
        )
        clause_ids.append(anchor.clause_id)

    text = "".join(parts)
    total_bytes = len(text.encode("utf-8"))
    if total_bytes > MAX_EXCERPT_BYTES:
        raise ContractError(
            "INVALID_SCHEMA",
            f"role {role!r} excerpt is {total_bytes} bytes; limit is {MAX_EXCERPT_BYTES}",
        )
    return ExcerptPacket(
        role=role,
        bundle_digest=checked.bundle_digest,
        clauses=tuple(clause_ids),
        text=text,
        total_bytes=total_bytes,
    )


def _ack_mapping(acknowledgment: object) -> dict[str, object]:
    if not isinstance(acknowledgment, Mapping):
        raise ContractError("INVALID_SCHEMA", "acknowledgment: mapping required")
    payload: dict[str, object] = {}
    for key, value in acknowledgment.items():
        if type(key) is not str:
            raise ContractError("INVALID_SCHEMA", "acknowledgment: string keys required")
        payload[key] = value
    return payload


def _known_anchors(role: object) -> tuple[ClauseAnchor, ...]:
    if type(role) is not str:
        raise ContractError("INVALID_SCHEMA", "acknowledgment.role: string required")
    anchors = MANDATORY_CLAUSES.get(role)
    if anchors is None:
        raise ContractError(
            "SPEC_UNACKNOWLEDGED",
            f"unknown runtime role {role!r}; supported roles: {list(RUNTIME_ROLES)!r}",
        )
    return anchors


def _check_timestamp(value: object) -> None:
    if type(value) is not str or _TIMESTAMP_RE.fullmatch(value) is None:
        raise ContractError(
            "INVALID_SCHEMA",
            "acknowledgment.acknowledged_at: strict UTC ISO-8601 string ending 'Z' required",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ContractError(
            "INVALID_SCHEMA", f"acknowledgment.acknowledged_at: invalid timestamp {value!r}"
        ) from None
    if parsed.utcoffset() != _ZERO_OFFSET:
        raise ContractError(
            "INVALID_SCHEMA", "acknowledgment.acknowledged_at: UTC offset must be zero"
        )


def _clause_ids(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ContractError(
            "INVALID_SCHEMA", "acknowledgment.clauses: sequence of clause ids required"
        )
    items: list[str] = []
    for index, item in enumerate(value):
        if type(item) is not str or not item.strip():
            raise ContractError(
                "INVALID_SCHEMA",
                f"acknowledgment.clauses[{index}]: non-empty string required",
            )
        items.append(item)
    return tuple(items)


def validate_acknowledgment(
    bundle: SpecBundle, acknowledgment: Mapping[str, object]
) -> None:
    """Validate an evidence-only acknowledgment; return ``None`` or fail typed.

    Exactly four keys are accepted. Any extra key — including waiver,
    permission, grant, unlock or authority-shaped names — is ``INVALID_SCHEMA``:
    a model acknowledgment may never claim a waived rule or grant permission.
    The bundle digest must match (``SPEC_UNACKNOWLEDGED``), the role must be a
    known runtime role (``SPEC_UNACKNOWLEDGED``), and ``acknowledged_at`` must
    be a strict UTC string ending ``Z``. Clause coverage uses set equality:
    duplicates are tolerated but add no coverage; missing or unexpected clause
    ids are ``SPEC_UNACKNOWLEDGED``. The function has no side effects and its
    ``None`` result is not authority.
    """
    checked = _checked_bundle(bundle)
    payload = _ack_mapping(acknowledgment)

    unknown = sorted(key for key in payload if key not in _EXPECTED_ACK_KEYS)
    if unknown:
        forbidden = sorted(
            key
            for key in unknown
            if any(fragment in key.casefold() for fragment in _FORBIDDEN_ACK_FRAGMENTS)
        )
        if forbidden:
            raise ContractError(
                "INVALID_SCHEMA",
                "acknowledgment: keys "
                f"{forbidden!r} may never waive a rule or grant permission",
            )
        raise ContractError("INVALID_SCHEMA", f"acknowledgment: unknown fields {unknown!r}")
    missing = sorted(_EXPECTED_ACK_KEYS - payload.keys())
    if missing:
        raise ContractError("INVALID_SCHEMA", f"acknowledgment: missing fields {missing!r}")

    digest = payload["bundle_digest"]
    if type(digest) is not str:
        raise ContractError("INVALID_SCHEMA", "acknowledgment.bundle_digest: string required")
    if digest != checked.bundle_digest:
        raise ContractError(
            "SPEC_UNACKNOWLEDGED",
            "acknowledgment.bundle_digest does not match the loaded bundle",
        )

    anchors = _known_anchors(payload["role"])
    _check_timestamp(payload["acknowledged_at"])

    required = {anchor.clause_id for anchor in anchors}
    provided = set(_clause_ids(payload["clauses"]))
    missing_clauses = sorted(required - provided)
    unexpected = sorted(provided - required)
    if missing_clauses or unexpected:
        raise ContractError(
            "SPEC_UNACKNOWLEDGED",
            "acknowledgment.clauses: "
            f"missing {missing_clauses!r}, unexpected {unexpected!r}",
        )
