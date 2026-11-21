"""Pure consistency checks for asserted qualification order, never storage proof.

An accepted member still needs a complete saved read, approved policy and verified
execution before consumption. Neither these hashes nor ordinals authenticate that.
"""

from __future__ import annotations

import hashlib
import json
import re
from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

_COMMAND_VERSION = "fpi-qualification-command-v2"
_EVENT_VERSION = "fpi-qualification-event-v2"
_VIEW_VERSION = "fpi-qualification-view-v2"
_MAX_COMMAND_BYTES = 300_000
_MAX_EVENT_BYTES = 400_000
_MAX_VIEW_BYTES = 16_000_000
_MAX_MEMBERS = 20_000
_MAX_HEADS = 100_000
_MAX_EVENTS = 100_000
_MAX_BASIS = 4096
_COMMAND_FIELDS = {
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
_EVENT_FIELDS = {
    "version",
    "command",
    "command_id",
    "event_ordinal",
    "recorded_at",
    "witness",
}
_HEAD_FIELDS = {"scope", "target", "event_id"}


def _canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _sha(document: str) -> str:
    return hashlib.sha256(document.encode("ascii")).hexdigest()


def _digest(value: Any) -> None:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("Expected lowercase SHA-256")


def _tuple(value: Any, maximum: int) -> None:
    if type(value) is not tuple or len(value) > maximum:
        raise ValueError("Expected bounded exact tuple")


def _scope_target(scope: Any, target: Any) -> None:
    if type(scope) is not str or scope not in ("membership", "value", "parser", "date"):
        raise ValueError("Invalid qualification scope")
    if scope == "date":
        _date_text(target)
    else:
        _digest(target)


def _date_text(value: Any) -> date:
    if type(value) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("Expected ISO reporting date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid reporting date") from None


def _utc(value: Any) -> datetime:
    if type(value) is not datetime:
        raise ValueError("Expected aware datetime")
    try:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Expected aware datetime")
        return value.astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("Invalid aware datetime") from None


def _head_document(head: FpiQualificationHead) -> dict[str, Any]:
    return {"scope": head.scope, "target": head.target, "event_id": head.event_id}


@dataclass(frozen=True)
class FpiQualificationCommand:
    scope: str
    target: str
    action: str
    reason_code: str
    evidence_sha256: str
    expected_prior_event_id: str | None = None
    chosen_membership_id: str | None = None
    basis_membership_ids: tuple[str, ...] = ()
    document_json: str = field(init=False, repr=False)
    command_id: str = field(init=False)

    def __post_init__(self) -> None:
        _scope_target(self.scope, self.target)
        if (
            type(self.reason_code) is not str
            or re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.reason_code) is None
        ):
            raise ValueError("Invalid reason code")
        _digest(self.evidence_sha256)
        _tuple(self.basis_membership_ids, _MAX_BASIS)
        if self.expected_prior_event_id is not None:
            _digest(self.expected_prior_event_id)
        if type(self.action) is not str:
            raise ValueError("Invalid qualification action")
        if self.scope == "date":
            _digest(self.chosen_membership_id)
            for member_id in self.basis_membership_ids:
                _digest(member_id)
            if (
                self.action != "RESOLVE"
                or not self.basis_membership_ids
                or len(set(self.basis_membership_ids)) != len(self.basis_membership_ids)
                or self.chosen_membership_id not in self.basis_membership_ids
            ):
                raise ValueError("Resolution requires chosen member in unique nonempty basis")
            object.__setattr__(
                self, "basis_membership_ids", tuple(sorted(self.basis_membership_ids))
            )
        elif (
            self.action not in ("ACCEPT", "WITHDRAW", "QUARANTINE")
            or self.chosen_membership_id is not None
            or self.basis_membership_ids
        ):
            raise ValueError("Invalid non-date qualification")
        document = _canonical(
            {
                "version": _COMMAND_VERSION,
                "scope": self.scope,
                "target": self.target,
                "action": self.action,
                "reason_code": self.reason_code,
                "evidence_sha256": self.evidence_sha256,
                "expected_prior_event_id": self.expected_prior_event_id,
                "chosen_membership_id": self.chosen_membership_id,
                "basis_membership_ids": self.basis_membership_ids,
            }
        )
        if len(document) > _MAX_COMMAND_BYTES:
            raise ValueError("Command exceeds canonical byte limit")
        object.__setattr__(self, "document_json", document)
        object.__setattr__(self, "command_id", _sha(document))


