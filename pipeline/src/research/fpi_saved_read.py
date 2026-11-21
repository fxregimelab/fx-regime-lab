"""Pure retained administrative evidence; consistency never grants execution authority."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, fields
from datetime import UTC, date, datetime, timedelta
from typing import Any, TypeVar
from uuid import UUID

from src.research.fpi_capture import FpiCapture
from src.research.fpi_parse_record import (
    FpiArtifact,
    FpiParseRecord,
    build_fpi_read_references,
    validate_fpi_artifact,
)
from src.research.fpi_qualification import (
    FpiQualificationHead,
    FpiQualificationMember,
    FpiQualificationView,
    decode_fpi_qualification_event,
)

_ERROR = "READ_INTEGRITY_ERROR"
_LIMITS = {
    "CANDIDATES": 20_000,
    "PARSES": 2048,
    "CAPTURES": 2048,
    "SUPPORT_MEMBERSHIPS": 20_000,
    "ARTIFACTS": 2113,
    "HEADS": 100_000,
    "EVENTS": 100_000,
    "ORIGINAL_BYTES": 64_000_000,
    "REFERENCE_BYTES": 16_000_000,
    "QUALIFICATION_BYTES": 16_000_000,
    "MANIFEST_BYTES": 16_000_000,
}
_POLICY_FIELDS = set(
    "version scope_version guardrail_version trust_mode selector_version selector_sha256 "
    "parser_allowlist definition_allowlist max_current_age_days max_history_age_days "
    "minimum_history history_window diagnostic_window_days feature_version model_version "
    "prediction_horizon source_rule source_rationale allow_withdrawal_fallback age_timezone "
    "missingness".split()
)
_REQUEST_FIELDS = set(
    "version decision_id run_id prediction_id model_sha256 pair mode policy_sha256".split()
)
_MANIFEST_FIELDS = set(
    "version read_id request_sha256 request policy_sha256 policy read_at scope status failure "
    "data execution_state acquisition_state eligible feature".split()
)
_STATUSES = {"COMPLETE", "READ_SCOPE_EXCEEDED", "CLOCK_INCONSISTENT"}
_SOURCES = {
    "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
    "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
}
_MIN_TIME = datetime.min.replace(tzinfo=UTC)
_INDIA_OFFSET = timedelta(hours=5, minutes=30)
_T = TypeVar("_T", "FpiAdminReadPolicy", "FpiAdminReadRequest", "FpiAdminReadManifest")


def _sr_canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def _sr_sha(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _sr_keys(value: Any, expected: set[str]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or any(type(key) is not str for key in value)
        or set(value) != expected
    ):
        raise ValueError(_ERROR)
    return value


def _sr_digest(value: Any) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(_ERROR)
    return value


def _sr_int(value: Any, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(_ERROR)
    return value


def _sr_time(value: Any, *, original: bool = False, transport: bool = False) -> datetime:
    ending = r"(?:Z|\+00:00)" if transport else r"\+00:00"
    fraction = r"(?:\.[0-9]{1,6})?" if original or transport else r"(?:\.[0-9]{6})?"
    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}" + fraction + ending
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise ValueError(_ERROR)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(_ERROR) from None
    if parsed.tzinfo != UTC or not (original or transport) and parsed.isoformat() != value:
        raise ValueError(_ERROR)
    return parsed


def _sr_date(value: Any) -> date:
    if type(value) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError(_ERROR)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(_ERROR) from None


def _sr_text_preflight(text: Any, maximum: int) -> str:
    # Scan before the recursive JSON decoder, including for original document inputs.
    if type(text) is not str or len(text) > maximum or not text.isascii() or "\x00" in text:
        raise ValueError(_ERROR)
    depth = 0
    quoted = escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char in "[{":
                depth += 1
                if depth > 32:
                    raise ValueError(_ERROR)
            elif char in "]}":
                depth -= 1
                if depth < 0:
                    raise ValueError(_ERROR)
    if quoted or depth:
        raise ValueError(_ERROR)
    return text


def _sr_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(_ERROR)
        result[key] = value
    return result


def _sr_invalid_constant(value: str) -> Any:
    raise ValueError(_ERROR)


def _sr_load(text: str, maximum: int) -> dict[str, Any]:
    _sr_text_preflight(text, maximum)
    try:
        value = json.loads(text, object_pairs_hook=_sr_pairs, parse_constant=_sr_invalid_constant)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is str:
                if not item.isascii() or "\x00" in item:
                    raise ValueError(_ERROR)
            elif type(item) is dict:
                pending.extend(item.keys())
                pending.extend(item.values())
            elif type(item) is list:
                pending.extend(item)
            elif item is not None and type(item) not in (bool, int):
                raise ValueError(_ERROR)
        if type(value) is not dict or _sr_canonical(value) != text:
            raise ValueError(_ERROR)
    except (ValueError, RecursionError):
        raise ValueError(_ERROR) from None
    return value


def _sr_policy(document: dict[str, Any]) -> None:
    _sr_keys(document, _POLICY_FIELDS)
    constants = {
        "version": "fpi-admin-read-policy-v1",
        "scope_version": "fpi-admin-scope-v1",
        "guardrail_version": "fpi-admin-read-limits-v1",
        "trust_mode": "ADMINISTRATIVE_UNVERIFIED",
        "selector_version": "NOT_EXECUTED",
        "age_timezone": "Asia/Kolkata",
        "missingness": "MISSING",
    }
    if any(document[key] != value for key, value in constants.items()):
        raise ValueError(_ERROR)
    _sr_digest(document["selector_sha256"])
    parsers = document["parser_allowlist"]
    if type(parsers) is not list or not 1 <= len(parsers) <= 64:
        raise ValueError(_ERROR)
    if [_sr_digest(item) for item in parsers] != sorted(set(parsers)):
        raise ValueError(_ERROR)
    if document["definition_allowlist"] != ["fpi-inr-observation-v1"]:
        raise ValueError(_ERROR)
    current = _sr_int(document["max_current_age_days"], 0, 100_000)
    _sr_int(document["max_history_age_days"], current, 100_000)
    minimum = _sr_int(document["minimum_history"], 10, 2520)
    _sr_int(document["history_window"], minimum, 2520)
    _sr_int(document["diagnostic_window_days"], 7, 7)
    for key in ("feature_version", "model_version", "prediction_horizon"):
        if (
            type(document[key]) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", document[key]) is None
        ):
            raise ValueError(_ERROR)
    if (
        type(document["source_rule"]) is not str
        or document["source_rule"] not in {"AGREEMENT", "LATEST", "MONTHLY"}
        or type(document["source_rationale"]) is not str
        or re.fullmatch(r"[\x20-\x7e]{1,1024}", document["source_rationale"]) is None
        or type(document["allow_withdrawal_fallback"]) is not bool
    ):
        raise ValueError(_ERROR)


@dataclass(frozen=True)
class FpiAdminReadPolicy:
    document_json: str
    policy_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _sr_policy(_sr_load(self.document_json, 32_768))
        object.__setattr__(self, "policy_sha256", _sr_sha(self.document_json))


def _sr_request(document: dict[str, Any]) -> None:
    _sr_keys(document, _REQUEST_FIELDS)
    if (
        document["version"] != "fpi-admin-read-request-v1"
        or document["pair"] != "USDINR"
        or document["mode"] != "ADMIN_EVIDENCE_READ"
    ):
        raise ValueError(_ERROR)
    for key in ("decision_id", "run_id"):
        value = document[key]
        if type(value) is not str or len(value) != 36:
            raise ValueError(_ERROR)
        try:
            uuid = UUID(value)
        except ValueError:
            raise ValueError(_ERROR) from None
        if uuid.version != 4 or str(uuid) != value:
            raise ValueError(_ERROR)
    for key in ("prediction_id", "model_sha256", "policy_sha256"):
        _sr_digest(document[key])


@dataclass(frozen=True)
class FpiAdminReadRequest:
    document_json: str
    request_sha256: str = field(init=False)
    read_id: str = field(init=False)
    decision_id: str = field(init=False)

    def __post_init__(self) -> None:
        document = _sr_load(self.document_json, 4096)
        _sr_request(document)
        identity = _sr_sha(self.document_json)
        object.__setattr__(self, "request_sha256", identity)
        object.__setattr__(self, "read_id", identity)
        object.__setattr__(self, "decision_id", document["decision_id"])


def _sr_scope(value: Any, policy: dict[str, Any], read_at: datetime) -> dict[str, Any]:
    scope = _sr_keys(
        value,
        set(
            "version india_date history_start_date history_start_clamped "
            "diagnostic_start_at diagnostic_start_clamped "
            "newest_reporting_date".split()
        ),
    )
    try:
        india_date = (read_at + _INDIA_OFFSET).date()
    except OverflowError:
        raise ValueError(_ERROR) from None
    history_ordinal = india_date.toordinal() - policy["max_history_age_days"]
    diagnostic_clamped = read_at - _MIN_TIME < timedelta(days=7)
    diagnostic = _MIN_TIME if diagnostic_clamped else read_at - timedelta(days=7)
    if (
        scope["version"] != "fpi-admin-scope-v1"
        or scope["india_date"] != india_date.isoformat()
        or scope["history_start_date"] != date.fromordinal(max(1, history_ordinal)).isoformat()
        or scope["history_start_clamped"] is not (history_ordinal < 1)
        or scope["diagnostic_start_at"] != diagnostic.isoformat()
        or scope["diagnostic_start_clamped"] is not diagnostic_clamped
    ):
        raise ValueError(_ERROR)
    if scope["newest_reporting_date"] is not None:
        _sr_date(scope["newest_reporting_date"])
    return scope


def _sr_failure(document: dict[str, Any], read_at: datetime) -> None:
    failure = _sr_keys(
        document["failure"], set("code dimension limit observed measurement witness".split())
    )
    if document["data"] is not None or failure["code"] != document["status"]:
        raise ValueError(_ERROR)
    dimension = failure["dimension"]
    if type(dimension) is not str:
        raise ValueError(_ERROR)
    scope = document["scope"]
    newest = scope["newest_reporting_date"]
    if document["status"] == "READ_SCOPE_EXCEEDED":
        if dimension not in _LIMITS or newest is not None and newest > scope["india_date"]:
            raise ValueError(_ERROR)
        limit = _LIMITS[dimension]
        _sr_int(failure["limit"], limit, limit)
        _sr_int(failure["observed"], limit + 1, 2**63 - 1)
        if failure["measurement"] not in ("EXACT", "AT_LEAST") or failure["witness"] is not None:
            raise ValueError(_ERROR)
        if failure["measurement"] == "AT_LEAST" and dimension != "QUALIFICATION_BYTES":
            if failure["observed"] != limit + 1:
                raise ValueError(_ERROR)
        return
    if any(failure[key] is not None for key in ("limit", "observed", "measurement")):
        raise ValueError(_ERROR)
    witness = _sr_keys(failure["witness"], {"kind", "id", "field", "value"})
    kind, identity, name, value = (witness[key] for key in ("kind", "id", "field", "value"))
    if dimension == "NEWEST_DATE":
        _sr_date(value)
        if (
            kind != "MEMBERSHIP_DATE"
            or identity is not None
            or name != "reporting_date"
            or value != newest
            or value <= scope["india_date"]
        ):
            raise ValueError(_ERROR)
        return
    if newest is not None and newest > scope["india_date"]:
        raise ValueError(_ERROR)
    _sr_digest(identity)
    allowed = {
        "CAPTURE": {"requested_at", "retrieved_at", "stored_at"},
        "PARSE": {"recorded_at", "stored_at"},
        "ARTIFACT": {"stored_at"},
        "EVENT": {"recorded_at"},
    }
    if (
        type(kind) is not str
        or kind not in allowed
        or type(name) is not str
        or name not in allowed[kind]
    ):
        raise ValueError(_ERROR)
    instant = _sr_time(value, original=kind == "PARSE" and name == "recorded_at")
    if dimension == "FUTURE_FAILURE_STORAGE":
        if kind != "PARSE" or name != "stored_at" or instant <= read_at:
            raise ValueError(_ERROR)
    elif dimension == "REFERENCED_TIME":
        if instant <= read_at:
            raise ValueError(_ERROR)
        if (
            kind == "CAPTURE"
            and name == "retrieved_at"
            or kind == "PARSE"
            and name == "recorded_at"
        ):
            try:
                instant + _INDIA_OFFSET
            except OverflowError:
                raise ValueError(_ERROR) from None
    elif dimension == "INDIA_TIME_RANGE":
        if not (
            kind == "CAPTURE"
            and name == "retrieved_at"
            or kind == "PARSE"
            and name == "recorded_at"
        ):
            raise ValueError(_ERROR)
        try:
            instant + _INDIA_OFFSET
        except OverflowError:
            return
        raise ValueError(_ERROR)
    else:
        raise ValueError(_ERROR)


def _sr_sorted_rows(
    value: Any, keys: set[str], order: tuple[str, ...], maximum: int
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) > maximum:
        raise ValueError(_ERROR)
    rows = [_sr_keys(row, keys) for row in value]
    identifiers: list[tuple[str, ...]] = []
    for row in rows:
        if any(type(row[key]) is not str for key in order):
            raise ValueError(_ERROR)
        identifiers.append(tuple(row[key] for key in order))
    if identifiers != sorted(set(identifiers)):
        raise ValueError(_ERROR)
    return rows


def _sr_set(value: Any, maximum: int, *, dates: bool = False) -> list[str]:
    if type(value) is not list or len(value) > maximum:
        raise ValueError(_ERROR)
    for item in value:
        if dates:
            _sr_date(item)
        else:
            _sr_digest(item)
    if value != sorted(set(value)):
        raise ValueError(_ERROR)
    return value


def _sr_references(
    data: dict[str, Any], read_at: datetime
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    refs = _sr_keys(data["references"], {"version", "captures", "parses"})
    if refs["version"] != "fpi-read-references-v1":
        raise ValueError(_ERROR)
    text = _sr_canonical(refs)
    if len(text) > _LIMITS["REFERENCE_BYTES"] or _sr_digest(data["reference_sha256"]) != _sr_sha(
        text
    ):
        raise ValueError(_ERROR)
    capture_rows = _sr_sorted_rows(
        refs["captures"],
        set(
            "capture_sha256 document_size source_url requested_at retrieved_at http_status "
            "body_size raw_sha256".split()
        ),
        ("capture_sha256",),
        _LIMITS["CAPTURES"],
    )
    captures: dict[str, dict[str, Any]] = {}
    for row in capture_rows:
        identity = _sr_digest(row["capture_sha256"])
        _sr_digest(row["raw_sha256"])
        _sr_int(row["document_size"], 1, 7_000_000)
        _sr_int(row["body_size"], 0, 5_000_000)
        _sr_int(row["http_status"], 100, 599)
        envelope = {
            key: row[key]
            for key in (
                "source_url",
                "requested_at",
                "retrieved_at",
                "http_status",
                "body_size",
                "raw_sha256",
            )
        }
        envelope.update(version="fpi-http-capture-v1", body_base64="")
        if row["document_size"] != len(_sr_canonical(envelope)) + 4 * ((row["body_size"] + 2) // 3):
            raise ValueError(_ERROR)
        if type(row["source_url"]) is not str or row["source_url"] not in _SOURCES:
            raise ValueError(_ERROR)
        requested, retrieved = _sr_time(row["requested_at"]), _sr_time(row["retrieved_at"])
        if not requested <= retrieved <= read_at:
            raise ValueError(_ERROR)
        captures[identity] = row
    parse_rows = _sr_sorted_rows(
        refs["parses"],
        set(
            "parse_id record_sha256 document_size content_sha256 capture_sha256 parser_sha256 "
            "definition_version recorded_at failure_reason memberships".split()
        ),
        ("parse_id",),
        _LIMITS["PARSES"],
    )
    parses: dict[str, dict[str, Any]] = {}
    members: dict[str, dict[str, Any]] = {}
    used_captures: set[str] = set()
    value_dates: dict[str, str] = {}
    for row in parse_rows:
        for key in (
            "parse_id",
            "record_sha256",
            "content_sha256",
            "capture_sha256",
            "parser_sha256",
        ):
            _sr_digest(row[key])
        _sr_int(row["document_size"], 1, 4_000_000)
        if row["definition_version"] != "fpi-inr-observation-v1":
            raise ValueError(_ERROR)
        if (
            row["parse_id"]
            != _sr_sha(
                _sr_canonical(
                    [row["capture_sha256"], row["parser_sha256"], row["definition_version"]]
                )
            )
            or row["capture_sha256"] not in captures
        ):
            raise ValueError(_ERROR)
        capture = captures[row["capture_sha256"]]
        used_captures.add(row["capture_sha256"])
        recorded = _sr_time(row["recorded_at"], original=True)
        retrieved = _sr_time(capture["retrieved_at"])
        try:
            recorded + _INDIA_OFFSET
            receipt_date = (retrieved + _INDIA_OFFSET).date()
        except OverflowError:
            raise ValueError(_ERROR) from None
        if not retrieved <= recorded <= read_at:
            raise ValueError(_ERROR)
        rows = _sr_sorted_rows(
            row["memberships"],
            {"reporting_date", "value_sha256", "membership_id", "source_evidence_sha256"},
            ("reporting_date",),
            31,
        )
        failure = row["failure_reason"]
        if failure is not None and (
            type(failure) is not str or re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", failure) is None
        ):
            raise ValueError(_ERROR)
        if (failure is None) != bool(rows) or failure is None and capture["http_status"] != 200:
            raise ValueError(_ERROR)
        for member in rows:
            if _sr_date(member["reporting_date"]) > receipt_date:
                raise ValueError(_ERROR)
            for key in ("membership_id", "value_sha256", "source_evidence_sha256"):
                _sr_digest(member[key])
            identity = member["membership_id"]
            if (
                identity
                != _sr_sha(
                    _sr_canonical(
                        [row["parse_id"], member["value_sha256"], member["source_evidence_sha256"]]
                    )
                )
                or identity in members
            ):
                raise ValueError(_ERROR)
            if (
                value_dates.setdefault(member["value_sha256"], member["reporting_date"])
                != member["reporting_date"]
            ):
                raise ValueError(_ERROR)
            members[identity] = {
                **member,
                "parse_id": row["parse_id"],
                "parser_sha256": row["parser_sha256"],
            }
            if len(members) > _LIMITS["SUPPORT_MEMBERSHIPS"]:
                raise ValueError(_ERROR)
        parses[row["parse_id"]] = row
    if used_captures != set(captures):
        raise ValueError(_ERROR)
    return captures, parses, members


def _sr_qualification(
    data: dict[str, Any],
    candidates: list[str],
    members: dict[str, dict[str, Any]],
    read_at: datetime,
) -> None:
    qualification = _sr_keys(data["qualification"], {"version", "members", "heads", "events"})
    if qualification["version"] != "fpi-qualification-view-v2":
        raise ValueError(_ERROR)
    text = _sr_canonical(qualification)
    if len(text) > _LIMITS["QUALIFICATION_BYTES"] or _sr_digest(
        data["qualification_sha256"]
    ) != _sr_sha(text):
        raise ValueError(_ERROR)
    expected_members = [
        {
            key: members[identity][key]
            for key in ("membership_id", "value_sha256", "parser_sha256", "reporting_date")
        }
        for identity in candidates
    ]
    if qualification["members"] != expected_members:
        raise ValueError(_ERROR)
    heads = _sr_sorted_rows(
        qualification["heads"],
        {"scope", "target", "event_id"},
        ("scope", "target"),
        _LIMITS["HEADS"],
    )
    event_documents = qualification["events"]
    if type(event_documents) is not list or len(event_documents) > _LIMITS["EVENTS"]:
        raise ValueError(_ERROR)
    events = []
    for document in event_documents:
        event_text = _sr_canonical(document)
        if len(event_text) > 400_000:
            raise ValueError(_ERROR)
        event = decode_fpi_qualification_event(event_text)
        if event.recorded_at > read_at:
            raise ValueError(_ERROR)
        events.append(event)
    if [event.event_id for event in events] != sorted({event.event_id for event in events}):
        raise ValueError(_ERROR)
    view = FpiQualificationView(
        members=tuple(
            FpiQualificationMember(
                item["membership_id"],
                item["value_sha256"],
                item["parser_sha256"],
                _sr_date(item["reporting_date"]),
            )
            for item in expected_members
        ),
        heads=tuple(FpiQualificationHead(**head) for head in heads),
        events=tuple(events),
    )
    if view.view_sha256 != data["qualification_sha256"]:
        raise ValueError(_ERROR)


def _sr_complete(document: dict[str, Any], read_at: datetime) -> None:
    if document["failure"] is not None:
        raise ValueError(_ERROR)
    data = _sr_keys(
        document["data"],
        set(
            "candidate_membership_ids candidate_dates "
            "diagnostic_parse_ids references reference_sha256 storage_times artifacts "
            "qualification qualification_sha256".split()
        ),
    )
    candidates = _sr_set(data["candidate_membership_ids"], _LIMITS["CANDIDATES"])
    dates = _sr_set(data["candidate_dates"], _LIMITS["CANDIDATES"], dates=True)
    diagnostics = _sr_set(data["diagnostic_parse_ids"], _LIMITS["PARSES"])
    captures, parses, members = _sr_references(data, read_at)
    scope = document["scope"]
    newest = scope["newest_reporting_date"]
    if newest is not None and newest > scope["india_date"]:
        raise ValueError(_ERROR)
    scoped = sorted(
        identity
        for identity, row in members.items()
        if scope["history_start_date"] <= row["reporting_date"] <= scope["india_date"]
        or row["reporting_date"] == newest
    )
    if candidates != scoped or dates != sorted(
        {members[identity]["reporting_date"] for identity in scoped}
    ):
        raise ValueError(_ERROR)
    if newest != (max(dates) if dates else None):
        raise ValueError(_ERROR)
    if members and (
        newest is None or any(row["reporting_date"] > newest for row in members.values())
    ):
        raise ValueError(_ERROR)
    candidate_parses = {members[identity]["parse_id"] for identity in candidates}
    if candidate_parses != {
        identity for identity, row in parses.items() if row["failure_reason"] is None
    }:
        raise ValueError(_ERROR)
    if diagnostics != sorted(set(parses) - candidate_parses):
        raise ValueError(_ERROR)
    candidate_captures = {parses[identity]["capture_sha256"] for identity in candidate_parses}
    storage = _sr_keys(data["storage_times"], {"captures", "parses"})
    parse_storage: dict[str, datetime] = {}
    for kind, identity_key, originals, minimum_field, maximum in (
        ("captures", "capture_sha256", captures, "retrieved_at", _LIMITS["CAPTURES"]),
        ("parses", "parse_id", parses, "recorded_at", _LIMITS["PARSES"]),
    ):
        times = _sr_sorted_rows(
            storage[kind], {identity_key, "stored_at"}, (identity_key,), maximum
        )
        if [row[identity_key] for row in times] != sorted(originals):
            raise ValueError(_ERROR)
        for row in times:
            stored = _sr_time(row["stored_at"])
            if (
                not _sr_time(originals[row[identity_key]][minimum_field], original=kind == "parses")
                <= stored
                <= read_at
            ):
                raise ValueError(_ERROR)
            if kind == "parses":
                parse_storage[row[identity_key]] = stored
    diagnostic_start = _sr_time(scope["diagnostic_start_at"])
    if any(
        not (
            diagnostic_start <= parse_storage[identity] <= read_at
            or parses[identity]["capture_sha256"] in candidate_captures
        )
        for identity in diagnostics
    ):
        raise ValueError(_ERROR)
    artifacts = _sr_sorted_rows(
        data["artifacts"],
        {"kind", "artifact_sha256", "document_size", "body_size", "stored_at"},
        ("kind", "artifact_sha256"),
        _LIMITS["ARTIFACTS"],
    )
    policy = document["policy"]
    expected = {("PARSER", row["parser_sha256"]) for row in parses.values()}
    expected.update(("PARSER", identity) for identity in policy["parser_allowlist"])
    expected.add(("SELECTOR", policy["selector_sha256"]))
    if [(row["kind"], row["artifact_sha256"]) for row in artifacts] != sorted(expected):
        raise ValueError(_ERROR)
    original_bytes = sum(row["document_size"] for row in captures.values()) + sum(
        row["document_size"] for row in parses.values()
    )
    for row in artifacts:
        _sr_digest(row["artifact_sha256"])
        original_bytes += _sr_int(row["document_size"], 1, 7_000_000)
        _sr_int(row["body_size"], 1, 5_000_000)
        envelope = {
            "version": "fpi-implementation-artifact-v1",
            "kind": row["kind"],
            "artifact_sha256": row["artifact_sha256"],
            "body_size": row["body_size"],
            "body_base64": "",
        }
        if row["document_size"] != len(_sr_canonical(envelope)) + 4 * ((row["body_size"] + 2) // 3):
            raise ValueError(_ERROR)
        if _sr_time(row["stored_at"]) > read_at:
            raise ValueError(_ERROR)
    if original_bytes > _LIMITS["ORIGINAL_BYTES"]:
        raise ValueError(_ERROR)
    _sr_qualification(data, candidates, members, read_at)


def _sr_manifest(document: dict[str, Any]) -> None:
    _sr_keys(document, _MANIFEST_FIELDS)
    if (
        document["version"] != "fpi-admin-read-v1"
        or document["execution_state"] != "UNVERIFIED"
        or document["acquisition_state"] != "UNVERIFIED"
        or document["eligible"] is not False
        or document["feature"] is not None
        or type(document["status"]) is not str
        or document["status"] not in _STATUSES
    ):
        raise ValueError(_ERROR)
    policy = FpiAdminReadPolicy(_sr_canonical(document["policy"]))
    request = FpiAdminReadRequest(_sr_canonical(document["request"]))
    if (
        document["policy_sha256"] != policy.policy_sha256
        or document["request"]["policy_sha256"] != policy.policy_sha256
        or document["request_sha256"] != request.request_sha256
        or document["read_id"] != request.read_id
    ):
        raise ValueError(_ERROR)
    read_at = _sr_time(document["read_at"])
    _sr_scope(document["scope"], document["policy"], read_at)
    if document["status"] == "COMPLETE":
        _sr_complete(document, read_at)
    else:
        if len(_sr_canonical(document)) > 65_536:
            raise ValueError(_ERROR)
        _sr_failure(document, read_at)


@dataclass(frozen=True)
class FpiAdminReadManifest:
    document_json: str
    read_sha256: str = field(init=False)
    read_id: str = field(init=False)
    request_sha256: str = field(init=False)
    decision_id: str = field(init=False)
    read_at: str = field(init=False)
    status: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            document = _sr_load(self.document_json, _LIMITS["MANIFEST_BYTES"])
            _sr_manifest(document)
            object.__setattr__(self, "read_sha256", _sr_sha(self.document_json))
            for name in ("read_id", "request_sha256", "read_at", "status"):
                object.__setattr__(self, name, document[name])
            object.__setattr__(self, "decision_id", document["request"]["decision_id"])
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
            raise ValueError(_ERROR) from None


def _sr_rebuild(value: _T, expected: type[_T]) -> _T:
    if type(value) is not expected:
        raise ValueError(_ERROR)
    try:
        rebuilt = expected(value.document_json)
        for item in fields(rebuilt):
            current = getattr(value, item.name)
            if type(current) is not str or current != getattr(rebuilt, item.name):
                raise ValueError(_ERROR)
        return rebuilt
    except (ValueError, AttributeError):
        raise ValueError(_ERROR) from None


def validate_fpi_admin_policy_receipt(value: Any, policy: FpiAdminReadPolicy) -> dict[str, Any]:
    policy = _sr_rebuild(policy, FpiAdminReadPolicy)
    row = _sr_keys(value, {"version", "policy_sha256", "inserted"}).copy()
    if (
        type(row["version"]) is not str
        or row["version"] != "fpi-admin-read-policy-receipt-v1"
        or _sr_digest(row["policy_sha256"]) != policy.policy_sha256
        or type(row["inserted"]) is not bool
    ):
        raise ValueError(_ERROR)
    return row


def validate_fpi_admin_read_receipt(value: Any, request: FpiAdminReadRequest) -> dict[str, Any]:
    request = _sr_rebuild(request, FpiAdminReadRequest)
    row = _sr_keys(
        value,
        set(
            "version decision_id request_sha256 read_id read_sha256 read_at "
            "status execution_state acquisition_state eligible inserted".split()
        ),
    ).copy()
    expected = {
        "version": "fpi-admin-read-receipt-v1",
        "decision_id": request.decision_id,
        "request_sha256": request.request_sha256,
        "read_id": request.read_id,
        "execution_state": "UNVERIFIED",
        "acquisition_state": "UNVERIFIED",
    }
    if (
        any(type(row[key]) is not str or row[key] != item for key, item in expected.items())
        or type(row["status"]) is not str
        or row["status"] not in _STATUSES
        or row["eligible"] is not False
        or type(row["inserted"]) is not bool
    ):
        raise ValueError(_ERROR)
    _sr_digest(row["read_sha256"])
    read_at = _sr_time(row["read_at"])
    try:
        read_at + _INDIA_OFFSET
    except OverflowError:
        raise ValueError(_ERROR) from None
    return row


def _sr_original_rows(value: Any, keys: set[str], maximum: int) -> tuple[dict[str, str], ...]:
    if type(value) is not tuple or len(value) > maximum:
        raise ValueError(_ERROR)
    copies = []
    for row in value:
        _sr_keys(row, keys)
        if any(type(item) is not str for item in row.values()):
            raise ValueError(_ERROR)
        copies.append(row.copy())
    return tuple(copies)


def verify_fpi_admin_read_originals(
    manifest: FpiAdminReadManifest,
    *,
    capture_rows: tuple[dict[str, Any], ...],
    parse_rows: tuple[dict[str, Any], ...],
    artifact_rows: tuple[dict[str, Any], ...],
    event_rows: tuple[dict[str, Any], ...],
) -> FpiAdminReadManifest:
    """Prove exact retained dependencies without executing artifacts or refreshing scope."""
    # Copy every supplied exact primitive before calling any dependency validators.
    captures = _sr_original_rows(
        capture_rows, {"capture_sha256", "document_json", "stored_at"}, _LIMITS["CAPTURES"]
    )
    parses = _sr_original_rows(
        parse_rows, {"parse_id", "record_sha256", "document_json", "stored_at"}, _LIMITS["PARSES"]
    )
    artifacts = _sr_original_rows(
        artifact_rows,
        {"kind", "artifact_sha256", "document_json", "stored_at"},
        _LIMITS["ARTIFACTS"],
    )
    events = _sr_original_rows(event_rows, {"event_id", "event_document_json"}, _LIMITS["EVENTS"])
    checked = _sr_rebuild(manifest, FpiAdminReadManifest)
    if checked.status != "COMPLETE":
        if captures or parses or artifacts or events:
            raise ValueError(_ERROR)
        return checked
    document = json.loads(checked.document_json)
    data = document["data"]
    reference = data["references"]
    total_bytes = 0
    # All count, identity, individual size and aggregate guards precede body decoding.
    for rows, expected_rows, identity_keys, cap, time_rows in (
        (
            captures,
            reference["captures"],
            ("capture_sha256",),
            7_000_000,
            data["storage_times"]["captures"],
        ),
        (parses, reference["parses"], ("parse_id",), 4_000_000, data["storage_times"]["parses"]),
        (artifacts, data["artifacts"], ("kind", "artifact_sha256"), 7_000_000, data["artifacts"]),
    ):
        expected = {tuple(row[key] for key in identity_keys): row for row in expected_rows}
        times = {tuple(row[key] for key in identity_keys): row["stored_at"] for row in time_rows}
        seen: set[tuple[str, ...]] = set()
        for row in rows:
            identity = tuple(row[key] for key in identity_keys)
            if identity in seen or identity not in expected:
                raise ValueError(_ERROR)
            seen.add(identity)
            text = row["document_json"]
            if (
                len(text) > cap
                or not text.isascii()
                or len(text) != expected[identity]["document_size"]
            ):
                raise ValueError(_ERROR)
            total_bytes += len(text)
            if total_bytes > _LIMITS["ORIGINAL_BYTES"]:
                raise ValueError(_ERROR)
            if _sr_time(row["stored_at"], transport=True) != _sr_time(times[identity]):
                raise ValueError(_ERROR)
            if (
                "record_sha256" in row
                and row["record_sha256"] != expected[identity]["record_sha256"]
            ):
                raise ValueError(_ERROR)
        if seen != set(expected):
            raise ValueError("READ_DEPENDENCY_MISSING")
    expected_events = {
        _sr_sha(_sr_canonical(row)): _sr_canonical(row) for row in data["qualification"]["events"]
    }
    seen_events: set[str] = set()
    event_bytes = 0
    for row in events:
        event_id, text = row["event_id"], row["event_document_json"]
        if event_id in seen_events or event_id not in expected_events or len(text) > 400_000:
            raise ValueError(_ERROR)
        event_bytes += len(text)
        if event_bytes > _LIMITS["QUALIFICATION_BYTES"] or text != expected_events[event_id]:
            raise ValueError(_ERROR)
        seen_events.add(event_id)
    if seen_events != set(expected_events):
        raise ValueError("READ_DEPENDENCY_MISSING")
    for rows, cap in ((captures, 7_000_000), (parses, 4_000_000), (artifacts, 7_000_000)):
        for row in rows:
            _sr_text_preflight(row["document_json"], cap)
    try:
        artifact_metadata = {
            (row["kind"], row["artifact_sha256"]): row for row in data["artifacts"]
        }
        for row in artifacts:
            artifact = FpiArtifact(row["artifact_sha256"], row["document_json"])
            validate_fpi_artifact(artifact)
            original = json.loads(artifact.document_json)
            metadata = artifact_metadata[(row["kind"], row["artifact_sha256"])]
            if original["kind"] != row["kind"] or original["body_size"] != metadata["body_size"]:
                raise ValueError(_ERROR)
        rebuilt = build_fpi_read_references(
            captures=tuple(
                FpiCapture(row["capture_sha256"], row["document_json"]) for row in captures
            ),
            records=tuple(
                FpiParseRecord(row["parse_id"], row["record_sha256"], row["document_json"])
                for row in parses
            ),
        )
        if (
            rebuilt.document_json != _sr_canonical(reference)
            or rebuilt.reference_sha256 != data["reference_sha256"]
        ):
            raise ValueError(_ERROR)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError(_ERROR) from None
    return checked
