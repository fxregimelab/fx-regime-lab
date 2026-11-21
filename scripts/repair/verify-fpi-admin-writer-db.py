"""Reconstruct a retained administrative read through the real private database.

The adapter deliberately translates only the exact RPCs and projected queries used
by the central writer. It is local test transport, not a PostgREST substitute.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))

from src.db import writer  # noqa: E402
from src.research.fpi_capture import FpiCapture  # noqa: E402
from src.research.fpi_parse_record import (  # noqa: E402
    FpiArtifact,
    FpiParseRecord,
    restore_fpi_parse_record,
)
from src.research.fpi_qualification import FpiQualificationCommand  # noqa: E402
from src.research.fpi_saved_read import (  # noqa: E402
    FpiAdminReadPolicy,
    FpiAdminReadRequest,
)

TABLE_PROJECTIONS = {
    "fpi_admin_reads": (
        "read_id,decision_id,request_sha256,request_document_json,policy_sha256,"
        "read_sha256,manifest_document_json,read_at,status"
    ),
    "fpi_captures": "capture_sha256,document_json,stored_at",
    "fpi_parse_results": "parse_id,record_sha256,document_json,stored_at",
    "fpi_implementation_artifacts": "kind,artifact_sha256,document_json,stored_at",
    "fpi_qualification_events": "event_id,event_document_json",
}
IDENTITIES = {
    "fpi_admin_reads": "read_id",
    "fpi_captures": "capture_sha256",
    "fpi_parse_results": "parse_id",
    "fpi_implementation_artifacts": "artifact_sha256",
    "fpi_qualification_events": "event_id",
}
RPC_FIELDS = {
    "append_fpi_capture": ("p_capture_sha256", "p_document_json"),
    "append_fpi_artifact": ("p_artifact_sha256", "p_document_json"),
    "append_fpi_parse_result": ("p_parse_id", "p_record_sha256", "p_document_json"),
    "append_fpi_qualification": ("p_command_id", "p_document_json"),
    "append_fpi_admin_read_policy": ("p_policy_sha256", "p_document_json"),
    "capture_fpi_admin_read": ("p_request_sha256", "p_document_json"),
}


class SqlBridge:
    """Minimal audited query chain with optional one-response corruption."""

    def __init__(self, harness: Any) -> None:
        self.harness = harness
        self.current: dict[str, Any] = {}
        self.calls: list[dict[str, Any]] = []
        self.corrupt: str | None = None

    def rpc(self, name: str, parameters: dict[str, str]) -> SqlBridge:
        assert name in RPC_FIELDS and set(parameters) == set(RPC_FIELDS[name])
        assert all(type(value) is str for value in parameters.values())
        self.current = {"rpc": name, "parameters": parameters.copy()}
        return self

    def table(self, name: str) -> SqlBridge:
        assert name in TABLE_PROJECTIONS
        self.current = {"table": name, "filters": {}}
        return self

    def select(self, projection: str) -> SqlBridge:
        assert self.current.get("table") in TABLE_PROJECTIONS
        assert projection == TABLE_PROJECTIONS[self.current["table"]]
        self.current["projection"] = projection
        return self

    def eq(self, key: str, value: str) -> SqlBridge:
        table = self.current["table"]
        assert (
            key == IDENTITIES[table]
            or table == "fpi_implementation_artifacts"
            and key == "kind"
        )
        assert type(value) is str and key not in self.current["filters"]
        self.current["filters"][key] = ("eq", value)
        return self

    def in_(self, key: str, values: list[str]) -> SqlBridge:
        assert key == IDENTITIES[self.current["table"]]
        assert type(values) is list and 1 <= len(values) <= 64
        assert all(type(value) is str for value in values) and len(set(values)) == len(
            values
        )
        self.current["filters"][key] = ("in", values.copy())
        return self

    def limit(self, value: int) -> SqlBridge:
        assert type(value) is int and 1 <= value <= 65
        self.current["limit"] = value
        return self

    def execute(self) -> SimpleNamespace:
        current = deepcopy(self.current)
        self.calls.append(current)
        if "rpc" in current:
            fields = RPC_FIELDS[current["rpc"]]
            values = ",".join(
                self.harness.literal(current["parameters"][key]) for key in fields
            )
            raw = self.harness.sql(
                "SET ROLE service_role; SELECT public."
                + current["rpc"]
                + "("
                + values
                + ")"
            )
            result: Any = json.loads(raw)
        else:
            table = current["table"]
            assert current["projection"] == TABLE_PROJECTIONS[table]
            assert current["limit"] <= 65 and current["filters"]
            where = []
            for key, (operator, value) in current["filters"].items():
                assert (
                    key == IDENTITIES[table]
                    or table == "fpi_implementation_artifacts"
                    and key == "kind"
                )
                if operator == "eq":
                    where.append(key + "=" + self.harness.literal(value))
                else:
                    assert operator == "in" and type(value) is list
                    where.append(
                        key + " IN (" + ",".join(map(self.harness.literal, value)) + ")"
                    )
            query = (
                "SET ROLE service_role; SELECT COALESCE(json_agg(to_jsonb(x)),'[]'::json) "
                "FROM (SELECT "
                + current["projection"]
                + " FROM public."
                + table
                + " WHERE "
                + " AND ".join(where)
                + " ORDER BY "
                + IDENTITIES[table]
                + " DESC LIMIT "
                + str(current["limit"])
                + ") x"
            )
            result = json.loads(self.harness.sql(query))
            assert type(result) is list
            if self.corrupt == "missing_parse" and table == "fpi_parse_results":
                result = result[:-1]
                self.corrupt = None
            elif self.corrupt == "extra_parse" and table == "fpi_parse_results":
                result.append(result[0].copy())
                self.corrupt = None
            elif self.corrupt == "changed_read_hash" and table == "fpi_admin_reads":
                result[0]["read_sha256"] = "f" * 64
                self.corrupt = None
            elif (
                self.corrupt == "wrong_artifact_kind"
                and table == "fpi_implementation_artifacts"
            ):
                result[0]["kind"] = (
                    "SELECTOR" if result[0]["kind"] == "PARSER" else "PARSER"
                )
                self.corrupt = None
        return SimpleNamespace(data=result)


def load_verifier(filename: str, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "scripts/repair" / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_fpi_admin_writer_database() -> None:
    sql_module = load_verifier("verify-fpi-admin-read-db.py", "parent_admin_db")
    original_module = load_verifier(
        "verify-fpi-admin-read-original.py", "parent_admin_orig"
    )
    harness = sql_module.Harness()
    harness.literal = sql_module.literal
    bridge = SqlBridge(harness)
    assert re.fullmatch(r"fxfpiadmin_[0-9a-f]{32}", harness.db)
    harness.setup()
    try:
        full_text, original_rows, _ = original_module._admin_original_fixture(
            narrow=False
        )
        _, narrow_rows, originally_narrow = original_module._admin_original_fixture(
            narrow=True
        )
        assert originally_narrow == 9 and original_rows == narrow_rows
        original_doc = json.loads(full_text)
        captures = {
            row["capture_sha256"]: FpiCapture(
                row["capture_sha256"], row["document_json"]
            )
            for row in original_rows["capture_rows"]
        }
        artifacts = [
            FpiArtifact(row["artifact_sha256"], row["document_json"])
            for row in original_rows["artifact_rows"]
        ]
        records = [
            FpiParseRecord(row["parse_id"], row["record_sha256"], row["document_json"])
            for row in original_rows["parse_rows"]
        ]
        with patch.object(writer, "_client", return_value=bridge):
            for artifact in artifacts:
                assert writer.archive_fpi_artifact(artifact)["inserted"] is True
                assert writer.archive_fpi_artifact(artifact)["inserted"] is False
            for capture in captures.values():
                assert writer.archive_fpi_capture(capture)["inserted"] is True
                assert writer.archive_fpi_capture(capture)["inserted"] is False
            for record in records:
                source_doc = json.loads(record.document_json)
                capture = captures[source_doc["capture_sha256"]]
                parse = restore_fpi_parse_record(record, capture)
                sources = tuple(
                    day["source_evidence_document_json"] for day in source_doc["days"]
                )
                assert (
                    writer.archive_fpi_parse_result(
                        parse, source_evidence_documents=sources
                    )["inserted"]
                    is True
                )
                assert (
                    writer.archive_fpi_parse_result(
                        parse, source_evidence_documents=sources
                    )["inserted"]
                    is False
                )
            assert harness.sql("SELECT count(*) FROM fpi_parsed_memberships") == "19"
            now = datetime.now(UTC) + timedelta(hours=1)
            latest_retrieved = max(
                datetime.fromisoformat(json.loads(row["document_json"])["retrieved_at"])
                for row in original_rows["capture_rows"]
            )
            now = max(now, latest_retrieved + timedelta(hours=1))
            now = now.replace(microsecond=0)
            harness.clock(now.isoformat())
            india_day = (now + timedelta(hours=5, minutes=30)).date()
            dates = sorted(
                {
                    date.fromisoformat(member["reporting_date"])
                    for item in original_doc["data"]["references"]["parses"]
                    for member in item["memberships"]
                }
            )
            policy_body = original_doc["policy"]
            policy_body["max_history_age_days"] = max(365, (india_day - dates[0]).days)
            policy = FpiAdminReadPolicy(sql_module.canonical(policy_body))
            first = writer.append_fpi_admin_read_policy(policy)
            assert first["inserted"] is True
            assert writer.append_fpi_admin_read_policy(policy) == {
                **first,
                "inserted": False,
            }

            def saved_read(
                policy_value: FpiAdminReadPolicy,
            ) -> tuple[Any, dict[str, Any], FpiAdminReadRequest]:
                request = FpiAdminReadRequest(
                    sql_module.canonical(
                        harness.request(json.loads(policy_value.document_json))
                    )
                )
                receipt = writer.capture_fpi_admin_read(request)
                assert receipt["inserted"] is True
                assert writer.capture_fpi_admin_read(request) == {
                    **receipt,
                    "inserted": False,
                }
                loaded = writer.load_fpi_admin_read(request.read_id)
                document = json.loads(loaded.document_json)
                assert loaded.read_sha256 == receipt["read_sha256"]
                assert document["eligible"] is False and document["feature"] is None
                assert (
                    document["execution_state"]
                    == document["acquisition_state"]
                    == "UNVERIFIED"
                )
                assert (
                    harness.sql(
                        "SET ROLE service_role; SELECT manifest_document_json FROM fpi_admin_reads "
                        "WHERE read_id=" + harness.literal(request.read_id)
                    )
                    == loaded.document_json
                )
                return loaded, document, request

            full, complete, request = saved_read(policy)
            assert complete["status"] == "COMPLETE"
            assert complete["data"]["references"] == original_doc["data"]["references"]
            assert len(complete["data"]["candidate_membership_ids"]) == 19
            assert (
                sum(
                    len(item["memberships"])
                    for item in complete["data"]["references"]["parses"]
                )
                == 19
            )
            for mutation in (
                "missing_parse",
                "extra_parse",
                "changed_read_hash",
                "wrong_artifact_kind",
            ):
                bridge.corrupt = mutation
                try:
                    writer.load_fpi_admin_read(request.read_id)
                except RuntimeError as exc:
                    assert str(exc) in {
                        "READ_DEPENDENCY_MISSING",
                        "READ_INTEGRITY_ERROR",
                    }
                    assert exc.__cause__ is None
                else:
                    raise AssertionError("Changed transport result was accepted")
                assert bridge.corrupt is None
                assert (
                    writer.load_fpi_admin_read(request.read_id).document_json
                    == full.document_json
                )

            narrow_body = {
                **policy_body,
                "max_history_age_days": (india_day - dates[len(dates) // 2]).days,
            }
            narrow_policy = FpiAdminReadPolicy(sql_module.canonical(narrow_body))
            assert (
                writer.append_fpi_admin_read_policy(narrow_policy)["inserted"] is True
            )
            narrow, compact, _ = saved_read(narrow_policy)
            assert compact["status"] == "COMPLETE"
            all_ids = {
                member["membership_id"]
                for item in compact["data"]["references"]["parses"]
                for member in item["memberships"]
            }
            candidate_ids = set(compact["data"]["candidate_membership_ids"])
            assert len(all_ids) == 19 and all_ids == {
                member["membership_id"]
                for item in original_doc["data"]["references"]["parses"]
                for member in item["memberships"]
            }
            assert len(all_ids - candidate_ids) == 9
            assert compact["data"]["references"] == original_doc["data"]["references"]
            assert (
                writer.load_fpi_admin_read(narrow.read_id).document_json
                == narrow.document_json
            )

            chosen = next(iter(candidate_ids))
            command = FpiQualificationCommand(
                "membership", chosen, "WITHDRAW", "ADMIN_REVIEW", "a" * 64
            )
            event = writer.append_fpi_qualification(command)
            assert event["inserted"] is True
            assert (
                writer.load_fpi_admin_read(full.read_id).document_json
                == full.document_json
            )
            assert (
                writer.load_fpi_admin_read(narrow.read_id).document_json
                == narrow.document_json
            )
            after, changed, _ = saved_read(narrow_policy)
            assert changed["status"] == "COMPLETE" and after.read_id != narrow.read_id
            heads = changed["data"]["qualification"]["heads"]
            assert any(
                head
                == {
                    "scope": "membership",
                    "target": chosen,
                    "event_id": event["event_id"],
                }
                for head in heads
            )
            assert changed["data"]["qualification"]["events"] == [
                json.loads(event["event_document_json"])
            ]
            assert any(
                call.get("table") == "fpi_qualification_events" for call in bridge.calls
            )
            assert (
                writer.load_fpi_admin_read(after.read_id).document_json
                == after.document_json
            )

            harness.clock((now - timedelta(days=1)).isoformat())
            before_failure = len(bridge.calls)
            failure, refused, failure_request = saved_read(narrow_policy)
            assert refused["status"] == "CLOCK_INCONSISTENT"
            assert refused["data"] is None
            assert [
                call.get("table")
                for call in bridge.calls[before_failure:]
                if "table" in call
            ] == ["fpi_admin_reads"]
            assert (
                writer.load_fpi_admin_read(failure_request.read_id).document_json
                == failure.document_json
            )
            harness.clock(now.isoformat())
            assert (
                writer.load_fpi_admin_read(after.read_id).document_json
                == after.document_json
            )

        print("ORIGINAL_MEMBERSHIPS=19; NARROW_SUPPORT_ONLY=9; TRANSPORT_MUTATIONS=4")
        print("SAVED_READS=4; RETAINED_REPLAY=verified; CURRENT_QUALIFICATION=verified")
        print("SAVED_FAILURE_NO_ORIGINAL_QUERIES=verified")
        print("FPI_ADMIN_WRITER_DATABASE_VERIFIED")
    finally:
        harness.sql(
            'DROP DATABASE "' + harness.db + '" WITH (FORCE)', database="postgres"
        )


if __name__ == "__main__":
    verify_fpi_admin_writer_database()
