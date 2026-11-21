"""Strict attempt events and observed source provenance for quote acquisition."""

import hashlib
import json
import platform
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import UUID

from src.research.quote_capture import canonical_json

CLIENT_VERSION = "fxregime-quote-http-v1"
DEFAULT_LIMITS = {
    "max_pages": 200, "max_page_bytes": 16_777_216, "max_total_bytes": 67_108_864,
    "deadline_seconds": 300, "request_timeout_seconds": 30,
}
_MAX_LIMITS = {
    "max_pages": 10_000, "max_page_bytes": 16_777_216, "max_total_bytes": 268_435_456,
    "deadline_seconds": 3600, "request_timeout_seconds": 60,
}
_FILES = (
    "pipeline/src/research/quote_acquisition.py", "pipeline/src/research/quote_attempt.py",
    "pipeline/src/research/quote_capture.py", "pipeline/src/research/quote_reference.py",
    "pipeline/src/db/writer.py",
)
_COMMON = {
    "attempt_id", "pair", "instrument", "window_start_ns", "window_end_ns",
    "implementation_sha256", "client_version", "runtime_manifest_json", "limits",
}
_FIELDS = _COMMON | {
    "version", "sequence", "previous_event_sha256", "kind", "occurred_at",
    "capture_sha256", "snapshot_sha256", "status", "reason", "event_sha256",
}
_REASONS = {
    "completed", "request_failed", "read_failed", "body_limit", "byte_budget", "page_limit",
    "time_budget", "http_status", "invalid_response", "capture_invalid", "capture_write_failed",
    "page_event_write_failed", "snapshot_write_failed", "cursor_cycle", "clock_invalid",
    "implementation_changed",
}
_INSTRUMENTS = {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}
_DAY_NS = 86_400_000_000_000


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _manifest(text: Any, fingerprint: Any) -> None:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 65_536:
        raise ValueError("Invalid quote runtime manifest")
    try:
        document = json.loads(text)
    except (ValueError, RecursionError):
        raise ValueError("Invalid quote runtime manifest") from None
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "client_version", "files", "dependencies"}
        or document["version"] != "quote-runtime-manifest-v1"
        or document["client_version"] != CLIENT_VERSION
        or not isinstance(document["files"], dict) or set(document["files"]) != set(_FILES)
        or any(not _is_hash(value) for value in document["files"].values())
        or not isinstance(document["dependencies"], dict)
        or set(document["dependencies"]) != {"python", "aiohttp"}
        or any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._+-]{1,128}", value)
               for value in document["dependencies"].values())
        or canonical_json(document) != text or _hash(text) != fingerprint
    ):
        raise ValueError("Invalid quote runtime manifest")


def quote_runtime_manifest() -> tuple[str, str]:
    """Fingerprint fixed disk sources and installed versions, not in-memory execution."""
    root = Path(__file__).resolve().parents[3]
    document = {
        "version": "quote-runtime-manifest-v1", "client_version": CLIENT_VERSION,
        "files": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in _FILES},
        "dependencies": {"python": platform.python_version(), "aiohttp": version("aiohttp")},
    }
    text = canonical_json(document)
    fingerprint = _hash(text)
    _manifest(text, fingerprint)
    return text, fingerprint


