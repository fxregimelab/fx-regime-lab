"""Pure selection from asserted, exact decision evidence; no visibility proof or I/O."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from src.research.fpi_capture import FpiCapture, validate_fpi_capture
from src.research.fpi_observation import FPI_OBSERVATION_VERSION, build_fpi_observation

_IST = timezone(timedelta(hours=5, minutes=30))
_LATEST = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"
_MONTHLY = "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx"
_SELECTOR = "fpi-decision-selection-v1"


def _hash(value: Any) -> str:
    def encode_day(item: Any) -> str:
        if type(item) is not date:
            raise TypeError("Unsupported fingerprint value")
        return item.isoformat()

    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=encode_day
    )
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _digest(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("Expected lowercase SHA-256")


def _text(value: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise ValueError("Expected nonempty bounded text")


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Expected aware datetime")
    try:
        result = value.astimezone(UTC)
        result.astimezone(_IST)
        return result
    except (ValueError, OverflowError) as exc:
        raise ValueError("Unsupported timestamp range") from exc


def _tuple(value: tuple[Any, ...]) -> None:
    if type(value) is not tuple:
        raise ValueError("Expected immutable tuple")


@dataclass(frozen=True)
class FpiParsedDay:
    """One complete canonical INR value and separate retained source evidence."""

    document_json: str
    source_evidence_sha256: str

    def __post_init__(self) -> None:
        _digest(self.source_evidence_sha256)
        if type(self.document_json) is not str or len(self.document_json) > 32768:
            raise ValueError("Invalid canonical INR document")
        try:
            document = json.loads(self.document_json)
            day = date.fromisoformat(document["reporting_date"])
            # Only reuse the numeric validator; this metadata is never retained or ordered.
            noon = datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=12)
            rebuilt = build_fpi_observation(
                reporting_date=day,
                categories=document["categories"],
                total=document["total"],
                source_url=_LATEST,
                raw_sha256="0" * 64,
                parser_version="numeric-validation",
                retrieved_at=noon,
                first_seen_at=noon,
            )
        except (KeyError, TypeError, ValueError, RecursionError) as exc:
            raise ValueError("Invalid canonical INR document") from exc
        if rebuilt.document_json != self.document_json:
            raise ValueError("INR document is not canonical")

    @property
    def reporting_date(self) -> date:
        return date.fromisoformat(json.loads(self.document_json)["reporting_date"])

    @property
    def value_sha256(self) -> str:
        return hashlib.sha256(self.document_json.encode("ascii")).hexdigest()

    @property
    def net_hundredths_cr(self) -> int:
        value = json.loads(self.document_json)["total"]["net_cr"]
        return int(value.replace(".", ""))


@dataclass(frozen=True)
class FpiParseResult:
    """Whole parse result. Same capture/parser/definition must have one retained result."""

    capture: FpiCapture
    parser_sha256: str
    definition_version: str
    recorded_at: datetime
    days: tuple[FpiParsedDay, ...] = ()
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        validate_fpi_capture(self.capture)
        _digest(self.parser_sha256)
        _text(self.definition_version)
        _tuple(self.days)
        if len(self.days) > 31:
            raise ValueError("Parse date set exceeds 31 dates")
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at))
        capture = json.loads(self.capture.document_json)
        end = datetime.fromisoformat(capture["retrieved_at"])
        if self.recorded_at < end:
            raise ValueError("Parse cannot precede retrieval")
        if self.failure_reason is not None:
            _text(self.failure_reason)
            if self.days:
                raise ValueError("Failed parse cannot retain a partial date set")
        elif not self.days or capture["http_status"] != 200:
            raise ValueError("Successful parse requires dates and HTTP 200")
        if any(type(day) is not FpiParsedDay for day in self.days):
            raise ValueError("Expected complete parsed days")
        if self.days and self.definition_version != FPI_OBSERVATION_VERSION:
            raise ValueError("Parse definition does not match canonical INR documents")
        dates = [day.reporting_date for day in self.days]
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate reporting date in parse result")
        if any(day > end.astimezone(_IST).date() for day in dates):
            raise ValueError("Reporting date follows capture")
        object.__setattr__(
            self, "days", tuple(sorted(self.days, key=lambda day: day.reporting_date))
        )

    @property
    def parse_id(self) -> str:
        return _hash([self.capture.capture_sha256, self.parser_sha256, self.definition_version])

    def membership_id(self, day: FpiParsedDay) -> str:
        if day not in self.days:
            raise ValueError("Day is not a member of this parse")
        return _hash([self.parse_id, day.value_sha256, day.source_evidence_sha256])

    @property
    def content_sha256(self) -> str:
        return _hash(
            {
                "parse_id": self.parse_id,
                "recorded_at": self.recorded_at.isoformat(),
                "days": [asdict(day) for day in self.days],
                "failure_reason": self.failure_reason,
            }
        )


@dataclass(frozen=True)
class FpiQualificationEvent:
    scope: str
    target: str
    action: str
    recorded_at: datetime
    reason: str
    evidence_ref: str
    prior_event_id: str | None = None
    chosen_membership_id: str | None = None
    basis_membership_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.scope not in ("membership", "value", "parser", "date"):
            raise ValueError("Invalid qualification scope")
        _text(self.reason)
        _text(self.evidence_ref)
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at))
        _tuple(self.basis_membership_ids)
        if len(self.basis_membership_ids) > 4096:
            raise ValueError("Resolution basis exceeds 4096 memberships")
        if self.prior_event_id is not None:
            _digest(self.prior_event_id)
        if self.scope == "date":
            if (
                type(self.target) is not str
                or date.fromisoformat(self.target).isoformat() != self.target
                or self.action != "RESOLVE"
                or self.chosen_membership_id is None
            ):
                raise ValueError("Date events require an explicit resolution")
            _digest(self.chosen_membership_id)
            for member in self.basis_membership_ids:
                _digest(member)
            if (
                not self.basis_membership_ids
                or len(set(self.basis_membership_ids)) != len(self.basis_membership_ids)
                or self.chosen_membership_id not in self.basis_membership_ids
            ):
                raise ValueError("Resolution requires an exact candidate basis")
            object.__setattr__(
                self, "basis_membership_ids", tuple(sorted(self.basis_membership_ids))
            )
        else:
            _digest(self.target)
            if self.action not in ("ACCEPT", "WITHDRAW", "QUARANTINE"):
                raise ValueError("Invalid qualification action")
            if self.chosen_membership_id is not None or self.basis_membership_ids:
                raise ValueError("Only date resolution has chosen memberships")

    @property
    def event_id(self) -> str:
        payload = asdict(self)
        payload["recorded_at"] = self.recorded_at.isoformat()
        return _hash(payload)


@dataclass(frozen=True)
class FpiSelectionPolicy:
    parser_allowlist: tuple[str, ...]
    max_current_age_days: int
    max_history_age_days: int
    history_window: int
    minimum_history: int
    feature_version: str
    model_version: str
    prediction_horizon: str
    selector_sha256: str
    definition_allowlist: tuple[str, ...] = (FPI_OBSERVATION_VERSION,)
    source_rule: str = "AGREEMENT"
    source_rationale: str = "Neither endpoint establishes source finality"
    allow_withdrawal_fallback: bool = False
    selector_version: str = _SELECTOR
    age_timezone: str = "Asia/Kolkata"
    missingness: str = "MISSING"

    def __post_init__(self) -> None:
        _digest(self.selector_sha256)
        for field in ("parser_allowlist", "definition_allowlist"):
            values = getattr(self, field)
            _tuple(values)
            if not values or len(values) > 64 or len(values) != len(set(values)):
                raise ValueError("Allowlists must be nonempty unique tuples")
            for value in values:
                (_digest if field == "parser_allowlist" else _text)(value)
            object.__setattr__(self, field, tuple(sorted(values)))
        for value in (
            self.max_current_age_days,
            self.max_history_age_days,
            self.history_window,
            self.minimum_history,
        ):
            if type(value) is not int or not 0 <= value <= 100000:
                raise ValueError("Invalid age/window policy")
        if not 10 <= self.minimum_history <= self.history_window <= 2520:
            raise ValueError("History minimum/window out of range")
        if self.max_history_age_days < self.max_current_age_days:
            raise ValueError("History age must cover the current age allowance")
        for value in (
            self.feature_version,
            self.model_version,
            self.prediction_horizon,
            self.source_rationale,
        ):
            _text(value)
        if self.source_rule not in ("AGREEMENT", "LATEST", "MONTHLY"):
            raise ValueError("Invalid endpoint policy")
        if type(self.allow_withdrawal_fallback) is not bool:
            raise ValueError("Withdrawal fallback must be explicit boolean")
        if (
            self.selector_version != _SELECTOR
            or self.age_timezone != "Asia/Kolkata"
            or self.missingness != "MISSING"
        ):
            raise ValueError("Unsupported selector semantics")

    @property
    def policy_sha256(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class FpiDecisionSnapshot:
    """Exact supplied read set, not proof of visibility, authenticity or external completeness."""

    decision_id: str
    decision_at: datetime
    policy_sha256: str
    parses: tuple[FpiParseResult, ...]
    events: tuple[FpiQualificationEvent, ...]
    ordered_capture_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.decision_id)
        _digest(self.policy_sha256)
        object.__setattr__(self, "decision_at", _utc(self.decision_at))
        for values in (self.parses, self.events, self.ordered_capture_ids):
            _tuple(values)
        if (
            len(self.parses) > 2048
            or len(self.events) > 20000
            or len(self.ordered_capture_ids) > 2048
        ):
            raise ValueError("Snapshot exceeds bounded record counts")
        parses: dict[str, FpiParseResult] = {}
        for parse in self.parses:
            if type(parse) is not FpiParseResult or parse.recorded_at > self.decision_at:
                raise ValueError("Invalid/future parse in snapshot")
            if parse.parse_id in parses and parses[parse.parse_id] != parse:
                raise ValueError("Contradictory output under one parser/capture identity")
            parses[parse.parse_id] = parse
        object.__setattr__(self, "parses", tuple(parses[key] for key in sorted(parses)))
        if sum(len(parse.capture.document_json) for parse in self.parses) > 64_000_000:
            raise ValueError("Snapshot exceeds 64000000 capture-document characters")
        events: dict[str, FpiQualificationEvent] = {}
        for event in self.events:
            if type(event) is not FpiQualificationEvent or event.recorded_at > self.decision_at:
                raise ValueError("Invalid/future event in snapshot")
            events[event.event_id] = event
        object.__setattr__(self, "events", tuple(events[key] for key in sorted(events)))
        captures = {parse.capture.capture_sha256 for parse in self.parses}
        for capture_id in self.ordered_capture_ids:
            _digest(capture_id)
            if capture_id not in captures:
                raise ValueError("Ordered capture is outside snapshot")
        object.__setattr__(
            self, "ordered_capture_ids", tuple(sorted(set(self.ordered_capture_ids)))
        )
        members = _members(self)
        if len(members) > 20000:
            raise ValueError("Snapshot exceeds 20000 memberships")
        targets: dict[str, set[str]] = {
            "membership": set(members),
            "value": {day.value_sha256 for _, day in members.values()},
            "parser": {parse.parser_sha256 for parse in self.parses},
            "date": {day.reporting_date.isoformat() for _, day in members.values()},
        }
        successors: set[tuple[str, str, str | None]] = set()
        for event in self.events:
            if event.target not in targets[event.scope]:
                raise ValueError("Qualification target is outside snapshot")
            key = (event.scope, event.target, event.prior_event_id)
            if key in successors:
                raise ValueError("Qualification transition conflict: same predecessor")
            successors.add(key)
            if event.prior_event_id is not None:
                prior = events.get(event.prior_event_id)
                if (
                    prior is None
                    or (prior.scope, prior.target) != (event.scope, event.target)
                    or prior.recorded_at > event.recorded_at
                ):
                    raise ValueError("Missing, unrelated or future qualification predecessor")
            if event.scope == "membership":
                if event.recorded_at < members[event.target][0].recorded_at:
                    raise ValueError("Qualification precedes parse")
            elif event.scope == "date":
                for member_id in event.basis_membership_ids:
                    if (
                        member_id not in members
                        or members[member_id][1].reporting_date.isoformat() != event.target
                        or members[member_id][0].recorded_at > event.recorded_at
                    ):
                        raise ValueError("Resolution has invalid candidate basis")
        # Memoized predecessor depths validate every chain in linear work.
        depths: dict[str, int] = {}
        for event_id in events:
            path: list[str] = []
            visited: set[str] = set()
            cursor_id: str | None = event_id
            while cursor_id is not None and cursor_id not in depths:
                if cursor_id in visited:
                    raise ValueError("Qualification cycle")
                visited.add(cursor_id)
                path.append(cursor_id)
                cursor_id = events[cursor_id].prior_event_id
            depth = depths[cursor_id] if cursor_id is not None else -1
            for item in reversed(path):
                depth += 1
                depths[item] = depth
        historical_heads: dict[tuple[str, str], FpiQualificationEvent] = {}
        for event_id, event in sorted(
            events.items(),
            key=lambda pair: (pair[1].recorded_at, pair[1].scope == "date", depths[pair[0]]),
        ):
            if event.scope == "date":
                chosen = event.chosen_membership_id
                assert chosen is not None
                parse, value = members[chosen]
                relevant = [
                    historical_heads.get(key)
                    for key in (
                        ("membership", chosen),
                        ("value", value.value_sha256),
                        ("parser", parse.parser_sha256),
                    )
                ]
                if (
                    relevant[0] is None
                    or relevant[0].action != "ACCEPT"
                    or any(item is not None and item.action != "ACCEPT" for item in relevant)
                ):
                    raise ValueError("Resolution target was not qualified at resolution time")
            historical_heads[(event.scope, event.target)] = event

    @property
    def input_set_sha256(self) -> str:
        return _hash(
            {
                "parses": [(p.parse_id, p.content_sha256) for p in self.parses],
                "events": [e.event_id for e in self.events],
                "ordered_capture_ids": self.ordered_capture_ids,
            }
        )

    @property
    def snapshot_sha256(self) -> str:
        return _hash(
            [
                "fpi-snapshot-v1",
                self.decision_id,
                self.decision_at.isoformat(),
                self.policy_sha256,
                self.input_set_sha256,
            ]
        )


@dataclass(frozen=True)
class FpiSelectedDate:
    reporting_date: date
    status: str
    value_sha256: str | None
    net_hundredths_cr: int | None
    membership_ids: tuple[str, ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class FpiSelection:
    status: str
    snapshot_sha256: str | None
    input_set_sha256: str | None
    policy_sha256: str
    current: FpiSelectedDate | None
    history: tuple[FpiSelectedDate, ...]
    excluded_dates: tuple[FpiSelectedDate, ...]
    parse_diagnostics: tuple[tuple[str, str], ...]
    selection_sha256: str


def _members(snapshot: FpiDecisionSnapshot) -> dict[str, tuple[FpiParseResult, FpiParsedDay]]:
    return {
        parse.membership_id(day): (parse, day) for parse in snapshot.parses for day in parse.days
    }


def _heads(snapshot: FpiDecisionSnapshot) -> dict[tuple[str, str], FpiQualificationEvent]:
    prior_ids = {event.prior_event_id for event in snapshot.events}
    return {(e.scope, e.target): e for e in snapshot.events if e.event_id not in prior_ids}


def _member_state(
    member_id: str,
    parse: FpiParseResult,
    day: FpiParsedDay,
    heads: dict[tuple[str, str], FpiQualificationEvent],
    policy: FpiSelectionPolicy,
) -> str:
    if (
        parse.parser_sha256 not in policy.parser_allowlist
        or parse.definition_version not in policy.definition_allowlist
    ):
        return "POLICY_EXCLUDED"
    events = [
        heads.get((scope, target))
        for scope, target in (
            ("membership", member_id),
            ("value", day.value_sha256),
            ("parser", parse.parser_sha256),
        )
    ]
    if any(event is not None and event.action == "WITHDRAW" for event in events):
        return "WITHDRAWN"
    if any(event is not None and event.action == "QUARANTINE" for event in events):
        return "QUARANTINED"
    return "AVAILABLE" if events[0] is not None and events[0].action == "ACCEPT" else "UNQUALIFIED"


def _resolved(day: date, entries: list[tuple[str, FpiParsedDay]], *reasons: str) -> FpiSelectedDate:
    values = {value.value_sha256 for _, value in entries}
    if len(values) != 1:
        return FpiSelectedDate(day, "CONFLICT", None, None, (), ("DIFFERENT_VALUES",))
    return FpiSelectedDate(
        day,
        "AVAILABLE",
        entries[0][1].value_sha256,
        entries[0][1].net_hundredths_cr,
        tuple(sorted(member for member, _ in entries)),
        tuple(sorted(reasons)),
    )


def _select_date(
    day: date,
    members: dict[str, tuple[FpiParseResult, FpiParsedDay]],
    snapshot: FpiDecisionSnapshot,
    policy: FpiSelectionPolicy,
    heads: dict[tuple[str, str], FpiQualificationEvent],
    metadata: dict[str, tuple[str, datetime, datetime]],
) -> FpiSelectedDate:
    states = {
        member: _member_state(member, parse, value, heads, policy)
        for member, (parse, value) in members.items()
    }
    resolution = heads.get(("date", day.isoformat()))
    if resolution is not None:
        if set(resolution.basis_membership_ids) != set(members):
            return FpiSelectedDate(day, "CONFLICT", None, None, (), ("STALE_RESOLUTION",))
        chosen = resolution.chosen_membership_id
        assert chosen is not None
        if states[chosen] != "AVAILABLE":
            return FpiSelectedDate(
                day, states[chosen], None, None, (), ("RESOLUTION_TARGET_UNAVAILABLE",)
            )
        return _resolved(day, [(chosen, members[chosen][1])], "EXPLICIT_RESOLUTION")
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for member, (parse, _) in members.items():
        capture_id = parse.capture.capture_sha256
        grouped[metadata[capture_id][0]][capture_id].append(member)
    endpoints: dict[str, FpiSelectedDate] = {}
    ordered = set(snapshot.ordered_capture_ids)
    for source, captures in grouped.items():
        capture_states: dict[str, FpiSelectedDate] = {}
        for capture_id, ids in captures.items():
            accepted = [
                (member, members[member][1]) for member in ids if states[member] == "AVAILABLE"
            ]
            if accepted:
                capture_states[capture_id] = _resolved(day, accepted)
            else:
                status = next(
                    (
                        state
                        for state in ("WITHDRAWN", "QUARANTINED", "POLICY_EXCLUDED")
                        if state in {states[member] for member in ids}
                    ),
                    "UNQUALIFIED",
                )
                capture_states[capture_id] = FpiSelectedDate(day, status, None, None, (), (status,))
        fallback = False
        if policy.allow_withdrawal_fallback:
            kept = {
                key: state
                for key, state in capture_states.items()
                if state.status not in ("WITHDRAWN", "QUARANTINED")
            }
            fallback = len(kept) != len(capture_states)
            if kept:
                capture_states = kept
        latest_start = max(
            (metadata[key][1] for key in capture_states if key in ordered), default=None
        )
        frontier = [
            key
            for key in capture_states
            if key not in ordered or latest_start is None or metadata[key][2] >= latest_start
        ]
        results = [capture_states[key] for key in frontier]
        bad = [result for result in results if result.status != "AVAILABLE"]
        if bad:
            status = bad[0].status if len({result.status for result in bad}) == 1 else "CONFLICT"
            endpoints[source] = FpiSelectedDate(
                day,
                status,
                None,
                None,
                (),
                tuple(sorted({r for result in bad for r in result.reasons})),
            )
        else:
            ids = [member for result in results for member in result.membership_ids]
            endpoints[source] = _resolved(
                day,
                [(member, members[member][1]) for member in ids],
                *(("POLICY_WITHDRAWAL_FALLBACK",) if fallback else ()),
            )
    priority = {"LATEST": _LATEST, "MONTHLY": _MONTHLY}.get(policy.source_rule)
    if priority is not None and priority in endpoints:
        result = endpoints[priority]
        return FpiSelectedDate(
            day,
            result.status,
            result.value_sha256,
            result.net_hundredths_cr,
            result.membership_ids,
            tuple(sorted((*result.reasons, "POLICY_SOURCE_PRIORITY"))),
        )
    results = list(endpoints.values())
    if any(result.status != "AVAILABLE" for result in results):
        bad = [result for result in results if result.status != "AVAILABLE"]
        status = bad[0].status if len({result.status for result in bad}) == 1 else "CONFLICT"
        return FpiSelectedDate(
            day,
            status,
            None,
            None,
            (),
            tuple(sorted({reason for result in bad for reason in result.reasons})),
        )
    ids = [member for result in results for member in result.membership_ids]
    return _resolved(
        day,
        [(member, members[member][1]) for member in ids],
        *sorted({reason for result in results for reason in result.reasons}),
    )


def select_fpi(snapshot: FpiDecisionSnapshot | None, policy: FpiSelectionPolicy) -> FpiSelection:
    """Select only the supplied snapshot; never infer historical read membership from a clock."""
    if type(policy) is not FpiSelectionPolicy:
        raise ValueError("Expected frozen selection policy")
    if snapshot is not None and type(snapshot) is not FpiDecisionSnapshot:
        raise ValueError("Expected decision snapshot, not timestamp cutoff")
    current: FpiSelectedDate | None = None
    history: tuple[FpiSelectedDate, ...] = ()
    exclusions: list[FpiSelectedDate] = []
    diagnostics: tuple[tuple[str, str], ...] = ()
    status = "VISIBILITY_UNPROVEN"
    if snapshot is not None:
        if snapshot.policy_sha256 != policy.policy_sha256:
            raise ValueError("Snapshot belongs to a different frozen policy")
        by_date: dict[date, dict[str, tuple[FpiParseResult, FpiParsedDay]]] = defaultdict(dict)
        for member, pair in _members(snapshot).items():
            by_date[pair[1].reporting_date][member] = pair
        heads = _heads(snapshot)
        metadata: dict[str, tuple[str, datetime, datetime]] = {}
        for parse in snapshot.parses:
            capture_id = parse.capture.capture_sha256
            if capture_id not in metadata:
                document = json.loads(parse.capture.document_json)
                metadata[capture_id] = (
                    document["source_url"],
                    datetime.fromisoformat(document["requested_at"]),
                    datetime.fromisoformat(document["retrieved_at"]),
                )
        dates = [
            _select_date(day, by_date[day], snapshot, policy, heads, metadata)
            for day in sorted(by_date)
        ]
        diagnostics = tuple(
            (p.parse_id, p.failure_reason) for p in snapshot.parses if p.failure_reason is not None
        )
        status = "NO_OBSERVATIONS"
        if dates:
            latest = dates[-1]
            today = snapshot.decision_at.astimezone(_IST).date()
            status = latest.status
            if (
                latest.status == "AVAILABLE"
                and (today - latest.reporting_date).days > policy.max_current_age_days
            ):
                latest = FpiSelectedDate(
                    latest.reporting_date, "STALE", None, None, (), ("CURRENT_AGE",)
                )
                status = "STALE"
            if latest.status != "AVAILABLE":
                exclusions = [
                    FpiSelectedDate(
                        item.reporting_date,
                        "CURRENT_UNAVAILABLE",
                        None,
                        None,
                        (),
                        ("NEWEST_DATE_UNAVAILABLE",),
                    )
                    if item.status == "AVAILABLE"
                    else item
                    for item in dates[:-1]
                ]
                exclusions.append(latest)
            else:
                current = latest
                eligible: list[FpiSelectedDate] = []
                for item in dates[:-1]:
                    if item.status != "AVAILABLE":
                        exclusions.append(item)
                    elif (today - item.reporting_date).days > policy.max_history_age_days:
                        exclusions.append(
                            FpiSelectedDate(
                                item.reporting_date, "STALE", None, None, (), ("HISTORY_AGE",)
                            )
                        )
                    else:
                        eligible.append(item)
                for item in eligible[: -policy.history_window]:
                    exclusions.append(
                        FpiSelectedDate(
                            item.reporting_date,
                            "OUTSIDE_WINDOW",
                            None,
                            None,
                            (),
                            ("HISTORY_WINDOW",),
                        )
                    )
                history = tuple(eligible[-policy.history_window :])
                status = (
                    "AVAILABLE"
                    if len(history) >= policy.minimum_history
                    else "INSUFFICIENT_HISTORY"
                )
    excluded = tuple(sorted(exclusions, key=lambda item: item.reporting_date))
    result = FpiSelection(
        status,
        snapshot.snapshot_sha256 if snapshot else None,
        snapshot.input_set_sha256 if snapshot else None,
        policy.policy_sha256,
        current,
        history,
        excluded,
        diagnostics,
        "",
    )
    content = asdict(result)
    del content["selection_sha256"]
    return replace(result, selection_sha256=_hash(content))
