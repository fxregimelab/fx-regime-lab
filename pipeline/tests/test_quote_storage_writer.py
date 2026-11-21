"""Central writer contract for immutable quote captures and derived snapshots."""

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.db.writer import archive_quote_capture, archive_quote_snapshot
from src.research.quote_capture import canonical_json, capture_quote_page, validate_quote_page
from src.research.quote_reference import build_quote_reference

DAY = 86_400_000_000_000
RECEIPT = datetime(2026, 5, 2, tzinfo=UTC)
PROVENANCE = {"implementation_sha256": "a" * 64, "client_version": "synthetic-fixture-v1"}


def page(*, pair: str = "EURUSD", body: bytes | None = None) -> dict[str, Any]:
    instruments = {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}
    return capture_quote_page(
        pair=pair, instrument=instruments[pair], window_start_ns=0, window_end_ns=DAY,
        page_index=0, requested_at=RECEIPT, received_at=RECEIPT, status_code=200,
        body=body or b'{"status":"OK","results":[{"participant_timestamp":1,'
                     b'"bid_price":1.100000000000000001,"ask_price":1.100000000000000003}]}',
        request_params={"timestamp.gte": "0", "timestamp.lt": str(DAY),
                        "sort": "timestamp", "order": "asc", "limit": "50000"},
        response_headers={},
    )


def echo_client() -> MagicMock:
    client = MagicMock()

    def rpc(name: str, parameters: dict[str, Any]) -> MagicMock:
        response = MagicMock()
        if name == "append_quote_capture":
            receipt = {"capture_sha256": parameters["p_capture_sha256"], "inserted": True}
        else:
            document = json.loads(parameters["p_unsigned_json"])
            receipt = {"snapshot_sha256": parameters["p_snapshot_sha256"], "inserted": True,
                       "capture_count": len(document["reference"]["capture_sha256"])}
        response.execute.return_value.data = receipt
        return response

    client.rpc.side_effect = rpc
    return client


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
def test_capture_serialization_reconstructs_exact_manifest_and_hash(pair: str) -> None:
    captured = page(pair=pair)
    client = echo_client()
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_quote_capture(captured)
    name, parameters = client.rpc.call_args.args
    assert name == "append_quote_capture"
    assert set(parameters) == {"p_capture_sha256", "p_unsigned_json"}
    unsigned = parameters["p_unsigned_json"]
    assert hashlib.sha256(unsigned.encode()).hexdigest() == captured["capture_sha256"]
    reconstructed = json.loads(unsigned) | {"capture_sha256": parameters["p_capture_sha256"]}
    validate_quote_page(reconstructed)
    assert reconstructed == captured
    assert receipt == {"capture_sha256": captured["capture_sha256"], "inserted": True}
    client.table.assert_not_called()
    captured["body_text"] = "later caller mutation"
    assert json.loads(unsigned)["body_text"] != captured["body_text"]


def test_capture_rejects_tampering_before_opening_client() -> None:
    captured = page()
    captured["http_status"] = 503
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_quote_capture(captured)
    factory.assert_not_called()


def test_expanded_unicode_capture_exceeds_storage_bound_without_truncation() -> None:
    raw = ('{"status":"OK","results":[],"diagnostic":"' + "\U0001f642" * 2_800_000
           + '"}').encode()
    assert len(raw) < 16 * 1024 * 1024
    captured = page(body=raw)
    assert len(canonical_json(captured).encode()) > 32 * 1024 * 1024
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError, match="32 MiB"):
        archive_quote_capture(captured)
    factory.assert_not_called()


@pytest.mark.parametrize("receipt", [
    None, [], {}, {"inserted": True}, {"capture_sha256": "wrong", "inserted": True},
    {"capture_sha256": "same", "inserted": 1},
    {"capture_sha256": "same", "inserted": True, "extra": "ignored"},
])
def test_capture_rejects_untrustworthy_database_receipt(receipt: Any) -> None:
    captured = page()
    if isinstance(receipt, dict) and receipt.get("capture_sha256") == "same":
        receipt = receipt | {"capture_sha256": captured["capture_sha256"]}
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = receipt
    with patch("src.db.writer._client", return_value=client), pytest.raises(RuntimeError):
        archive_quote_capture(captured)


def test_snapshot_serialization_binds_actual_constructor_output_without_uploading_pages() -> None:
    captured = page()
    client = echo_client()
    original = copy.deepcopy(captured)
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_quote_snapshot([captured], as_of=RECEIPT, **PROVENANCE)
    client.rpc.assert_called_once()
    name, parameters = client.rpc.call_args.args
    assert name == "append_quote_snapshot"
    unsigned = parameters["p_unsigned_json"]
    document = json.loads(unsigned)
    assert set(document) == {"version", "implementation_sha256", "client_version", "reference"}
    assert document["reference"] == build_quote_reference([original], as_of=RECEIPT)
    assert document["reference"]["open"] == "1.100000000000000002"
    assert document["reference"]["validation_eligible"] is False
    assert parameters["p_snapshot_sha256"] == hashlib.sha256(unsigned.encode()).hexdigest()
    assert receipt["capture_count"] == 1
    assert captured == original
    client.table.assert_not_called()


