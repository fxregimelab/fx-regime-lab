"""Local transport and integrity controls; fixtures confer no acquisition authority."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from concurrent.futures import CancelledError
from copy import deepcopy
from dataclasses import fields, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from src.db import writer
from src.research import fpi_parse_record as originals
from src.research.fpi_capture import build_fpi_capture
from src.research.fpi_parse_record import build_fpi_artifact, build_fpi_parse_record
from src.research.fpi_qualification import FpiQualificationCommand, FpiQualificationEventV2
from src.research.fpi_saved_read import (
    FpiAdminReadManifest,
    FpiAdminReadPolicy,
    FpiAdminReadRequest,
    verify_fpi_admin_read_originals,
)
from tests.test_fpi_parse_record import successful_parse
from tests.test_fpi_read_references import expected_bundle
from tests.test_fpi_saved_read import sr_fixture, sr_refresh, sr_test_canonical, sr_test_sha


class AdminReadFake:
    """Apply filters, projection and row caps before any deliberate response corruption."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables
        self.calls: list[dict[str, Any]] = []
        self.current: dict[str, Any] = {}
        self.receipt: Any = None
        self.error: BaseException | None = None
        self.page_cap = 1000
        self.hook: Callable[[AdminReadFake, Any], Any] | None = None
        self.responses: list[Any] = []

    def table(self, name: str) -> AdminReadFake:
        self.current = {"table": name, "eq": {}, "in": {}}
        return self

    def rpc(self, name: str, args: dict[str, Any]) -> AdminReadFake:
        self.current = {"rpc": name, "args": args}
        return self

    def select(self, projection: str) -> AdminReadFake:
        assert projection != "*"
        self.current["projection"] = projection
        return self

    def eq(self, key: str, value: str) -> AdminReadFake:
        self.current["eq"][key] = value
        return self

    def in_(self, key: str, values: list[str]) -> AdminReadFake:
        assert 1 <= len(values) <= 64
        assert len(set(values)) == len(values)
        self.current["in"][key] = values.copy()
        return self

    def limit(self, value: int) -> AdminReadFake:
        assert 1 <= value <= 256
        self.current["limit"] = value
        return self

    def execute(self) -> SimpleNamespace:
        self.calls.append(deepcopy(self.current))
        if self.error is not None:
            raise self.error
        if "rpc" in self.current:
            data = self.receipt
        else:
            rows = self.tables[self.current["table"]]
            rows = [row for row in rows if all(
                row[key] == value for key, value in self.current["eq"].items()
            ) and all(row[key] in values for key, values in self.current["in"].items())]
            keys = self.current["projection"].split(",")
            data = [{key: row[key] for key in keys} for row in rows][
                :min(self.page_cap, self.current["limit"])
            ]
        if self.hook is not None:
            data = self.hook(self, data)
        self.responses.append(data)
        return SimpleNamespace(data=data)


def writer_fixture(
    document: dict[str, Any], rows: dict[str, Any],
) -> tuple[FpiAdminReadManifest, AdminReadFake]:
    text = sr_test_canonical(document)
    manifest = FpiAdminReadManifest(text)
    read_row = {
        "read_id": manifest.read_id, "decision_id": manifest.decision_id,
        "request_sha256": manifest.request_sha256,
        "request_document_json": sr_test_canonical(document["request"]),
        "policy_sha256": document["policy_sha256"], "read_sha256": manifest.read_sha256,
        "manifest_document_json": text, "read_at": manifest.read_at, "status": manifest.status,
    }
    fake = AdminReadFake({
        "fpi_admin_reads": [read_row],
        "fpi_captures": list(rows["capture_rows"]),
        "fpi_parse_results": list(rows["parse_rows"]),
        "fpi_implementation_artifacts": list(rows["artifact_rows"]),
        "fpi_qualification_events": list(rows["event_rows"]),
    })
    return manifest, fake


def bind_fake(monkeypatch: pytest.MonkeyPatch, fake: AdminReadFake) -> Mock:
    client = Mock(return_value=fake)
    monkeypatch.setattr(writer, "_client", client)
    return client


