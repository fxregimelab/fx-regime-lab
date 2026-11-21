"""Offline original-report proof with explicitly authored administrative metadata."""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))

from src.research import fpi_parse_record as records  # noqa: E402
from src.research.fpi_capture import build_fpi_capture  # noqa: E402
from src.research.fpi_observation import FPI_OBSERVATION_VERSION  # noqa: E402
from src.research.fpi_qualification import (  # noqa: E402
    FpiQualificationHead,
    FpiQualificationMember,
    FpiQualificationView,
)
from src.research.fpi_selection import FpiParsedDay, FpiParseResult  # noqa: E402


def _admin_original_fixture(*, narrow: bool) -> tuple[str, dict[str, Any], int]:
    spec = importlib.util.spec_from_file_location(
        "admin_retained_source", ROOT / "pipeline/scripts/verify_fpi_source_capture.py"
    )
    assert spec is not None and spec.loader is not None
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    reference_spec = importlib.util.spec_from_file_location(
        "admin_original_reference_oracle",
        ROOT / "scripts/repair/verify-fpi-read-references-original.py",
    )
    assert reference_spec is not None and reference_spec.loader is not None
    oracle = importlib.util.module_from_spec(reference_spec)
    reference_spec.loader.exec_module(oracle)
    # These retained local source files are reference labels, never approved execution.
    artifacts = (
        records.build_fpi_artifact(
            kind="PARSER", body=(ROOT / "pipeline/src/research/fpi_parser.py").read_bytes()
        ),
        records.build_fpi_artifact(
            kind="SELECTOR", body=(ROOT / "pipeline/src/research/fpi_selection.py").read_bytes()
        ),
    )
    captures, parses = [], []
    for name in ("latest", "monthly"):
        parsed, retrieved_at = source._verify_capture(oracle.CAPTURE_DIR, name)
        retained = source._CAPTURES[name]
        receipt = json.loads((oracle.CAPTURE_DIR / retained["receipt"]).read_bytes())
        capture = build_fpi_capture(
            body=(oracle.CAPTURE_DIR / retained["html"]).read_bytes(),
            source_url=retained["source_url"],
            requested_at=datetime.fromisoformat(receipt["started_at"].replace("Z", "+00:00")),
            retrieved_at=retrieved_at,
            http_status=200,
        )
        result = FpiParseResult(
            capture,
            artifacts[0].artifact_sha256,
            FPI_OBSERVATION_VERSION,
            retrieved_at,
            tuple(
                FpiParsedDay(item.observation.document_json, item.source_evidence.evidence_sha256)
                for item in parsed
            ),
        )
        captures.append(capture)
        parses.append(
            records.build_fpi_parse_record(
                result,
                source_evidence_documents=tuple(
                    item.source_evidence.document_json for item in parsed
                ),
            )
        )
    reference_text = oracle._expected_reference_document(tuple(captures), tuple(parses))
    references = json.loads(reference_text)
    all_members = [
        (item, member) for item in references["parses"] for member in item["memberships"]
    ]
    assert len(all_members) == 19
    # Authored storage/read times test consistency only, not historical SQL visibility.
    stored = max(
        datetime.fromisoformat(item["retrieved_at"]) for item in references["captures"]
    ) + timedelta(seconds=10)
    read_at = stored + timedelta(hours=1)
    india_date = read_at.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
    dates = sorted({date.fromisoformat(member["reporting_date"]) for _, member in all_members})
    history_age = (india_date - dates[len(dates) // 2]).days if narrow else 365
    assert 0 <= history_age <= 100000
    history_start = india_date - timedelta(days=history_age)
    newest = max(dates)
    candidates = [
        (item, member)
        for item, member in all_members
        if history_start <= date.fromisoformat(member["reporting_date"]) <= india_date
        or date.fromisoformat(member["reporting_date"]) == newest
    ]
    # Both original parses must participate; narrow scope keeps extra Monthly support.
    assert {item["parse_id"] for item, _ in candidates} == {
        item["parse_id"] for item in references["parses"]
    }
    support_only = len(all_members) - len(candidates)
    assert (support_only > 0) if narrow else (support_only == 0)
    members = tuple(
        FpiQualificationMember(
            member["membership_id"],
            member["value_sha256"],
            item["parser_sha256"],
            date.fromisoformat(member["reporting_date"]),
        )
        for item, member in candidates
    )
    targets = {
        (scope, target)
        for member in members
        for scope, target in (
            ("membership", member.membership_id),
            ("value", member.value_sha256),
            ("parser", member.parser_sha256),
            ("date", member.reporting_date.isoformat()),
        )
    }
    qualification = FpiQualificationView(
        members,
        tuple(FpiQualificationHead(scope, target, None) for scope, target in sorted(targets)),
        (),
    )
    policy = {
        "version": "fpi-admin-read-policy-v1",
        "scope_version": "fpi-admin-scope-v1",
        "guardrail_version": "fpi-admin-read-limits-v1",
        "trust_mode": "ADMINISTRATIVE_UNVERIFIED",
        "selector_version": "NOT_EXECUTED",
        "selector_sha256": artifacts[1].artifact_sha256,
        "parser_allowlist": [artifacts[0].artifact_sha256],
        "definition_allowlist": [FPI_OBSERVATION_VERSION],
        "max_current_age_days": 0,
        "max_history_age_days": history_age,
        "minimum_history": 10,
        "history_window": 60,
        "diagnostic_window_days": 7,
        "feature_version": "fixture-admin-v1",
        "model_version": "fixture-model-v1",
        "prediction_horizon": "T5",
        "source_rule": "AGREEMENT",
        "source_rationale": "Original source proof with authored storage metadata",
        "allow_withdrawal_fallback": False,
        "age_timezone": "Asia/Kolkata",
        "missingness": "MISSING",
    }
    policy_text = json.dumps(policy, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    policy_hash = hashlib.sha256(policy_text.encode("ascii")).hexdigest()
    request = {
        "version": "fpi-admin-read-request-v1",
        "decision_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "prediction_id": "3" * 64,
        "model_sha256": "4" * 64,
        "pair": "USDINR",
        "mode": "ADMIN_EVIDENCE_READ",
        "policy_sha256": policy_hash,
    }
    request_text = json.dumps(request, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    request_hash = hashlib.sha256(request_text.encode("ascii")).hexdigest()
    artifact_entries = []
    artifact_rows = []
    for artifact in artifacts:
        document = json.loads(artifact.document_json)
        artifact_entries.append(
            {
                "kind": document["kind"],
                "artifact_sha256": artifact.artifact_sha256,
                "document_size": len(artifact.document_json),
                "body_size": document["body_size"],
                "stored_at": stored.isoformat(),
            }
        )
        artifact_rows.append(
            {
                "kind": document["kind"],
                "artifact_sha256": artifact.artifact_sha256,
                "document_json": artifact.document_json,
                "stored_at": stored.isoformat(),
            }
        )
    document = {
        "version": "fpi-admin-read-v1",
        "read_id": request_hash,
        "request_sha256": request_hash,
        "request": request,
        "policy_sha256": policy_hash,
        "policy": policy,
        "read_at": read_at.isoformat(),
        "scope": {
            "version": "fpi-admin-scope-v1",
            "india_date": india_date.isoformat(),
            "history_start_date": history_start.isoformat(),
            "history_start_clamped": False,
            "diagnostic_start_at": (read_at - timedelta(days=7)).isoformat(),
            "diagnostic_start_clamped": False,
            "newest_reporting_date": newest.isoformat(),
        },
        "status": "COMPLETE",
        "failure": None,
        "execution_state": "UNVERIFIED",
        "acquisition_state": "UNVERIFIED",
        "eligible": False,
        "feature": None,
        "data": {
            "candidate_membership_ids": sorted(member.membership_id for member in members),
            "candidate_dates": sorted({member.reporting_date.isoformat() for member in members}),
            "diagnostic_parse_ids": [],
            "references": references,
            "reference_sha256": hashlib.sha256(reference_text.encode("ascii")).hexdigest(),
            "storage_times": {
                "captures": [
                    {"capture_sha256": item["capture_sha256"], "stored_at": stored.isoformat()}
                    for item in references["captures"]
                ],
                "parses": [
                    {"parse_id": item["parse_id"], "stored_at": stored.isoformat()}
                    for item in references["parses"]
                ],
            },
            "artifacts": sorted(
                artifact_entries, key=lambda item: (item["kind"], item["artifact_sha256"])
            ),
            "qualification": {
                "version": "fpi-qualification-view-v2",
                "members": [
                    {
                        "membership_id": member.membership_id,
                        "value_sha256": member.value_sha256,
                        "parser_sha256": member.parser_sha256,
                        "reporting_date": member.reporting_date.isoformat(),
                    }
                    for member in qualification.members
                ],
                "heads": [
                    {"scope": head.scope, "target": head.target, "event_id": head.event_id}
                    for head in qualification.heads
                ],
                "events": [],
            },
            "qualification_sha256": qualification.view_sha256,
        },
    }
    view_text = json.dumps(
        document["data"]["qualification"], ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(view_text.encode("ascii")).hexdigest() == qualification.view_sha256
    rows = {
        "capture_rows": tuple(
            {
                "capture_sha256": item.capture_sha256,
                "document_json": item.document_json,
                "stored_at": stored.isoformat(),
            }
            for item in captures
        ),
        "parse_rows": tuple(
            {
                "parse_id": item.parse_id,
                "record_sha256": item.record_sha256,
                "document_json": item.document_json,
                "stored_at": stored.isoformat(),
            }
            for item in parses
        ),
        "artifact_rows": tuple(artifact_rows),
        "event_rows": (),
    }
    return (
        json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        rows,
        support_only,
    )


def _assert_admin_read_originals(codec: Any, document: str, rows: dict[str, Any]) -> Any:
    manifest = codec.FpiAdminReadManifest(document)
    rebuilt = codec.verify_fpi_admin_read_originals(manifest, **rows)
    assert rebuilt.document_json == document
    assert rebuilt.read_sha256 == hashlib.sha256(document.encode("ascii")).hexdigest()
    assert json.loads(rebuilt.document_json)["eligible"] is False
    return rebuilt


def verify_original_admin_reads() -> None:
    # Import only on explicit execution, after the implementation's independent readiness.
    codec = importlib.import_module("src.research.fpi_saved_read")
    for narrow in (False, True):
        document, rows, support_only = _admin_original_fixture(narrow=narrow)
        manifest = _assert_admin_read_originals(codec, document, rows)
        _assert_admin_read_originals(
            codec, document, {key: tuple(reversed(value)) for key, value in rows.items()}
        )
        wrong_times = copy.deepcopy(rows)
        original_time = datetime.fromisoformat(wrong_times["capture_rows"][0]["stored_at"])
        wrong_times["capture_rows"][0]["stored_at"] = (
            original_time + timedelta(seconds=1)
        ).isoformat()
        try:
            codec.verify_fpi_admin_read_originals(manifest, **wrong_times)
        except ValueError:
            pass
        else:
            raise AssertionError("Wrong retained storage time escaped verification")
        if narrow:
            partial = json.loads(document)
            candidate_ids = set(partial["data"]["candidate_membership_ids"])
            changed = False
            for item in partial["data"]["references"]["parses"]:
                for index, member in enumerate(item["memberships"]):
                    if member["membership_id"] not in candidate_ids:
                        item["memberships"].pop(index)
                        changed = True
                        break
                if changed:
                    break
            assert changed and support_only > 0
            refs = json.dumps(
                partial["data"]["references"],
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            partial["data"]["reference_sha256"] = hashlib.sha256(refs.encode("ascii")).hexdigest()
            partial_text = json.dumps(
                partial, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            )
            # Compact metadata alone cannot prove full parse support; originals must catch this.
            partial_manifest = codec.FpiAdminReadManifest(partial_text)
            try:
                codec.verify_fpi_admin_read_originals(partial_manifest, **rows)
            except ValueError:
                pass
            else:
                raise AssertionError("Rehashed missing support member escaped original comparison")
        _assert_admin_read_originals(codec, document, rows)
        print(
            f"Verified scope narrow={narrow}: 19 retained memberships; {support_only} support-only"
        )
    print("FPI_ADMIN_READ_ORIGINALS_VERIFIED")


if __name__ == "__main__":
    verify_original_admin_reads()
