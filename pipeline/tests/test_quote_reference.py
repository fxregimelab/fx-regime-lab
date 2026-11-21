"""Adversarial contract tests for deterministic quote reference construction."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal, Overflow, Underflow, localcontext
from fractions import Fraction
from typing import Any

import pytest

from src.research.quote_capture import capture_quote_page
from src.research.quote_reference import build_quote_reference

DAY_NS = 86_400_000_000_000
CAPTURED_AT = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
PAIR_INSTRUMENTS = {
    "EURUSD": "C:EUR-USD",
    "USDJPY": "C:USD-JPY",
    "USDINR": "C:USD-INR",
}


def _page(
    body: str | dict[str, Any],
    *,
    pair: str = "EURUSD",
    page_index: int = 0,
    cursor: str | None = None,
    next_cursor: str | None = None,
    status: int = 200,
    requested_at: datetime | None = None,
    received_at: datetime | None = None,
    window_start_ns: int = 0,
    limit: str = "50000",
) -> dict[str, Any]:
    instrument = PAIR_INSTRUMENTS[pair]
    request_time = requested_at or CAPTURED_AT + timedelta(seconds=page_index * 2)
    receipt_time = received_at or request_time + timedelta(seconds=1)
    request_params = {
        "timestamp.gte": str(window_start_ns),
        "timestamp.lt": str(window_start_ns + DAY_NS),
        "sort": "timestamp",
        "order": "asc",
        "limit": limit,
    }
    if cursor is not None:
        request_params["cursor"] = cursor
    if isinstance(body, dict):
        payload = dict(body)
        if next_cursor is not None:
            payload["next_url"] = (
                f"https://api.massive.com/v3/quotes/{instrument}?cursor={next_cursor}"
            )
        body_text = json.dumps(payload, separators=(",", ":"))
    else:
        if next_cursor is not None:
            raise AssertionError("string bodies must include their own next_url")
        body_text = body
    return capture_quote_page(
        pair=pair,
        instrument=instrument,
        window_start_ns=window_start_ns,
        window_end_ns=window_start_ns + DAY_NS,
        page_index=page_index,
        requested_at=request_time,
        received_at=receipt_time,
        status_code=status,
        body=body_text.encode(),
        request_params=request_params,
        response_headers={"content-type": "application/json"},
    )


def _quote(timestamp: int, bid: int | str, ask: int | str, **extra: Any) -> str:
    fields = [
        f'"participant_timestamp":{timestamp}',
        f'"bid_price":{bid}',
        f'"ask_price":{ask}',
    ]
    fields.extend(f"{json.dumps(key)}:{json.dumps(value)}" for key, value in extra.items())
    return "{" + ",".join(fields) + "}"


def _body(*quotes: str) -> str:
    return '{"results":[' + ",".join(quotes) + '],"status":"OK"}'


def test_rejects_empty_pages_naive_as_of_and_tampered_manifest() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_quote_reference([], as_of=CAPTURED_AT)
    page = _page(_body(_quote(0, "1.0", "1.2")))
    with pytest.raises(ValueError, match="timezone-aware"):
        build_quote_reference([page], as_of=CAPTURED_AT.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        build_quote_reference([page], as_of="2026-09-27")  # type: ignore[arg-type]
    page["body_text"] = _body(_quote(0, "9", "10"))
    with pytest.raises(ValueError):
        build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))


def test_exact_nanosecond_boundaries_and_decimal_midpoints() -> None:
    page = _page(
        _body(
            _quote(0, "1.0000000000000000001", "1.0000000000000000003"),
            _quote(DAY_NS - 1, "1.2", "1.4"),
        )
    )
    result = build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["acquisition_complete"] is True
    assert result["open"] == "1.0000000000000000002"
    assert result["close"] == "1.3"
    assert result["low"] == "1.0000000000000000002"
    assert result["high"] == "1.3"
    assert result["first_timestamp_ns"] == "0"
    assert result["last_timestamp_ns"] == str(DAY_NS - 1)
    assert result["first_event_offset_ns"] == "0"
    assert result["last_event_age_ns"] == "1"
    assert result["exclusion_reasons"] == ["coverage_policy_unverified"]
    assert result["project_maturity"] == "provisional"
    assert result["validation_eligible"] is False


def test_midpoint_is_exact_under_hostile_ambient_decimal_context() -> None:
    generator = random.Random(20260927)
    cases: list[tuple[str, str]] = []
    for _ in range(128):
        exponent = generator.randint(-20, 20)
        bid_coefficient = generator.randint(10**16, 10**17 - 1)
        ask_coefficient = bid_coefficient + generator.randint(0, 10**15)
        cases.append((f"{bid_coefficient}e{exponent}", f"{ask_coefficient}e{exponent}"))
    cases.extend(
        [
            ("1e-128", "1e128"),
            ("1.234567890123456789e-100", "9.876543210987654321e100"),
        ]
    )

    with localcontext() as context:
        context.prec = 3
        context.Emin = -9
        context.Emax = 9
        context.traps[Overflow] = True
        context.traps[Underflow] = True
        for bid, ask in cases:
            page = _page(_body(_quote(1, bid, ask)))
            result = build_quote_reference(
                [page], as_of=CAPTURED_AT + timedelta(hours=1)
            )
            expected = (Fraction(Decimal(bid)) + Fraction(Decimal(ask))) / 2
            assert Fraction(Decimal(result["open"])) == expected


@pytest.mark.parametrize(
    "price",
    ["1234567890123456789012345678901234567890" * 4, "1e129", "1e-129"],
)
def test_prices_outside_numeric_resource_envelope_are_retained_but_invalid(
    price: str,
) -> None:
    page = _page(_body(_quote(1, price, price)))
    result = build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["acquisition_complete"] is True
    assert result["source_occurrence_count"] == 1
    assert result["invalid_occurrence_count"] == 1
    assert result["open"] is None
    assert "numeric_limit_exceeded" in result["exclusion_reasons"]


def test_daily_window_must_be_closed_before_request_and_as_of() -> None:
    window_end = datetime(1970, 1, 2, tzinfo=UTC)
    closed = _page(
        _body(_quote(1, "1", "1")),
        requested_at=window_end,
        received_at=window_end,
    )
    complete = build_quote_reference([closed], as_of=window_end)
    assert complete["acquisition_complete"] is True

    intraday_time = window_end - timedelta(hours=12)
    intraday = _page(
        _body(_quote(1, "1", "1")),
        requested_at=intraday_time,
        received_at=intraday_time,
    )
    incomplete = build_quote_reference(
        [intraday], as_of=intraday_time + timedelta(seconds=1)
    )
    assert incomplete["acquisition_complete"] is False
    assert {"request_before_window_end", "window_not_closed_as_of"} <= set(
        incomplete["exclusion_reasons"]
    )
    assert incomplete["open"] is None


def test_deep_invalid_json_is_diagnostic_instead_of_escaping_parser_errors() -> None:
    page = _page("[" * 2_000 + "0" + "]" * 2_000)
    result = build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["acquisition_complete"] is False
    assert "manifest_issue:invalid_json" in result["exclusion_reasons"]
    assert {"invalid_body", "invalid_status"} & set(result["exclusion_reasons"])
    assert result["open"] is None
    assert result["first_timestamp_ns"] is None


def test_occurrences_duplicates_invalid_rows_and_timestamp_ties_are_separate() -> None:
    first = _quote(0, "1.0", "1.2", exchange=7)
    page = _page(
        _body(
            first,
            first,
            _quote(0, "1.1", "1.3", exchange=9),
            _quote(10, "1.2", "1.4"),
            _quote(11, "2", "1"),
            _quote(DAY_NS, "1", "1"),
        )
    )
    result = build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["source_occurrence_count"] == 6
    assert result["distinct_row_count"] == 5
    assert result["duplicate_count"] == 1
    assert result["invalid_occurrence_count"] == 1
    assert result["out_of_window_count"] == 1
    assert result["unique_timestamp_count"] == 2
    assert result["ambiguous_open"] is True
    assert result["open"] is None
    assert result["ambiguous_close"] is False
    assert result["close"] == "1.3"
    assert result["low"] == "1.1"
    assert result["high"] == "1.3"
    assert set(result["exclusion_reasons"]) == {
        "ambiguous_open",
        "coverage_policy_unverified",
        "invalid_quote_occurrence",
        "out_of_window_occurrence",
    }


def test_equal_midpoint_ties_are_not_ambiguous_but_distinct_close_ties_are() -> None:
    equal = _page(
        _body(
            _quote(1, "1", "3"),
            _quote(1, "1.5", "2.5"),
            _quote(2, "3", "3"),
        )
    )
    equal_result = build_quote_reference(
        [equal], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert equal_result["ambiguous_open"] is False
    assert equal_result["open"] == "2"

    ambiguous = _page(
        _body(
            _quote(1, "1", "1"),
            _quote(2, "2", "2"),
            _quote(2, "3", "3"),
        )
    )
    ambiguous_result = build_quote_reference(
        [ambiguous], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert ambiguous_result["ambiguous_close"] is True
    assert ambiguous_result["close"] is None
    assert "ambiguous_close" in ambiguous_result["exclusion_reasons"]


def test_complete_empty_snapshot_is_visible_but_has_no_bar() -> None:
    result = build_quote_reference(
        [_page({"status": "OK", "results": []})],
        as_of=CAPTURED_AT + timedelta(hours=1),
    )
    assert result["acquisition_complete"] is True
    assert result["source_occurrence_count"] == 0
    assert result["open"] is None
    assert result["exclusion_reasons"] == ["coverage_policy_unverified", "no_valid_quotes"]


def test_ordered_capture_lineage_and_input_hash_ignore_as_of() -> None:
    first = _page(
        {"status": "OK", "results": [{"participant_timestamp": 1, "bid_price": 1, "ask_price": 1}]},
        next_cursor="page-two",
    )
    second = _page(
        {"status": "OK", "results": [{"participant_timestamp": 2, "bid_price": 2, "ask_price": 2}]},
        page_index=1,
        cursor="page-two",
    )
    early = build_quote_reference([first, second], as_of=CAPTURED_AT + timedelta(hours=1))
    late = build_quote_reference([first, second], as_of=CAPTURED_AT + timedelta(days=1))
    assert early["capture_sha256"] == [first["capture_sha256"], second["capture_sha256"]]
    assert early["input_sha256"] == late["input_sha256"]
    assert early["as_of"] != late["as_of"]
    assert early["open"] == "1"
    assert early["close"] == "2"


@pytest.mark.parametrize(
    ("pages", "reason"),
    [
        (
            lambda: [_page({"status": "OK", "results": []}, next_cursor="missing")],
            "missing_last_page",
        ),
        (lambda: [_page({"status": "ERROR", "results": []}, status=500)], "http_status_not_ok"),
        (lambda: [_page({"status": "OK"})], "invalid_schema"),
    ],
)
def test_incomplete_acquisitions_never_expose_prefix_statistics(
    pages: Any, reason: str
) -> None:
    result = build_quote_reference(pages(), as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["acquisition_complete"] is False
    assert reason in result["exclusion_reasons"]
    assert result["source_occurrence_count"] == 0
    assert result["first_timestamp_ns"] is None
    assert result["open"] is None
    assert result["high"] is None


def test_reordered_pages_and_cursor_cycle_are_explicit_defects() -> None:
    first = _page(
        {"status": "OK", "results": []},
        next_cursor="same-cursor",
    )
    second = _page(
        {"status": "OK", "results": []},
        page_index=1,
        cursor="same-cursor",
        next_cursor="same-cursor",
    )
    cyclic = build_quote_reference([first, second], as_of=CAPTURED_AT + timedelta(hours=1))
    assert {"cursor_cycle", "missing_last_page"} <= set(cyclic["exclusion_reasons"])
    reordered = build_quote_reference([second, first], as_of=CAPTURED_AT + timedelta(hours=1))
    assert reordered["capture_sha256"] == [second["capture_sha256"], first["capture_sha256"]]
    assert {"out_of_order_pages", "broken_cursor_chain"} <= set(
        reordered["exclusion_reasons"]
    )
    assert reordered["open"] is None


def test_broken_cursor_chain_is_distinct_from_a_cycle() -> None:
    first = _page({"status": "OK", "results": []}, next_cursor="cursor-a")
    second = _page(
        {"status": "OK", "results": []},
        page_index=1,
        cursor="cursor-b",
    )
    result = build_quote_reference([first, second], as_of=CAPTURED_AT + timedelta(hours=1))
    assert "broken_cursor_chain" in result["exclusion_reasons"]
    assert "cursor_cycle" not in result["exclusion_reasons"]


def test_cross_page_identity_fixed_parameters_and_duplicate_captures_fail_closed() -> None:
    first = _page({"status": "OK", "results": []}, next_cursor="cursor-c")
    other_pair = _page(
        {"status": "OK", "results": []},
        pair="USDJPY",
        page_index=1,
        cursor="cursor-c",
        limit="100",
        window_start_ns=DAY_NS,
    )
    inconsistent = build_quote_reference(
        [first, other_pair], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert {
        "inconsistent_pair",
        "inconsistent_instrument",
        "inconsistent_window_start_ns",
        "inconsistent_window_end_ns",
        "inconsistent_request_parameters",
    } <= set(inconsistent["exclusion_reasons"])
    assert inconsistent["acquisition_complete"] is False

    duplicate = build_quote_reference(
        [first, first], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert "duplicate_capture_hash" in duplicate["exclusion_reasons"]
    assert duplicate["open"] is None


def test_invalid_types_and_noninteger_source_timestamp_are_visible() -> None:
    invalid_type = _page(_body(_quote(1, '"1.0"', "1.2")))
    result = build_quote_reference(
        [invalid_type], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert result["acquisition_complete"] is True
    assert result["invalid_occurrence_count"] == 1
    assert result["open"] is None

    normalized_timestamp = _page(
        '{"results":[{"ask_price":1.2,"bid_price":1.1,'
        '"participant_timestamp":1.0}],"status":"OK"}'
    )
    normalized = build_quote_reference(
        [normalized_timestamp], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert normalized["acquisition_complete"] is False
    assert "manifest_issue:non_integer_quote_timestamp" in normalized["exclusion_reasons"]
    assert normalized["source_occurrence_count"] == 0


def test_failed_page_with_real_prefix_rows_never_constructs_ohlc() -> None:
    page = _page(_body(_quote(1, "1", "2")), status=503)
    result = build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["acquisition_complete"] is False
    assert result["source_occurrence_count"] == 0
    assert result["open"] is None
    assert result["high"] is None


def test_late_receipt_and_overlapping_acquisition_are_not_complete() -> None:
    first = _page({"status": "OK", "results": []}, next_cursor="opaque-123")
    second = _page(
        {"status": "OK", "results": []},
        page_index=1,
        cursor="opaque-123",
        requested_at=CAPTURED_AT + timedelta(milliseconds=500),
        received_at=CAPTURED_AT + timedelta(seconds=2),
    )
    result = build_quote_reference([first, second], as_of=CAPTURED_AT + timedelta(seconds=1))
    assert result["acquisition_complete"] is False
    assert {"overlapping_acquisition", "receipt_after_as_of"} <= set(
        result["exclusion_reasons"]
    )


def test_corrected_capture_changes_fingerprint_without_mutating_old_result() -> None:
    original_page = _page(_body(_quote(1, "1", "1")))
    corrected_page = _page(_body(_quote(1, "2", "2")))
    original = build_quote_reference(
        [original_page], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    corrected = build_quote_reference(
        [corrected_page], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    repeated = build_quote_reference(
        [original_page], as_of=CAPTURED_AT + timedelta(hours=1)
    )
    assert original["capture_sha256"] != corrected["capture_sha256"]
    assert original["input_sha256"] != corrected["input_sha256"]
    assert original == repeated
    assert original["open"] == "1"
    assert corrected["open"] == "2"


@pytest.mark.parametrize("pair", list(PAIR_INSTRUMENTS))
def test_locked_pair_manifest_consistency(pair: str) -> None:
    page = _page(_body(_quote(1, "1", "1")), pair=pair)
    result = build_quote_reference([page], as_of=CAPTURED_AT + timedelta(hours=1))
    assert result["pair"] == pair
    assert result["instrument"] == PAIR_INSTRUMENTS[pair]
    assert result["validation_eligible"] is False