@pytest.mark.parametrize("operation", ["policy", "read"])
@pytest.mark.parametrize("corrupt", [None, "hash", "extra", "bool", "trust", "time"])
def test_admin_append_receipt(
    monkeypatch: pytest.MonkeyPatch, operation: str, corrupt: str | None,
) -> None:
    document, rows = sr_fixture(empty=True)
    manifest, fake = writer_fixture(document, rows)
    call: Callable[[Any], dict[str, Any]]
    if operation == "policy":
        value: Any = FpiAdminReadPolicy(sr_test_canonical(document["policy"]))
        call = writer.append_fpi_admin_read_policy
        fake.receipt = {"version": "fpi-admin-read-policy-receipt-v1",
                        "policy_sha256": value.policy_sha256, "inserted": True}
        args = {"p_policy_sha256": value.policy_sha256, "p_document_json": value.document_json}
    else:
        value = FpiAdminReadRequest(sr_test_canonical(document["request"]))
        call = writer.capture_fpi_admin_read
        fake.receipt = {
            "version": "fpi-admin-read-receipt-v1", "decision_id": value.decision_id,
            "request_sha256": value.request_sha256, "read_id": value.read_id,
            "read_sha256": manifest.read_sha256, "read_at": manifest.read_at,
            "status": "COMPLETE", "execution_state": "UNVERIFIED",
            "acquisition_state": "UNVERIFIED", "eligible": False, "inserted": True,
        }
        args = {"p_request_sha256": value.request_sha256, "p_document_json": value.document_json}
    bind_fake(monkeypatch, fake)
    if corrupt is not None:
        if corrupt == "hash":
            fake.receipt["policy_sha256" if operation == "policy" else "read_id"] = "0" * 64
        elif corrupt == "bool":
            fake.receipt["inserted"] = 1
        elif corrupt == "time":
            fake.receipt["read_at"] = "2026-09-28T00:00:00Z"
        elif corrupt == "trust":
            fake.receipt["eligible"] = True
        else:
            fake.receipt["private-fixture-secret"] = "private-fixture-secret"
        with pytest.raises(RuntimeError, match="^READ_INTEGRITY_ERROR$") as error:
            call(value)
        assert error.value.__suppress_context__
        assert error.value.__cause__ is None
    else:
        result = call(value)
        before = result.copy()
        fake.receipt["inserted"] = False
        retry = call(value)
        assert result == before
        assert retry == {**before, "inserted": False}
        assert result is not fake.receipt and retry is not fake.receipt
        assert fake.calls[0] == fake.calls[1]
    assert fake.calls[0] == {
        "rpc": ("append_fpi_admin_read_policy" if operation == "policy"
                else "capture_fpi_admin_read"),
        "args": args,
    }
    assert len(fake.calls) == (2 if corrupt is None else 1)


