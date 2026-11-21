"""Synthetic codec checks; these do not establish source authenticity or DB visibility."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.db.writer import archive_fpi_artifact, archive_fpi_parse_result
from src.research.fpi_capture import build_fpi_capture
from src.research.fpi_observation import FPI_OBSERVATION_VERSION, FPI_ROUTES, build_fpi_observation
from src.research.fpi_parse_record import (
    FpiArtifact,
    FpiParseRecord,
    build_fpi_artifact,
    build_fpi_parse_record,
    restore_fpi_parse_record,
    validate_fpi_artifact,
    validate_fpi_parse_record,
)
from src.research.fpi_selection import FpiParsedDay, FpiParseResult
from tests.test_fpi_observation import _fpi_fixture

T0 = datetime(2026, 9, 25, 12, tzinfo=UTC)
PARSER = hashlib.sha256(b"synthetic complete parser bundle").hexdigest()
LATEST = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"


def source_document(day: int, *, route_value: str = "0.70") -> str:
    categories: dict[str, object] = {}
    subtotals = []
    for category, routes in FPI_ROUTES.items():
        subtotal = f"{len(routes) * int(route_value.replace('.', '')) / 100:.2f}"
        subtotals.append(int(subtotal.replace(".", "")))
        categories[category] = {
            "routes_net_usd_million": dict.fromkeys(routes, route_value),
            "subtotal_net_usd_million": subtotal,
        }
    document = {
        "version": "nsdl-fpi-source-evidence-v1",
        "reporting_date": f"2026-09-{day:02d}",
        "usd_units": "USD_MILLION",
        "conversion_rate_units": "INR_PER_USD",
        "conversion_rate_inr_per_usd": "80.1234",
        "categories": categories,
        "total_net_usd_million": f"{sum(subtotals) / 100:.2f}",
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def successful_parse(*days: int) -> tuple[FpiParseResult, tuple[str, ...]]:
    capture = build_fpi_capture(
        body=b"synthetic retained response",
        source_url=LATEST,
        requested_at=T0,
        retrieved_at=T0 + timedelta(minutes=1),
        http_status=200,
    )
    evidence = tuple(source_document(day) for day in days)
    parsed_days = tuple(
        FpiParsedDay(
            build_fpi_observation(**_fpi_fixture(day)).document_json,
            hashlib.sha256(source.encode("ascii")).hexdigest(),
        )
        for day, source in zip(days, evidence, strict=True)
    )
    return (
        FpiParseResult(
            capture,
            PARSER,
            FPI_OBSERVATION_VERSION,
            T0 + timedelta(minutes=2),
            parsed_days,
        ),
        evidence,
    )


def client_with(data: object) -> MagicMock:
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = data
    return client


def test_artifact_round_trip_retains_arbitrary_exact_bytes() -> None:
    body = bytes(range(256)) + b"\x00\xffimplementation"
    parser = build_fpi_artifact(kind="PARSER", body=body)
    selector = build_fpi_artifact(kind="SELECTOR", body=body)
    validate_fpi_artifact(parser)
    document = json.loads(parser.document_json)
    assert parser.artifact_sha256 == hashlib.sha256(body).hexdigest()
    assert document["body_size"] == len(body)
    assert parser.artifact_sha256 == selector.artifact_sha256
    assert parser.document_json != selector.document_json


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "RUNNER"},
        {"kind": []},
        {"kind": {}},
        {"body_size": True},
        {"body_base64": "AA"},
        {"artifact_sha256": "0" * 64},
        {"extra": "field"},
    ],
)
def test_artifact_reconstructs_every_claim(change: dict[str, object]) -> None:
    artifact = build_fpi_artifact(kind="PARSER", body=b"bundle")
    document = json.loads(artifact.document_json)
    document.update(change)
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    forged = FpiArtifact(artifact.artifact_sha256, text)
    with pytest.raises(ValueError):
        validate_fpi_artifact(forged)


def test_complete_parse_round_trip_preserves_inr_and_independent_usd_evidence() -> None:
    parse, sources = successful_parse(24, 25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    validate_fpi_parse_record(record)
    restored = restore_fpi_parse_record(record, parse.capture)
    document = json.loads(record.document_json)
    assert restored == parse
    assert record.parse_id == parse.parse_id
    assert document["content_sha256"] == parse.content_sha256
    assert [row["reporting_date"] for row in document["days"]] == [
        "2026-09-24",
        "2026-09-25",
    ]
    assert [row["source_evidence_document_json"] for row in document["days"]] == list(sources)
    assert [row["membership_id"] for row in document["days"]] == [
        parse.membership_id(day) for day in parse.days
    ]


def test_failed_parse_round_trip_preserves_machine_failure_without_days() -> None:
    parse, _ = successful_parse(25)
    failed = replace(parse, days=(), failure_reason="MALFORMED_REPORT")
    record = build_fpi_parse_record(failed, source_evidence_documents=())
    assert restore_fpi_parse_record(record, parse.capture) == failed
    assert json.loads(record.document_json)["days"] == []


@pytest.mark.parametrize("reason", ["raw exception", "bad-code", "A" * 65, ""])
def test_failure_reason_is_bounded_machine_code(reason: str) -> None:
    parse, _ = successful_parse(25)
    failed = replace(parse, days=(), failure_reason="FAILED")
    object.__setattr__(failed, "failure_reason", reason)
    with pytest.raises(ValueError, match="machine code"):
        build_fpi_parse_record(failed, source_evidence_documents=())


def test_rejects_forged_frozen_day_and_partial_source_evidence_before_io() -> None:
    parse, sources = successful_parse(24, 25)
    forged = parse.days[0]
    object.__setattr__(forged, "source_evidence_sha256", "not-a-hash")
    with pytest.raises(ValueError):
        build_fpi_parse_record(parse, source_evidence_documents=sources)
    parse, sources = successful_parse(24, 25)
    with pytest.raises(ValueError, match="every parsed date"):
        build_fpi_parse_record(parse, source_evidence_documents=sources[:1])
    object.__setattr__(parse, "days", list(parse.days))
    with pytest.raises(ValueError, match="immutable tuple"):
        build_fpi_parse_record(parse, source_evidence_documents=sources)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: " " + text,
        lambda text: text.replace(
            '"version":"nsdl-fpi-source-evidence-v1"', '"version":"future"'
        ),
        lambda text: text.replace('"usd_units":"USD_MILLION"', '"usd_units":"USD"'),
        lambda text: text.replace(
            '"conversion_rate_units":"INR_PER_USD"', '"conversion_rate_units":"USD_PER_INR"'
        ),
        lambda text: text.replace(
            '"conversion_rate_inr_per_usd":"80.1234"',
            '"conversion_rate_inr_per_usd":"0.0000"',
        ),
        lambda text: text.replace(
            '"conversion_rate_inr_per_usd":"80.1234"',
            '"conversion_rate_inr_per_usd":true',
        ),
        lambda text: text.replace('"0.70"', '"00.70"', 1),
        lambda text: text.replace('"0.70"', '"-0.00"', 1),
        lambda text: text.replace('"0.70"', 'true', 1),
        lambda text: text.replace('"1.40"', '"9.99"', 1),
        lambda text: text.replace('"reporting_date":"2026-09-25"', '"reporting_date":"2026-09-24"'),
    ],
)
def test_source_evidence_rejects_noncanonical_or_unreconciled_values(
    mutate: object,
) -> None:
    parse, sources = successful_parse(25)
    changed = mutate(sources[0])  # type: ignore[operator]
    changed_day = replace(
        parse.days[0], source_evidence_sha256=hashlib.sha256(changed.encode("ascii")).hexdigest()
    )
    altered = replace(parse, days=(changed_day,))
    with pytest.raises(ValueError):
        build_fpi_parse_record(altered, source_evidence_documents=(changed,))


def test_record_rejects_tampered_redundant_identities_and_duplicate_keys() -> None:
    parse, sources = successful_parse(25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    document = json.loads(record.document_json)
    document["days"][0]["membership_id"] = "0" * 64
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    with pytest.raises(ValueError, match="membership"):
        validate_fpi_parse_record(
            FpiParseRecord(record.parse_id, hashlib.sha256(text.encode()).hexdigest(), text)
        )
    duplicate = record.document_json.replace('"version":', '"version":"duplicate","version":', 1)
    with pytest.raises(ValueError, match="unique-key"):
        validate_fpi_parse_record(
            FpiParseRecord(
                record.parse_id, hashlib.sha256(duplicate.encode()).hexdigest(), duplicate
            )
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", "future"),
        ("parse_id", "0" * 64),
        ("content_sha256", "0" * 64),
        ("capture_sha256", "0" * 64),
        ("parser_sha256", "0" * 64),
        ("definition_version", "future"),
        ("recorded_at", "2026-09-25T12:02:00.000000Z"),
        ("failure_reason", "FAILED"),
        ("days", []),
    ],
)
def test_record_rejects_each_altered_envelope_claim(field: str, value: object) -> None:
    parse, sources = successful_parse(25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    document = json.loads(record.document_json)
    document[field] = value
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    parse_id = document["parse_id"] if type(document["parse_id"]) is str else record.parse_id
    forged = FpiParseRecord(parse_id, hashlib.sha256(text.encode("ascii")).hexdigest(), text)
    with pytest.raises(ValueError):
        validate_fpi_parse_record(forged)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reporting_date", "2026-09-24"),
        ("value_sha256", "0" * 64),
        ("membership_id", "0" * 64),
        ("document_json", "{}"),
        ("source_evidence_sha256", "0" * 64),
        ("source_evidence_document_json", "{}"),
    ],
)
def test_record_rejects_each_altered_nested_day_claim(field: str, value: object) -> None:
    parse, sources = successful_parse(25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    document = json.loads(record.document_json)
    document["days"][0][field] = value
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    forged = FpiParseRecord(
        record.parse_id, hashlib.sha256(text.encode("ascii")).hexdigest(), text
    )
    with pytest.raises(ValueError):
        restore_fpi_parse_record(forged, parse.capture)


def test_restore_requires_exact_capture_identity() -> None:
    parse, sources = successful_parse(25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    other = build_fpi_capture(
        body=b"other",
        source_url=LATEST,
        requested_at=T0,
        retrieved_at=T0 + timedelta(minutes=1),
        http_status=200,
    )
    with pytest.raises(ValueError, match="supplied capture"):
        restore_fpi_parse_record(record, other)


def test_artifact_writer_calls_only_exact_rpc_and_returns_detached_receipt() -> None:
    artifact = build_fpi_artifact(kind="PARSER", body=b"bundle")
    original = {
        "artifact_sha256": artifact.artifact_sha256,
        "kind": "PARSER",
        "inserted": True,
        "stored_at": "2026-09-27T12:00:00.123456Z",
    }
    client = client_with(original)
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_fpi_artifact(artifact)
    client.rpc.assert_called_once_with(
        "append_fpi_artifact",
        {
            "p_artifact_sha256": artifact.artifact_sha256,
            "p_document_json": artifact.document_json,
        },
    )
    client.table.assert_not_called()
    assert receipt == original and receipt is not original


def test_parse_writer_calls_only_exact_rpc_and_checks_complete_receipt() -> None:
    parse, sources = successful_parse(24, 25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    document = json.loads(record.document_json)
    original = {
        "parse_id": record.parse_id,
        "record_sha256": record.record_sha256,
        "content_sha256": document["content_sha256"],
        "membership_ids": [row["membership_id"] for row in document["days"]],
        "inserted": False,
        "stored_at": "2026-09-27T12:00:00+00:00",
    }
    client = client_with(original)
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_fpi_parse_result(parse, source_evidence_documents=sources)
    client.rpc.assert_called_once_with(
        "append_fpi_parse_result",
        {
            "p_parse_id": record.parse_id,
            "p_record_sha256": record.record_sha256,
            "p_document_json": record.document_json,
        },
    )
    client.table.assert_not_called()
    assert receipt == original and receipt is not original
    original["membership_ids"].reverse()
    assert receipt["membership_ids"] != original["membership_ids"]


def test_writers_validate_before_client_and_sanitize_transport_errors() -> None:
    artifact = build_fpi_artifact(kind="PARSER", body=b"bundle")
    invalid = replace(artifact, artifact_sha256="0" * 64)
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_fpi_artifact(invalid)
    factory.assert_not_called()
    parse, sources = successful_parse(25)
    bad_source = sources[0].replace('"usd_units":"USD_MILLION"', '"usd_units":"USD"')
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_fpi_parse_result(parse, source_evidence_documents=(bad_source,))
    factory.assert_not_called()
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError(sources[0])
    with patch("src.db.writer._client", return_value=client):
        with pytest.raises(RuntimeError, match="^FPI parse archive failed$") as failure:
            archive_fpi_parse_result(parse, source_evidence_documents=sources)
    assert sources[0] not in str(failure.value)


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "SELECTOR"},
        {"inserted": 1},
        {"stored_at": "2026-09-27T12:00:00.1234567Z"},
        {"stored_at": "2026-09-31T12:00:00Z"},
        {"extra": True},
    ],
)
def test_artifact_writer_rejects_inexact_receipt(change: dict[str, object]) -> None:
    artifact = build_fpi_artifact(kind="PARSER", body=b"bundle")
    receipt: dict[str, object] = {
        "artifact_sha256": artifact.artifact_sha256,
        "kind": "PARSER",
        "inserted": True,
        "stored_at": "2026-09-27T12:00:00Z",
    }
    receipt.update(change)
    with patch("src.db.writer._client", return_value=client_with(receipt)):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_artifact(artifact)


@pytest.mark.parametrize(
    "receipt",
    [
        [],
        True,
        {},
        {
            "artifact_sha256": True,
            "kind": "PARSER",
            "inserted": True,
            "stored_at": "2026-09-27T12:00:00Z",
        },
        {
            "artifact_sha256": "0" * 64,
            "kind": "PARSER",
            "inserted": True,
            "stored_at": "2026-09-27T12:00:00Z",
        },
        {
            "artifact_sha256": "0" * 64,
            "kind": "PARSER",
            "inserted": True,
            "stored_at": "2026-09-31T12:00:00Z",
            "extra": True,
        },
    ],
)
def test_artifact_writer_rejects_nonobject_missing_bool_hash_and_date_receipts(
    receipt: object,
) -> None:
    artifact = build_fpi_artifact(kind="PARSER", body=b"bundle")
    with patch("src.db.writer._client", return_value=client_with(receipt)):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_artifact(artifact)


def test_parse_writer_rejects_reordered_memberships_and_early_timestamp() -> None:
    parse, sources = successful_parse(24, 25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    document = json.loads(record.document_json)
    receipt = {
        "parse_id": record.parse_id,
        "record_sha256": record.record_sha256,
        "content_sha256": document["content_sha256"],
        "membership_ids": [row["membership_id"] for row in reversed(document["days"])],
        "inserted": True,
        "stored_at": "2026-09-25T12:01:00Z",
    }
    with patch("src.db.writer._client", return_value=client_with(receipt)):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_parse_result(parse, source_evidence_documents=sources)
    receipt["membership_ids"].reverse()
    with patch("src.db.writer._client", return_value=client_with(receipt)):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_parse_result(parse, source_evidence_documents=sources)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parse_id", "0" * 64),
        ("record_sha256", "0" * 64),
        ("content_sha256", "0" * 64),
        ("membership_ids", ["0" * 64]),
        ("inserted", 1),
        ("stored_at", "2026-09-27T12:00:00.1234567Z"),
        ("stored_at", "2026-09-31T12:00:00Z"),
    ],
)
def test_parse_writer_rejects_each_altered_receipt_claim(field: str, value: object) -> None:
    parse, sources = successful_parse(25)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    document = json.loads(record.document_json)
    receipt: dict[str, object] = {
        "parse_id": record.parse_id,
        "record_sha256": record.record_sha256,
        "content_sha256": document["content_sha256"],
        "membership_ids": [document["days"][0]["membership_id"]],
        "inserted": True,
        "stored_at": "2026-09-27T12:00:00Z",
    }
    receipt[field] = value
    with patch("src.db.writer._client", return_value=client_with(receipt)):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_parse_result(parse, source_evidence_documents=sources)


@pytest.mark.parametrize("receipt", [[], True, {}, {"parse_id": True}, {"extra": True}])
def test_parse_writer_rejects_nonobject_missing_bool_and_extra_receipts(receipt: object) -> None:
    parse, sources = successful_parse(25)
    with patch("src.db.writer._client", return_value=client_with(receipt)):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_parse_result(parse, source_evidence_documents=sources)
