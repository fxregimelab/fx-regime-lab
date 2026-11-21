"""Pure FPI byte-capture and central-writer contract tests."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.db.writer import archive_fpi_capture
from src.research.fpi_capture import FpiCapture, build_fpi_capture, validate_fpi_capture

LATEST = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"
MONTHLY = "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx"
REQUESTED = datetime(2026, 9, 27, 6, 0, tzinfo=UTC)
RETRIEVED = REQUESTED + timedelta(seconds=2, microseconds=123456)


def capture(
    *,
    body: bytes = b"\x00\xff<html>authored synthetic fixture</html>\r\n",
    source_url: str = LATEST,
    requested_at: datetime = REQUESTED,
    retrieved_at: datetime = RETRIEVED,
    http_status: int = 200,
) -> FpiCapture:
    return build_fpi_capture(
        body=body,
        source_url=source_url,
        requested_at=requested_at,
        retrieved_at=retrieved_at,
        http_status=http_status,
    )


def forged(document: dict[str, Any]) -> FpiCapture:
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return FpiCapture(hashlib.sha256(text.encode("ascii")).hexdigest(), text)


def client_with(receipt: Any) -> MagicMock:
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = receipt
    return client


def test_capture_preserves_arbitrary_bytes_and_canonical_identity() -> None:
    body = b"\x00\xff\xfe<html>\r\npublic report\x00</html>"
    built = capture(
        body=body,
        requested_at=datetime(2026, 9, 27, 11, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        retrieved_at=datetime(2026, 9, 27, 7, 0, 0, 1, tzinfo=UTC),
    )
    document = json.loads(built.document_json)
    assert set(document) == {
        "version", "source_url", "requested_at", "retrieved_at", "http_status",
        "body_base64", "body_size", "raw_sha256",
    }
    assert document["version"] == "fpi-http-capture-v1"
    assert document["requested_at"] == "2026-09-27T06:00:00+00:00"
    assert document["retrieved_at"] == "2026-09-27T07:00:00.000001+00:00"
    assert base64.b64decode(document["body_base64"], validate=True) == body
    assert document["body_size"] == len(body)
    assert document["raw_sha256"] == hashlib.sha256(body).hexdigest()
    assert built.document_json == json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert built.capture_sha256 == hashlib.sha256(built.document_json.encode("ascii")).hexdigest()
    validate_fpi_capture(built)
    with pytest.raises(FrozenInstanceError):
        built.document_json = "changed"  # type: ignore[misc]


def test_empty_failure_body_is_evidence_and_metadata_changes_identity() -> None:
    first = capture(body=b"", http_status=503)
    exact_retry = capture(body=b"", http_status=503)
    later = capture(body=b"", http_status=503, retrieved_at=RETRIEVED + timedelta(seconds=1))
    changed_status = capture(body=b"", http_status=502)
    changed_source = capture(body=b"", http_status=503, source_url=MONTHLY)
    assert json.loads(first.document_json)["body_base64"] == ""
    assert first == exact_retry
    assert len({first.capture_sha256, later.capture_sha256,
                changed_status.capture_sha256, changed_source.capture_sha256}) == 4


@pytest.mark.parametrize(
    "changes",
    [
        {"body": bytearray(b"x")},
        {"source_url": LATEST + "?date=2026-09-27"},
        {"source_url": LATEST + "#report"},
        {"source_url": "https://user@www.fpi.nsdl.co.in/web/Reports/Latest.aspx"},
        {"source_url": "http://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"},
        {"http_status": True},
        {"http_status": 99},
        {"http_status": 600},
        {"requested_at": REQUESTED.replace(tzinfo=None)},
        {"retrieved_at": REQUESTED - timedelta(microseconds=1)},
        {
            "requested_at": datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1))),
            "retrieved_at": RETRIEVED,
        },
    ],
)
def test_builder_rejects_invalid_transport_claims(changes: dict[str, Any]) -> None:
    arguments: dict[str, Any] = {
        "body": b"fixture",
        "source_url": LATEST,
        "requested_at": REQUESTED,
        "retrieved_at": RETRIEVED,
        "http_status": 200,
    }
    arguments.update(changes)
    with pytest.raises(ValueError):
        build_fpi_capture(**arguments)


def test_body_bound_is_exact() -> None:
    validate_fpi_capture(capture(body=b"x" * 5_000_000))
    with pytest.raises(ValueError, match="5000000"):
        capture(body=b"x" * 5_000_001)


@pytest.mark.parametrize(
    "mutation",
    [
        {"version": "fpi-http-capture-v2"},
        {"source_url": LATEST + "/"},
        {"http_status": True},
        {"http_status": 200.0},
        {"body_size": True},
        {"body_size": 1.0},
        {"body_size": 999},
        {"body_base64": "Zh=="},
        {"body_base64": "***="},
        {"raw_sha256": "F" * 64},
        {"requested_at": "2026-09-27T06:00:00Z"},
        {"retrieved_at": "2026-09-27T05:59:59+00:00"},
    ],
)
def test_validator_reconstructs_every_claim(mutation: dict[str, Any]) -> None:
    document = json.loads(capture(body=b"f").document_json)
    document.update(mutation)
    with pytest.raises(ValueError):
        validate_fpi_capture(forged(document))


def test_validator_rejects_type_hash_fields_and_noncanonical_text() -> None:
    built = capture()
    with pytest.raises(ValueError):
        validate_fpi_capture({})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_fpi_capture(replace(built, capture_sha256="A" * 64))
    with pytest.raises(ValueError):
        validate_fpi_capture(replace(built, document_json=" " + built.document_json))
    document = json.loads(built.document_json)
    document["extra"] = "field"
    with pytest.raises(ValueError):
        validate_fpi_capture(forged(document))
    duplicate = built.document_json.replace(
        '"body_size":', '"body_size":0,"body_size":', 1
    )
    with pytest.raises(ValueError):
        validate_fpi_capture(
            FpiCapture(hashlib.sha256(duplicate.encode()).hexdigest(), duplicate)
        )
    exponent = capture(body=b"f").document_json.replace('"body_size":1', '"body_size":1e0')
    with pytest.raises(ValueError):
        validate_fpi_capture(FpiCapture(hashlib.sha256(exponent.encode()).hexdigest(), exponent))


@pytest.mark.parametrize(
    "stored_at",
    ["2026-09-27T06:00:03Z", "2026-09-27T06:00:03.1+00:00", "2026-09-27T06:00:03.123456+00:00"],
)
def test_writer_sends_exact_rpc_and_returns_detached_receipt(stored_at: str) -> None:
    built = capture()
    original = {
        "capture_sha256": built.capture_sha256,
        "inserted": True,
        "stored_at": stored_at,
    }
    client = client_with(original)
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_fpi_capture(built)
    client.rpc.assert_called_once_with(
        "append_fpi_capture",
        {"p_capture_sha256": built.capture_sha256, "p_document_json": built.document_json},
    )
    client.table.assert_not_called()
    assert receipt == original and receipt is not original
    original["inserted"] = False
    assert receipt["inserted"] is True


def test_writer_validates_before_creating_client() -> None:
    altered = replace(capture(), capture_sha256="0" * 64)
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_fpi_capture(altered)
    factory.assert_not_called()


@pytest.mark.parametrize(
    "document",
    ["x" * 7_000_001, "[" * 5000],
    ids=["oversized", "deeply-malformed"],
)
def test_writer_rejects_oversized_or_deeply_malformed_document_before_client(
    document: str,
) -> None:
    altered = FpiCapture(hashlib.sha256(document.encode()).hexdigest(), document)
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_fpi_capture(altered)
    factory.assert_not_called()


def test_writer_accepts_exact_retry_receipt() -> None:
    built = capture()
    retry = {
        "capture_sha256": built.capture_sha256,
        "inserted": False,
        "stored_at": "2026-09-27T06:00:03Z",
    }
    with patch("src.db.writer._client", return_value=client_with(retry)):
        assert archive_fpi_capture(built) == retry


def test_writer_sanitizes_client_and_provider_errors() -> None:
    for side_effect in (
        RuntimeError("credential secret-value"),
        ValueError("response contained captured body"),
    ):
        client = MagicMock()
        client.rpc.return_value.execute.side_effect = side_effect
        with patch("src.db.writer._client", return_value=client):
            with pytest.raises(RuntimeError, match="^FPI capture archive failed$") as failure:
                archive_fpi_capture(capture())
        assert failure.value.__cause__ is None
    with patch("src.db.writer._client", side_effect=RuntimeError("credential")):
        with pytest.raises(RuntimeError, match="^FPI capture archive failed$"):
            archive_fpi_capture(capture())


@pytest.mark.parametrize(
    "receipt",
    [
        None,
        [],
        {},
        {
            "capture_sha256": "same",
            "inserted": True,
            "stored_at": "2026-09-27T06:00:03Z",
            "extra": 1,
        },
        {"capture_sha256": "wrong", "inserted": True, "stored_at": "2026-09-27T06:00:03Z"},
        {"capture_sha256": "same", "inserted": 1, "stored_at": "2026-09-27T06:00:03Z"},
        {"capture_sha256": "same", "inserted": True, "stored_at": 1},
        {"capture_sha256": "same", "inserted": True, "stored_at": "2026-09-27 06:00:03Z"},
        {"capture_sha256": "same", "inserted": True, "stored_at": "2026-09-27T06:00:03.1234567Z"},
        {"capture_sha256": "same", "inserted": True, "stored_at": "2026-09-27T11:30:03+05:30"},
        {"capture_sha256": "same", "inserted": True, "stored_at": "2026-02-30T06:00:03Z"},
        {"capture_sha256": "same", "inserted": True, "stored_at": "2026-09-27T06:00:01Z"},
    ],
)
def test_writer_rejects_untrustworthy_receipts(receipt: Any) -> None:
    built = capture()
    if type(receipt) is dict and receipt.get("capture_sha256") == "same":
        receipt = receipt | {"capture_sha256": built.capture_sha256}
    client = client_with(receipt)
    with patch("src.db.writer._client", return_value=client):
        with pytest.raises(RuntimeError, match="invalid receipt"):
            archive_fpi_capture(built)
