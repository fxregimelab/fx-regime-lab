"""Pure, canonical envelopes for retained FPI implementations and parse results.

These records preserve bytes and parsed evidence. They do not execute artifacts,
qualify observations, or establish source authenticity or decision visibility.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from src.research.fpi_capture import FpiCapture, validate_fpi_capture
from src.research.fpi_observation import FPI_OBSERVATION_VERSION, FPI_ROUTES
from src.research.fpi_selection import FpiParsedDay, FpiParseResult

FPI_ARTIFACT_VERSION = "fpi-implementation-artifact-v1"
FPI_PARSE_RECORD_VERSION = "fpi-parse-record-v1"
FPI_SOURCE_EVIDENCE_VERSION = "nsdl-fpi-source-evidence-v1"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_FAILURE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_MONEY = re.compile(r"-?(?:0|[1-9][0-9]{0,15})\.[0-9]{2}")
_RATE = re.compile(r"(?:0|[1-9][0-9]{0,5})\.[0-9]{4}")
_UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?\+00:00"
)
_ARTIFACT_FIELDS = {"version", "kind", "artifact_sha256", "body_size", "body_base64"}
_RECORD_FIELDS = {
    "version",
    "parse_id",
    "content_sha256",
    "capture_sha256",
    "parser_sha256",
    "definition_version",
    "recorded_at",
    "failure_reason",
    "days",
}
_DAY_FIELDS = {
    "reporting_date",
    "value_sha256",
    "membership_id",
    "document_json",
    "source_evidence_sha256",
    "source_evidence_document_json",
}
_SOURCE_FIELDS = {
    "version",
    "reporting_date",
    "usd_units",
    "conversion_rate_units",
    "conversion_rate_inr_per_usd",
    "categories",
    "total_net_usd_million",
}
_MAX_BODY_BYTES = 5_000_000
_MAX_ARTIFACT_DOCUMENT_BYTES = 7_000_000
_MAX_DAY_DOCUMENT_CHARS = 32_768
_MAX_RECORD_BYTES = 4_000_000
FPI_READ_REFERENCES_VERSION = "fpi-read-references-v1"
_MAX_READ_INPUTS = 2048
_MAX_READ_CAPTURE_CHARS = 7_000_000
_MAX_READ_ORIGINAL_BYTES = 64_000_000
_MAX_READ_MEMBERSHIPS = 20_000
_MAX_READ_REFERENCE_BYTES = 16_000_000


@dataclass(frozen=True)
class FpiArtifact:
    artifact_sha256: str
    document_json: str


@dataclass(frozen=True)
class FpiParseRecord:
    parse_id: str
    record_sha256: str
    document_json: str


def _canonical(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _load_exact(document_json: str, *, label: str, max_bytes: int) -> dict[str, Any]:
    if type(document_json) is not str or "\x00" in document_json:
        raise ValueError(f"{label} must be text without NUL")
    if len(document_json) > max_bytes:
        raise ValueError(f"{label} exceeds its size limit")
    try:
        encoded = document_json.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be canonical ASCII JSON") from exc
    if len(encoded) > max_bytes:
        raise ValueError(f"{label} exceeds its size limit")
    try:
        value = json.loads(document_json, object_pairs_hook=_pairs_object)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError(f"{label} is not valid unique-key JSON") from exc
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    if _canonical(value) != document_json:
        raise ValueError(f"{label} is not canonical JSON")
    return value


def _digest(value: Any, *, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"Invalid {field}")
    return value


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _parse_utc(value: Any, *, field: str) -> datetime:
    if type(value) is not str or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise ValueError(f"Invalid {field}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}") from exc
    if parsed.tzinfo != UTC or parsed.isoformat() != value:
        raise ValueError(f"Invalid {field}")
    return parsed


def build_fpi_artifact(*, kind: str, body: bytes) -> FpiArtifact:
    """Retain exact implementation bytes without executing or trusting them."""
    if type(kind) is not str or kind not in {"PARSER", "SELECTOR"}:
        raise ValueError("FPI artifact kind must be PARSER or SELECTOR")
    if type(body) is not bytes or not 1 <= len(body) <= _MAX_BODY_BYTES:
        raise ValueError("FPI artifact body must contain 1 through 5000000 bytes")
    digest = hashlib.sha256(body).hexdigest()
    document_json = _canonical(
        {
            "version": FPI_ARTIFACT_VERSION,
            "kind": kind,
            "artifact_sha256": digest,
            "body_size": len(body),
            "body_base64": base64.b64encode(body).decode("ascii"),
        }
    )
    artifact = FpiArtifact(digest, document_json)
    validate_fpi_artifact(artifact)
    return artifact


def validate_fpi_artifact(artifact: FpiArtifact) -> None:
    if type(artifact) is not FpiArtifact:
        raise ValueError("Expected an exact FpiArtifact")
    digest = _digest(artifact.artifact_sha256, field="artifact SHA-256")
    document = _load_exact(
        artifact.document_json,
        label="FPI artifact document",
        max_bytes=_MAX_ARTIFACT_DOCUMENT_BYTES,
    )
    if set(document) != _ARTIFACT_FIELDS:
        raise ValueError("FPI artifact document has invalid fields")
    if (
        type(document["version"]) is not str
        or document["version"] != FPI_ARTIFACT_VERSION
        or type(document["kind"]) is not str
        or document["kind"] not in {"PARSER", "SELECTOR"}
    ):
        raise ValueError("Invalid FPI artifact version or kind")
    if type(document["artifact_sha256"]) is not str or document["artifact_sha256"] != digest:
        raise ValueError("FPI artifact identity does not match")
    if type(document["body_size"]) is not int or not 1 <= document["body_size"] <= _MAX_BODY_BYTES:
        raise ValueError("Invalid FPI artifact body size")
    if type(document["body_base64"]) is not str:
        raise ValueError("Invalid FPI artifact body encoding")
    try:
        body = base64.b64decode(document["body_base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid FPI artifact Base64") from exc
    if base64.b64encode(body).decode("ascii") != document["body_base64"]:
        raise ValueError("FPI artifact Base64 is not canonical")
    if len(body) != document["body_size"] or hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("FPI artifact bytes do not match their claims")


def _money(value: Any, *, field: str) -> int:
    if type(value) is not str or _MONEY.fullmatch(value) is None or value == "-0.00":
        raise ValueError(f"Invalid {field}")
    whole, fraction = value.lstrip("-").split(".")
    amount = int(whole) * 100 + int(fraction)
    return -amount if value.startswith("-") else amount


def _reconcile(children: list[int], parent: int, *, field: str) -> None:
    if 2 * abs(sum(children) - parent) > len(children) + 1:
        raise ValueError(f"FPI source {field} values do not reconcile")


def _validate_source_document(document_json: str, reporting_date: date) -> str:
    if type(document_json) is not str:
        raise ValueError("FPI source evidence document must be text")
    if len(document_json) > _MAX_DAY_DOCUMENT_CHARS:
        raise ValueError("FPI source evidence document exceeds 32768 characters")
    document = _load_exact(
        document_json,
        label="FPI source evidence document",
        max_bytes=_MAX_DAY_DOCUMENT_CHARS,
    )
    if set(document) != _SOURCE_FIELDS:
        raise ValueError("FPI source evidence has invalid fields")
    if (
        document["version"] != FPI_SOURCE_EVIDENCE_VERSION
        or document["reporting_date"] != reporting_date.isoformat()
        or document["usd_units"] != "USD_MILLION"
        or document["conversion_rate_units"] != "INR_PER_USD"
    ):
        raise ValueError("FPI source evidence metadata does not match")
    rate = document["conversion_rate_inr_per_usd"]
    if type(rate) is not str or _RATE.fullmatch(rate) is None or int(rate.replace(".", "")) == 0:
        raise ValueError("Invalid FPI INR per USD conversion rate")
    categories = document["categories"]
    if type(categories) is not dict or set(categories) != set(FPI_ROUTES):
        raise ValueError("FPI source evidence requires the exact seven categories")
    subtotals: list[int] = []
    for category, expected_routes in FPI_ROUTES.items():
        group = categories[category]
        if type(group) is not dict or set(group) != {
            "routes_net_usd_million",
            "subtotal_net_usd_million",
        }:
            raise ValueError("FPI source evidence category has invalid fields")
        routes = group["routes_net_usd_million"]
        if type(routes) is not dict or set(routes) != set(expected_routes):
            raise ValueError("FPI source evidence routes are missing or unknown")
        values = [_money(routes[route], field="route USD amount") for route in expected_routes]
        subtotal = _money(group["subtotal_net_usd_million"], field="subtotal USD amount")
        _reconcile(values, subtotal, field="category")
        subtotals.append(subtotal)
    total = _money(document["total_net_usd_million"], field="total USD amount")
    _reconcile(subtotals, total, field="total")
    return hashlib.sha256(document_json.encode("ascii")).hexdigest()


def _rebuild_day(day: FpiParsedDay) -> FpiParsedDay:
    if type(day) is not FpiParsedDay:
        raise ValueError("Expected an exact FpiParsedDay")
    rebuilt = FpiParsedDay(day.document_json, day.source_evidence_sha256)
    if rebuilt != day:
        raise ValueError("FPI parsed day does not match reconstructed evidence")
    return rebuilt


def _rebuild_parse(parse: FpiParseResult) -> FpiParseResult:
    if type(parse) is not FpiParseResult:
        raise ValueError("Expected an exact FpiParseResult")
    if parse.failure_reason is not None and (
        type(parse.failure_reason) is not str
        or _FAILURE_CODE.fullmatch(parse.failure_reason) is None
    ):
        raise ValueError("FPI parse failure_reason must be a bounded machine code")
    if type(parse.days) is not tuple or len(parse.days) > 31:
        raise ValueError("FPI parse days must be a bounded immutable tuple")
    days = tuple(_rebuild_day(day) for day in parse.days)
    rebuilt = FpiParseResult(
        parse.capture,
        parse.parser_sha256,
        parse.definition_version,
        parse.recorded_at,
        days,
        parse.failure_reason,
    )
    if rebuilt != parse:
        raise ValueError("FPI parse does not match reconstructed evidence")
    return rebuilt


def build_fpi_parse_record(
    parse: FpiParseResult, *, source_evidence_documents: tuple[str, ...]
) -> FpiParseRecord:
    """Encode one complete successful parse or one complete failed parse."""
    rebuilt = _rebuild_parse(parse)
    if type(source_evidence_documents) is not tuple:
        raise ValueError("FPI source evidence documents must be an immutable tuple")
    if len(source_evidence_documents) != len(rebuilt.days):
        raise ValueError("FPI source evidence must match every parsed date exactly")
    day_documents: list[dict[str, Any]] = []
    for day, source_document in zip(rebuilt.days, source_evidence_documents, strict=True):
        source_hash = _validate_source_document(source_document, day.reporting_date)
        if source_hash != day.source_evidence_sha256:
            raise ValueError("FPI source evidence SHA-256 does not match parsed membership")
        day_documents.append(
            {
                "reporting_date": day.reporting_date.isoformat(),
                "value_sha256": day.value_sha256,
                "membership_id": rebuilt.membership_id(day),
                "document_json": day.document_json,
                "source_evidence_sha256": source_hash,
                "source_evidence_document_json": source_document,
            }
        )
    document = {
        "version": FPI_PARSE_RECORD_VERSION,
        "parse_id": rebuilt.parse_id,
        "content_sha256": rebuilt.content_sha256,
        "capture_sha256": rebuilt.capture.capture_sha256,
        "parser_sha256": rebuilt.parser_sha256,
        "definition_version": rebuilt.definition_version,
        "recorded_at": rebuilt.recorded_at.isoformat(),
        "failure_reason": rebuilt.failure_reason,
        "days": day_documents,
    }
    document_json = _canonical(document)
    if len(document_json.encode("ascii")) > _MAX_RECORD_BYTES:
        raise ValueError("FPI parse record exceeds 4000000 bytes")
    record = FpiParseRecord(
        rebuilt.parse_id,
        hashlib.sha256(document_json.encode("ascii")).hexdigest(),
        document_json,
    )
    validate_fpi_parse_record(record)
    return record


def _record_parts(record: FpiParseRecord) -> tuple[dict[str, Any], tuple[FpiParsedDay, ...]]:
    if type(record) is not FpiParseRecord:
        raise ValueError("Expected an exact FpiParseRecord")
    parse_id = _digest(record.parse_id, field="parse ID")
    record_sha256 = _digest(record.record_sha256, field="parse record SHA-256")
    document = _load_exact(
        record.document_json, label="FPI parse record", max_bytes=_MAX_RECORD_BYTES
    )
    if set(document) != _RECORD_FIELDS:
        raise ValueError("FPI parse record has invalid fields")
    if document["version"] != FPI_PARSE_RECORD_VERSION or document["parse_id"] != parse_id:
        raise ValueError("FPI parse record identity does not match")
    if hashlib.sha256(record.document_json.encode("ascii")).hexdigest() != record_sha256:
        raise ValueError("FPI parse record SHA-256 does not match")
    capture_sha = _digest(document["capture_sha256"], field="capture SHA-256")
    parser_sha = _digest(document["parser_sha256"], field="parser SHA-256")
    if (
        type(document["definition_version"]) is not str
        or document["definition_version"] != FPI_OBSERVATION_VERSION
    ):
        raise ValueError("Unsupported FPI parse definition")
    recorded_at = _parse_utc(document["recorded_at"], field="FPI parse recorded_at")
    del recorded_at
    if _fingerprint([capture_sha, parser_sha, document["definition_version"]]) != parse_id:
        raise ValueError("FPI parse ID does not match its dependencies")
    failure = document["failure_reason"]
    if failure is not None and (
        type(failure) is not str or _FAILURE_CODE.fullmatch(failure) is None
    ):
        raise ValueError("Invalid FPI parse failure_reason")
    rows = document["days"]
    if type(rows) is not list or len(rows) > 31:
        raise ValueError("Invalid FPI parse day set")
    if (failure is None) != bool(rows):
        raise ValueError("FPI parse must be wholly successful or wholly failed")
    days: list[FpiParsedDay] = []
    dates: list[date] = []
    for row in rows:
        if type(row) is not dict or set(row) != _DAY_FIELDS:
            raise ValueError("FPI parse day has invalid fields")
        if type(row["reporting_date"]) is not str:
            raise ValueError("Invalid FPI parse reporting date")
        try:
            reporting_date = date.fromisoformat(row["reporting_date"])
        except ValueError as exc:
            raise ValueError("Invalid FPI parse reporting date") from exc
        if reporting_date.isoformat() != row["reporting_date"]:
            raise ValueError("Invalid FPI parse reporting date")
        source_hash = _validate_source_document(
            row["source_evidence_document_json"], reporting_date
        )
        if source_hash != _digest(row["source_evidence_sha256"], field="source evidence SHA-256"):
            raise ValueError("FPI source evidence hash does not match")
        day = FpiParsedDay(row["document_json"], source_hash)
        if day.reporting_date != reporting_date:
            raise ValueError("FPI INR and source evidence dates do not match")
        if _digest(row["value_sha256"], field="value SHA-256") != day.value_sha256:
            raise ValueError("FPI value SHA-256 does not match")
        membership_id = _fingerprint([parse_id, day.value_sha256, source_hash])
        if _digest(row["membership_id"], field="membership ID") != membership_id:
            raise ValueError("FPI membership ID does not match")
        days.append(day)
        dates.append(reporting_date)
    if dates != sorted(set(dates)):
        raise ValueError("FPI parse dates must be unique and ascending")
    content_sha = _digest(document["content_sha256"], field="content SHA-256")
    expected_content = _fingerprint(
        {
            "parse_id": parse_id,
            "recorded_at": document["recorded_at"],
            "days": [asdict(day) for day in days],
            "failure_reason": failure,
        }
    )
    if content_sha != expected_content:
        raise ValueError("FPI parse content SHA-256 does not match")
    return document, tuple(days)


def validate_fpi_parse_record(record: FpiParseRecord) -> None:
    _record_parts(record)


def restore_fpi_parse_record(record: FpiParseRecord, capture: FpiCapture) -> FpiParseResult:
    """Rebuild and fully compare a retained parse against its exact capture."""
    document, days = _record_parts(record)
    validate_fpi_capture(capture)
    if capture.capture_sha256 != document["capture_sha256"]:
        raise ValueError("FPI parse record does not belong to the supplied capture")
    restored = FpiParseResult(
        capture,
        document["parser_sha256"],
        document["definition_version"],
        _parse_utc(document["recorded_at"], field="FPI parse recorded_at"),
        days,
        document["failure_reason"],
    )
    source_documents = tuple(row["source_evidence_document_json"] for row in document["days"])
    if build_fpi_parse_record(
        restored, source_evidence_documents=source_documents
    ) != record:
        raise ValueError("Restored FPI parse does not reproduce the complete record")
    return restored


@dataclass(frozen=True)
class FpiReadReferences:
    """Compact identities; direct construction does not verify retained originals."""

    reference_sha256: str
    document_json: str


def build_fpi_read_references(
    *, captures: tuple[FpiCapture, ...], records: tuple[FpiParseRecord, ...]
) -> FpiReadReferences:
    """Validate whole retained documents once and retain every compact membership."""
    if type(captures) is not tuple or type(records) is not tuple:
        raise ValueError("FPI read inputs must be exact tuples")
    if len(captures) > _MAX_READ_INPUTS or len(records) > _MAX_READ_INPUTS:
        raise ValueError("FPI read input count exceeds its limit")

    # Snapshot only exact immutable primitives before any full-document validation.
    capture_copies: dict[str, FpiCapture] = {}
    record_copies: dict[str, FpiParseRecord] = {}
    original_documents: set[str] = set()
    original_bytes = 0
    for items, expected_type, limit in (
        (captures, FpiCapture, _MAX_READ_CAPTURE_CHARS),
        (records, FpiParseRecord, _MAX_RECORD_BYTES),
    ):
        for item in items:
            if type(item) is not expected_type:
                raise ValueError("FPI read input has an invalid exact type")
            text = item.document_json
            if type(text) is not str or len(text) > limit:
                raise ValueError("FPI read original document exceeds its text limit")
            if not text.isascii():
                raise ValueError("FPI read original document must be ASCII")
            if type(item) is FpiCapture:
                identity = _digest(item.capture_sha256, field="capture SHA-256")
                capture_copy = FpiCapture(identity, text)
                if identity in capture_copies and capture_copies[identity] != capture_copy:
                    raise ValueError("Contradictory FPI capture identity")
                capture_copies[identity] = capture_copy
            elif type(item) is FpiParseRecord:
                identity = _digest(item.parse_id, field="parse ID")
                digest = _digest(item.record_sha256, field="parse record SHA-256")
                record_copy = FpiParseRecord(identity, digest, text)
                if identity in record_copies and record_copies[identity] != record_copy:
                    raise ValueError("Contradictory FPI parse identity")
                record_copies[identity] = record_copy
            if text not in original_documents:
                original_bytes += len(text)
                if original_bytes > _MAX_READ_ORIGINAL_BYTES:
                    raise ValueError("FPI read original document budget exceeded")
                original_documents.add(text)

    capture_metadata: dict[str, dict[str, Any]] = {}
    capture_fragments: list[str] = []
    parse_fragments: list[str] = []
    # Account for the full outer envelope and commas before joining any aggregate.
    envelope = '{"captures":[],"parses":[],"version":"' + FPI_READ_REFERENCES_VERSION + '"}'
    reference_bytes = len(envelope)
    if reference_bytes > _MAX_READ_REFERENCE_BYTES:
        raise ValueError("FPI read reference document budget exceeded")
    for identity, capture_copy in sorted(capture_copies.items()):
        validate_fpi_capture(capture_copy)
        metadata = json.loads(capture_copy.document_json)
        capture_metadata[identity] = {
            key: metadata[key]
            for key in (
                "source_url",
                "requested_at",
                "retrieved_at",
                "http_status",
                "body_size",
                "raw_sha256",
            )
        }
        fragment = _canonical(
            {
                "capture_sha256": identity,
                "document_size": len(capture_copy.document_json),
                **capture_metadata[identity],
            }
        )
        reference_bytes += len(fragment) + bool(capture_fragments)
        if reference_bytes > _MAX_READ_REFERENCE_BYTES:
            raise ValueError("FPI read reference document budget exceeded")
        capture_fragments.append(fragment)

    used_captures: set[str] = set()
    memberships = 0
    india = timezone(timedelta(hours=5, minutes=30))
    for identity, record_copy in sorted(record_copies.items()):
        document, days = _record_parts(record_copy)
        capture_id = document["capture_sha256"]
        if capture_id not in capture_metadata:
            raise ValueError("FPI read parse requires a missing capture")
        metadata = capture_metadata[capture_id]
        used_captures.add(capture_id)
        recorded = _parse_utc(document["recorded_at"], field="FPI parse recorded_at")
        retrieved = datetime.fromisoformat(metadata["retrieved_at"])
        try:
            recorded.astimezone(india)
            receipt_date = retrieved.astimezone(india).date()
        except (ValueError, OverflowError) as exc:
            raise ValueError("Unsupported FPI read timestamp range") from exc
        if recorded < retrieved:
            raise ValueError("FPI read parse cannot precede retrieval")
        if document["failure_reason"] is None and (
            metadata["http_status"] != 200
            or document["definition_version"] != FPI_OBSERVATION_VERSION
        ):
            raise ValueError("Successful FPI read parse requires HTTP 200 and canonical definition")
        if any(day.reporting_date > receipt_date for day in days):
            raise ValueError("FPI read reporting date follows capture")
        memberships += len(days)
        if memberships > _MAX_READ_MEMBERSHIPS:
            raise ValueError("FPI read membership count exceeds its limit")
        fragment = _canonical(
            {
                **{
                    key: document[key]
                    for key in (
                        "content_sha256",
                        "capture_sha256",
                        "parser_sha256",
                        "definition_version",
                        "recorded_at",
                        "failure_reason",
                    )
                },
                "parse_id": identity,
                "record_sha256": record_copy.record_sha256,
                "document_size": len(record_copy.document_json),
                "memberships": [
                    {
                        key: row[key]
                        for key in (
                            "reporting_date",
                            "value_sha256",
                            "membership_id",
                            "source_evidence_sha256",
                        )
                    }
                    for row in document["days"]
                ],
            }
        )
        reference_bytes += len(fragment) + bool(parse_fragments)
        if reference_bytes > _MAX_READ_REFERENCE_BYTES:
            raise ValueError("FPI read reference document budget exceeded")
        parse_fragments.append(fragment)
    if used_captures != set(capture_metadata):
        raise ValueError("FPI read contains unused captures")
    document_json = (
        '{"captures":['
        + ",".join(capture_fragments)
        + '],"parses":['
        + ",".join(parse_fragments)
        + '],"version":"'
        + FPI_READ_REFERENCES_VERSION
        + '"}'
    )
    return FpiReadReferences(
        hashlib.sha256(document_json.encode("ascii")).hexdigest(), document_json
    )
