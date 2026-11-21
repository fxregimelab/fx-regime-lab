"""Independent strict-schema, source-fingerprint and central-writer regressions."""

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.db.writer import archive_quote_acquisition_event
from src.research.quote_attempt import (
    CLIENT_VERSION,
    DEFAULT_LIMITS,
    make_quote_acquisition_event,
    quote_runtime_manifest,
    validate_quote_acquisition_event,
)
from src.research.quote_capture import canonical_json

STAMP = datetime(2026, 5, 2, tzinfo=UTC)
FILES = (
    "pipeline/src/research/quote_acquisition.py", "pipeline/src/research/quote_attempt.py",
    "pipeline/src/research/quote_capture.py", "pipeline/src/research/quote_reference.py",
    "pipeline/src/db/writer.py",
)


def common() -> dict[str, Any]:
    manifest = canonical_json({
        "version": "quote-runtime-manifest-v1", "client_version": CLIENT_VERSION,
        "files": dict.fromkeys(FILES, "a" * 64),
        "dependencies": {"python": "3.14.5", "aiohttp": "3.12.0"},
    })
    return {
        "attempt_id": "b17f5249-790e-40bf-a65c-7f9644398e7e", "pair": "EURUSD",
        "instrument": "C:EUR-USD", "window_start_ns": "0", "window_end_ns": "86400000000000",
        "implementation_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
        "client_version": CLIENT_VERSION, "runtime_manifest_json": manifest,
        "limits": dict(DEFAULT_LIMITS),
    }


def started() -> dict[str, Any]:
    return make_quote_acquisition_event(common(), sequence=0, previous_event_sha256=None,
                                        kind="started", occurred_at=STAMP)


def rehash(event: dict[str, Any]) -> dict[str, Any]:
    event["event_sha256"] = hashlib.sha256(canonical_json({
        key: value for key, value in event.items() if key != "event_sha256"
    }).encode()).hexdigest()
    return event


def test_events_are_detached_and_phase_values_explicit() -> None:
    inputs = common()
    start = make_quote_acquisition_event(inputs, sequence=0, previous_event_sha256=None,
                                        kind="started", occurred_at=STAMP)
    inputs["limits"]["max_pages"] = 1
    assert start["limits"]["max_pages"] == 200
    saved = make_quote_acquisition_event(common(), sequence=1,
        previous_event_sha256=start["event_sha256"], kind="page_saved", occurred_at=STAMP,
        capture_sha256="b" * 64)
    terminal = make_quote_acquisition_event(common(), sequence=2,
        previous_event_sha256=saved["event_sha256"], kind="finished", occurred_at=STAMP,
        snapshot_sha256="c" * 64, status="complete", reason="completed")
    assert saved["runtime_manifest_json"] is None
    assert terminal["runtime_manifest_json"] is None
    for event in (start, saved, terminal):
        validate_quote_acquisition_event(json.loads(canonical_json(event)))


@pytest.mark.parametrize(("field", "value"), [
    ("version", "unknown"), ("attempt_id", "B17F5249-790E-40BF-A65C-7F9644398E7E"),
    ("attempt_id", 1), ("sequence", True), ("sequence", 0.0), ("sequence", -1),
    ("sequence", 10002), ("sequence", 1), ("previous_event_sha256", "a" * 64),
    ("pair", "GBPUSD"), ("pair", []), ("instrument", "C:USD-EUR"),
    ("window_start_ns", 0), ("window_start_ns", "00"), ("window_start_ns", "1"),
    ("window_start_ns", "0e0"), ("window_start_ns", "-86400000000000"),
    ("window_end_ns", "86400000000001"), ("implementation_sha256", "A" * 64),
    ("implementation_sha256", "b" * 64), ("client_version", "asserted-v1"),
    ("occurred_at", "2026-05-02"), ("occurred_at", "2026-05-02T00:00:00Z"),
    ("occurred_at", "2026-05-02T00:00:00+01:00"), ("occurred_at", None),
    ("runtime_manifest_json", None), ("kind", "finished"), ("capture_sha256", "c" * 64),
    ("snapshot_sha256", "d" * 64), ("status", "complete"), ("reason", "request_failed"),
])
def test_hash_consistent_but_invalid_start_rejected_before_database(field: str, value: Any) -> None:
    event = rehash(started() | {field: value})
    with patch("src.db.writer._client") as factory, pytest.raises(ValueError):
        archive_quote_acquisition_event(event)
    factory.assert_not_called()


@pytest.mark.parametrize("change", [
    {"max_pages": False}, {"max_pages": 10001}, {"max_pages": 1.0},
    {"max_page_bytes": 0}, {"max_page_bytes": 16777217},
    {"max_total_bytes": 1}, {"max_total_bytes": 268435457},
    {"deadline_seconds": 3601}, {"request_timeout_seconds": 61}, {"extra": 1},
])
def test_invalid_limits_reject_even_when_hash_matches(change: dict[str, Any]) -> None:
    event = started()
    event["limits"].update(change)
    with pytest.raises(ValueError):
        validate_quote_acquisition_event(rehash(event))


