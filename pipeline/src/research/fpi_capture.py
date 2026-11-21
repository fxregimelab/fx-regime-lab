"""Pure, byte-exact capture envelopes for fixed NSDL FPI report responses."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

FPI_CAPTURE_VERSION = "fpi-http-capture-v1"
_MAX_BODY_BYTES = 5_000_000
_MAX_DOCUMENT_BYTES = 7_000_000
_SOURCE_URLS = frozenset(
    {
        "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
        "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
    }
)
_FIELDS = {
    "version",
    "source_url",
    "requested_at",
    "retrieved_at",
    "http_status",
    "body_base64",
    "body_size",
    "raw_sha256",
}
_UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{6})?\+00:00"
)
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class FpiCapture:
    """Identity and canonical JSON for one complete HTTP response body."""

    capture_sha256: str
    document_json: str


def _utc(value: datetime, *, field: str) -> datetime:
    if type(value) is not datetime:
        raise ValueError(f"{field} must be a datetime")
    try:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError(f"{field} must be timezone-aware")
        normalized = value.astimezone(UTC)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field} is outside the supported UTC range") from exc
    if not 1 <= normalized.year <= 9999:
        raise ValueError(f"{field} is outside the supported UTC range")
    return normalized


def _timestamp(value: Any, *, field: str) -> datetime:
    if type(value) is not str or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise ValueError(f"Invalid {field} in FPI capture")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field} in FPI capture") from exc
    if parsed.tzinfo != UTC or parsed.isoformat() != value:
        raise ValueError(f"Invalid {field} in FPI capture")
    return parsed


def _canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_fpi_capture(
    *,
    body: bytes,
    source_url: str,
    requested_at: datetime,
    retrieved_at: datetime,
    http_status: int,
) -> FpiCapture:
    """Build a deterministic envelope without parsing or decoding the response body."""
    if type(body) is not bytes:
        raise ValueError("FPI capture body must be bytes")
    if len(body) > _MAX_BODY_BYTES:
        raise ValueError("FPI capture body exceeds 5000000 bytes")
    if type(source_url) is not str or source_url not in _SOURCE_URLS:
        raise ValueError("Invalid FPI source URL")
    if type(http_status) is not int or not 100 <= http_status <= 599:
        raise ValueError("FPI capture HTTP status must be an integer from 100 through 599")
    requested_utc = _utc(requested_at, field="requested_at")
    retrieved_utc = _utc(retrieved_at, field="retrieved_at")
    if requested_utc > retrieved_utc:
        raise ValueError("FPI request time cannot follow retrieval time")
    document = {
        "version": FPI_CAPTURE_VERSION,
        "source_url": source_url,
        "requested_at": requested_utc.isoformat(),
        "retrieved_at": retrieved_utc.isoformat(),
        "http_status": http_status,
        "body_base64": base64.b64encode(body).decode("ascii"),
        "body_size": len(body),
        "raw_sha256": hashlib.sha256(body).hexdigest(),
    }
    document_json = _canonical_json(document)
    capture = FpiCapture(
        capture_sha256=hashlib.sha256(document_json.encode("ascii")).hexdigest(),
        document_json=document_json,
    )
    validate_fpi_capture(capture)
    return capture


def validate_fpi_capture(capture: FpiCapture) -> None:
    """Verify type, canonical text, exact bytes, timestamps and both fingerprints."""
    if type(capture) is not FpiCapture:
        raise ValueError("FPI capture must be an exact FpiCapture")
    if type(capture.capture_sha256) is not str or _SHA256.fullmatch(
        capture.capture_sha256
    ) is None:
        raise ValueError("Invalid FPI capture SHA-256")
    if type(capture.document_json) is not str:
        raise ValueError("FPI capture document must be text")
    try:
        encoded_document = capture.document_json.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("FPI capture document must be canonical ASCII JSON") from exc
    if len(encoded_document) > _MAX_DOCUMENT_BYTES:
        raise ValueError("FPI capture document exceeds 7000000 bytes")
    try:
        document = json.loads(capture.document_json)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("FPI capture document is not valid JSON") from exc
    if type(document) is not dict or set(document) != _FIELDS:
        raise ValueError("FPI capture document has invalid fields")
    if _canonical_json(document) != capture.document_json:
        raise ValueError("FPI capture document is not canonical JSON")
    if type(document["version"]) is not str or document["version"] != FPI_CAPTURE_VERSION:
        raise ValueError("Invalid FPI capture version")
    if type(document["source_url"]) is not str or document["source_url"] not in _SOURCE_URLS:
        raise ValueError("Invalid FPI source URL")
    if type(document["http_status"]) is not int or not 100 <= document["http_status"] <= 599:
        raise ValueError("Invalid FPI capture HTTP status")
    if type(document["body_size"]) is not int or not 0 <= document["body_size"] <= _MAX_BODY_BYTES:
        raise ValueError("Invalid FPI capture body size")
    if type(document["body_base64"]) is not str:
        raise ValueError("Invalid FPI capture Base64 body")
    try:
        body = base64.b64decode(document["body_base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid FPI capture Base64 body") from exc
    if base64.b64encode(body).decode("ascii") != document["body_base64"]:
        raise ValueError("FPI capture body is not canonical Base64")
    if len(body) != document["body_size"]:
        raise ValueError("FPI capture body size does not match decoded bytes")
    if type(document["raw_sha256"]) is not str or _SHA256.fullmatch(
        document["raw_sha256"]
    ) is None:
        raise ValueError("Invalid FPI raw SHA-256")
    if hashlib.sha256(body).hexdigest() != document["raw_sha256"]:
        raise ValueError("FPI raw SHA-256 does not match decoded bytes")
    requested_at = _timestamp(document["requested_at"], field="requested_at")
    retrieved_at = _timestamp(document["retrieved_at"], field="retrieved_at")
    if requested_at > retrieved_at:
        raise ValueError("FPI request time cannot follow retrieval time")
    if hashlib.sha256(encoded_document).hexdigest() != capture.capture_sha256:
        raise ValueError("FPI capture SHA-256 does not match the document")
