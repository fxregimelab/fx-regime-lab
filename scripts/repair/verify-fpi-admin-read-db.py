"""Exercise saved administrative reads in a disposable real PostgreSQL database.

The parent owns runtime startup. No database or module-loading work occurs on import.
MIGRATION_SQL may be replaced by the parent for independent negative controls.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "supabase/migrations/20260928000014_fpi_admin_reads.sql"
MIGRATION_SQL: str | None = None
BASE = [
    "wsl",
    "-d",
    "Ubuntu-24.04",
    "--",
    "/usr/lib/postgresql/17/bin/psql",
    "-h",
    "/home/shreyash/.local/state/fxregime-repair/socket",
    "-p",
    "55437",
    "-X",
    "-qAt",
    "-v",
    "ON_ERROR_STOP=1",
    "-v",
    "VERBOSITY=terse",
]
NOW = "2026-10-01T12:00:00+00:00"
EMPTY_REFERENCES_HASH = "5043b6cf68a2600dc6ae8f6af32a222a8cfa63a2774f61ec2833060024a81e58"
EMPTY_QUALIFICATION_HASH = "4512d5d55af1633da699dbf2578900e14377e99a1acb26d2b6095fd667c5de19"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class Harness:
    def __init__(self) -> None:
        self.db = "fxfpiadmin_" + uuid.uuid4().hex
        self.migration = (
            MIGRATION_SQL
            if MIGRATION_SQL is not None
            else MIGRATION_PATH.read_text(encoding="utf-8")
        )
        self.checks: list[str] = []
        self.rejections = 0
        self.reads = 0
        self.originals: dict[str, tuple[Any, Any]] = {}
        self.artifacts: dict[tuple[str, str], Any] = {}
        self.events: dict[str, dict[str, Any]] = {}
        self.plans: list[str] = []
        self.bounds: dict[str, int] = {}
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT / "pipeline"))
        spec = importlib.util.spec_from_file_location(
            "fpi_existing_parse_fixture", ROOT / "scripts/repair/verify-fpi-parse-db.py"
        )
        assert spec is not None and spec.loader is not None
        self.fixture: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.fixture)
        self.record: Any = importlib.import_module("src.research.fpi_parse_record")
        self.qual: Any = importlib.import_module("src.research.fpi_qualification")

    def sql(
        self,
        text: str,
        *,
        database: str | None = None,
        error: str | None = None,
        timer: int = 30000,
    ) -> str:
        result = subprocess.run(
            BASE + ["-d", database or self.db],
            input=(f"SET statement_timeout='{timer}ms'; " + text).encode(),
            capture_output=True,
            timeout=70,
        )
        stderr = result.stderr.decode()
        if error is None:
            assert result.returncode == 0, stderr[:1400]
        else:
            assert result.returncode != 0 and error in stderr, stderr[:1400]
            assert "SENSITIVE_SENTINEL" not in stderr
            self.rejections += 1
        return result.stdout.decode().strip()

    def apply(self, source: str | None = None) -> None:
        self.sql(source or self.migration)
        self.clock(NOW)

    def clock(self, value: str) -> None:
        self.sql(
            "CREATE OR REPLACE FUNCTION public.fpi_admin_clock() RETURNS timestamptz "
            "LANGUAGE sql VOLATILE SET search_path=pg_catalog,public AS $$ SELECT "
            + literal(value)
            + "::timestamptz $$"
        )

    def setup(self) -> None:
        self.sql("CREATE DATABASE " + self.db, database="postgres")
        self.sql(
            "DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE "
            "rolname='anon') THEN CREATE ROLE anon; END IF; IF NOT "
            "EXISTS(SELECT FROM pg_roles WHERE rolname='authenticated') "
            "THEN CREATE ROLE authenticated; END IF; IF NOT EXISTS(SELECT"
            " FROM pg_roles WHERE rolname='service_role') THEN CREATE "
            "ROLE service_role; END IF; END $$;"
        )
        for name in (
            "20260927000010_fpi_capture_storage.sql",
            "20260927000011_fpi_parse_storage.sql",
            "20260928000012_fpi_qualification_storage.sql",
            "20260928000013_fpi_storage_timeouts.sql",
        ):
            self.sql((ROOT / "supabase/migrations" / name).read_text(encoding="utf-8"))
        self.apply()

    def rpc(self, name: str, *values: str, error: str | None = None) -> dict[str, Any]:
        raw = self.sql(
            "SET ROLE service_role; SELECT public."
            + name
            + "("
            + ",".join(map(literal, values))
            + ");",
            error=error,
        )
        return {} if error is not None else dict(json.loads(raw))

    def artifact(self, kind: str, body: bytes) -> Any:
        value = self.record.build_fpi_artifact(kind=kind, body=body)
        self.rpc("append_fpi_artifact", value.artifact_sha256, value.document_json)
        self.artifacts[(kind, value.artifact_sha256)] = value
        return value

    def policy(self, parser: Any, selector: Any, **overrides: Any) -> dict[str, Any]:
        value = {
            "version": "fpi-admin-read-policy-v1",
            "scope_version": "fpi-admin-scope-v1",
            "guardrail_version": "fpi-admin-read-limits-v1",
            "trust_mode": "ADMINISTRATIVE_UNVERIFIED",
            "selector_version": "NOT_EXECUTED",
            "selector_sha256": selector.artifact_sha256,
            "parser_allowlist": [parser.artifact_sha256],
            "definition_allowlist": ["fpi-inr-observation-v1"],
            "max_current_age_days": 7,
            "max_history_age_days": 365,
            "minimum_history": 10,
            "history_window": 60,
            "diagnostic_window_days": 7,
            "feature_version": "fixture-feature-v1",
            "model_version": "fixture-model-v1",
            "prediction_horizon": "T5",
            "source_rule": "AGREEMENT",
            "source_rationale": "Neither endpoint establishes source finality",
            "allow_withdrawal_fallback": False,
            "age_timezone": "Asia/Kolkata",
            "missingness": "MISSING",
            **overrides,
        }
        text = canonical(value)
        receipt = self.rpc("append_fpi_admin_read_policy", digest(text), text)
        assert receipt == {
            "version": "fpi-admin-read-policy-receipt-v1",
            "policy_sha256": digest(text),
            "inserted": True,
        }
        assert self.rpc("append_fpi_admin_read_policy", digest(text), text) == {
            **receipt,
            "inserted": False,
        }
        return value

    def request(self, policy: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        return {
            "version": "fpi-admin-read-request-v1",
            "decision_id": str(uuid.uuid4()),
            "run_id": str(uuid.uuid4()),
            "prediction_id": "3" * 64,
            "model_sha256": "4" * 64,
            "pair": "USDINR",
            "mode": "ADMIN_EVIDENCE_READ",
            "policy_sha256": digest(canonical(policy)),
            **overrides,
        }

    def read(self, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        text = canonical(request)
        receipt = self.rpc("capture_fpi_admin_read", digest(text), text)
        raw = self.sql(
            (
                "SET ROLE service_role; SELECT manifest_document_json FROM "
                "fpi_admin_reads WHERE read_id="
            )
            + literal(digest(text))
        )
        doc = json.loads(raw)
        assert raw == canonical(doc) and digest(raw) == receipt["read_sha256"]
        assert receipt == {
            "version": "fpi-admin-read-receipt-v1",
            "decision_id": request["decision_id"],
            "request_sha256": digest(text),
            "read_id": digest(text),
            "read_sha256": digest(raw),
            "read_at": doc["read_at"],
            "status": doc["status"],
            "execution_state": "UNVERIFIED",
            "acquisition_state": "UNVERIFIED",
            "eligible": False,
            "inserted": receipt["inserted"],
        }
        assert doc["execution_state"] == doc["acquisition_state"] == "UNVERIFIED"
        assert doc["eligible"] is False and doc["feature"] is None
        assert doc["request"] == request and doc["request_sha256"] == doc["read_id"] == digest(text)
        if doc["status"] != "COMPLETE":
            assert doc["data"] is None and len(raw) < 65536
        self.reads += 1
        return receipt, doc

    def retain(self, parse: Any, sources: tuple[str, ...]) -> Any:
        record = self.record.build_fpi_parse_record(parse, source_evidence_documents=sources)
        self.rpc("append_fpi_capture", parse.capture.capture_sha256, parse.capture.document_json)
        self.rpc(
            "append_fpi_parse_result", parse.parse_id, record.record_sha256, record.document_json
        )
        self.originals[parse.parse_id] = (parse, record)
        return record

    def sample(
        self, parser: Any, sequence: int, count: int = 2, failed: bool = False, latest: bool = False
    ) -> tuple[Any, Any]:
        parse, sources = self.fixture.synthetic_parse(
            parser.artifact_sha256, sequence=sequence, count=count, failed=failed
        )
        if latest:
            builder = importlib.import_module("src.research.fpi_capture")
            metadata = json.loads(parse.capture.document_json)
            capture = builder.build_fpi_capture(
                body=b"independent latest endpoint fixture",
                source_url="https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
                requested_at=datetime.fromisoformat(metadata["requested_at"]),
                retrieved_at=datetime.fromisoformat(metadata["retrieved_at"]),
                http_status=200,
            )
            parse = replace(parse, capture=capture)
        return parse, self.retain(parse, sources)

    def complete(
        self,
        doc: dict[str, Any],
        candidate_ids: set[str],
        parse_ids: set[str],
        event_ids: set[str] | None = None,
        heads: dict[tuple[str, str], str] | None = None,
    ) -> None:
        assert doc["status"] == "COMPLETE", doc["failure"]
        data = doc["data"]
        parses = [self.originals[key][0] for key in sorted(parse_ids)]
        captures = {p.capture.capture_sha256: p.capture for p in parses}
        references = self.record.build_fpi_read_references(
            captures=tuple(captures.values()),
            records=tuple(self.originals[key][1] for key in sorted(parse_ids)),
        )
        assert data["references"] == json.loads(references.document_json)
        assert data["reference_sha256"] == digest(references.document_json)
        assert data["candidate_membership_ids"] == sorted(candidate_ids)
        expected_members = sorted(
            [
                {
                    "membership_id": p.membership_id(d),
                    "value_sha256": d.value_sha256,
                    "parser_sha256": p.parser_sha256,
                    "reporting_date": d.reporting_date.isoformat(),
                }
                for p in parses
                for d in p.days
                if p.membership_id(d) in candidate_ids
            ],
            key=lambda d: d["membership_id"],
        )
        targets = {
            (kind, m[key])
            for m in expected_members
            for kind, key in (
                ("membership", "membership_id"),
                ("value", "value_sha256"),
                ("parser", "parser_sha256"),
                ("date", "reporting_date"),
            )
        }
        view = {
            "version": "fpi-qualification-view-v2",
            "members": expected_members,
            "heads": [
                {"scope": k, "target": v, "event_id": (heads or {}).get((k, v))}
                for k, v in sorted(targets)
            ],
            "events": [self.events[key] for key in sorted(event_ids or set())],
        }
        assert data["qualification"] == view and data["qualification_sha256"] == digest(
            canonical(view)
        )
        assert data["candidate_dates"] == sorted({m["reporting_date"] for m in expected_members})
        assert data["diagnostic_parse_ids"] == sorted(
            p.parse_id for p in parses if p.failure_reason is not None
        )
        parser_ids = {p.parser_sha256 for p in parses} | set(doc["policy"]["parser_allowlist"])
        expected_artifacts = {("PARSER", key) for key in parser_ids} | {
            ("SELECTOR", doc["policy"]["selector_sha256"])
        }
        assert [(a["kind"], a["artifact_sha256"]) for a in data["artifacts"]] == sorted(
            expected_artifacts
        )
        for a in data["artifacts"]:
            source = self.artifacts[(a["kind"], a["artifact_sha256"])]
            assert a["document_size"] == len(source.document_json)
            assert a["body_size"] == json.loads(source.document_json)["body_size"]

    def basic(self) -> tuple[Any, Any, dict[str, Any]]:
        parser = self.artifact("PARSER", b"independent fixture parser v1")
        selector = self.artifact("SELECTOR", b"independent fixture selector v1")
        policy = self.policy(parser, selector)
        self.sql(
            self.mutate(
                "fpi_implementation_artifacts", "stored_at='2026-09-27 00:00:00+00'", "true"
            )
        )
        request = self.request(
            policy,
            decision_id="11111111-1111-4111-8111-111111111111",
            run_id="22222222-2222-4222-8222-222222222222",
        )
        receipt, empty = self.read(request)
        self.complete(empty, set(), set())
        assert empty["scope"]["newest_reporting_date"] is None
        assert (
            digest(canonical(empty["data"]["references"]))
            == "5043b6cf68a2600dc6ae8f6af32a222a8cfa63a2774f61ec2833060024a81e58"
        )
        assert (
            digest(canonical(empty["data"]["qualification"]))
            == "4512d5d55af1633da699dbf2578900e14377e99a1acb26d2b6095fd667c5de19"
        )
        expected = {
            "version": "fpi-admin-read-v1",
            "read_id": digest(canonical(request)),
            "request_sha256": digest(canonical(request)),
            "request": request,
            "policy_sha256": digest(canonical(policy)),
            "policy": policy,
            "read_at": NOW,
            "scope": {
                "version": "fpi-admin-scope-v1",
                "india_date": "2026-10-01",
                "history_start_date": "2025-10-01",
                "history_start_clamped": False,
                "diagnostic_start_at": "2026-09-24T12:00:00+00:00",
                "diagnostic_start_clamped": False,
                "newest_reporting_date": None,
            },
            "execution_state": "UNVERIFIED",
            "acquisition_state": "UNVERIFIED",
            "eligible": False,
            "feature": None,
            "status": "COMPLETE",
            "failure": None,
            "data": {
                "candidate_membership_ids": [],
                "candidate_dates": [],
                "diagnostic_parse_ids": [],
                "references": {"captures": [], "parses": [], "version": "fpi-read-references-v1"},
                "reference_sha256": EMPTY_REFERENCES_HASH,
                "qualification": {
                    "events": [],
                    "heads": [],
                    "members": [],
                    "version": "fpi-qualification-view-v2",
                },
                "qualification_sha256": EMPTY_QUALIFICATION_HASH,
                "storage_times": {"captures": [], "parses": []},
                "artifacts": [
                    {
                        "kind": kind,
                        "artifact_sha256": value.artifact_sha256,
                        "document_size": len(value.document_json),
                        "body_size": json.loads(value.document_json)["body_size"],
                        "stored_at": "2026-09-27T00:00:00+00:00",
                    }
                    for kind, value in (("PARSER", parser), ("SELECTOR", selector))
                ],
            },
        }
        assert empty == expected
        assert (
            digest(canonical(expected))
            == "4fbffecbbc0f2d14a9d7277a129a13027621b2faeb6e7bb58cf9e6a3d8a4e930"
        )
        golden_policy = {**policy, "parser_allowlist": ["2" * 64], "selector_sha256": "1" * 64}
        assert (
            digest(canonical(golden_policy))
            == "005430dfbdde7fb1aacd83d75a8763fe931dbbd7de220a07be14a27dbaac5f87"
        )
        self.apply(self.limited("ARTIFACTS", 1))
        overflow_request = {**request, "decision_id": "44444444-4444-4444-8444-444444444444"}
        _, overflow = self.read(overflow_request)
        expected_overflow = {
            **expected,
            "request": overflow_request,
            "request_sha256": digest(canonical(overflow_request)),
            "read_id": digest(canonical(overflow_request)),
            "status": "READ_SCOPE_EXCEEDED",
            "data": None,
            "failure": {
                "code": "READ_SCOPE_EXCEEDED",
                "dimension": "ARTIFACTS",
                "limit": 1,
                "observed": 2,
                "measurement": "AT_LEAST",
                "witness": None,
            },
        }
        assert overflow == expected_overflow
        assert (
            digest(canonical(expected_overflow))
            == "9d7d848b2d447258744b736143c945e4fca4e2c40215ce42e05de68cd989e3b4"
        )
        self.apply()
        assert self.read(request)[0] == {**receipt, "inserted": False}
        changed = canonical({**request, "model_sha256": "5" * 64})
        self.rpc("capture_fpi_admin_read", digest(changed), changed, error="READ_REQUEST_CONFLICT")
        p, _ = self.sample(parser, 1)
        ids = {p.membership_id(d) for d in p.days}
        _, complete = self.read(self.request(policy))
        self.complete(complete, ids, {p.parse_id})
        short = self.policy(parser, selector, max_history_age_days=7)
        _, stale = self.read(self.request(short))
        self.complete(stale, {p.membership_id(p.days[-1])}, {p.parse_id})
        alternate = self.artifact("PARSER", b"independent disallowed parser v2")
        p2, _ = self.sample(alternate, 2, latest=True)
        ids |= {p2.membership_id(d) for d in p2.days}
        failed, _ = self.sample(alternate, 3, failed=True)
        _, multi = self.read(self.request(policy))
        self.complete(multi, ids, {p.parse_id, p2.parse_id, failed.parse_id})
        assert self.read(request)[1] == empty
        self.checks.append(
            "SR01-04,15,22: pinned empty complete/reference/view bytes, "
            "independent original references, complete endpoints/parsers,"
            " stale sentinel and immutable retry"
        )
        return parser, selector, policy

    def mutate(self, table: str, assignments: str, predicate: str) -> str:
        trigger = "fpi_captures_immutable_rows" if table == "fpi_captures" else "immutable_rows"
        return (
            f"ALTER TABLE {table} DISABLE TRIGGER {trigger}; "
            f"UPDATE {table} SET {assignments} WHERE {predicate}; "
            f"ALTER TABLE {table} ENABLE TRIGGER {trigger}; "
        )

    def scratch_read(
        self, policy: dict[str, Any], before: str, *, error: str | None = None
    ) -> dict[str, Any]:
        request = self.request(policy)
        text = canonical(request)
        raw = self.sql(
            "BEGIN; "
            + before
            + "SET ROLE service_role; SELECT capture_fpi_admin_read("
            + literal(digest(text))
            + ","
            + literal(text)
            + "); RESET ROLE; "
            "SELECT manifest_document_json FROM fpi_admin_reads WHERE read_id="
            + literal(digest(text))
            + "; ROLLBACK;",
            error=error,
        )
        return {} if error else dict(json.loads(raw.splitlines()[-1]))

    def clocks_and_corruption(self, policy: dict[str, Any]) -> None:
        success = next(p for p, _ in self.originals.values() if p.failure_reason is None)
        failed = next(p for p, _ in self.originals.values() if p.failure_reason is not None)
        capture_id = success.capture.capture_sha256
        for table, assignments, predicate, dimension in (
            (
                "fpi_parsed_memberships",
                "reporting_date='2026-10-02'",
                "membership_id=" + literal(success.membership_id(success.days[0])),
                "NEWEST_DATE",
            ),
            (
                "fpi_parse_results",
                "stored_at='2026-10-02'",
                "parse_id=" + literal(failed.parse_id),
                "FUTURE_FAILURE_STORAGE",
            ),
            (
                "fpi_captures",
                "stored_at='2026-10-02'",
                "capture_sha256=" + literal(capture_id),
                "REFERENCED_TIME",
            ),
            (
                "fpi_parse_results",
                "stored_at='2026-10-02'",
                "parse_id=" + literal(success.parse_id),
                "REFERENCED_TIME",
            ),
            (
                "fpi_implementation_artifacts",
                "stored_at='2026-10-02'",
                "kind='SELECTOR'",
                "REFERENCED_TIME",
            ),
            (
                "fpi_captures",
                (
                    "requested_at='9999-12-31 20:00+00',retrieved_at='9999-12-31 "
                    "20:00+00',stored_at='9999-12-31 20:00+00'"
                ),
                "capture_sha256=" + literal(capture_id),
                "INDIA_TIME_RANGE",
            ),
        ):
            doc = self.scratch_read(policy, self.mutate(table, assignments, predicate))
            assert (
                doc["status"] == "CLOCK_INCONSISTENT" and doc["failure"]["dimension"] == dimension
            ), doc
            assert doc["data"] is None
        for table, assignments, predicate in (
            ("fpi_captures", "body_size=body_size+1", "capture_sha256=" + literal(capture_id)),
            (
                "fpi_parse_results",
                "record_sha256=repeat('f',64)",
                "parse_id=" + literal(success.parse_id),
            ),
            (
                "fpi_parsed_memberships",
                "value_sha256=repeat('f',64)",
                "membership_id=" + literal(success.membership_id(success.days[0])),
            ),
            (
                "fpi_parsed_memberships",
                "source_evidence_document_json='{}'",
                "membership_id=" + literal(success.membership_id(success.days[0])),
            ),
            ("fpi_implementation_artifacts", "body_size=body_size+1", "kind='SELECTOR'"),
            (
                "fpi_captures",
                "document_json=repeat('x',7000001)",
                "capture_sha256=" + literal(capture_id),
            ),
            (
                "fpi_parse_results",
                "document_json=repeat('x',4000001)",
                "parse_id=" + literal(success.parse_id),
            ),
            (
                "fpi_implementation_artifacts",
                "document_json=repeat('x',7000001)",
                "kind='SELECTOR'",
            ),
        ):
            self.scratch_read(
                policy, self.mutate(table, assignments, predicate), error="READ_INTEGRITY_ERROR"
            )
        request = canonical(self.request(policy))
        for value in ("0001-01-01 BC", "9999-12-31 20:00:00+00", "infinity"):
            self.clock(value)
            self.rpc("capture_fpi_admin_read", digest(request), request, error="READ_CLOCK_RANGE")
        self.clock(NOW)
        for table, predicate in (
            ("fpi_parse_results", "parse_id=" + literal(failed.parse_id)),
            ("fpi_captures", "capture_sha256=" + literal(capture_id)),
            ("fpi_implementation_artifacts", "kind='SELECTOR'"),
        ):
            self.scratch_read(
                policy,
                self.mutate(table, "stored_at='infinity'", predicate),
                error="READ_INTEGRITY_ERROR",
            )
        # Year-one clamping on an otherwise empty archive, preserving all fixtures by rollback.
        before = (
            "SET session_replication_role=replica; DELETE FROM "
            "fpi_parsed_memberships; DELETE FROM fpi_parse_results; "
            "DELETE FROM fpi_captures; SET "
            "session_replication_role=origin; "
        )
        before += self.mutate(
            "fpi_implementation_artifacts", "stored_at='0001-01-01 00:00:00+00'", "true"
        )
        before += (
            "CREATE OR REPLACE FUNCTION public.fpi_admin_clock() RETURNS "
            "timestamptz LANGUAGE sql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ SELECT '0001-01-02 "
            "00:00:00+00'::timestamptz $$; "
        )
        clamped = self.scratch_read(policy, before)
        assert (
            clamped["status"] == "COMPLETE"
            and clamped["scope"]["history_start_clamped"]
            and clamped["scope"]["diagnostic_start_clamped"]
        )
        assert clamped["scope"]["history_start_date"] == "0001-01-01"
        self.checks.append(
            "SR08-09,19: deterministic clock failures, year "
            "bounds/clamping, corrupted projections/documents rejected"
        )

    def permissions_inputs(self, policy: dict[str, Any]) -> None:
        request = self.request(policy)
        _, original = self.read(request)
        before = self.sql(
            "SELECT count(*)||':'||sum(length(manifest_document_json)) FROM fpi_admin_reads"
        )
        self.apply()
        assert (
            self.sql(
                "SELECT count(*)||':'||sum(length(manifest_document_json)) FROM fpi_admin_reads"
            )
            == before
        )
        assert self.read(request)[1] == original
        for table in ("fpi_admin_reads", "fpi_admin_read_policies"):
            for role in ("anon", "authenticated"):
                self.sql(f"SET ROLE {role}; SELECT * FROM {table}", error="permission denied")
            self.sql(
                f"SET ROLE service_role; INSERT INTO {table} DEFAULT VALUES",
                error="permission denied",
            )
            self.sql(
                f"SET ROLE service_role; UPDATE {table} SET "
                + (
                    "read_id=read_id"
                    if table == "fpi_admin_reads"
                    else "policy_sha256=policy_sha256"
                ),
                error="permission denied",
            )
            self.sql(f"DELETE FROM {table}", error="immutable")
            self.sql(f"TRUNCATE {table} CASCADE", error="immutable")
        helpers = json.loads(
            self.sql(
                "SELECT jsonb_agg(oid::regprocedure::text) FROM pg_proc WHERE"
                " pronamespace='public'::regnamespace AND proname LIKE "
                "'fpi_admin_%'"
            )
        )
        for role in ("anon", "authenticated", "service_role"):
            for signature in helpers:
                assert (
                    self.sql(
                        "SELECT has_function_privilege("
                        + literal(role)
                        + ","
                        + literal(signature)
                        + ",'EXECUTE')"
                    )
                    == "f"
                )
        text = canonical(request)
        self.sql(
            "SET statement_timeout=0; SET ROLE service_role; SELECT capture_fpi_admin_read("
            + literal(digest(text))
            + ","
            + literal(text)
            + ")",
            error="READ_REQUEST_INVALID",
        )
        self.sql(
            (
                "BEGIN ISOLATION LEVEL REPEATABLE READ; SET ROLE "
                "service_role; SELECT capture_fpi_admin_read("
            )
            + literal(digest(text))
            + ","
            + literal(text)
            + ")",
            error="READ_REQUEST_INVALID",
        )
        for raw in (
            " " + text,
            text[:-1] + ',"pair":"USDINR"}',
            canonical({**request, "eligible": True}),
            canonical({**request, "version": "next"}),
            canonical({**request, "decision_id": str(uuid.uuid1())}),
            "[" * 33 + "0" + "]" * 33,
            "x" * 4097,
        ):
            self.rpc("capture_fpi_admin_read", digest(raw), raw, error="READ_INTEGRITY_ERROR")
        for key, value in (
            ("history_window", True),
            ("source_rationale", True),
            ("source_rationale", "SENSITIVE_SENTINEL\n"),
            ("parser_allowlist", ["a" * 64, "a" * 64]),
            ("definition_allowlist", []),
        ):
            raw = canonical({**policy, key: value})
            self.rpc("append_fpi_admin_read_policy", digest(raw), raw, error="READ_REQUEST_INVALID")
        self.clock("2026-11-02T12:00:00+00:00")
        shifted = self.scratch_read(policy, "SET TIME ZONE 'America/New_York'; ")
        assert shifted["scope"]["diagnostic_start_at"] == "2026-10-26T12:00:00+00:00"
        self.clock(NOW)
        self.checks.append(
            "SR20-22: strict input/refused authority, inherited "
            "timeout/isolation, private helpers, immutable owner/service "
            "boundaries and populated reapply"
        )

    def scope_edges(self, parser: Any, selector: Any, policy: dict[str, Any]) -> None:
        # A full Monthly parse crosses the lower boundary; another parse exists only on its support
        # date.
        alternate = self.artifact("PARSER", b"support-only alternate")
        support_only, _ = self.sample(alternate, 40, count=1)
        narrow = self.policy(parser, selector, max_current_age_days=1, max_history_age_days=1)
        before = self.mutate("fpi_captures", "stored_at='2026-01-03 13:00+00'", "true")
        before += self.mutate("fpi_parse_results", "stored_at='2026-01-03 13:00+00'", "true")
        before += self.mutate(
            "fpi_implementation_artifacts", "stored_at='2026-01-03 13:00+00'", "true"
        )
        before += (
            "CREATE OR REPLACE FUNCTION public.fpi_admin_clock() RETURNS "
            "timestamptz LANGUAGE sql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ SELECT '2026-01-03 "
            "14:00+00'::timestamptz $$; "
        )
        doc = self.scratch_read(narrow, before)
        chosen = [
            p for p, _ in self.originals.values() if p.failure_reason is None and len(p.days) == 2
        ]
        failed_ids = {
            p.parse_id for p, _ in self.originals.values() if p.failure_reason is not None
        }
        self.complete(
            doc,
            {p.membership_id(p.days[-1]) for p in chosen},
            {p.parse_id for p in chosen} | failed_ids,
        )
        assert support_only.parse_id not in {
            p["parse_id"] for p in doc["data"]["references"]["parses"]
        }
        assert doc["scope"]["history_start_date"] == "2026-01-02"
        # Failure branches are a closed time interval plus a fixed successful-capture seed.
        base = chosen[0]
        new_parsers = [self.artifact("PARSER", f"failure branch {n}".encode()) for n in range(5)]
        left, _ = self.sample(new_parsers[0], 41, failed=True)
        right, _ = self.sample(new_parsers[1], 42, failed=True)
        shared = replace(left, capture=base.capture, parser_sha256=new_parsers[2].artifact_sha256)
        self.retain(shared, ())
        recursive = replace(left, parser_sha256=new_parsers[3].artifact_sha256)
        self.retain(recursive, ())
        unrelated, _ = self.sample(new_parsers[4], 43, failed=True)
        before = self.mutate(
            "fpi_parse_results", "stored_at='2026-09-23 12:00+00'", "failure_reason IS NOT NULL"
        )
        before += self.mutate(
            "fpi_parse_results",
            "stored_at='2026-09-24 12:00+00'",
            "parse_id=" + literal(left.parse_id),
        )
        before += self.mutate(
            "fpi_parse_results",
            "stored_at='2026-10-01 12:00+00'",
            "parse_id=" + literal(right.parse_id),
        )
        doc = self.scratch_read(policy, before)
        successes = [p for p, _ in self.originals.values() if p.failure_reason is None]
        included = {p.parse_id for p in successes} | {
            left.parse_id,
            right.parse_id,
            shared.parse_id,
        }
        self.complete(doc, {p.membership_id(d) for p in successes for d in p.days}, included)
        assert (
            recursive.parse_id not in doc["data"]["diagnostic_parse_ids"]
            and unrelated.parse_id not in doc["data"]["diagnostic_parse_ids"]
        )
        self.checks.append(
            "SR05-06: Monthly lower-bound support without alternative "
            "expansion; both closed diagnostic boundaries, old "
            "candidate-capture failure and nonrecursive failure-only "
            "capture"
        )

    def qualification(self, policy: dict[str, Any]) -> None:
        parses = [p for p, _ in self.originals.values() if p.failure_reason is None]
        chosen = parses[0]
        member = chosen.membership_id(chosen.days[0])
        day = chosen.days[0].reporting_date.isoformat()
        basis = tuple(
            sorted(
                p.membership_id(d)
                for p in parses
                for d in p.days
                if d.reporting_date.isoformat() == day
            )
        )
        self.sql(
            "CREATE OR REPLACE FUNCTION public.fpi_qualification_clock() "
            "RETURNS timestamptz LANGUAGE sql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ SELECT '2026-09-27 "
            "00:00:00+00'::timestamptz $$"
        )
        command = self.qual.FpiQualificationCommand(
            "membership", member, "ACCEPT", "ADMIN_REVIEW", "a" * 64
        )
        accepted = self.rpc("append_fpi_qualification", command.command_id, command.document_json)
        self.events[accepted["event_id"]] = json.loads(accepted["event_document_json"])
        command = self.qual.FpiQualificationCommand(
            "date",
            day,
            "RESOLVE",
            "ADMIN_REVIEW",
            "a" * 64,
            chosen_membership_id=member,
            basis_membership_ids=basis,
        )
        resolved = self.rpc("append_fpi_qualification", command.command_id, command.document_json)
        self.events[resolved["event_id"]] = json.loads(resolved["event_document_json"])
        self.sql(
            "CREATE OR REPLACE FUNCTION public.fpi_qualification_clock() "
            "RETURNS timestamptz LANGUAGE sql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ SELECT '2026-09-26 "
            "00:00:00+00'::timestamptz $$"
        )
        previous = accepted["event_id"]
        for index in range(8):
            command = self.qual.FpiQualificationCommand(
                "membership",
                member,
                "WITHDRAW" if index % 2 == 0 else "ACCEPT",
                "ADMIN_REVIEW",
                "a" * 64,
                expected_prior_event_id=previous,
            )
            result = self.rpc("append_fpi_qualification", command.command_id, command.document_json)
            previous = result["event_id"]
            self.events[previous] = json.loads(result["event_document_json"])
        _, doc = self.read(self.request(policy))
        ids = {p.membership_id(d) for p in parses for d in p.days}
        self.complete(
            doc,
            ids,
            set(self.originals),
            {accepted["event_id"], resolved["event_id"], previous},
            {("date", day): resolved["event_id"], ("membership", member): previous},
        )
        assert len(doc["data"]["qualification"]["events"]) == 3
        bad = self.scratch_read(
            policy,
            self.mutate(
                "fpi_qualification_events",
                "recorded_at='2026-10-02'",
                "event_id=" + literal(previous),
            ),
        )
        assert bad["failure"]["dimension"] == "REFERENCED_TIME"
        for assignments in (
            "recorded_at='2026-09-25'",
            "event_ordinal=1000000",
            "scope='value',target=" + literal(chosen.days[0].value_sha256),
            "command_document_json='{}'",
            "event_document_json=repeat('x',400001)",
        ):
            self.scratch_read(
                policy,
                self.mutate(
                    "fpi_qualification_events", assignments, "event_id=" + literal(previous)
                ),
                error="READ_INTEGRITY_ERROR",
            )
        self.checks.append(
            "SR11,14: equal/decreasing ordinal history, current plus "
            "historical resolution witness closure, explicit absence and "
            "future-event clock refusal"
        )

    def limited(self, dimension: str, limit: int) -> str:
        spans = {
            "CANDIDATES": ("candidates", "candidate_parses", 20000),
            "PARSES": ("candidate_parses", "parses", 2048),
            "CAPTURES": ("capture_ids", "captures", 2048),
            "SUPPORT_MEMBERSHIPS": ("support", "artifact_ids", 20000),
            "ARTIFACTS": ("artifact_ids", "artifacts", 2113),
            "HEADS": ("targets", "heads", 100000),
            "EVENTS": ("event_ids", "events", 100000),
            "ORIGINAL_BYTES": ("original_guard", "capture_documents_input", 64000000),
            "REFERENCE_BYTES": ("reference_guard", "qualification_size", 16000000),
            "QUALIFICATION_BYTES": ("qualification_guard", "event_documents_input", 16000000),
            "MANIFEST_BYTES": ("final_guard", "data_input", 16000000),
        }
        first, last, old = spans[dimension]
        start = self.migration.index(" " + first + " AS MATERIALIZED")
        stop = self.migration.index(" " + last + " AS MATERIALIZED", start + 1)
        body = self.migration[start:stop]
        body = re.sub(r"\b" + str(old + 1) + r"\b", str(limit + 1), body)
        body = re.sub(r"\b" + str(old) + r"\b", str(limit), body)
        return self.migration[:start] + body + self.migration[stop:]

    def guardrails(self, policy: dict[str, Any]) -> None:
        _, doc = self.read(self.request(policy))
        data = doc["data"]
        refs = data["references"]
        self.bounds = {
            "CANDIDATES": len(data["candidate_membership_ids"]),
            "PARSES": len(refs["parses"]),
            "CAPTURES": len(refs["captures"]),
            "SUPPORT_MEMBERSHIPS": sum(len(p["memberships"]) for p in refs["parses"]),
            "ARTIFACTS": len(data["artifacts"]),
            "HEADS": len(data["qualification"]["heads"]),
            "EVENTS": len(data["qualification"]["events"]),
            "ORIGINAL_BYTES": sum(
                x["document_size"] for x in refs["captures"] + refs["parses"] + data["artifacts"]
            ),
            "REFERENCE_BYTES": len(canonical(refs)),
            "QUALIFICATION_BYTES": len(canonical(data["qualification"])),
            "MANIFEST_BYTES": len(canonical(doc)),
        }
        for dimension, observed in self.bounds.items():
            self.apply(self.limited(dimension, observed))
            _, at = self.read(self.request(policy))
            assert at["status"] == "COMPLETE", (dimension, at["failure"])
            self.apply(self.limited(dimension, observed - 1))
            request = self.request(policy)
            receipt, over = self.read(request)
            assert (
                over["status"] == "READ_SCOPE_EXCEEDED"
                and over["failure"]["dimension"] == dimension
            ), (dimension, over)
            assert (
                over["failure"]["limit"] == observed - 1 and over["failure"]["observed"] >= observed
            )
            assert over["failure"]["measurement"] == (
                "EXACT" if dimension.endswith("BYTES") else over["failure"]["measurement"]
            )
            self.apply()
            assert self.read(request)[0] == {**receipt, "inserted": False}
        # Earlier count guard wins over an uninspected future candidate metadata clock.
        self.apply(self.limited("CANDIDATES", 1))
        candidate = next(p for p, _ in self.originals.values() if p.failure_reason is None)
        doc = self.scratch_read(
            policy,
            self.mutate(
                "fpi_captures",
                "stored_at='2026-10-02'",
                "capture_sha256=" + literal(candidate.capture.capture_sha256),
            ),
        )
        assert doc["failure"]["dimension"] == "CANDIDATES"
        # Prove that over-limit inputs never invoke raw decoding, with an under-limit positive
        # control.
        decoder = (
            "CREATE OR REPLACE FUNCTION public.fpi_admin_original(k "
            "text,i text,value text,cap integer) RETURNS jsonb LANGUAGE "
            "plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$ "
            "BEGIN RAISE EXCEPTION 'DECODER_CALLED'; END $$; "
        )
        doc = self.scratch_read(policy, decoder)
        assert doc["failure"]["dimension"] == "CANDIDATES"
        self.apply()
        self.scratch_read(policy, decoder, error="READ_INTEGRITY_ERROR")
        self.sql(
            "CREATE FUNCTION scratch_decoder(integer) RETURNS integer LANGUAGE plpgsql "
            "VOLATILE AS $$ BEGIN RAISE EXCEPTION 'DECODER_CALLED'; END $$"
        )
        self.sql(
            "SELECT CASE WHEN (SELECT count(*) FROM generate_series(1,2))<=1 "
            "THEN array_agg(scratch_decoder(x)) END FROM generate_series(1,2) x",
            error="DECODER_CALLED",
        )
        guarded = (
            "WITH bound AS MATERIALIZED (SELECT count(*) n FROM generate_series(1,2)), "
            "input AS MATERIALIZED (SELECT x FROM generate_series(1,2) x "
            "CROSS JOIN bound WHERE n<=1) SELECT coalesce(array_agg(scratch_decoder(x)),"
            "ARRAY[]::integer[]) FROM input"
        )
        assert self.sql(guarded) == "{}"
        negative_plan = self.sql("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) " + guarded)
        self.plans.append(
            canonical(
                {
                    "guarded_decoder_plan_sha256": digest(negative_plan),
                    "case_only_control_rejected": True,
                }
            )
        )
        self.sql("DROP FUNCTION scratch_decoder(integer)")
        # Preliminary date-head bytes precede the subsequent event closure count.
        source = self.limited("EVENTS", 0)
        begin = source.index(" preliminary_guard AS MATERIALIZED")
        end = source.index(" date_events_input AS MATERIALIZED", begin)
        source = source[:begin] + source[begin:end].replace("16000000", "1") + source[end:]
        self.apply(source)
        _, doc = self.read(self.request(policy))
        assert (
            doc["failure"]["dimension"] == "QUALIFICATION_BYTES"
            and doc["failure"]["measurement"] == "AT_LEAST"
        )
        self.apply()
        # Inspect the actual CTE execution plan with all relations, then indexed source probes.
        request_text = canonical(self.request(policy))
        query = (
            "WITH\n"
            + self.migration.split("\n WITH\n", 1)[1].split(
                "\n INSERT INTO public.fpi_admin_reads", 1
            )[0]
        )
        query = query.replace("p_request_sha256", literal(digest(request_text)))
        query = re.sub(r"\breq\b", "(" + literal(request_text) + "::jsonb)", query)
        plan = self.sql(
            "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) " + query + " SELECT doc FROM manifest"
        )
        parsed_plan = json.loads(plan)[0]
        assert parsed_plan["Plan"]["Actual Rows"] == 1
        self.plans.append(
            canonical(
                {
                    "execution_ms": parsed_plan["Execution Time"],
                    "planning_ms": parsed_plan["Planning Time"],
                    "plan_sha256": digest(plan),
                }
            )
        )
        for query, index in (
            (
                (
                    "SELECT membership_id FROM fpi_parsed_memberships WHERE "
                    "reporting_date BETWEEN '2026-01-01' AND '2026-01-02' LIMIT 2"
                ),
                "fpi_admin_membership_date_id",
            ),
            (
                (
                    "SELECT parse_id FROM fpi_parse_results WHERE failure_reason "
                    "IS NOT NULL AND stored_at>'2026-01-01' LIMIT 2"
                ),
                "fpi_admin_failure_time_id",
            ),
        ):
            plan = self.sql("SET enable_seqscan=off; EXPLAIN (ANALYZE,BUFFERS) " + query)
            assert index in plan
            self.plans.append(
                canonical({"index": index, "actual_index_used": True, "plan_sha256": digest(plan)})
            )
        self.checks.append(
            "SR16-17,25-26: all eleven dimensions at bound and over "
            "bound, immutable overflow retry, decoder guard positive "
            "control, staged precedence and actual plans"
        )

    def hold(self, key: int) -> subprocess.Popen[bytes]:
        process = subprocess.Popen(
            BASE + ["-d", self.db],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(
            f"BEGIN; SELECT pg_advisory_xact_lock(946031,{key}); SELECT 'HELD';\n".encode()
        )
        process.stdin.flush()
        while process.stdout.readline().strip() != b"HELD":
            assert process.poll() is None
        return process

    def release(self, process: subprocess.Popen[bytes]) -> None:
        out, err = process.communicate(b"COMMIT;\n\\q\n", timeout=10)
        assert process.returncode == 0, (out, err)

    def wait_blocked(self, name: str) -> None:
        end = time.monotonic() + 8
        while time.monotonic() < end:
            if (
                self.sql(
                    "SELECT count(*) FROM pg_stat_activity WHERE application_name="
                    + literal(name)
                    + " AND wait_event='advisory'"
                )
                == "1"
            ):
                return
            time.sleep(0.04)
        raise AssertionError("Worker did not reach the observed advisory barrier")

    def concurrency(self, parser: Any, policy: dict[str, Any]) -> None:
        request = self.request(policy)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.read(request), range(2)))
        assert sorted(r[0]["inserted"] for r in results) == [False, True]
        assert results[0][1] == results[1][1]
        # Block an actual new parse transaction after all member inserts, before commit.
        parse, sources = self.fixture.synthetic_parse(parser.artifact_sha256, sequence=90)
        record = self.record.build_fpi_parse_record(parse, source_evidence_documents=sources)
        self.rpc("append_fpi_capture", parse.capture.capture_sha256, parse.capture.document_json)
        held = self.hold(1)
        with ThreadPoolExecutor(max_workers=1) as pool:
            work = pool.submit(
                self.sql,
                (
                    "SET application_name='fpi-admin-parse-barrier'; BEGIN; SET "
                    "ROLE service_role; SELECT append_fpi_parse_result("
                )
                + ",".join(
                    map(literal, (parse.parse_id, record.record_sha256, record.document_json))
                )
                + "); RESET ROLE; SELECT pg_advisory_xact_lock(946031,1); COMMIT;",
            )
            try:
                self.wait_blocked("fpi-admin-parse-barrier")
                _, before = self.read(self.request(policy))
                assert parse.parse_id not in {
                    p["parse_id"] for p in before["data"]["references"]["parses"]
                }
            finally:
                self.release(held)
            work.result(timeout=10)
        self.originals[parse.parse_id] = (parse, record)
        _, after = self.read(self.request(policy))
        assert {parse.membership_id(d) for d in parse.days} <= set(
            after["data"]["candidate_membership_ids"]
        )
        # Force a middle-member error in the real append RPC; no parent or child survives.
        other, sources = self.fixture.synthetic_parse(parser.artifact_sha256, sequence=91)
        record = self.record.build_fpi_parse_record(other, source_evidence_documents=sources)
        self.rpc("append_fpi_capture", other.capture.capture_sha256, other.capture.document_json)
        self.sql(
            (
                "CREATE FUNCTION scratch_member_failure() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN IF NEW.parse_id="
            )
            + literal(other.parse_id)
            + (
                " AND NEW.reporting_date='2026-01-02' THEN RAISE EXCEPTION "
                "'scratch failure'; END IF; RETURN NEW; END $$; CREATE "
                "TRIGGER scratch_member_failure BEFORE INSERT ON "
                "fpi_parsed_memberships FOR EACH ROW EXECUTE FUNCTION "
                "scratch_member_failure();"
            )
        )
        self.rpc(
            "append_fpi_parse_result",
            other.parse_id,
            record.record_sha256,
            record.document_json,
            error="FPI parse rejected",
        )
        assert (
            self.sql(
                "SELECT count(*) FROM fpi_parse_results WHERE parse_id=" + literal(other.parse_id)
            )
            == "0"
        )
        assert (
            self.sql(
                "SELECT count(*) FROM fpi_parsed_memberships WHERE parse_id="
                + literal(other.parse_id)
            )
            == "0"
        )
        self.sql(
            "DROP TRIGGER scratch_member_failure ON "
            "fpi_parsed_memberships; DROP FUNCTION "
            "scratch_member_failure()"
        )
        # Hold the actual decision namespace before the RPC begins; commit a new original during its
        # wait.
        request = self.request(policy)
        key = int(digest(request["decision_id"])[:8], 16)
        if key >= 2**31:
            key -= 2**32
        process = subprocess.Popen(
            BASE + ["-d", self.db],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(
            f"BEGIN; SELECT pg_advisory_xact_lock(946029,{key}); SELECT 'HELD';\n".encode()
        )
        process.stdin.flush()
        while process.stdout.readline().strip() != b"HELD":
            assert process.poll() is None
        text = canonical(request)
        self.clock("2026-10-01T18:29:59+00:00")
        with ThreadPoolExecutor(max_workers=1) as pool:
            work = pool.submit(
                self.sql,
                (
                    "SET application_name='fpi-admin-decision-barrier'; SET ROLE "
                    "service_role; SELECT capture_fpi_admin_read("
                )
                + literal(digest(text))
                + ","
                + literal(text)
                + ")",
            )
            try:
                self.wait_blocked("fpi-admin-decision-barrier")
                committed, _ = self.sample(parser, 92)
                self.clock("2026-10-01T18:30:00+00:00")
            finally:
                self.release(process)
            receipt = json.loads(work.result(timeout=10))
        assert receipt["read_at"] == "2026-10-01T18:30:00+00:00"
        _, doc = self.read(request)
        assert doc["scope"]["india_date"] == "2026-10-02"
        assert {committed.membership_id(d) for d in committed.days} <= set(
            doc["data"]["candidate_membership_ids"]
        )
        self.clock(NOW)
        # A real outer timer cancels the same lock path and leaves no retained read.
        req = self.request(policy)
        raw = canonical(req)
        key = int(digest(req["decision_id"])[:8], 16)
        if key >= 2**31:
            key -= 2**32
        process = subprocess.Popen(
            BASE + ["-d", self.db],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(
            f"BEGIN; SELECT pg_advisory_xact_lock(946029,{key}); SELECT 'HELD';\n".encode()
        )
        process.stdin.flush()
        while process.stdout.readline().strip() != b"HELD":
            assert process.poll() is None
        try:
            self.sql(
                "SET ROLE service_role; SELECT capture_fpi_admin_read("
                + literal(digest(raw))
                + ","
                + literal(raw)
                + ")",
                error="statement timeout",
                timer=150,
            )
            assert (
                self.sql(
                    "SELECT count(*) FROM fpi_admin_reads WHERE read_id=" + literal(digest(raw))
                )
                == "0"
            )
        finally:
            self.release(process)
        assert self.read(req)[0]["inserted"]
        self.checks.append(
            "SR12-13,15,18,24: observed transaction/decision barriers, "
            "atomic full parse visibility/rollback, concurrent identity, "
            "actual cancellation and same-identity recovery"
        )

    def visibility_edges(self, policy: dict[str, Any]) -> None:
        existing = next(p for p, _ in self.originals.values() if p.failure_reason is None)
        for shared in (False, True):
            parser = self.artifact(
                "PARSER", b"old uncommitted shared" if shared else b"old uncommitted unrelated"
            )
            value, sources = self.fixture.synthetic_parse(
                parser.artifact_sha256, sequence=120 + int(shared), failed=True
            )
            if shared:
                value = replace(value, capture=existing.capture)
            record = self.record.build_fpi_parse_record(value, source_evidence_documents=sources)
            self.rpc(
                "append_fpi_capture", value.capture.capture_sha256, value.capture.document_json
            )
            held = self.hold(2)
            with ThreadPoolExecutor(max_workers=1) as pool:
                transaction = (
                    "SET application_name='fpi-admin-old-failure'; BEGIN; SET "
                    "ROLE service_role; SELECT append_fpi_parse_result("
                )
                transaction += (
                    ",".join(
                        map(literal, (value.parse_id, record.record_sha256, record.document_json))
                    )
                    + "); RESET ROLE; "
                )
                transaction += self.mutate(
                    "fpi_parse_results",
                    "stored_at='2026-09-23 12:00+00'",
                    "parse_id=" + literal(value.parse_id),
                )
                work = pool.submit(
                    self.sql, transaction + "SELECT pg_advisory_xact_lock(946031,2); COMMIT;"
                )
                try:
                    self.wait_blocked("fpi-admin-old-failure")
                    request = self.request(policy)
                    _, before = self.read(request)
                    assert value.parse_id not in before["data"]["diagnostic_parse_ids"]
                finally:
                    self.release(held)
                work.result(timeout=10)
            self.originals[value.parse_id] = (value, record)
            _, after = self.read(self.request(policy))
            assert (value.parse_id in after["data"]["diagnostic_parse_ids"]) is shared
            assert self.read(request)[1] == before
        # An uncommitted withdrawal holds the real qualification lock. Reading must not wait on that
        # lock.
        head = max(
            (event for event in self.events.values() if event["command"]["scope"] == "membership"),
            key=lambda event: event["event_ordinal"],
        )
        target = head["command"]["target"]
        prior_id = digest(canonical(head))
        command = self.qual.FpiQualificationCommand(
            "membership",
            target,
            "WITHDRAW",
            "ADMIN_REVIEW",
            "b" * 64,
            expected_prior_event_id=prior_id,
        )
        held = self.hold(3)
        with ThreadPoolExecutor(max_workers=1) as pool:
            work = pool.submit(
                self.sql,
                (
                    "SET application_name='fpi-admin-withdrawal'; BEGIN; SET ROLE"
                    " service_role; SELECT append_fpi_qualification("
                )
                + literal(command.command_id)
                + ","
                + literal(command.document_json)
                + "); RESET ROLE; SELECT pg_advisory_xact_lock(946031,3); COMMIT;",
            )
            try:
                self.wait_blocked("fpi-admin-withdrawal")
                request = self.request(policy)
                _, before = self.read(request)
                found = next(
                    h
                    for h in before["data"]["qualification"]["heads"]
                    if h["scope"] == "membership" and h["target"] == target
                )
                assert found["event_id"] == prior_id
            finally:
                self.release(held)
            result = json.loads(work.result(timeout=10).splitlines()[0])
        self.events[result["event_id"]] = json.loads(result["event_document_json"])
        _, after = self.read(self.request(policy))
        assert (
            next(
                h
                for h in after["data"]["qualification"]["heads"]
                if h["scope"] == "membership" and h["target"] == target
            )["event_id"]
            == result["event_id"]
        )
        assert self.read(request)[1] == before
        # Pause within the materializing clock: a concurrent complete parse is outside that
        # statement's snapshot.
        day = next(
            m["reporting_date"]
            for m in after["data"]["qualification"]["members"]
            if m["membership_id"] == target
        )
        command = self.qual.FpiQualificationCommand(
            "membership",
            target,
            "ACCEPT",
            "ADMIN_REVIEW",
            "c" * 64,
            expected_prior_event_id=result["event_id"],
        )
        accepted = self.rpc("append_fpi_qualification", command.command_id, command.document_json)
        self.events[accepted["event_id"]] = json.loads(accepted["event_document_json"])
        prior = next(
            h["event_id"]
            for h in after["data"]["qualification"]["heads"]
            if h["scope"] == "date" and h["target"] == day
        )
        command = self.qual.FpiQualificationCommand(
            "date",
            day,
            "RESOLVE",
            "ADMIN_REVIEW",
            "c" * 64,
            expected_prior_event_id=prior,
            chosen_membership_id=target,
            basis_membership_ids=tuple(
                sorted(
                    m["membership_id"]
                    for m in after["data"]["qualification"]["members"]
                    if m["reporting_date"] == day
                )
            ),
        )
        resolved = self.rpc("append_fpi_qualification", command.command_id, command.document_json)
        self.events[resolved["event_id"]] = json.loads(resolved["event_document_json"])
        held = self.hold(4)
        self.sql(
            "CREATE OR REPLACE FUNCTION fpi_admin_clock() RETURNS "
            "timestamptz LANGUAGE plpgsql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ BEGIN PERFORM "
            "pg_advisory_xact_lock(946031,4); RETURN '2026-10-01 "
            "12:00+00'::timestamptz; END $$"
        )
        request = self.request(policy)
        raw = canonical(request)
        parser = self.artifact("PARSER", b"materialization boundary parser")
        with ThreadPoolExecutor(max_workers=1) as pool:
            work = pool.submit(
                self.sql,
                (
                    "SET application_name='fpi-admin-materialization'; SET ROLE "
                    "service_role; SELECT capture_fpi_admin_read("
                )
                + literal(digest(raw))
                + ","
                + literal(raw)
                + ")",
            )
            try:
                self.wait_blocked("fpi-admin-materialization")
                late, _ = self.sample(parser, 130)
            finally:
                self.release(held)
            work.result(timeout=10)
        self.clock(NOW)
        _, before = self.read(request)
        assert not (
            {late.membership_id(d) for d in late.days}
            & set(before["data"]["candidate_membership_ids"])
        )
        _, after = self.read(self.request(policy))
        assert {late.membership_id(d) for d in late.days} <= set(
            after["data"]["candidate_membership_ids"]
        )
        for document, expected_status in ((before, "RESOLVED"), (after, "STALE_RESOLUTION")):
            saved_view = document["data"]["qualification"]
            assert (
                next(
                    h["event_id"]
                    for h in saved_view["heads"]
                    if h["scope"] == "date" and h["target"] == day
                )
                == resolved["event_id"]
            )
            assert self.events[resolved["event_id"]] in saved_view["events"]
            view = self.qual.FpiQualificationView(
                tuple(
                    self.qual.FpiQualificationMember(
                        **{**m, "reporting_date": date.fromisoformat(m["reporting_date"])}
                    )
                    for m in saved_view["members"]
                ),
                tuple(self.qual.FpiQualificationHead(**h) for h in saved_view["heads"]),
                tuple(
                    self.qual.decode_fpi_qualification_event(canonical(e))
                    for e in saved_view["events"]
                ),
            )
            evaluation = self.qual.evaluate_fpi_qualification(view)
            assert (
                next(status for d, status, _ in evaluation.date_resolutions if d.isoformat() == day)
                == expected_status
            )
        # Cancellation during materialization also rolls back, rather than inventing a saved
        # overflow.
        self.sql(
            "CREATE OR REPLACE FUNCTION fpi_admin_clock() RETURNS "
            "timestamptz LANGUAGE plpgsql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ BEGIN PERFORM "
            "pg_sleep(1); RETURN '2026-10-01 12:00+00'::timestamptz; END "
            "$$"
        )
        request = self.request(policy)
        raw = canonical(request)
        self.sql(
            "SET ROLE service_role; SELECT capture_fpi_admin_read("
            + literal(digest(raw))
            + ","
            + literal(raw)
            + ")",
            error="statement timeout",
            timer=100,
        )
        assert (
            self.sql("SELECT count(*) FROM fpi_admin_reads WHERE read_id=" + literal(digest(raw)))
            == "0"
        )
        self.clock(NOW)
        assert self.read(request)[0]["inserted"]
        self.checks.append(
            "SR07,10,12,18: old-stored uncommitted failures with both "
            "scope outcomes; withdrawal lock independence; "
            "within-statement committed parse exclusion; read-time "
            "cancellation/rollback/retry"
        )

    def large_originals(self, policy: dict[str, Any]) -> None:
        for size in (100000, 200000, 1000000):
            artifact = self.artifact("PARSER", b"x" * size)
            start = time.monotonic()
            value = self.sql(
                "SELECT length(fpi_admin_original('PARSER',"
                + literal(artifact.artifact_sha256)
                + ",document_json,7000000)::text) "
                "FROM fpi_implementation_artifacts WHERE kind='PARSER' AND artifact_sha256="
                + literal(artifact.artifact_sha256)
            )
            elapsed = time.monotonic() - start
            assert int(value) > size
            self.plans.append(
                canonical(
                    {
                        "valid_artifact_body_bytes": size,
                        "validation_wall_seconds": round(elapsed, 4),
                    }
                )
            )
        # A shared capture occurs under many distinct parsers; set union counts each identity once.
        original = next(p for p, _ in self.originals.values() if p.failure_reason is None)
        source_docs = tuple(
            row["source_evidence_document_json"]
            for row in json.loads(self.originals[original.parse_id][1].document_json)["days"]
        )
        added: set[str] = set()
        for n in range(12):
            artifact = self.artifact("PARSER", f"shared capture parser {n}".encode())
            parsed = replace(original, parser_sha256=artifact.artifact_sha256)
            self.retain(parsed, source_docs)
            added.add(parsed.parse_id)
        _, doc = self.read(self.request(policy))
        assert added <= {p["parse_id"] for p in doc["data"]["references"]["parses"]}
        assert (
            sum(
                c["capture_sha256"] == original.capture.capture_sha256
                for c in doc["data"]["references"]["captures"]
            )
            == 1
        )
        # This scratch-only wrapper records actual body validation calls while returning the real
        # result.
        self.sql(
            "ALTER FUNCTION fpi_admin_original(text,text,text,integer) "
            "RENAME TO scratch_original; CREATE TABLE "
            "scratch_validation_counts(kind text,id text,n "
            "integer,PRIMARY KEY(kind,id)); CREATE FUNCTION "
            "fpi_admin_original(k text,i text,value text,cap integer) "
            "RETURNS jsonb LANGUAGE plpgsql VOLATILE SET "
            "search_path=pg_catalog,public AS $$ BEGIN INSERT INTO "
            "scratch_validation_counts VALUES(k,i,1) ON CONFLICT(kind,id)"
            " DO UPDATE SET n=scratch_validation_counts.n+1; RETURN "
            "scratch_original(k,i,value,cap); END $$;"
        )
        _, doc = self.read(self.request(policy))
        counts = json.loads(
            self.sql(
                "SELECT jsonb_agg(to_jsonb(c) ORDER BY kind,id) FROM "
                "scratch_validation_counts c WHERE kind<>'EVENT'"
            )
        )
        assert all(row["n"] == 1 for row in counts), counts
        assert len(counts) == sum(
            len(doc["data"]["references"][key]) for key in ("captures", "parses")
        ) + len(doc["data"]["artifacts"])
        self.plans.append(
            canonical(
                {
                    "unique_original_validations": len(counts),
                    "max_calls_per_original": max(row["n"] for row in counts),
                }
            )
        )
        self.apply()
        self.sql(
            "DROP FUNCTION scratch_original(text,text,text,integer); DROP"
            " TABLE scratch_validation_counts"
        )
        self.checks.append(
            "SR17: actual 100KB/200KB/1MB valid artifact timings, "
            "twelve-parser shared capture and counted single validation "
            "per original"
        )

    def run(self) -> None:
        try:
            self.setup()
            parser, selector, policy = self.basic()
            self.clocks_and_corruption(policy)
            self.permissions_inputs(policy)
            self.scope_edges(parser, selector, policy)
            self.qualification(policy)
            self.guardrails(policy)
            self.concurrency(parser, policy)
            self.visibility_edges(policy)
            self.large_originals(policy)
            report = [
                "# Saved administrative FPI reads: database verification",
                "",
                "These results are from a disposable local PostgreSQL 17 database. "
                "The parent started and checked the socket-only runtime. "
                "The verifier drops its database in a finally block. No production data, "
                "provider request, credential, deployment or consumer activation was used.",
                "",
                "Migration 14 adds private immutable policies and saved reads. The capture RPC "
                "uses a decision lock, committed retry lookup and one evidence/INSERT statement. "
                "Its sampled clock, membership scope, diagnostics, originals, heads and witnesses "
                "share that statement snapshot. Every result remains UNVERIFIED and ineligible.",
                "",
                "The downstream audit inspected migrations 10–13, original capture/parse "
                "verifiers, the existing reference builder and qualification-v2 codec, central "
                "writer entry points, the legacy selector and staged signal consumer. "
                "Existing writer, scheduler/staged selection and replay meanings remain unchanged. "
                "New RPCs and helpers were absent from GitNexus: impact UNKNOWN; no rebuild of "
                "its index. Private helper/table grants and immutable owner/application behavior "
                "are exercised below; no prior grants were weakened.",
                "",
                f"Migration SHA-256: `{digest(self.migration)}`.",
                f"Verifier SHA-256: `{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}`.",
                f"Retained-read/retry checks: {self.reads}. "
                f"Expected SQL refusals: {self.rejections}.",
                "",
                "## Executed database scenarios",
                "",
                *["- " + check for check in self.checks],
                "",
                "SR19 covers authoritative SQL projection/original corruption here. "
                "Returned-row omission, forged Python types and provider pagination in SR19–20 "
                "belong to codec/writer integration. SR23 is the parent's independent negative "
                "control. This leaf does not claim those separate gates, a live read's origin, "
                "trusted execution/acquisition or usable FPI features.",
                "",
                "## Measured bounds and plans",
                "",
                "Each listed fixture bound passed exactly, then failed at bound minus one with "
                "the expected dimension and without partial data. Capped count probes report "
                "AT_LEAST; complete bounded unions and byte sums report EXACT. Production limits "
                "remain those in the contract. Reduced limits are scratch migration text only.",
                "",
                "```json",
                json.dumps(
                    {
                        "fixture_bounds": self.bounds,
                        "plans_timings_counters": [json.loads(item) for item in self.plans],
                    },
                    indent=2,
                    sort_keys=True,
                ),
                "```",
                "",
                "Canonical golden hashes: COMPLETE empty manifest "
                "`4fbffecbbc0f2d14a9d7277a129a13027621b2faeb6e7bb58cf9e6a3d8a4e930`; "
                "ARTIFACTS overflow manifest "
                "`9d7d848b2d447258744b736143c945e4fca4e2c40215ce42e05de68cd989e3b4`. "
                "Expected objects are authored from original fixtures independently of SQL output.",
                "",
                "The G1 ledger records its actual command result. G2, cross-language loader "
                "integration, broader repair acceptance and release remain the parent's work.",
            ]
            (ROOT / "reports/repair-fpi-admin-read-db.md").write_text(
                "\n".join(report) + "\n", encoding="utf-8"
            )
            print(
                "FPI_ADMIN_READ_DB_VERIFIED",
                canonical(
                    {
                        "checks": self.checks,
                        "reads": self.reads,
                        "rejections": self.rejections,
                        "migration_sha256": digest(self.migration),
                        "measured_boundary_values": self.bounds,
                        "plans_and_counters": [json.loads(item) for item in self.plans],
                    }
                ),
            )
        finally:
            self.sql("DROP DATABASE IF EXISTS " + self.db + " WITH (FORCE)", database="postgres")


def main() -> None:
    Harness().run()


if __name__ == "__main__":
    main()
