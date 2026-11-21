"""Synthetic retained-reference checks; no source, snapshot or execution authority."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest

from src.research import fpi_parse_record as codec
from src.research.fpi_capture import FpiCapture, build_fpi_capture, validate_fpi_capture
from src.research.fpi_parse_record import (
    FpiParseRecord,
    FpiReadReferences,
    build_fpi_parse_record,
    build_fpi_read_references,
    restore_fpi_parse_record,
)
from src.research.fpi_selection import FpiParsedDay, FpiParseResult
from tests.test_fpi_parse_record import source_document, successful_parse


def canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def fixture(*days: int) -> tuple[FpiParseResult, FpiParseRecord]:
    parse, sources = successful_parse(*(days or (24, 25)))
    return parse, build_fpi_parse_record(parse, source_evidence_documents=sources)


def changed_record(parse: FpiParseResult, record: FpiParseRecord, **changes: Any) -> FpiParseRecord:
    """Rebind independent inner hashes to isolate cross-capture semantic checks."""
    document = json.loads(record.document_json)
    document.update(changes)
    document["parse_id"] = sha(
        canonical(
            [
                document["capture_sha256"],
                document["parser_sha256"],
                document["definition_version"],
            ]
        )
    )
    for row in document["days"]:
        row["membership_id"] = sha(
            canonical(
                [
                    document["parse_id"],
                    row["value_sha256"],
                    row["source_evidence_sha256"],
                ]
            )
        )
    document["content_sha256"] = sha(
        canonical(
            {
                "parse_id": document["parse_id"],
                "recorded_at": document["recorded_at"],
                "days": [asdict(day) for day in parse.days] if document["days"] else [],
                "failure_reason": document["failure_reason"],
            }
        )
    )
    text = canonical(document)
    return FpiParseRecord(document["parse_id"], sha(text), text)


def expected_bundle(
    captures: tuple[FpiCapture, ...], records: tuple[FpiParseRecord, ...]
) -> FpiReadReferences:
    capture_rows = []
    parse_rows = []
    for capture in sorted(set(captures), key=lambda value: value.capture_sha256):
        document = json.loads(capture.document_json)
        del document["version"], document["body_base64"]
        capture_rows.append(
            {
                **document,
                "capture_sha256": capture.capture_sha256,
                "document_size": len(capture.document_json),
            }
        )
    for record in sorted(set(records), key=lambda value: value.parse_id):
        document = json.loads(record.document_json)
        del document["version"]
        members = document.pop("days")
        for member in members:
            del member["document_json"], member["source_evidence_document_json"]
        parse_rows.append(
            {
                **document,
                "memberships": members,
                "record_sha256": record.record_sha256,
                "document_size": len(record.document_json),
            }
        )
    text = canonical(
        {"version": "fpi-read-references-v1", "captures": capture_rows, "parses": parse_rows}
    )
    return FpiReadReferences(sha(text), text)


def test_exact_complete_reference_and_detached_immutable_output() -> None:
    parse, record = fixture(*range(1, 26))
    captures, records = (parse.capture,), (record,)
    before = (asdict(parse.capture), asdict(record))
    result = build_fpi_read_references(captures=captures, records=records)
    assert result == expected_bundle(captures, records)
    assert len(json.loads(result.document_json)["parses"][0]["memberships"]) == 25
    assert (asdict(parse.capture), asdict(record)) == before
    with pytest.raises(AttributeError):
        result.document_json = "forged"  # type: ignore[misc]
    object.__setattr__(record, "document_json", "mutated afterward")
    assert result.reference_sha256 == sha(result.document_json)
    assert "body_base64" not in result.document_json
    assert "source_evidence_document_json" not in result.document_json


def test_empty_bundle_exact_identity() -> None:
    assert build_fpi_read_references(captures=(), records=()) == expected_bundle((), ())


def test_shared_captures_alternate_parsers_failures_permutations_and_retries() -> None:
    parse, record = fixture()
    second = changed_record(parse, record, parser_sha256="a" * 64)
    failed = changed_record(
        parse, record, parser_sha256="b" * 64, days=[], failure_reason="MALFORMED_REPORT"
    )
    for records in itertools.permutations((record, second, failed)):
        refs = build_fpi_read_references(captures=(parse.capture,) * 2, records=records * 2)
        assert refs == expected_bundle((parse.capture,), records)
        for item in records:
            restore_fpi_parse_record(item, parse.capture)


def test_unique_documents_validated_once_with_many_shared_parses() -> None:
    parse, record = fixture()
    records = tuple(changed_record(parse, record, parser_sha256=sha(str(i))) for i in range(40))
    with (
        patch.object(codec, "validate_fpi_capture", wraps=validate_fpi_capture) as captures,
        patch.object(codec, "_record_parts", wraps=codec._record_parts) as parts,
        patch.object(codec, "restore_fpi_parse_record", side_effect=AssertionError("not a loop")),
    ):
        result = build_fpi_read_references(captures=(parse.capture,) * 40, records=records * 2)
    assert captures.call_count == 1
    assert parts.call_count == 40
    assert result == expected_bundle((parse.capture,), records)


@pytest.mark.parametrize(
    "kind",
    [
        "capture_text",
        "capture_type",
        "parse_text",
        "parse_type",
        "capture_id",
        "parse_id",
        "record_hash",
    ],
)
def test_forged_fields_and_types_reject_before_validation(kind: str) -> None:
    parse, record = fixture()
    captures: Any = (parse.capture,)
    records: Any = (record,)
    if kind == "capture_type":
        captures = (object(),)
    elif kind == "parse_type":
        records = (object(),)
    else:
        target, field = {
            "capture_text": (parse.capture, "document_json"),
            "parse_text": (record, "document_json"),
            "capture_id": (parse.capture, "capture_sha256"),
            "parse_id": (record, "parse_id"),
            "record_hash": (record, "record_sha256"),
        }[kind]
        object.__setattr__(target, field, ["PRIVATE_MARKER"])
    with patch.object(codec, "validate_fpi_capture") as validator:
        with pytest.raises(ValueError) as error:
            build_fpi_read_references(captures=captures, records=records)
        assert "PRIVATE_MARKER" not in str(error.value)
        validator.assert_not_called()


@pytest.mark.parametrize("kind", ["capture", "record", "hash"])
def test_contradictory_duplicates_reject_both_orders_before_validation(kind: str) -> None:
    parse, record = fixture()
    for reverse in (False, True):
        captures: tuple[FpiCapture, ...] = (parse.capture,)
        records: tuple[FpiParseRecord, ...] = (record,)
        if kind == "capture":
            captures += (replace(parse.capture, document_json=parse.capture.document_json + " "),)
        elif kind == "record":
            records += (replace(record, document_json=record.document_json + " "),)
        else:
            records += (replace(record, record_sha256="0" * 64),)
        with patch.object(codec, "validate_fpi_capture") as validator:
            with pytest.raises(ValueError, match="Contradictory"):
                build_fpi_read_references(
                    captures=captures[:: -1 if reverse else 1],
                    records=records[:: -1 if reverse else 1],
                )
            validator.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "unused", "wrong"])
def test_exact_capture_dependency_coverage(kind: str) -> None:
    parse, record = fixture()
    captures: tuple[FpiCapture, ...] = (parse.capture,)
    records: tuple[FpiParseRecord, ...] = (record,)
    if kind == "missing":
        captures = ()
    elif kind == "unused":
        records = ()
    else:
        records = (changed_record(parse, record, capture_sha256="0" * 64),)
    with pytest.raises(ValueError, match="missing|unused"):
        build_fpi_read_references(captures=captures, records=records)


@pytest.mark.parametrize(
    "kind",
    [
        "capture_list",
        "record_list",
        "capture_count",
        "record_count",
        "capture_size",
        "record_size",
        "ascii",
        "budget",
    ],
)
def test_preflight_rejects_before_document_decoding_or_hashing(kind: str) -> None:
    parse, record = fixture()
    captures: Any = (parse.capture,)
    records: Any = (record,)
    if kind == "capture_list":
        captures = list(captures)
    elif kind == "record_list":
        records = list(records)
    elif kind == "capture_count":
        captures *= 2049
    elif kind == "record_count":
        records *= 2049
    elif kind == "capture_size":
        captures = (replace(parse.capture, document_json="x" * 7_000_001),)
    elif kind == "record_size":
        records = (replace(record, document_json="x" * 4_000_001),)
    elif kind == "ascii":
        records = (replace(record, document_json="\u00e9"),)
    budget = len(parse.capture.document_json) + len(record.document_json)
    with (
        patch.object(codec, "_MAX_READ_ORIGINAL_BYTES", budget - 1 if kind == "budget" else budget),
        patch.object(json, "loads", side_effect=AssertionError("decoded before preflight")),
        patch.object(hashlib, "sha256", side_effect=AssertionError("hashed before preflight")),
    ):
        with pytest.raises(ValueError):
            build_fpi_read_references(captures=captures, records=records)


def test_exact_preflight_bounds_and_deduplicated_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    parse, record = fixture()
    budget = len(parse.capture.document_json) + len(record.document_json)
    monkeypatch.setattr(codec, "_MAX_READ_ORIGINAL_BYTES", budget)
    monkeypatch.setattr(codec, "_MAX_READ_CAPTURE_CHARS", len(parse.capture.document_json))
    monkeypatch.setattr(codec, "_MAX_RECORD_BYTES", len(record.document_json))
    assert build_fpi_read_references(
        captures=(parse.capture,) * 2048, records=(record,) * 2048
    ) == expected_bundle((parse.capture,), (record,))


@pytest.mark.parametrize("limit", [0, 1, 2, 3])
def test_membership_limit_counts_all_members_and_retries(
    limit: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse, record = fixture(24, 25)
    monkeypatch.setattr(codec, "_MAX_READ_MEMBERSHIPS", limit)
    if limit < 2:
        with pytest.raises(ValueError, match="membership count"):
            build_fpi_read_references(captures=(parse.capture,), records=(record,) * 2)
    else:
        assert build_fpi_read_references(captures=(parse.capture,), records=(record,) * 2)


@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize("empty", [False, True])
def test_exact_reference_document_limit(
    delta: int,
    empty: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse, record = fixture()
    captures, records = (() if empty else (parse.capture,)), (() if empty else (record,))
    expected = expected_bundle(captures, records)
    monkeypatch.setattr(codec, "_MAX_READ_REFERENCE_BYTES", len(expected.document_json) + delta)
    if delta < 0:
        with pytest.raises(ValueError, match="reference document budget"):
            build_fpi_read_references(captures=captures, records=records)
    else:
        assert build_fpi_read_references(captures=captures, records=records) == expected


@pytest.mark.parametrize(
    "kind",
    [
        "capture_hash",
        "raw_body",
        "record_hash",
        "source",
        "member",
        "definition",
        "early_recorded",
        "future_day",
        "http",
        "overflow",
    ],
)
def test_corruption_and_cross_capture_rejections_match_restore(kind: str) -> None:
    parse, record = fixture()
    capture = parse.capture
    if kind == "capture_hash":
        capture = replace(capture, capture_sha256="0" * 64)
    elif kind == "raw_body":
        capture = replace(capture, document_json=capture.document_json.replace("c3lu", "AAAA"))
    elif kind == "record_hash":
        record = replace(record, record_sha256="0" * 64)
    elif kind in {"source", "member"}:
        document = json.loads(record.document_json)
        field = "source_evidence_document_json" if kind == "source" else "membership_id"
        document["days"][0][field] = "PRIVATE_MARKER"
        text = canonical(document)
        record = FpiParseRecord(record.parse_id, sha(text), text)
    elif kind == "definition":
        record = changed_record(parse, record, definition_version="future")
    elif kind == "early_recorded":
        record = changed_record(parse, record, recorded_at="2026-09-25T12:00:00+00:00")
    elif kind == "overflow":
        record = changed_record(parse, record, recorded_at="9999-12-31T18:30:00+00:00")
    else:
        receipt = datetime(2026, 9, 24, 18, 29, 59, tzinfo=UTC)
        capture = build_fpi_capture(
            body=b"synthetic retained report",
            source_url=json.loads(capture.document_json)["source_url"],
            requested_at=receipt,
            retrieved_at=receipt,
            http_status=500 if kind == "http" else 200,
        )
        record = changed_record(parse, record, capture_sha256=capture.capture_sha256)
    with pytest.raises((ValueError, OverflowError)):
        restore_fpi_parse_record(record, capture)
    with pytest.raises(ValueError) as error:
        build_fpi_read_references(captures=(capture,), records=(record,))
    assert "PRIVATE_MARKER" not in str(error.value)


@pytest.mark.parametrize("stamp", ["0001-01-01T00:00:00+00:00", "9999-12-31T18:29:59.999999+00:00"])
def test_earliest_and_latest_valid_timestamps_for_failed_results(stamp: str) -> None:
    parse, record = fixture()
    receipt = datetime.fromisoformat(stamp)
    capture = build_fpi_capture(
        body=b"",
        source_url=json.loads(parse.capture.document_json)["source_url"],
        requested_at=receipt,
        retrieved_at=receipt,
        http_status=503,
    )
    record = changed_record(
        parse,
        record,
        capture_sha256=capture.capture_sha256,
        recorded_at=stamp,
        failure_reason="HTTP_ERROR",
        days=[],
    )
    restore_fpi_parse_record(record, capture)
    assert build_fpi_read_references(captures=(capture,), records=(record,)) == expected_bundle(
        (capture,), (record,)
    )


def test_india_midnight_date_boundary_and_parse_at_receipt() -> None:
    parse, record = fixture(25)
    receipt = datetime(2026, 9, 24, 18, 30, tzinfo=UTC)
    capture = build_fpi_capture(
        body=b"synthetic monthly",
        source_url="https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
        requested_at=receipt,
        retrieved_at=receipt,
        http_status=200,
    )
    record = changed_record(
        parse, record, capture_sha256=capture.capture_sha256, recorded_at=receipt.isoformat()
    )
    restore_fpi_parse_record(record, capture)
    assert build_fpi_read_references(captures=(capture,), records=(record,)) == expected_bundle(
        (capture,), (record,)
    )


def test_complete_31_day_monthly_memberships_and_multiple_capture_sorting() -> None:
    parse, original = fixture(25)
    sources = tuple(
        source_document(25).replace("2026-09-25", f"2026-08-{day:02d}") for day in range(1, 32)
    )
    days = tuple(
        FpiParsedDay(
            parse.days[0].document_json.replace("2026-09-25", f"2026-08-{day:02d}"),
            sha(source),
        )
        for day, source in enumerate(sources, 1)
    )
    receipt = datetime(2026, 9, 1, tzinfo=UTC)
    monthly = build_fpi_capture(
        body=b"synthetic 31 date monthly report",
        source_url="https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
        requested_at=receipt,
        retrieved_at=receipt,
        http_status=200,
    )
    result = FpiParseResult(monthly, parse.parser_sha256, parse.definition_version, receipt, days)
    record = build_fpi_parse_record(result, source_evidence_documents=sources)
    assert restore_fpi_parse_record(record, monthly) == result
    for captures in itertools.permutations((monthly, parse.capture)):
        for records in itertools.permutations((record, original)):
            references = build_fpi_read_references(captures=captures, records=records)
            assert references == expected_bundle(captures, records)
            loaded = json.loads(references.document_json)
            assert sum(len(row["memberships"]) for row in loaded["parses"]) == 32


def test_primitive_snapshots_survive_mutation_of_original_objects_during_validation() -> None:
    parse, record = fixture()
    expected = expected_bundle((parse.capture,), (record,))

    def validate_then_mutate(capture: FpiCapture) -> None:
        validate_fpi_capture(capture)
        object.__setattr__(parse.capture, "document_json", "invalid original after snapshot")
        object.__setattr__(record, "document_json", "invalid original after snapshot")

    with patch.object(codec, "validate_fpi_capture", side_effect=validate_then_mutate):
        assert build_fpi_read_references(captures=(parse.capture,), records=(record,)) == expected


@pytest.mark.parametrize("stamp", ["0001-01-01", "9999-12-31"])
def test_earliest_latest_valid_reporting_dates(stamp: str) -> None:
    parse, _ = fixture(25)
    source = source_document(25).replace("2026-09-25", stamp)
    day = FpiParsedDay(parse.days[0].document_json.replace("2026-09-25", stamp), sha(source))
    receipt = datetime.fromisoformat(stamp + "T12:00:00+00:00")
    capture = build_fpi_capture(
        body=b"synthetic date edge",
        source_url=json.loads(parse.capture.document_json)["source_url"],
        requested_at=receipt,
        retrieved_at=receipt,
        http_status=200,
    )
    result = FpiParseResult(capture, parse.parser_sha256, parse.definition_version, receipt, (day,))
    record = build_fpi_parse_record(result, source_evidence_documents=(source,))
    assert restore_fpi_parse_record(record, capture) == result
    assert build_fpi_read_references(captures=(capture,), records=(record,)) == expected_bundle(
        (capture,), (record,)
    )


def test_subclasses_and_string_subclasses_rejected_in_preflight() -> None:
    class CaptureSubclass(FpiCapture):
        pass

    class RecordSubclass(FpiParseRecord):
        pass

    class TextSubclass(str):
        pass

    parse, record = fixture()
    examples = (
        ((CaptureSubclass(**asdict(parse.capture)),), (record,)),
        ((parse.capture,), (RecordSubclass(**asdict(record)),)),
        (
            (replace(parse.capture, document_json=TextSubclass(parse.capture.document_json)),),
            (record,),
        ),
        ((parse.capture,), (replace(record, parse_id=TextSubclass(record.parse_id)),)),
    )
    with patch.object(codec, "validate_fpi_capture") as validate:
        for captures, records in examples:
            with pytest.raises(ValueError):
                build_fpi_read_references(captures=captures, records=records)
        validate.assert_not_called()
