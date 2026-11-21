"""Independent contract tests for pure immutable quote-snapshot reconciliation."""

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal, getcontext, localcontext
from typing import Any

import pytest

from src.research.quote_capture import canonical_json, capture_quote_page
from src.research.quote_reference import build_quote_reference
from src.research.quote_revision import reconcile_quote_snapshots

DAY_NS = 86_400_000_000_000
CAPTURED_AT = datetime(2026, 9, 27, tzinfo=UTC)
PARAMETERS = {
    "timestamp.gte": "0",
    "timestamp.lt": str(DAY_NS),
    "sort": "timestamp",
    "order": "asc",
    "limit": "50000",
}


def _row(timestamp: int, bid: str, ask: str, **extra: Any) -> dict[str, Any]:
    return {
        "participant_timestamp": timestamp,
        "bid_price": Decimal(bid),
        "ask_price": Decimal(ask),
        **extra,
    }


def _body(
    rows: list[Any], *, next_cursor: str | None = None,
    instrument: str = "C:EUR-USD",
) -> bytes:
    value: dict[str, Any] = {"status": "OK", "results": rows}
    if next_cursor is not None:
        value["next_url"] = (
            f"https://api.massive.com/v3/quotes/{instrument}?cursor=" + next_cursor
        )
    return canonical_json(value).encode()


def _page(
    rows: list[Any], *, page_index: int = 0, cursor: str | None = None,
    next_cursor: str | None = None, status: int = 200, pair: str = "EURUSD",
) -> dict[str, Any]:
    instruments = {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}
    instrument = instruments[pair]
    params = dict(PARAMETERS)
    if cursor is not None:
        params["cursor"] = cursor
    return capture_quote_page(
        pair=pair,
        instrument=instrument,
        window_start_ns=0,
        window_end_ns=DAY_NS,
        page_index=page_index,
        requested_at=CAPTURED_AT + timedelta(seconds=page_index * 2),
        received_at=CAPTURED_AT + timedelta(seconds=page_index * 2 + 1),
        status_code=status,
        body=_body(rows, next_cursor=next_cursor, instrument=instrument),
        request_params=params,
        response_headers={},
    )


def _snapshot(
    pages: list[dict[str, Any]], *, as_of: datetime | None = None,
    implementation: str = "a" * 64, client: str = "fixture-v1",
    whitespace: bool = False,
) -> dict[str, str]:
    reference = build_quote_reference(pages, as_of=as_of or CAPTURED_AT + timedelta(hours=1))
    document = {
        "version": "quote-snapshot-v1",
        "implementation_sha256": implementation,
        "client_version": client,
        "reference": reference,
    }
    unsigned = (
        json.dumps(json.loads(canonical_json(document)), indent=2)
        if whitespace
        else canonical_json(document)
    )
    return {
        "snapshot_sha256": hashlib.sha256(unsigned.encode()).hexdigest(),
        "unsigned_json": unsigned,
    }


def _reconcile(
    before_pages: list[dict[str, Any]], after_pages: list[dict[str, Any]],
    *, before_snapshot: dict[str, str] | None = None,
    after_snapshot: dict[str, str] | None = None,
) -> dict[str, Any]:
    return reconcile_quote_snapshots(
        before=before_snapshot or _snapshot(before_pages),
        before_pages=before_pages,
        after=after_snapshot or _snapshot(after_pages),
        after_pages=after_pages,
        as_of=CAPTURED_AT + timedelta(days=1),
    )


def test_identical_complete_snapshots_have_zero_full_diff_and_stable_hash() -> None:
    rows = [_row(1, "1.1", "1.3"), _row(2, "1.2", "1.4")]
    pages = [_page(rows)]
    first = _reconcile(pages, pages)
    second = _reconcile(pages, pages)
    assert first == second
    assert set(first) == {
        "version", "comparison_algorithm", "as_of", "pair", "instrument",
        "series_id", "algorithm_version", "window_start_ns", "window_end_ns",
        "before_snapshot_sha256", "after_snapshot_sha256", "before_input_sha256",
        "after_input_sha256", "before_implementation_sha256",
        "after_implementation_sha256", "before_client_version", "after_client_version",
        "snapshot_changed", "implementation_changed", "comparable", "exclusion_reasons",
        "before_content_sha256", "after_content_sha256", "source_content_changed",
        "before_counts", "after_counts", "retained_occurrence_count",
        "added_occurrence_count", "removed_occurrence_count", "changes",
        "reference_changes", "event_lineage", "provider_finality", "project_maturity",
        "validation_eligible", "reconciliation_sha256",
    }
    assert first["snapshot_changed"] is False
    assert first["source_content_changed"] is False
    assert first["before_counts"] == {
        "occurrence_count": 2,
        "distinct_row_count": 2,
        "duplicate_count": 0,
    }
    assert first["after_counts"] == first["before_counts"]
    assert first["retained_occurrence_count"] == 2
    assert first["added_occurrence_count"] == 0
    assert first["removed_occurrence_count"] == 0
    assert first["changes"] == []
    assert first["reference_changes"] == {}
    assert first["validation_eligible"] is False
    inventory = sorted(
        [
            {
                "row_sha256": hashlib.sha256(canonical_json(row).encode()).hexdigest(),
                "count": 1,
            }
            for row in rows
        ],
        key=lambda item: str(item["row_sha256"]),
    )
    assert first["before_content_sha256"] == hashlib.sha256(
        canonical_json(inventory).encode()
    ).hexdigest()
    unsigned = {key: value for key, value in first.items() if key != "reconciliation_sha256"}
    assert first["reconciliation_sha256"] == hashlib.sha256(
        canonical_json(unsigned).encode()
    ).hexdigest()