@pytest.mark.parametrize("operation", ["policy", "read", "load"])
def test_admin_forged_input(monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    document, _ = sr_fixture(empty=True)
    client = Mock(side_effect=AssertionError("must fail before client acquisition"))
    monkeypatch.setattr(writer, "_client", client)
    if operation == "load":
        for invalid_id in (None, True, "A" * 64, "0" * 63, "private-fixture-secret", 2,
                           type("ForgedStr", (str,), {})("0" * 64)):
            with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$"):
                writer.load_fpi_admin_read(invalid_id)  # type: ignore[arg-type]
    else:
        cls = FpiAdminReadPolicy if operation == "policy" else FpiAdminReadRequest
        call = writer.append_fpi_admin_read_policy if operation == "policy" else (
            writer.capture_fpi_admin_read
        )
        value = cls(sr_test_canonical(document["policy" if operation == "policy" else "request"]))
        for field in fields(value):
            for forged in (False, "0" * 64,
                           type("ForgedStr", (str,), {})(getattr(value, field.name))):
                bad = deepcopy(value)
                object.__setattr__(bad, field.name, forged)
                with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$"):
                    call(bad)  # type: ignore[arg-type]
        invalid_object: Any
        for invalid_object in (None, {}, SimpleNamespace(**vars(value)),
                               type("ForgedPolicy", (cls,), {})(value.document_json)):
            with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$"):
                call(invalid_object)
    client.assert_not_called()


@pytest.mark.parametrize("operation", ["policy", "read", "load"])
@pytest.mark.parametrize("error", [
    RuntimeError("private-fixture-secret"), CancelledError("cancel"),
    asyncio.CancelledError("cancel"), KeyboardInterrupt(), SystemExit(), MemoryError(),
])
def test_admin_transport_exceptions(
    monkeypatch: pytest.MonkeyPatch, operation: str, error: BaseException,
) -> None:
    document, rows = sr_fixture(empty=True)
    manifest, fake = writer_fixture(document, rows)
    bind_fake(monkeypatch, fake)
    fake.error = error
    inputs: dict[str, tuple[Any, Any]] = {
        "policy": (writer.append_fpi_admin_read_policy,
                   FpiAdminReadPolicy(sr_test_canonical(document["policy"]))),
        "read": (writer.capture_fpi_admin_read,
                 FpiAdminReadRequest(sr_test_canonical(document["request"]))),
        "load": (writer.load_fpi_admin_read, manifest.read_id),
    }
    call, value = inputs[operation]
    with pytest.raises(type(error)) as caught:
        call(value)
    if type(error) is RuntimeError:
        assert str(caught.value) == "READ_INTEGRITY_ERROR"
        assert caught.value.__suppress_context__
    else:
        assert caught.value is error
    assert len(fake.calls) == 1


@pytest.mark.parametrize("scope", ["empty", "support", "full"])
def test_admin_load_valid(monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    document, rows = sr_fixture(empty=scope == "empty", event=scope != "empty",
                                diagnostics=scope == "full", alternatives=scope == "full")
    manifest, fake = writer_fixture(document, rows)
    # PostgreSQL transport may choose a different spelling of the same UTC instant.
    fake.tables["fpi_admin_reads"][0]["read_at"] = "2026-09-28T00:00:00.000000Z"
    bind_fake(monkeypatch, fake)
    verify = Mock(wraps=verify_fpi_admin_read_originals)
    bulk = Mock(wraps=originals.build_fpi_read_references)
    capture_validation = Mock(wraps=getattr(originals, "validate_fpi_capture"))
    record_parts = Mock(wraps=originals._record_parts)
    artifact_validation = Mock(wraps=originals.validate_fpi_artifact)
    monkeypatch.setattr(writer, "verify_fpi_admin_read_originals", verify)
    monkeypatch.setattr("src.research.fpi_saved_read.build_fpi_read_references", bulk)
    monkeypatch.setattr(originals, "validate_fpi_capture", capture_validation)
    monkeypatch.setattr(originals, "_record_parts", record_parts)
    monkeypatch.setattr("src.research.fpi_saved_read.validate_fpi_artifact", artifact_validation)
    loaded = writer.load_fpi_admin_read(manifest.read_id)
    assert loaded == manifest and loaded is not manifest
    assert json.loads(loaded.document_json)["eligible"] is False
    assert json.loads(loaded.document_json)["feature"] is None
    verify.assert_called_once()
    bulk.assert_called_once()
    assert capture_validation.call_count == len(rows["capture_rows"])
    assert record_parts.call_count == len(rows["parse_rows"])
    assert artifact_validation.call_count == len(rows["artifact_rows"])
    assert fake.calls[0] == {"table": "fpi_admin_reads", "eq": {"read_id": manifest.read_id},
                             "in": {}, "projection": writer._FPI_ADMIN_READ_PROJECTION, "limit": 2}
    for call in fake.calls[1:]:
        assert len(call["in"]) == 1
        assert call["limit"] == len(next(iter(call["in"].values()))) + 1
    if scope == "support":
        checked = json.loads(loaded.document_json)["data"]
        assert len(checked["references"]["parses"][0]["memberships"]) == 3
        assert len(checked["candidate_membership_ids"]) == 1


@pytest.mark.parametrize("status", ["READ_SCOPE_EXCEEDED", "CLOCK_INCONSISTENT"])
def test_admin_failure_load(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    document, rows = sr_fixture(empty=True)
    document.update(status=status, data=None)
    if status == "READ_SCOPE_EXCEEDED":
        document["failure"] = {"code": status, "dimension": "CANDIDATES", "limit": 20000,
                               "observed": 20001, "measurement": "AT_LEAST", "witness": None}
    else:
        document["scope"]["newest_reporting_date"] = "2026-09-29"
        document["failure"] = {"code": status, "dimension": "NEWEST_DATE", "limit": None,
                               "observed": None, "measurement": None,
                               "witness": {"kind": "MEMBERSHIP_DATE", "id": None,
                                           "field": "reporting_date", "value": "2026-09-29"}}
    manifest, fake = writer_fixture(document, rows)
    bind_fake(monkeypatch, fake)
    verify = Mock(wraps=verify_fpi_admin_read_originals)
    monkeypatch.setattr(writer, "verify_fpi_admin_read_originals", verify)
    assert writer.load_fpi_admin_read(manifest.read_id) == manifest
    assert len(fake.calls) == 1
    verify.assert_called_once_with(manifest, capture_rows=(), parse_rows=(),
                                   artifact_rows=(), event_rows=())


@pytest.mark.parametrize("field", writer._FPI_ADMIN_READ_PROJECTION.split(","))
@pytest.mark.parametrize("value", ["private-fixture-secret", None, True])
def test_admin_row_corruption(monkeypatch: pytest.MonkeyPatch, field: str, value: Any) -> None:
    document, rows = sr_fixture(event=True)
    manifest, fake = writer_fixture(document, rows)
    fake.hook = lambda _, data: [{**data[0], field: value}]
    bind_fake(monkeypatch, fake)
    with pytest.raises(RuntimeError, match="^READ_INTEGRITY_ERROR$"):
        writer.load_fpi_admin_read(manifest.read_id)
    assert len(fake.calls) == 1


@pytest.mark.parametrize("table", ["fpi_admin_reads", "fpi_captures", "fpi_parse_results",
                                   "fpi_implementation_artifacts", "fpi_qualification_events"])
@pytest.mark.parametrize("corruption", ["missing", "duplicate", "extra", "unknown-field",
                                       "body", "stored-time", "truncated"])
def test_admin_dependency_corruption(
    monkeypatch: pytest.MonkeyPatch, table: str, corruption: str,
) -> None:
    document, rows = sr_fixture(event=True, alternatives=True)
    manifest, fake = writer_fixture(document, rows)
    identity = {"fpi_admin_reads": "read_id", "fpi_captures": "capture_sha256",
                "fpi_parse_results": "parse_id", "fpi_implementation_artifacts": "artifact_sha256",
                "fpi_qualification_events": "event_id"}[table]
    # Each callback runs only after the fake has enforced its query and provider row cap.
    def damage(current: AdminReadFake, data: Any) -> Any:
        if current.current["table"] != table:
            return data
        if corruption in ("missing", "truncated"):
            return data[:-1]
        if corruption == "duplicate":
            return data + [data[0].copy()]
        if corruption == "extra":
            return data + [{**data[0], identity: "0" * 64}]
        if corruption == "unknown-field":
            return [{**data[0], "private-fixture-secret": "private-fixture-secret"}]
        key = "stored_at" if corruption == "stored-time" and "stored_at" in data[0] else (
            "event_document_json" if table == "fpi_qualification_events" else (
                "manifest_document_json" if table == "fpi_admin_reads" else "document_json"
            )
        )
        return [{**data[0], key: "private-fixture-secret"}, *data[1:]]
    fake.hook = damage
    bind_fake(monkeypatch, fake)
    with pytest.raises(RuntimeError, match="^READ_(INTEGRITY_ERROR|DEPENDENCY_MISSING)$") as error:
        writer.load_fpi_admin_read(manifest.read_id)
    assert error.value.__cause__ is None and error.value.__suppress_context__
    assert any(call["table"] == table for call in fake.calls)


def test_admin_callback_detachment(monkeypatch: pytest.MonkeyPatch) -> None:
    document, rows = sr_fixture(event=True)
    manifest, fake = writer_fixture(document, rows)
    def change_prior(current: AdminReadFake, data: Any) -> Any:
        for previous in current.responses:
            for row in previous:
                for key in row:
                    row[key] = "private-fixture-secret"
        return data
    fake.hook = change_prior
    bind_fake(monkeypatch, fake)
    assert writer.load_fpi_admin_read(manifest.read_id) == manifest


def large_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    document, rows = sr_fixture(empty=True)
    captures, records, events, artifact_rows = [], [], [], list(rows["artifact_rows"])
    parse, sources = successful_parse(25)
    capture_document = json.loads(parse.capture.document_json)
    stored = "2026-09-26T00:00:00+00:00"
    for index in range(130):
        artifact = build_fpi_artifact(kind="PARSER", body=f"synthetic parser {index}".encode())
        artifact_rows.append({"kind": "PARSER", "artifact_sha256": artifact.artifact_sha256,
                              "document_json": artifact.document_json, "stored_at": stored})
        capture = build_fpi_capture(
            body=f"synthetic capture {index}".encode(), source_url=capture_document["source_url"],
            requested_at=datetime.fromisoformat(capture_document["requested_at"]),
            retrieved_at=datetime.fromisoformat(capture_document["retrieved_at"]),
            http_status=200,
        )
        captures.append(capture)
        record = build_fpi_parse_record(replace(parse, capture=capture,
                                                parser_sha256=artifact.artifact_sha256),
                                        source_evidence_documents=sources)
        records.append(record)
        member = json.loads(record.document_json)["days"][0]["membership_id"]
        events.append(FpiQualificationEventV2(
            FpiQualificationCommand("membership", member, "ACCEPT", "RESEARCH", "5" * 64),
            index + 1, datetime(2026, 9, 27, tzinfo=UTC),
        ))
    # Both kinds may legitimately retain the same raw body hash.
    selector = build_fpi_artifact(kind="SELECTOR", body=b"synthetic parser 0")
    artifact_rows = [row for row in artifact_rows if row["kind"] != "SELECTOR"]
    artifact_rows.append({"kind": "SELECTOR", "artifact_sha256": selector.artifact_sha256,
                          "document_json": selector.document_json, "stored_at": stored})
    document["policy"]["selector_sha256"] = selector.artifact_sha256
    references = json.loads(expected_bundle(tuple(captures), tuple(records)).document_json)
    data = document["data"]
    data["references"] = references
    members = sorted([{
        "membership_id": member["membership_id"], "value_sha256": member["value_sha256"],
        "reporting_date": member["reporting_date"], "parser_sha256": row["parser_sha256"],
    } for row in references["parses"] for member in row["memberships"]],
        key=lambda row: row["membership_id"])
    data["candidate_membership_ids"] = [row["membership_id"] for row in members]
    data["candidate_dates"] = ["2026-09-25"]
    document["scope"]["newest_reporting_date"] = "2026-09-25"
    data["storage_times"] = {
        "captures": [{"capture_sha256": row["capture_sha256"], "stored_at": stored}
                     for row in references["captures"]],
        "parses": [{"parse_id": row["parse_id"], "stored_at": stored}
                   for row in references["parses"]],
    }
    data["artifacts"] = sorted([{
        "kind": row["kind"], "artifact_sha256": row["artifact_sha256"],
        "document_size": len(row["document_json"]),
        "body_size": json.loads(row["document_json"])["body_size"], "stored_at": stored,
    } for row in artifact_rows], key=lambda row: (row["kind"], row["artifact_sha256"]))
    targets = {(kind, row[key]) for row in members for kind, key in (
        ("membership", "membership_id"), ("value", "value_sha256"),
        ("parser", "parser_sha256"), ("date", "reporting_date"),
    )}
    event_ids = {event.command.target: event.event_id for event in events}
    data["qualification"] = {
        "version": "fpi-qualification-view-v2", "members": members,
        "heads": [{"scope": kind, "target": target,
                   "event_id": event_ids.get(target) if kind == "membership" else None}
                  for kind, target in sorted(targets)],
        "events": [json.loads(event.document_json)
                   for event in sorted(events, key=lambda event: event.event_id)],
    }
    sr_refresh(document)
    return document, {
        "capture_rows": tuple({"capture_sha256": row.capture_sha256,
                                "document_json": row.document_json, "stored_at": stored}
                               for row in captures),
        "parse_rows": tuple({"parse_id": row.parse_id, "record_sha256": row.record_sha256,
                              "document_json": row.document_json, "stored_at": stored}
                             for row in records),
        "artifact_rows": tuple(artifact_rows),
        "event_rows": tuple({"event_id": row.event_id, "event_document_json": row.document_json}
                             for row in events),
    }


@pytest.mark.parametrize("page_cap", [1000, 63])
def test_admin_actual_batching(monkeypatch: pytest.MonkeyPatch, page_cap: int) -> None:
    document, rows = large_fixture()
    manifest, fake = writer_fixture(document, rows)
    fake.page_cap = page_cap
    bind_fake(monkeypatch, fake)
    if page_cap == 63:
        with pytest.raises(RuntimeError, match="^READ_DEPENDENCY_MISSING$"):
            writer.load_fpi_admin_read(manifest.read_id)
        assert len(fake.calls) == 2
        return
    assert writer.load_fpi_admin_read(manifest.read_id) == manifest
    for table in ("fpi_captures", "fpi_parse_results", "fpi_qualification_events"):
        sizes = [len(next(iter(call["in"].values()))) for call in fake.calls
                 if call["table"] == table]
        assert sizes == [64, 64, 2]
    artifact_calls = [call for call in fake.calls
                      if call["table"] == "fpi_implementation_artifacts"]
    assert [len(call["in"]["artifact_sha256"]) for call in artifact_calls] == [64, 64, 3, 1]
    assert [call["eq"] for call in artifact_calls] == [{"kind": "PARSER"}] * 3 + [
        {"kind": "SELECTOR"}
    ]
    shared = document["policy"]["selector_sha256"]
    assert sum(shared in call["in"]["artifact_sha256"] for call in artifact_calls) == 2


@pytest.mark.parametrize("case", ["manifest", "request", "capture", "parse", "artifact", "event"])
def test_admin_limits_before_decode(monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    document, rows = sr_fixture(event=True)
    manifest, fake = writer_fixture(document, rows)
    table, key, limit = {
        "manifest": ("fpi_admin_reads", "manifest_document_json", 16_000_000),
        "request": ("fpi_admin_reads", "request_document_json", 4096),
        "capture": ("fpi_captures", "document_json", 7_000_000),
        "parse": ("fpi_parse_results", "document_json", 4_000_000),
        "artifact": ("fpi_implementation_artifacts", "document_json", 7_000_000),
        "event": ("fpi_qualification_events", "event_document_json", 400_000),
    }[case]
    fake.tables[table][0][key] = "[" * (limit + 1)
    bind_fake(monkeypatch, fake)
    verify = Mock(wraps=verify_fpi_admin_read_originals)
    monkeypatch.setattr(writer, "verify_fpi_admin_read_originals", verify)
    with pytest.raises(RuntimeError, match="^READ_INTEGRITY_ERROR$"):
        writer.load_fpi_admin_read(manifest.read_id)
    verify.assert_not_called()


@pytest.mark.parametrize("case", ["capture", "parse", "artifact", "event", "support", "head"])
def test_admin_original_integrity(monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    document, rows = sr_fixture(event=True)
    manifest, fake = writer_fixture(document, rows)
    if case in ("support", "head"):
        changed = deepcopy(document)
        if case == "support":
            changed["data"]["references"]["parses"][0]["memberships"].pop(0)
        else:
            changed["data"]["qualification"]["heads"].pop(0)
        sr_refresh(changed)
        text = sr_test_canonical(changed)
        fake.tables["fpi_admin_reads"][0].update(
            manifest_document_json=text, read_sha256=sr_test_sha(text),
        )
    else:
        table, key, before, after = {
            "capture": ("fpi_captures", "document_json", "c3ludGhldGlj", "d3ludGhldGlj"),
            "parse": ("fpi_parse_results", "record_sha256", None, "0" * 64),
            "artifact": ("fpi_implementation_artifacts", "document_json",
                         "c3ludGhldGlj", "d3ludGhldGlj"),
            "event": ("fpi_qualification_events", "event_document_json", "RESEARCH", "RESEARCI"),
        }[case]
        row = fake.tables[table][0]
        original = row[key]
        row[key] = after if before is None else original.replace(before, after)
        assert row[key] != original and len(row[key]) == len(original)
    bind_fake(monkeypatch, fake)
    with pytest.raises(RuntimeError, match="^READ_INTEGRITY_ERROR$"):
        writer.load_fpi_admin_read(manifest.read_id)
