"""Pure reconciliation of immutable quote snapshots and retained source rows."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.research.quote_capture import canonical_json, validate_quote_page
from src.research.quote_reference import build_quote_reference

_MAX_SNAPSHOT_BYTES = 1024 * 1024
_MAX_PAGES = 10_000
_MAX_RAW_BYTES_PER_SIDE = 268_435_456
_MAX_BODY_BYTES_PER_PAGE = 33_554_432
_MAX_BODY_BYTES_PER_SIDE = 536_870_912
_SNAPSHOT_FIELDS = {"version", "implementation_sha256", "client_version", "reference"}
_REFERENCE_CHANGE_FIELDS = (
    "ambiguous_close",
    "ambiguous_open",
    "close",
    "first_event_offset_ns",
    "first_timestamp_ns",
    "high",
    "invalid_occurrence_count",
    "last_event_age_ns",
    "last_timestamp_ns",
    "low",
    "open",
    "out_of_window_count",
    "unique_timestamp_count",
)


def _reject_constant(_: str) -> None:
    raise ValueError("Non-finite JSON number")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _strict_json(value: str) -> Any:
    try:
        return json.loads(
            value,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError("Invalid strict JSON") from exc


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _canonical_reference_as_of(reference: Any) -> tuple[dict[str, Any], datetime]:
    if not isinstance(reference, dict):
        raise ValueError("Snapshot reference must be an object")
    value = reference.get("as_of")
    if not isinstance(value, str):
        raise ValueError("Snapshot reference as_of must be a string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Snapshot reference as_of is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Snapshot reference as_of must be timezone-aware")
    parsed = parsed.astimezone(UTC)
    if parsed.isoformat() != value:
        raise ValueError("Snapshot reference as_of must be canonical UTC")
    return reference, parsed


def _load_snapshot(envelope: Mapping[str, Any]) -> tuple[dict[str, Any], datetime]:
    if not isinstance(envelope, Mapping) or set(envelope) != {
        "snapshot_sha256",
        "unsigned_json",
    }:
        raise ValueError("Snapshot envelope must contain exact fields")
    fingerprint = envelope["snapshot_sha256"]
    unsigned = envelope["unsigned_json"]
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("Snapshot fingerprint must be lowercase SHA-256")
    if not isinstance(unsigned, str):
        raise ValueError("Snapshot unsigned_json must be text")
    try:
        encoded = unsigned.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Snapshot unsigned_json must be valid UTF-8 text") from exc
    if len(encoded) > _MAX_SNAPSHOT_BYTES:
        raise ValueError("Snapshot unsigned_json exceeds 1 MiB")
    if hashlib.sha256(encoded).hexdigest() != fingerprint:
        raise ValueError("Snapshot fingerprint mismatch")
    document = _strict_json(unsigned)
    if not isinstance(document, dict) or set(document) != _SNAPSHOT_FIELDS:
        raise ValueError("Snapshot document must contain exact fields")
    if document["version"] != "quote-snapshot-v1":
        raise ValueError("Unsupported quote snapshot version")
    implementation = document["implementation_sha256"]
    client_version = document["client_version"]
    if not isinstance(implementation, str) or not re.fullmatch(
        r"[0-9a-f]{64}", implementation
    ):
        raise ValueError("Invalid snapshot implementation fingerprint")
    if not isinstance(client_version, str) or not re.fullmatch(
        r"[a-zA-Z0-9._-]{1,128}", client_version
    ):
        raise ValueError("Invalid snapshot client version")
    reference, reference_as_of = _canonical_reference_as_of(document["reference"])
    document["reference"] = reference
    return document, reference_as_of


def _preflight_pages(pages: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("Quote pages must be a sequence")
    if not 1 <= len(pages) <= _MAX_PAGES:
        raise ValueError("Each snapshot requires between 1 and 10000 pages")
    detached = tuple(pages)
    raw_total = 0
    body_total = 0
    for page in detached:
        if not isinstance(page, Mapping):
            raise ValueError("Every quote page must be an object")
        raw_size = page.get("raw_size_bytes")
        body_text = page.get("body_text")
        if type(raw_size) is not int or raw_size < 0:
            raise ValueError("Quote page raw_size_bytes must be a nonnegative integer")
        if not isinstance(body_text, str):
            raise ValueError("Quote page body_text must be text")
        try:
            body_size = len(body_text.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("Quote page body_text must be valid UTF-8 text") from exc
        if body_size > _MAX_BODY_BYTES_PER_PAGE:
            raise ValueError("Quote page body_text exceeds 32 MiB")
        raw_total += raw_size
        body_total += body_size
        if raw_total > _MAX_RAW_BYTES_PER_SIDE:
            raise ValueError("Quote pages exceed the 256 MiB raw-byte ceiling")
        if body_total > _MAX_BODY_BYTES_PER_SIDE:
            raise ValueError("Quote pages exceed the 512 MiB retained-text ceiling")
    return detached


def _validated_reference(
    pages: Sequence[Mapping[str, Any]], document: Mapping[str, Any]
) -> dict[str, Any]:
    reference, reference_as_of = _canonical_reference_as_of(document["reference"])
    for page in pages:
        validate_quote_page(page)
    identity_fields = ("pair", "instrument", "window_start_ns", "window_end_ns")
    if any(
        page[field] != pages[0][field]
        for page in pages[1:]
        for field in identity_fields
    ):
        raise ValueError("Snapshot pages must share one pair, instrument and UTC window")
    rebuilt = build_quote_reference(pages, as_of=reference_as_of)
    try:
        matches = _strict_equal(reference, rebuilt)
    except RecursionError as exc:
        raise ValueError("Snapshot reference nesting exceeds comparison limit") from exc
    if not matches:
        raise ValueError("Stored snapshot reference does not match supplied pages")
    return rebuilt


def _row_multiset(
    pages: Sequence[Mapping[str, Any]], signatures_by_hash: dict[str, str]
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for page in pages:
        body = _strict_json(page["body_text"])
        if (
            not isinstance(body, dict)
            or body.get("status") != "OK"
            or not isinstance(body.get("results"), list)
        ):
            raise ValueError("Complete acquisition contains an invalid retained body")
        for row in body["results"]:
            signature = canonical_json(row)
            row_hash = hashlib.sha256(signature.encode("utf-8")).hexdigest()
            previous = signatures_by_hash.setdefault(row_hash, signature)
            if previous != signature:
                raise ValueError("Retained-row SHA-256 collision")
            counts[row_hash] += 1
    return counts


def _counts(counts: Counter[str]) -> dict[str, int]:
    occurrence_count = sum(counts.values())
    distinct_count = len(counts)
    return {
        "occurrence_count": occurrence_count,
        "distinct_row_count": distinct_count,
        "duplicate_count": occurrence_count - distinct_count,
    }


def _content_sha256(counts: Counter[str]) -> str:
    inventory = [
        {"row_sha256": row_hash, "count": counts[row_hash]}
        for row_hash in sorted(counts)
    ]
    return hashlib.sha256(canonical_json(inventory).encode("utf-8")).hexdigest()


def _reference_changes(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    return {
        field: {"before": before[field], "after": after[field]}
        for field in _REFERENCE_CHANGE_FIELDS
        if not _strict_equal(before[field], after[field])
    }


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Comparison as_of must be timezone-aware")
    return value.astimezone(UTC)


def reconcile_quote_snapshots(
    *,
    before: Mapping[str, Any],
    before_pages: Sequence[Mapping[str, Any]],
    after: Mapping[str, Any],
    after_pages: Sequence[Mapping[str, Any]],
    as_of: datetime,
) -> dict[str, Any]:
    """Compare complete retained-row multisets without inferring provider event identity."""
    comparison_as_of = _aware_utc(as_of)
    before_document, before_as_of = _load_snapshot(before)
    after_document, after_as_of = _load_snapshot(after)
    before_page_set = _preflight_pages(before_pages)
    after_page_set = _preflight_pages(after_pages)
    before_reference = _validated_reference(before_page_set, before_document)
    after_reference = _validated_reference(after_page_set, after_document)

    if not before_as_of <= after_as_of <= comparison_as_of:
        raise ValueError("Snapshot and comparison as_of values are reversed or future-dated")
    identity_fields = (
        "pair",
        "instrument",
        "window_start_ns",
        "window_end_ns",
        "series_id",
        "algorithm_version",
    )
    if any(
        not _strict_equal(before_reference[field], after_reference[field])
        for field in identity_fields
    ):
        raise ValueError("Quote snapshots do not describe the same series and UTC window")

    reasons: list[str] = []
    if not before_reference["acquisition_complete"]:
        reasons.append("before_acquisition_incomplete")
    if not after_reference["acquisition_complete"]:
        reasons.append("after_acquisition_incomplete")
    comparable = not reasons

    before_counts: dict[str, int] | None = None
    after_counts: dict[str, int] | None = None
    before_content_hash: str | None = None
    after_content_hash: str | None = None
    source_changed: bool | None = None
    retained_count: int | None = None
    added_count: int | None = None
    removed_count: int | None = None
    changes: list[dict[str, Any]] | None = None
    reference_changes: dict[str, dict[str, Any]] | None = None

    if comparable:
        signatures_by_hash: dict[str, str] = {}
        before_rows = _row_multiset(before_page_set, signatures_by_hash)
        after_rows = _row_multiset(after_page_set, signatures_by_hash)
        before_counts = _counts(before_rows)
        after_counts = _counts(after_rows)
        for counts, reference in (
            (before_counts, before_reference),
            (after_counts, after_reference),
        ):
            expected = {
                "occurrence_count": reference["source_occurrence_count"],
                "distinct_row_count": reference["distinct_row_count"],
                "duplicate_count": reference["duplicate_count"],
            }
            if not _strict_equal(counts, expected):
                raise ValueError("Retained-row counts disagree with rebuilt reference")
        before_content_hash = _content_sha256(before_rows)
        after_content_hash = _content_sha256(after_rows)
        source_changed = before_content_hash != after_content_hash
        retained_count = sum(
            min(before_rows[row_hash], after_rows[row_hash])
            for row_hash in before_rows.keys() | after_rows.keys()
        )
        changes = []
        added_count = 0
        removed_count = 0
        for row_hash in sorted(before_rows.keys() | after_rows.keys()):
            before_count = before_rows[row_hash]
            after_count = after_rows[row_hash]
            delta = after_count - before_count
            if not delta:
                continue
            changes.append(
                {
                    "row_sha256": row_hash,
                    "before_count": before_count,
                    "after_count": after_count,
                    "delta": delta,
                }
            )
            if delta > 0:
                added_count += delta
            else:
                removed_count -= delta
        reference_changes = _reference_changes(before_reference, after_reference)

    result: dict[str, Any] = {
        "version": "quote-reconciliation-v1",
        "comparison_algorithm": "retained-row-multiset-v1",
        "as_of": comparison_as_of.isoformat(),
        "pair": before_reference["pair"],
        "instrument": before_reference["instrument"],
        "series_id": before_reference["series_id"],
        "algorithm_version": before_reference["algorithm_version"],
        "window_start_ns": before_reference["window_start_ns"],
        "window_end_ns": before_reference["window_end_ns"],
        "before_snapshot_sha256": before["snapshot_sha256"],
        "after_snapshot_sha256": after["snapshot_sha256"],
        "before_input_sha256": before_reference["input_sha256"],
        "after_input_sha256": after_reference["input_sha256"],
        "before_implementation_sha256": before_document["implementation_sha256"],
        "after_implementation_sha256": after_document["implementation_sha256"],
        "before_client_version": before_document["client_version"],
        "after_client_version": after_document["client_version"],
        "snapshot_changed": before["snapshot_sha256"] != after["snapshot_sha256"],
        "implementation_changed": (
            before_document["implementation_sha256"]
            != after_document["implementation_sha256"]
            or before_document["client_version"] != after_document["client_version"]
        ),
        "comparable": comparable,
        "exclusion_reasons": sorted(reasons),
        "before_content_sha256": before_content_hash,
        "after_content_sha256": after_content_hash,
        "source_content_changed": source_changed,
        "before_counts": before_counts,
        "after_counts": after_counts,
        "retained_occurrence_count": retained_count,
        "added_occurrence_count": added_count,
        "removed_occurrence_count": removed_count,
        "changes": changes,
        "reference_changes": reference_changes,
        "event_lineage": "ambiguous",
        "provider_finality": "unknown",
        "project_maturity": "provisional",
        "validation_eligible": False,
    }
    result["reconciliation_sha256"] = hashlib.sha256(
        canonical_json(result).encode("utf-8")
    ).hexdigest()
    return result