def test_metadata_only_snapshot_change_preserves_source_content() -> None:
    pages = [_page([_row(1, "1", "1")])]
    before = _snapshot(pages, whitespace=True)
    after = _snapshot(
        pages,
        as_of=CAPTURED_AT + timedelta(hours=2),
        implementation="b" * 64,
        client="fixture-v2",
    )
    result = _reconcile(pages, pages, before_snapshot=before, after_snapshot=after)
    assert result["snapshot_changed"] is True
    assert result["implementation_changed"] is True
    assert result["before_content_sha256"] == result["after_content_sha256"]
    assert result["source_content_changed"] is False
    assert result["changes"] == []
    assert result["reference_changes"] == {}


def test_repartitioned_rows_change_input_lineage_but_not_content() -> None:
    rows = [_row(1, "1", "1"), _row(2, "2", "2")]
    one_page = [_page(rows)]
    two_pages = [
        _page([rows[0]], next_cursor="opaque-two"),
        _page([rows[1]], page_index=1, cursor="opaque-two"),
    ]
    result = _reconcile(one_page, two_pages)
    assert result["before_input_sha256"] != result["after_input_sha256"]
    assert result["snapshot_changed"] is True
    assert result["source_content_changed"] is False
    assert result["retained_occurrence_count"] == 2
    assert result["changes"] == []


def test_full_multiset_diff_tracks_duplicates_and_reference_effects() -> None:
    stable = _row(10, "1", "1", exchange=1)
    removed = _row(20, "2", "2", exchange=2)
    added_same_timestamp = _row(20, "3", "3", exchange=3)
    malformed = {"bid_price": 4, "ask_price": 4}
    outside = _row(DAY_NS, "5", "5")
    before_pages = [_page([stable, stable, removed, malformed, outside])]
    after_pages = [_page([stable, added_same_timestamp, malformed, malformed, outside])]
    result = _reconcile(before_pages, after_pages)
    assert result["before_counts"] == {
        "occurrence_count": 5,
        "distinct_row_count": 4,
        "duplicate_count": 1,
    }
    assert result["after_counts"] == {
        "occurrence_count": 5,
        "distinct_row_count": 4,
        "duplicate_count": 1,
    }
    assert result["retained_occurrence_count"] == 3
    assert result["added_occurrence_count"] == 2
    assert result["removed_occurrence_count"] == 2
    assert result["before_counts"]["occurrence_count"] == 3 + 2
    assert result["after_counts"]["occurrence_count"] == 3 + 2
    expected = {
        hashlib.sha256(canonical_json(stable).encode()).hexdigest(): (2, 1, -1),
        hashlib.sha256(canonical_json(removed).encode()).hexdigest(): (1, 0, -1),
        hashlib.sha256(canonical_json(added_same_timestamp).encode()).hexdigest(): (0, 1, 1),
        hashlib.sha256(canonical_json(malformed).encode()).hexdigest(): (1, 2, 1),
    }
    assert {
        item["row_sha256"]: (
            item["before_count"], item["after_count"], item["delta"]
        )
        for item in result["changes"]
    } == expected
    assert result["reference_changes"] == {
        "close": {"before": "2", "after": "3"},
        "high": {"before": "2", "after": "3"},
        "invalid_occurrence_count": {"before": 1, "after": 2},
    }