@dataclass(frozen=True)
class FpiQualificationHead:
    scope: str
    target: str
    event_id: str | None

    def __post_init__(self) -> None:
        _scope_target(self.scope, self.target)
        if self.event_id is not None:
            _digest(self.event_id)


def _copy_head(value: FpiQualificationHead) -> FpiQualificationHead:
    if type(value) is not FpiQualificationHead:
        raise ValueError("Expected qualification head")
    try:
        return FpiQualificationHead(value.scope, value.target, value.event_id)
    except AttributeError:
        raise ValueError("Incomplete qualification head") from None


@dataclass(frozen=True)
class FpiResolutionWitness:
    heads: tuple[FpiQualificationHead, ...]

    def __post_init__(self) -> None:
        _tuple(self.heads, 3)
        if len(self.heads) != 3:
            raise ValueError("Resolution needs three scope heads")
        heads = tuple(_copy_head(head) for head in self.heads)
        if {head.scope for head in heads} != {"membership", "value", "parser"}:
            raise ValueError("Resolution needs membership/value/parser heads")
        if next(head for head in heads if head.scope == "membership").event_id is None:
            raise ValueError("Historical membership must have qualification")
        object.__setattr__(self, "heads", tuple(sorted(heads, key=lambda h: (h.scope, h.target))))


def _copy_command(value: FpiQualificationCommand) -> FpiQualificationCommand:
    if type(value) is not FpiQualificationCommand:
        raise ValueError("Expected qualification command")
    try:
        rebuilt = FpiQualificationCommand(
            value.scope,
            value.target,
            value.action,
            value.reason_code,
            value.evidence_sha256,
            value.expected_prior_event_id,
            value.chosen_membership_id,
            value.basis_membership_ids,
        )
        if rebuilt != value:
            raise ValueError("Forged qualification command")
        return rebuilt
    except AttributeError:
        raise ValueError("Incomplete qualification command") from None


@dataclass(frozen=True)
class FpiQualificationEventV2:
    command: FpiQualificationCommand
    event_ordinal: int
    recorded_at: datetime
    witness: FpiResolutionWitness | None = None
    document_json: str = field(init=False, repr=False)
    event_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.event_ordinal) is not int or not 1 <= self.event_ordinal <= 2**63 - 1:
            raise ValueError("Event ordinal outside signed bigint range")
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at))
        command = _copy_command(self.command)
        object.__setattr__(self, "command", command)
        witness_doc = "null"
        if command.scope == "date":
            if type(self.witness) is not FpiResolutionWitness:
                raise ValueError("Resolution requires witness")
            try:
                witness = FpiResolutionWitness(self.witness.heads)
            except AttributeError:
                raise ValueError("Incomplete resolution witness") from None
            if witness != self.witness:
                raise ValueError("Forged resolution witness")
            object.__setattr__(self, "witness", witness)
            witness_doc = _canonical({"heads": [_head_document(h) for h in witness.heads]})
        elif self.witness is not None:
            raise ValueError("Only resolution may have witness")
        # Embed the already validated command without parsing or serializing it again.
        document = (
            '{"command":'
            + command.document_json
            + ',"command_id":'
            + _canonical(command.command_id)
            + ',"event_ordinal":'
            + str(self.event_ordinal)
            + ',"recorded_at":'
            + _canonical(self.recorded_at.isoformat())
            + ',"version":'
            + _canonical(_EVENT_VERSION)
            + ',"witness":'
            + witness_doc
            + "}"
        )
        if len(document) > _MAX_EVENT_BYTES:
            raise ValueError("Event exceeds canonical byte limit")
        object.__setattr__(self, "document_json", document)
        object.__setattr__(self, "event_id", _sha(document))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> Any:
    raise ValueError("Invalid JSON numeric constant")