def test_snapshot_retries_are_stable_and_later_as_of_is_a_new_snapshot() -> None:
    captured = page()
    client = echo_client()
    with patch("src.db.writer._client", return_value=client):
        first = archive_quote_snapshot([captured], as_of=RECEIPT, **PROVENANCE)
        retry = archive_quote_snapshot([captured], as_of=RECEIPT, **PROVENANCE)
        later = archive_quote_snapshot([captured], as_of=RECEIPT + timedelta(days=1), **PROVENANCE)
    assert first == retry
    assert later["snapshot_sha256"] != first["snapshot_sha256"]
    inputs = [json.loads(call.args[1]["p_unsigned_json"])["reference"]["input_sha256"]
              for call in client.rpc.call_args_list]
    assert len(set(inputs)) == 1


def test_duplicate_or_failed_captures_remain_explicit_incomplete_snapshot_evidence() -> None:
    captured = page()
    client = echo_client()
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_quote_snapshot([captured, captured], as_of=RECEIPT, **PROVENANCE)
    document = json.loads(client.rpc.call_args.args[1]["p_unsigned_json"])
    reference = document["reference"]
    assert reference["capture_sha256"] == [captured["capture_sha256"]] * 2
    assert reference["acquisition_complete"] is False and reference["open"] is None
    assert "duplicate_capture_hash" in reference["exclusion_reasons"]
    assert receipt["capture_count"] == 2


@pytest.mark.parametrize("provenance", [
    PROVENANCE | {"implementation_sha256": "A" * 64},
    PROVENANCE | {"implementation_sha256": "a" * 63},
    PROVENANCE | {"client_version": ""}, PROVENANCE | {"client_version": "x" * 129},
    PROVENANCE | {"client_version": "version with spaces"},
    PROVENANCE | {"client_version": "https://client?api_key=secret"},
])
def test_invalid_provenance_fails_before_client(provenance: dict[str, str]) -> None:
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_quote_snapshot([page()], as_of=RECEIPT, **provenance)
    factory.assert_not_called()


@pytest.mark.parametrize("kind", ["empty", "too_many", "mismatched_pair", "tampered", "naive"])
def test_invalid_snapshot_inputs_do_not_acquire_client(kind: str) -> None:
    captured = page()
    pages = [captured]
    as_of = RECEIPT
    if kind == "empty":
        pages = []
    elif kind == "too_many":
        pages = [captured] * 10001
    elif kind == "mismatched_pair":
        pages.append(page(pair="USDJPY"))
    elif kind == "tampered":
        captured["pair"] = "USDJPY"
    else:
        as_of = RECEIPT.replace(tzinfo=None)
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_quote_snapshot(pages, as_of=as_of, **PROVENANCE)
    factory.assert_not_called()


@pytest.mark.parametrize("receipt", [
    None, {}, {"snapshot_sha256": "same", "inserted": True},
    {"snapshot_sha256": "wrong", "inserted": True, "capture_count": 1},
    {"snapshot_sha256": "same", "inserted": 1, "capture_count": 1},
    {"snapshot_sha256": "same", "inserted": True, "capture_count": True},
    {"snapshot_sha256": "same", "inserted": True, "capture_count": 2},
    {"snapshot_sha256": "same", "inserted": True, "capture_count": 1, "extra": "ignored"},
])
def test_snapshot_rejects_invalid_receipts(receipt: Any) -> None:
    captured = page()
    client = echo_client()
    with patch("src.db.writer._client", return_value=client):
        correct = archive_quote_snapshot([captured], as_of=RECEIPT, **PROVENANCE)
    if isinstance(receipt, dict) and receipt.get("snapshot_sha256") == "same":
        receipt = receipt | {"snapshot_sha256": correct["snapshot_sha256"]}
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = receipt
    with patch("src.db.writer._client", return_value=client), pytest.raises(RuntimeError):
        archive_quote_snapshot([captured], as_of=RECEIPT, **PROVENANCE)


def test_rpc_failure_is_propagated_without_fallback_or_rewrite() -> None:
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("archive unavailable")
    with patch("src.db.writer._client", return_value=client):
        with pytest.raises(RuntimeError, match="archive unavailable"):
            archive_quote_capture(page())
        with pytest.raises(RuntimeError, match="archive unavailable"):
            archive_quote_snapshot([page()], as_of=RECEIPT, **PROVENANCE)
    assert [call.args[0] for call in client.rpc.call_args_list] == [
        "append_quote_capture", "append_quote_snapshot",
    ]
    client.table.assert_not_called()