def test_same_timestamp_price_addition_can_make_close_ambiguous() -> None:
    before_pages = [_page([_row(1, "1", "1"), _row(2, "2", "2")])]
    after_pages = [_page([_row(1, "1", "1"), _row(2, "2", "2"), _row(2, "3", "3")])]
    result = _reconcile(before_pages, after_pages)
    assert result["added_occurrence_count"] == 1
    assert result["removed_occurrence_count"] == 0
    assert result["before_counts"]["occurrence_count"] == (
        result["retained_occurrence_count"] + result["removed_occurrence_count"]
    )
    assert result["after_counts"]["occurrence_count"] == (
        result["retained_occurrence_count"] + result["added_occurrence_count"]
    )
    assert result["reference_changes"] == {
        "ambiguous_close": {"before": False, "after": True},
        "close": {"before": "2", "after": None},
        "high": {"before": "2", "after": "3"},
    }


def test_complete_empty_sets_are_comparable_content() -> None:
    pages = [_page([])]
    result = _reconcile(pages, pages)
    assert result["comparable"] is True
    assert result["before_counts"] == {
        "occurrence_count": 0,
        "distinct_row_count": 0,
        "duplicate_count": 0,
    }
    assert result["retained_occurrence_count"] == 0
    assert result["before_content_sha256"] == hashlib.sha256(b"[]").hexdigest()


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
def test_all_locked_pairs_are_supported_without_qualification(pair: str) -> None:
    pages = [_page([_row(1, "1", "1")], pair=pair)]
    result = _reconcile(pages, pages)
    assert result["pair"] == pair
    assert result["comparable"] is True
    assert result["validation_eligible"] is False


def test_result_array_order_is_not_treated_as_event_lineage() -> None:
    first = _row(1, "1", "1", exchange=1)
    second = _row(2, "2", "2", exchange=2)
    before_pages = [_page([first, second])]
    after_pages = [_page([second, first])]
    result = _reconcile(before_pages, after_pages)
    assert result["snapshot_changed"] is True
    assert result["source_content_changed"] is False
    assert result["changes"] == []
    assert result["event_lineage"] == "ambiguous"


def test_incomplete_prefixes_never_look_like_removed_rows() -> None:
    complete = [_page([_row(1, "1", "1")])]
    incomplete = [_page([_row(1, "1", "1")], status=503)]
    result = _reconcile(incomplete, complete)
    assert result["comparable"] is False
    assert result["exclusion_reasons"] == ["before_acquisition_incomplete"]
    for field in (
        "before_content_sha256", "after_content_sha256", "source_content_changed",
        "before_counts", "after_counts", "retained_occurrence_count",
        "added_occurrence_count", "removed_occurrence_count", "changes",
        "reference_changes",
    ):
        assert result[field] is None


def test_hash_consistent_mixed_identity_snapshot_is_rejected() -> None:
    mixed_pages = [
        _page([], next_cursor="opaque-two"),
        _page([], page_index=1, cursor="opaque-two", pair="USDJPY"),
    ]
    mixed_snapshot = _snapshot(mixed_pages)
    with pytest.raises(ValueError, match="share one pair"):
        _reconcile(
            mixed_pages,
            mixed_pages,
            before_snapshot=mixed_snapshot,
            after_snapshot=mixed_snapshot,
        )


def test_exact_long_decimal_is_context_independent_and_inputs_are_unchanged() -> None:
    price = "1.123456789012345678901234567890123456789"
    before_pages = [_page([_row(1, price, price)])]
    after_pages = [_page([_row(1, price, price), _row(2, "2", "2")])]
    before_snapshot = _snapshot(before_pages)
    after_snapshot = _snapshot(after_pages)
    originals = copy.deepcopy((before_pages, after_pages, before_snapshot, after_snapshot))
    with localcontext() as context:
        context.prec = 2
        context.Emax = 9
        context.Emin = -9
        first = _reconcile(
            before_pages, after_pages,
            before_snapshot=before_snapshot, after_snapshot=after_snapshot,
        )
    assert getcontext().prec != 2
    second = _reconcile(
        before_pages, after_pages,
        before_snapshot=before_snapshot, after_snapshot=after_snapshot,
    )
    assert first == second
    assert (before_pages, after_pages, before_snapshot, after_snapshot) == originals
    assert first["reference_changes"]["high"] == {"before": price, "after": "2"}


@pytest.mark.parametrize("mutation", ["hash", "reference", "typed_count", "wrong_pages"])
def test_tampered_envelope_or_bound_reference_is_rejected(mutation: str) -> None:
    pages = [_page([_row(1, "1", "1")])]
    envelope = _snapshot(pages)
    supplied_pages = pages
    if mutation == "hash":
        envelope["snapshot_sha256"] = "0" * 64
    elif mutation in {"reference", "typed_count"}:
        document = json.loads(envelope["unsigned_json"])
        if mutation == "reference":
            document["reference"]["open"] = "999"
            unsigned = canonical_json(document)
        else:
            document["reference"]["source_occurrence_count"] = 1.0
            unsigned = json.dumps(document, separators=(",", ":"))
        envelope = {
            "snapshot_sha256": hashlib.sha256(unsigned.encode()).hexdigest(),
            "unsigned_json": unsigned,
        }
    else:
        supplied_pages = [_page([_row(2, "2", "2")])]
    with pytest.raises(ValueError):
        _reconcile(pages, supplied_pages, after_snapshot=envelope)


