"""Deterministic daily reference construction from captured quote pages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Context, Decimal, localcontext
from typing import Any

from src.research.quote_capture import canonical_json, validate_quote_page

SERIES_ID = "massive-fx-bbo-mid-utc-v1"
ALGORITHM_VERSION = "quote-midpoint-utc-v1"
_MAX_PRICE_DIGITS = 128
_MAX_PRICE_EXPONENT = 128
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("validated manifest timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("validated manifest timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("validated manifest timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _reject_constant(_: str) -> None:
    raise ValueError("non-finite JSON number")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load_body(value: object) -> object:
    if not isinstance(value, str):
        raise ValueError("body_text must be a string")
    return json.loads(
        value,
        parse_float=Decimal,
        parse_int=int,
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicate_pairs,
    )


def _datetime_ns(value: datetime) -> int:
    delta = value - _EPOCH
    return (
        (delta.days * 86_400 + delta.seconds) * 1_000_000_000
        + delta.microseconds * 1_000
    )


def _as_price(value: object) -> tuple[Decimal | None, bool]:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return None, False
    price = value if isinstance(value, Decimal) else Decimal(value)
    if not price.is_finite() or price <= 0:
        return None, False
    exponent = price.as_tuple().exponent
    assert isinstance(exponent, int)
    if (
        len(price.as_tuple().digits) > _MAX_PRICE_DIGITS
        or abs(exponent) > _MAX_PRICE_EXPONENT
        or abs(price.adjusted()) > _MAX_PRICE_EXPONENT
    ):
        return None, True
    return price, False


def _midpoint(bid: Decimal, ask: Decimal) -> Decimal:
    # Aligning very different exponents can require more precision than the
    # process-wide Decimal context. This local bound keeps the sum exact.
    precision = max(len(bid.as_tuple().digits), len(ask.as_tuple().digits))
    precision += abs(bid.adjusted() - ask.adjusted()) + 4
    arithmetic_context = Context(prec=precision, Emin=-999_999, Emax=999_999)
    with localcontext(arithmetic_context):
        return (bid + ask) / Decimal(2)


def _decimal_text(value: Decimal) -> str:
    return canonical_json(value)


def _base_result(
    first: Mapping[str, Any], *, as_of_text: str, capture_hashes: list[str]
) -> dict[str, Any]:
    fingerprint = canonical_json(
        {"algorithm_version": ALGORITHM_VERSION, "capture_sha256": capture_hashes}
    )
    return {
        "series_id": SERIES_ID,
        "algorithm_version": ALGORITHM_VERSION,
        "pair": first["pair"],
        "instrument": first["instrument"],
        "window_start_ns": first["window_start_ns"],
        "window_end_ns": first["window_end_ns"],
        "as_of": as_of_text,
        "capture_sha256": capture_hashes,
        "input_sha256": hashlib.sha256(fingerprint.encode("utf-8")).hexdigest(),
        "acquisition_complete": False,
        "source_occurrence_count": 0,
        "distinct_row_count": 0,
        "duplicate_count": 0,
        "unique_timestamp_count": 0,
        "invalid_occurrence_count": 0,
        "out_of_window_count": 0,
        "first_timestamp_ns": None,
        "last_timestamp_ns": None,
        "first_event_offset_ns": None,
        "last_event_age_ns": None,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "ambiguous_open": False,
        "ambiguous_close": False,
        "exclusion_reasons": [],
        "provider_finality": "unknown",
        "project_maturity": "provisional",
        "validation_eligible": False,
    }


def build_quote_reference(
    pages: Sequence[Mapping[str, Any]], *, as_of: datetime
) -> dict[str, Any]:
    """Build a provisional exact-midpoint reference from immutable page manifests."""
    if not pages:
        raise ValueError("at least one quote page is required")
    as_of_text = _utc_text(as_of)
    as_of_utc = as_of.astimezone(UTC)

    # No cross-page or body interpretation is allowed until every individual
    # capture has passed its own integrity validation.
    for page in pages:
        validate_quote_page(page)

    capture_hashes = [str(page["capture_sha256"]) for page in pages]
    result = _base_result(pages[0], as_of_text=as_of_text, capture_hashes=capture_hashes)
    reasons: set[str] = {"coverage_policy_unverified"}

    first = pages[0]
    window_end_ns = int(first["window_end_ns"])
    if _datetime_ns(as_of_utc) < window_end_ns:
        reasons.add("window_not_closed_as_of")
    for field in ("pair", "instrument", "window_start_ns", "window_end_ns"):
        if any(page[field] != first[field] for page in pages[1:]):
            reasons.add(f"inconsistent_{field}")
    fixed_parameters = first["request_parameters"]
    for page in pages[1:]:
        if any(
            key in page["request_parameters"]
            and page["request_parameters"][key] != fixed_parameters[key]
            for key in fixed_parameters
        ):
            reasons.add("inconsistent_request_parameters")

    indices = [page["page_index"] for page in pages]
    if indices != list(range(len(pages))):
        reasons.add("out_of_order_pages")
    if len(capture_hashes) != len(set(capture_hashes)):
        reasons.add("duplicate_capture_hash")

    request_cursors = [page["request_cursor_sha256"] for page in pages]
    next_cursors = [page["next_cursor_sha256"] for page in pages]
    if request_cursors[0] is not None:
        reasons.add("broken_cursor_chain")
    for index in range(1, len(pages)):
        if request_cursors[index] != next_cursors[index - 1]:
            reasons.add("broken_cursor_chain")
    if next_cursors[-1] is not None:
        reasons.add("missing_last_page")
    requested_cursor_values = [cursor for cursor in request_cursors if cursor is not None]
    next_cursor_values = [cursor for cursor in next_cursors if cursor is not None]
    if (
        len(requested_cursor_values) != len(set(requested_cursor_values))
        or len(next_cursor_values) != len(set(next_cursor_values))
    ):
        reasons.add("cursor_cycle")

    previous_requested: datetime | None = None
    previous_received: datetime | None = None
    parsed_bodies: list[dict[str, Any]] = []
    for page in pages:
        requested = _parse_datetime(page["requested_at"])
        received = _parse_datetime(page["received_at"])
        if _datetime_ns(requested) < window_end_ns:
            reasons.add("request_before_window_end")
        if received > as_of_utc:
            reasons.add("receipt_after_as_of")
        if previous_requested is not None and requested < previous_requested:
            reasons.add("nonmonotonic_acquisition")
        if previous_received is not None and received < previous_received:
            reasons.add("nonmonotonic_acquisition")
        if previous_received is not None and requested < previous_received:
            reasons.add("overlapping_acquisition")
        previous_requested = requested
        previous_received = received

        if page["http_status"] != 200:
            reasons.add("http_status_not_ok")
        for issue in page["issues"]:
            reasons.add(f"manifest_issue:{issue}")
        try:
            body = _load_body(page["body_text"])
        except (TypeError, ValueError, json.JSONDecodeError, RecursionError, OverflowError):
            reasons.add("invalid_body")
            continue
        if not isinstance(body, dict) or body.get("status") != "OK":
            reasons.add("invalid_status")
            continue
        if "results" not in body or not isinstance(body["results"], list):
            reasons.add("invalid_schema")
            continue
        parsed_bodies.append(body)

    acquisition_defects = reasons - {"coverage_policy_unverified"}
    if acquisition_defects:
        result["exclusion_reasons"] = sorted(reasons)
        return result

    result["acquisition_complete"] = True
    occurrences = [row for body in parsed_bodies for row in body["results"]]
    signatures = [canonical_json(row) for row in occurrences]
    result["source_occurrence_count"] = len(occurrences)
    result["distinct_row_count"] = len(set(signatures))
    result["duplicate_count"] = len(signatures) - len(set(signatures))

    start_ns = int(first["window_start_ns"])
    end_ns = int(first["window_end_ns"])
    valid: list[tuple[int, Decimal]] = []
    invalid_count = 0
    out_of_window_count = 0
    for row in occurrences:
        if not isinstance(row, dict):
            invalid_count += 1
            continue
        timestamp = row.get("participant_timestamp")
        bid, bid_limit = _as_price(row.get("bid_price"))
        ask, ask_limit = _as_price(row.get("ask_price"))
        if bid_limit or ask_limit:
            reasons.add("numeric_limit_exceeded")
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, int)
            or bid is None
            or ask is None
            or bid > ask
        ):
            invalid_count += 1
            continue
        if not start_ns <= timestamp < end_ns:
            out_of_window_count += 1
            continue
        valid.append((timestamp, _midpoint(bid, ask)))

    result["invalid_occurrence_count"] = invalid_count
    result["out_of_window_count"] = out_of_window_count
    if invalid_count:
        reasons.add("invalid_quote_occurrence")
    if out_of_window_count:
        reasons.add("out_of_window_occurrence")
    if not valid:
        reasons.add("no_valid_quotes")
        result["exclusion_reasons"] = sorted(reasons)
        return result

    timestamps = {timestamp for timestamp, _ in valid}
    first_timestamp = min(timestamps)
    last_timestamp = max(timestamps)
    result["unique_timestamp_count"] = len(timestamps)
    result["first_timestamp_ns"] = str(first_timestamp)
    result["last_timestamp_ns"] = str(last_timestamp)
    result["first_event_offset_ns"] = str(first_timestamp - start_ns)
    result["last_event_age_ns"] = str(end_ns - last_timestamp)

    midpoints = [midpoint for _, midpoint in valid]
    result["high"] = _decimal_text(max(midpoints))
    result["low"] = _decimal_text(min(midpoints))
    first_midpoints = {midpoint for timestamp, midpoint in valid if timestamp == first_timestamp}
    last_midpoints = {midpoint for timestamp, midpoint in valid if timestamp == last_timestamp}
    result["ambiguous_open"] = len(first_midpoints) > 1
    result["ambiguous_close"] = len(last_midpoints) > 1
    if result["ambiguous_open"]:
        reasons.add("ambiguous_open")
    else:
        result["open"] = _decimal_text(next(iter(first_midpoints)))
    if result["ambiguous_close"]:
        reasons.add("ambiguous_close")
    else:
        result["close"] = _decimal_text(next(iter(last_midpoints)))
    result["exclusion_reasons"] = sorted(reasons)
    return result