def _load(document: str, maximum: int) -> dict[str, Any]:
    if type(document) is not str or len(document) > maximum or not document.isascii():
        raise ValueError("Expected bounded ASCII document")
    # Reject depth before JSON allocation; strings cannot hide delimiters from this scan.
    depth, quoted, escaped = 0, False, False
    for char in document:
        if char == "\x00":
            raise ValueError("NUL in document")
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 8:
                raise ValueError("Document nesting limit exceeded")
        elif char in "]}":
            depth -= 1
    try:
        value = json.loads(document, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Invalid qualification JSON") from None
    if type(value) is not dict:
        raise ValueError("Expected document object")
    return value


def _keys(value: Any, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict or value.keys() != keys:
        raise ValueError("Unexpected document fields")
    return value


def _command_from_document(value: Any) -> FpiQualificationCommand:
    document = _keys(value, _COMMAND_FIELDS)
    if type(document["version"]) is not str or document["version"] != _COMMAND_VERSION:
        raise ValueError("Unsupported command version")
    basis = document["basis_membership_ids"]
    if type(basis) is not list or len(basis) > _MAX_BASIS:
        raise ValueError("Invalid command basis array")
    return FpiQualificationCommand(
        document["scope"],
        document["target"],
        document["action"],
        document["reason_code"],
        document["evidence_sha256"],
        document["expected_prior_event_id"],
        document["chosen_membership_id"],
        tuple(basis),
    )


def decode_fpi_qualification_command(document_json: str) -> FpiQualificationCommand:
    command = _command_from_document(_load(document_json, _MAX_COMMAND_BYTES))
    if command.document_json != document_json:
        raise ValueError("Noncanonical qualification command")
    return command


def decode_fpi_qualification_event(document_json: str) -> FpiQualificationEventV2:
    document = _keys(_load(document_json, _MAX_EVENT_BYTES), _EVENT_FIELDS)
    if type(document["version"]) is not str or document["version"] != _EVENT_VERSION:
        raise ValueError("Unsupported event version")
    command = _command_from_document(document["command"])
    _digest(document["command_id"])
    if command.command_id != document["command_id"]:
        raise ValueError("Command identity mismatch")
    witness = None
    if document["witness"] is not None:
        heads = _keys(document["witness"], {"heads"})["heads"]
        if type(heads) is not list or len(heads) != 3:
            raise ValueError("Invalid witness head array")
        witness = FpiResolutionWitness(
            tuple(FpiQualificationHead(**_keys(head, _HEAD_FIELDS)) for head in heads)
        )
    timestamp = document["recorded_at"]
    if type(timestamp) is not str or len(timestamp) > 32:
        raise ValueError("Invalid event timestamp")
    try:
        recorded_at = datetime.fromisoformat(timestamp)
    except ValueError:
        raise ValueError("Invalid event timestamp") from None
    event = FpiQualificationEventV2(command, document["event_ordinal"], recorded_at, witness)
    if event.document_json != document_json:
        raise ValueError("Noncanonical qualification event")
    return event


@dataclass(frozen=True)
class FpiQualificationMember:
    membership_id: str
    value_sha256: str
    parser_sha256: str
    reporting_date: date

    def __post_init__(self) -> None:
        for value in (self.membership_id, self.value_sha256, self.parser_sha256):
            _digest(value)
        if type(self.reporting_date) is not date:
            raise ValueError("Expected exact reporting date")


def _copy_member(value: FpiQualificationMember) -> FpiQualificationMember:
    if type(value) is not FpiQualificationMember:
        raise ValueError("Expected qualification member")
    try:
        return FpiQualificationMember(
            value.membership_id, value.value_sha256, value.parser_sha256, value.reporting_date
        )
    except AttributeError:
        raise ValueError("Incomplete qualification member") from None


def _copy_event(value: FpiQualificationEventV2) -> FpiQualificationEventV2:
    if type(value) is not FpiQualificationEventV2:
        raise ValueError("Expected qualification event")
    try:
        rebuilt = FpiQualificationEventV2(
            value.command, value.event_ordinal, value.recorded_at, value.witness
        )
        if rebuilt != value:
            raise ValueError("Forged qualification event")
        return rebuilt
    except AttributeError:
        raise ValueError("Incomplete qualification event") from None


def _member_targets(member: FpiQualificationMember) -> tuple[tuple[str, str], ...]:
    return (
        ("membership", member.membership_id),
        ("value", member.value_sha256),
        ("parser", member.parser_sha256),
    )


@dataclass(frozen=True)
class FpiQualificationView:
    """Complete *asserted* universe and compact heads; no authenticated read claim."""

    members: tuple[FpiQualificationMember, ...]
    heads: tuple[FpiQualificationHead, ...]
    events: tuple[FpiQualificationEventV2, ...]
    view_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _tuple(self.members, _MAX_MEMBERS)
        _tuple(self.heads, _MAX_HEADS)
        _tuple(self.events, _MAX_EVENTS)
        members: dict[str, FpiQualificationMember] = {}
        heads: dict[tuple[str, str], FpiQualificationHead] = {}
        events: dict[str, FpiQualificationEventV2] = {}
        member_docs: dict[str, str] = {}
        head_docs: dict[tuple[str, str], str] = {}
        required_targets: set[tuple[str, str]] = set()
        date_members: dict[str, set[str]] = {}
        value_dates: dict[str, date] = {}
        # Exact overhead plus one comma per element after the first, counted before joining.
        used = len(
            '{"events":[],"heads":[],"members":[],"version":' + _canonical(_VIEW_VERSION) + "}"
        )

        def reserve(document: str, index: int) -> None:
            nonlocal used
            used += len(document) + int(index > 0)
            if used > _MAX_VIEW_BYTES:
                raise ValueError("View exceeds canonical byte limit")

        for index, supplied_member in enumerate(self.members):
            member = _copy_member(supplied_member)
            if member.membership_id in members:
                raise ValueError("Duplicate membership identity")
            prior_date = value_dates.setdefault(member.value_sha256, member.reporting_date)
            if prior_date != member.reporting_date:
                raise ValueError("One value hash cannot name different reporting dates")
            document = _canonical(
                {
                    "membership_id": member.membership_id,
                    "value_sha256": member.value_sha256,
                    "parser_sha256": member.parser_sha256,
                    "reporting_date": member.reporting_date.isoformat(),
                }
            )
            reserve(document, index)
            members[member.membership_id] = member
            member_docs[member.membership_id] = document
            required_targets.update(_member_targets(member))
            day = member.reporting_date.isoformat()
            required_targets.add(("date", day))
            date_members.setdefault(day, set()).add(member.membership_id)
        for index, supplied_head in enumerate(self.heads):
            head = _copy_head(supplied_head)
            key = (head.scope, head.target)
            if key in heads:
                raise ValueError("Duplicate qualification head target")
            document = _canonical(_head_document(head))
            reserve(document, index)
            heads[key], head_docs[key] = head, document
        if set(heads) != required_targets:
            raise ValueError("Heads must exactly cover the membership universe")
        command_ids: set[str] = set()
        ordinals: set[int] = set()
        successors: set[tuple[str, str, str | None]] = set()
        by_target: dict[tuple[str, str], list[FpiQualificationEventV2]] = {}
        for index, supplied_event in enumerate(self.events):
            event = _copy_event(supplied_event)
            reserve(event.document_json, index)
            command = event.command
            key = (command.scope, command.target)
            if key not in required_targets:
                raise ValueError("Event target outside membership universe")
            if (
                event.event_id in events
                or command.command_id in command_ids
                or event.event_ordinal in ordinals
            ):
                raise ValueError("Duplicate event, command or ordinal")
            successor = (*key, command.expected_prior_event_id)
            if successor in successors:
                raise ValueError("Forked qualification successor")
            successors.add(successor)
            events[event.event_id] = event
            command_ids.add(command.command_id)
            ordinals.add(event.event_ordinal)
            by_target.setdefault(key, []).append(event)
        target_ordinals: dict[tuple[str, str], list[int]] = {}
        for key, target_events in by_target.items():
            target_events.sort(key=lambda event: event.event_ordinal)
            target_ordinals[key] = [event.event_ordinal for event in target_events]
        required_events: set[str] = set()
        for key, head in heads.items():
            target_events = by_target.get(key, [])
            latest = target_events[-1].event_id if target_events else None
            if head.event_id != latest:
                raise ValueError("Current head is missing, wrong-target or not latest")
            if head.event_id is not None:
                required_events.add(head.event_id)
        for event in events.values():
            command = event.command
            prior = events.get(command.expected_prior_event_id or "")
            if prior is not None and (
                prior.event_ordinal >= event.event_ordinal
                or (prior.command.scope, prior.command.target) != (command.scope, command.target)
            ):
                raise ValueError("Supplied predecessor must be earlier on same target")
            if command.scope != "date":
                continue
            if not set(command.basis_membership_ids) <= date_members[command.target]:
                raise ValueError("Resolution basis outside reporting date")
            chosen = members[command.chosen_membership_id]  # type: ignore[index]
            witness = event.witness
            if witness is None:  # Constructors already reject this; keep contextual check explicit.
                raise ValueError("Resolution requires witness")
            if {(h.scope, h.target) for h in witness.heads} != set(_member_targets(chosen)):
                raise ValueError("Witness targets do not match chosen membership")
            for head in witness.heads:
                key = (head.scope, head.target)
                position = bisect_left(target_ordinals.get(key, []), event.event_ordinal)
                latest_past = by_target[key][position - 1] if position else None
                if head.event_id is None:
                    if latest_past is not None:
                        raise ValueError("Witness absence contradicts earlier event")
                    continue
                historical = events.get(head.event_id)
                if (
                    historical is None
                    or historical is not latest_past
                    or historical.command.action != "ACCEPT"
                ):
                    raise ValueError("Witness must name latest earlier accepted scope head")
                required_events.add(head.event_id)
        if required_events != set(events):
            raise ValueError("Event set must contain exactly current and witness heads")
        member_keys, head_keys, event_keys = sorted(members), sorted(heads), sorted(events)
        document = (
            '{"events":['
            + ",".join(events[key].document_json for key in event_keys)
            + '],"heads":['
            + ",".join(head_docs[key] for key in head_keys)
            + '],"members":['
            + ",".join(member_docs[key] for key in member_keys)
            + '],"version":'
            + _canonical(_VIEW_VERSION)
            + "}"
        )
        object.__setattr__(self, "members", tuple(members[key] for key in member_keys))
        object.__setattr__(self, "heads", tuple(heads[key] for key in head_keys))
        object.__setattr__(self, "events", tuple(events[key] for key in event_keys))
        object.__setattr__(self, "view_sha256", _sha(document))


def _validated_view(view: FpiQualificationView) -> FpiQualificationView:
    if type(view) is not FpiQualificationView:
        raise ValueError("Expected qualification view")
    try:
        rebuilt = FpiQualificationView(view.members, view.heads, view.events)
        if rebuilt != view:
            raise ValueError("Forged qualification view")
        return rebuilt
    except AttributeError:
        raise ValueError("Incomplete qualification view") from None


def _qualification(member: FpiQualificationMember, heads: dict[tuple[str, str], str]) -> str:
    actions = [heads.get(target) for target in _member_targets(member)]
    if "QUARANTINE" in actions:
        return "QUARANTINED"
    if "WITHDRAW" in actions:
        return "WITHDRAWN"
    return "ACCEPTED" if actions[0] == "ACCEPT" else "UNQUALIFIED"


@dataclass(frozen=True)
class FpiQualificationEvaluation:
    view_sha256: str
    member_states: tuple[tuple[str, str], ...]
    date_resolutions: tuple[tuple[date, str, str | None], ...]
    result_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _digest(self.view_sha256)
        _tuple(self.member_states, _MAX_MEMBERS)
        _tuple(self.date_resolutions, _MAX_MEMBERS)
        states: dict[str, str] = {}
        dates: set[date] = set()
        for row in self.member_states:
            _tuple(row, 2)
            if len(row) != 2:
                raise ValueError("Invalid member state row")
            member_id, status = row
            _digest(member_id)
            if (
                type(status) is not str
                or status not in ("ACCEPTED", "UNQUALIFIED", "WITHDRAWN", "QUARANTINED")
                or member_id in states
            ):
                raise ValueError("Invalid or duplicate member state")
            states[member_id] = status
        for resolution in self.date_resolutions:
            _tuple(resolution, 3)
            if len(resolution) != 3:
                raise ValueError("Invalid date resolution row")
            day, status, chosen = resolution
            if (
                type(day) is not date
                or day in dates
                or type(status) is not str
                or status
                not in ("NO_RESOLUTION", "STALE_RESOLUTION", "TARGET_UNQUALIFIED", "RESOLVED")
            ):
                raise ValueError("Invalid or duplicate date resolution")
            dates.add(day)
            if status == "RESOLVED":
                _digest(chosen)
                if states.get(chosen or "") != "ACCEPTED":
                    raise ValueError("Resolution result must choose accepted member")
            elif chosen is not None:
                raise ValueError("Unresolved result cannot choose member")
        object.__setattr__(self, "member_states", tuple(sorted(self.member_states)))
        object.__setattr__(self, "date_resolutions", tuple(sorted(self.date_resolutions)))
        document = _canonical(
            {
                "version": "fpi-qualification-evaluation-v2",
                "view_sha256": self.view_sha256,
                "member_states": self.member_states,
                "date_resolutions": [
                    (day.isoformat(), status, chosen)
                    for day, status, chosen in self.date_resolutions
                ],
            }
        )
        object.__setattr__(self, "result_sha256", _sha(document))


def evaluate_fpi_qualification(view: FpiQualificationView) -> FpiQualificationEvaluation:
    """Validate once and evaluate every member/date using bounded shared maps."""
    view = _validated_view(view)
    events = {event.event_id: event for event in view.events}
    heads = {(head.scope, head.target): head.event_id for head in view.heads}
    actions = {
        key: events[event_id].command.action
        for key, event_id in heads.items()
        if event_id is not None
    }
    states: dict[str, str] = {}
    by_date: dict[date, set[str]] = {}
    for member in view.members:
        states[member.membership_id] = _qualification(member, actions)
        by_date.setdefault(member.reporting_date, set()).add(member.membership_id)
    resolutions: list[tuple[date, str, str | None]] = []
    for day, members in by_date.items():
        head_id = heads[("date", day.isoformat())]
        status, chosen = "NO_RESOLUTION", None
        if head_id is not None:
            command = events[head_id].command
            if set(command.basis_membership_ids) != members:
                status = "STALE_RESOLUTION"
            elif states[command.chosen_membership_id or ""] != "ACCEPTED":
                status = "TARGET_UNQUALIFIED"
            else:
                status, chosen = "RESOLVED", command.chosen_membership_id
        resolutions.append((day, status, chosen))
    return FpiQualificationEvaluation(view.view_sha256, tuple(states.items()), tuple(resolutions))


def member_qualification(view: FpiQualificationView, membership_id: str) -> str:
    _digest(membership_id)
    result = evaluate_fpi_qualification(view)
    for member_id, state in result.member_states:
        if member_id == membership_id:
            return state
    raise ValueError("Unknown membership")


def date_resolution(view: FpiQualificationView, reporting_date: date) -> tuple[str, str | None]:
    if type(reporting_date) is not date:
        raise ValueError("Expected exact reporting date")
    result = evaluate_fpi_qualification(view)
    for day, status, chosen in result.date_resolutions:
        if day == reporting_date:
            return status, chosen
    raise ValueError("Unknown reporting date")