def validate_quote_acquisition_event(event: Mapping[str, Any]) -> None:
    """Validate local shape and phase; persistence enforces cross-event lineage."""
    if not isinstance(event, Mapping) or set(event) != _FIELDS:
        raise ValueError("Invalid quote attempt fields")
    if event["version"] != "quote-acquisition-event-v1":
        raise ValueError("Invalid quote attempt version")
    attempt_id = event["attempt_id"]
    try:
        if not isinstance(attempt_id, str) or str(UUID(attempt_id)) != attempt_id:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError("Invalid quote attempt identity") from None
    sequence = event["sequence"]
    if type(sequence) is not int or not 0 <= sequence <= 10_001:
        raise ValueError("Invalid quote attempt sequence")
    pair = event["pair"]
    if not isinstance(pair, str) or pair not in _INSTRUMENTS:
        raise ValueError("Invalid quote attempt pair")
    if event["instrument"] != _INSTRUMENTS[pair]:
        raise ValueError("Invalid quote attempt instrument")
    for field in ("window_start_ns", "window_end_ns"):
        if (not isinstance(event[field], str)
                or not re.fullmatch(r"0|[1-9][0-9]{0,20}", event[field])):
            raise ValueError("Invalid quote attempt window")
    start, end = int(event["window_start_ns"]), int(event["window_end_ns"])
    if start % _DAY_NS or end - start != _DAY_NS:
        raise ValueError("Invalid quote attempt window")
    if not _is_hash(event["implementation_sha256"]) or event["client_version"] != CLIENT_VERSION:
        raise ValueError("Invalid quote attempt provenance")
    stamp = event["occurred_at"]
    try:
        if not isinstance(stamp, str):
            raise ValueError
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        if parsed.astimezone(UTC).isoformat() != stamp:
            raise ValueError
    except (ValueError, OverflowError):
        raise ValueError("Invalid quote attempt time") from None
    limits = event["limits"]
    if not isinstance(limits, dict) or set(limits) != set(_MAX_LIMITS):
        raise ValueError("Invalid quote attempt limits")
    if any(type(limits[key]) is not int or not 1 <= limits[key] <= bound
           for key, bound in _MAX_LIMITS.items()):
        raise ValueError("Invalid quote attempt limits")
    if limits["max_total_bytes"] < limits["max_page_bytes"]:
        raise ValueError("Invalid quote attempt limits")
    if event["kind"] == "started":
        if sequence != 0 or event["previous_event_sha256"] is not None:
            raise ValueError("Invalid quote attempt start")
        _manifest(event["runtime_manifest_json"], event["implementation_sha256"])
    elif event["kind"] in ("page_saved", "finished"):
        if sequence == 0 or not _is_hash(event["previous_event_sha256"]):
            raise ValueError("Invalid quote attempt predecessor")
        if event["runtime_manifest_json"] is not None:
            raise ValueError("Runtime manifest is start-only")
    else:
        raise ValueError("Invalid quote attempt kind")
    if event["kind"] == "page_saved":
        if not _is_hash(event["capture_sha256"]) or sequence > limits["max_pages"]:
            raise ValueError("Invalid quote attempt capture")
    elif event["capture_sha256"] is not None:
        raise ValueError("Capture hash is page-only")
    if event["kind"] == "finished":
        reason = event["reason"]
        if not isinstance(reason, str) or reason not in _REASONS:
            raise ValueError("Invalid quote attempt terminal reason")
        if event["status"] != ("complete" if reason == "completed" else "failed"):
            raise ValueError("Invalid quote attempt terminal status")
        snapshot = event["snapshot_sha256"]
        if snapshot is not None and not _is_hash(snapshot):
            raise ValueError("Invalid quote attempt snapshot")
        if event["status"] == "complete" and (snapshot is None or sequence == 1):
            raise ValueError("Completed acquisition requires captured snapshot")
        if sequence == 1 and snapshot is not None:
            raise ValueError("Zero-page attempt cannot have a snapshot")
        if sequence > limits["max_pages"] + 1:
            raise ValueError("Invalid quote attempt terminal sequence")
    elif (event["status"] != "running" or event["reason"] is not None
          or event["snapshot_sha256"] is not None):
        raise ValueError("Invalid quote attempt running status")
    unsigned = canonical_json({key: value for key, value in event.items() if key != "event_sha256"})
    if len(unsigned.encode("utf-8")) > 65_536:
        raise ValueError("Serialized quote attempt exceeds 64 KiB")
    if not _is_hash(event["event_sha256"]) or event["event_sha256"] != _hash(unsigned):
        raise ValueError("Quote attempt fingerprint mismatch")


def make_quote_acquisition_event(
    common: Mapping[str, Any], *, sequence: int, previous_event_sha256: str | None,
    kind: str, occurred_at: datetime, capture_sha256: str | None = None,
    snapshot_sha256: str | None = None, status: str = "running", reason: str | None = None,
) -> dict[str, Any]:
    """Build a detached strict event; every outgoing event validates before persistence."""
    if not isinstance(common, Mapping) or set(common) != _COMMON:
        raise ValueError("Invalid quote attempt common fields")
    if (not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None
            or occurred_at.utcoffset() is None):
        raise ValueError("Quote attempt time must be timezone-aware")
    event = dict(common) | {
        "version": "quote-acquisition-event-v1", "sequence": sequence,
        "previous_event_sha256": previous_event_sha256, "kind": kind,
        "occurred_at": occurred_at.astimezone(UTC).isoformat(),
        "capture_sha256": capture_sha256, "snapshot_sha256": snapshot_sha256,
        "status": status, "reason": reason,
    }
    if kind != "started":
        event["runtime_manifest_json"] = None
    # Validate original scalar types before JSON detachment can normalize them.
    event["event_sha256"] = _hash(canonical_json(event))
    validate_quote_acquisition_event(event)
    return dict(json.loads(canonical_json(event)))