def test_missing_page_collection_rejects_before_reference_comparison() -> None:
    pages = [_page([])]
    snapshot = _snapshot(pages)
    with pytest.raises(ValueError, match="between 1 and 10000"):
        reconcile_quote_snapshots(
            before=snapshot,
            before_pages=[],
            after=snapshot,
            after_pages=pages,
            as_of=CAPTURED_AT + timedelta(days=1),
        )


@pytest.mark.parametrize(
    "unsigned",
    [
        '{"version":"quote-snapshot-v1","version":"quote-snapshot-v1"}',
        '{"version":NaN}',
    ],
)
def test_duplicate_keys_and_nonfinite_outer_numbers_reject(unsigned: str) -> None:
    envelope = {
        "snapshot_sha256": hashlib.sha256(unsigned.encode()).hexdigest(),
        "unsigned_json": unsigned,
    }
    pages = [_page([])]
    with pytest.raises(ValueError):
        _reconcile(pages, pages, before_snapshot=envelope)


def test_noncanonical_future_and_reversed_as_of_reject() -> None:
    pages = [_page([])]
    document = json.loads(_snapshot(pages)["unsigned_json"])
    document["reference"]["as_of"] = "2026-09-27T01:00:00Z"
    unsigned = canonical_json(document)
    noncanonical = {
        "snapshot_sha256": hashlib.sha256(unsigned.encode()).hexdigest(),
        "unsigned_json": unsigned,
    }
    with pytest.raises(ValueError, match="canonical UTC"):
        _reconcile(pages, pages, before_snapshot=noncanonical)

    later = _snapshot(pages, as_of=CAPTURED_AT + timedelta(hours=3))
    earlier = _snapshot(pages, as_of=CAPTURED_AT + timedelta(hours=2))
    with pytest.raises(ValueError, match="reversed or future"):
        _reconcile(pages, pages, before_snapshot=later, after_snapshot=earlier)

    with pytest.raises(ValueError, match="timezone-aware"):
        reconcile_quote_snapshots(
            before=earlier,
            before_pages=pages,
            after=earlier,
            after_pages=pages,
            as_of=datetime(2026, 9, 28),
        )


def test_resource_preflight_uses_actual_retained_text_and_raw_totals(monkeypatch: Any) -> None:
    import src.research.quote_revision as revision

    pages = [_page([])]
    snapshot = _snapshot(pages)
    body_size = len(pages[0]["body_text"].encode())
    monkeypatch.setattr(revision, "_MAX_BODY_BYTES_PER_PAGE", body_size)
    reconcile_quote_snapshots(
        before=snapshot, before_pages=pages, after=snapshot, after_pages=pages,
        as_of=CAPTURED_AT + timedelta(days=1),
    )
    monkeypatch.setattr(revision, "_MAX_BODY_BYTES_PER_PAGE", body_size - 1)
    with pytest.raises(ValueError, match="body_text exceeds"):
        reconcile_quote_snapshots(
            before=snapshot, before_pages=pages, after=snapshot, after_pages=pages,
            as_of=CAPTURED_AT + timedelta(days=1),
        )
    monkeypatch.setattr(revision, "_MAX_BODY_BYTES_PER_PAGE", body_size)
    monkeypatch.setattr(revision, "_MAX_BODY_BYTES_PER_SIDE", body_size * 2 - 1)
    with pytest.raises(ValueError, match="retained-text ceiling"):
        reconcile_quote_snapshots(
            before=snapshot, before_pages=pages * 2, after=snapshot, after_pages=pages,
            as_of=CAPTURED_AT + timedelta(days=1),
        )
    monkeypatch.setattr(revision, "_MAX_BODY_BYTES_PER_SIDE", body_size * 2)
    monkeypatch.setattr(revision, "_MAX_RAW_BYTES_PER_SIDE", pages[0]["raw_size_bytes"] - 1)
    with pytest.raises(ValueError, match="raw-byte ceiling"):
        reconcile_quote_snapshots(
            before=snapshot, before_pages=pages, after=snapshot, after_pages=pages,
            as_of=CAPTURED_AT + timedelta(days=1),
        )