@pytest.mark.parametrize("case", [
    "missing", "extra", "hash", "manifest_duplicate", "manifest_spacing",
    "files", "dependency", "credential", "manifest_size",
])
def test_strict_fields_and_runtime_manifest(case: str) -> None:
    event = started()
    if case == "missing":
        event.pop("limits")
    elif case == "extra":
        event["debug"] = "secret"
    elif case == "hash":
        event["event_sha256"] = "0" * 64
    else:
        manifest = json.loads(event["runtime_manifest_json"])
        if case == "files":
            manifest["files"]["unexpected.py"] = "b" * 64
        elif case == "dependency":
            manifest["dependencies"]["python"] = "secret space"
        elif case == "credential":
            manifest["api_key"] = "secret"
        text = canonical_json(manifest)
        if case == "manifest_duplicate":
            text = '{"version":"quote-runtime-manifest-v1",' + text[1:]
        elif case == "manifest_spacing":
            text = " " + text
        elif case == "manifest_size":
            text = " " * 65537
        event["runtime_manifest_json"] = text
        event["implementation_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    if case != "hash":
        rehash(event)
    with pytest.raises(ValueError):
        validate_quote_acquisition_event(event)


@pytest.mark.parametrize(("change", "sequence"), [
    ({"reason": "completed", "status": "failed"}, 2),
    ({"reason": "request_failed", "status": "complete"}, 2),
    ({"reason": "raw provider error"}, 2), ({"snapshot_sha256": "bad"}, 2),
    ({"snapshot_sha256": "b" * 64}, 1),
    ({"status": "complete", "reason": "completed", "snapshot_sha256": None}, 2),
    ({"runtime_manifest_json": "{}"}, 2), ({"previous_event_sha256": None}, 2),
    ({"capture_sha256": "d" * 64}, 2), ({}, 202),
])
def test_terminal_phase_contract(change: dict[str, Any], sequence: int) -> None:
    event = make_quote_acquisition_event(common(), sequence=sequence if sequence < 202 else 2,
        previous_event_sha256="a" * 64, kind="finished", occurred_at=STAMP,
        status="failed", reason="request_failed")
    event.update(change)
    event["sequence"] = sequence
    with pytest.raises(ValueError):
        validate_quote_acquisition_event(rehash(event))


def test_make_rejects_extra_common_fields_and_naive_time_and_normalizes_timezone() -> None:
    with pytest.raises(ValueError):
        make_quote_acquisition_event(common() | {"secret": "bad"}, sequence=0,
            previous_event_sha256=None, kind="started", occurred_at=STAMP)
    with pytest.raises(ValueError):
        make_quote_acquisition_event(common(), sequence=0, previous_event_sha256=None,
                                     kind="started", occurred_at=datetime(2026, 5, 2))
    result = make_quote_acquisition_event(common(), sequence=0, previous_event_sha256=None,
        kind="started", occurred_at=STAMP.astimezone(timezone(timedelta(hours=5, minutes=30))))
    assert result["occurred_at"] == STAMP.isoformat()


def test_runtime_manifest_fingerprints_exact_bytes_and_actual_versions() -> None:
    text, fingerprint = quote_runtime_manifest()
    document = json.loads(text)
    root = Path(__file__).resolve().parents[2]
    assert set(document["files"]) == set(FILES)
    for name in FILES:
        assert document["files"][name] == hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert hashlib.sha256(text.encode()).hexdigest() == fingerprint
    assert len(document["dependencies"]) == 2
    with patch("src.research.quote_attempt.Path.read_bytes", return_value=b"changed source"):
        assert quote_runtime_manifest()[1] != fingerprint
    with patch("src.research.quote_attempt.version", return_value="999.0+test"):
        assert quote_runtime_manifest()[1] != fingerprint
    with patch("src.research.quote_attempt.Path.read_bytes", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            quote_runtime_manifest()


def test_writer_preserves_exact_event_and_duplicate_receipt() -> None:
    event = started()
    for inserted in (True, False):
        client = MagicMock()
        receipt = {"event_sha256": event["event_sha256"], "attempt_id": event["attempt_id"],
                   "sequence": 0, "inserted": inserted}
        client.rpc.return_value.execute.return_value.data = receipt
        with patch("src.db.writer._client", return_value=client):
            assert archive_quote_acquisition_event(event) == receipt
        name, parameters = client.rpc.call_args.args
        assert name == "append_quote_acquisition_event"
        assert set(parameters) == {"p_event_sha256", "p_unsigned_json"}
        assert hashlib.sha256(parameters["p_unsigned_json"].encode()).hexdigest() == (
            event["event_sha256"])
        assert json.loads(parameters["p_unsigned_json"]) | {
            "event_sha256": parameters["p_event_sha256"]} == event
        client.table.assert_not_called()


@pytest.mark.parametrize("change", [None, [], {}, {"sequence": True}, {"sequence": 0.0},
    {"sequence": 1}, {"inserted": 1}, {"extra": 1}, {"event_sha256": "wrong"},
    {"attempt_id": "wrong"}])
def test_writer_refuses_malformed_receipts(change: Any) -> None:
    event = started()
    receipt = {"event_sha256": event["event_sha256"], "attempt_id": event["attempt_id"],
               "sequence": 0, "inserted": True}
    result = receipt | change if isinstance(change, dict) and change else change
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = copy.deepcopy(result)
    with patch("src.db.writer._client", return_value=client), pytest.raises(RuntimeError):
        archive_quote_acquisition_event(event)


def test_writer_sanitizes_database_errors_without_fallback() -> None:
    client = MagicMock()
    client.rpc.side_effect = RuntimeError("apiKey=PRIVATE")
    with patch("src.db.writer._client", return_value=client), pytest.raises(RuntimeError) as caught:
        archive_quote_acquisition_event(started())
    assert "PRIVATE" not in str(caught.value)
    assert caught.value.__suppress_context__
    client.table.assert_not_called()
