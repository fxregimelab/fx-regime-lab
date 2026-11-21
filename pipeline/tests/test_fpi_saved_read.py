"""Authored evidence fixtures test consistency, never database origin or release trust."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.research import fpi_parse_record as original_codec
from src.research import fpi_saved_read as codec
from src.research.fpi_capture import build_fpi_capture, validate_fpi_capture
from src.research.fpi_parse_record import (
    build_fpi_artifact,
    build_fpi_parse_record,
    build_fpi_read_references,
    validate_fpi_artifact,
)
from src.research.fpi_qualification import (
    FpiQualificationCommand,
    FpiQualificationEventV2,
    FpiQualificationView,
)
from src.research.fpi_saved_read import (
    FpiAdminReadManifest,
    FpiAdminReadPolicy,
    FpiAdminReadRequest,
    validate_fpi_admin_policy_receipt,
    validate_fpi_admin_read_receipt,
    verify_fpi_admin_read_originals,
)
from tests.test_fpi_parse_record import successful_parse
from tests.test_fpi_read_references import expected_bundle


def sr_test_canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sr_test_sha(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def sr_policy_document() -> dict[str, Any]:
    return {
        "version": "fpi-admin-read-policy-v1",
        "scope_version": "fpi-admin-scope-v1",
        "guardrail_version": "fpi-admin-read-limits-v1",
        "trust_mode": "ADMINISTRATIVE_UNVERIFIED",
        "selector_version": "NOT_EXECUTED",
        "selector_sha256": "1" * 64,
        "parser_allowlist": ["2" * 64],
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
    }


def sr_request_document(policy_sha: str) -> dict[str, Any]:
    return {
        "version": "fpi-admin-read-request-v1",
        "decision_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "prediction_id": "3" * 64,
        "model_sha256": "4" * 64,
        "pair": "USDINR",
        "mode": "ADMIN_EVIDENCE_READ",
        "policy_sha256": policy_sha,
    }


def sr_refresh(document: dict[str, Any]) -> None:
    document["policy_sha256"] = sr_test_sha(sr_test_canonical(document["policy"]))
    document["request"]["policy_sha256"] = document["policy_sha256"]
    document["request_sha256"] = sr_test_sha(sr_test_canonical(document["request"]))
    document["read_id"] = document["request_sha256"]
    if document["data"] is not None:
        for key, hash_key in (
            ("references", "reference_sha256"),
            ("qualification", "qualification_sha256"),
        ):
            document["data"][hash_key] = sr_test_sha(sr_test_canonical(document["data"][key]))


def sr_fixture(
    *,
    empty: bool = False,
    event: bool = False,
    age: int = 3,
    diagnostics: bool = False,
    alternatives: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parser = build_fpi_artifact(kind="PARSER", body=b"synthetic complete parser bundle")
    selector = build_fpi_artifact(kind="SELECTOR", body=b"synthetic complete selector bundle")
    policy = sr_policy_document()
    policy.update(
        selector_sha256=selector.artifact_sha256,
        parser_allowlist=[parser.artifact_sha256],
        max_history_age_days=age,
        max_current_age_days=0,
    )
    parse, sources = successful_parse(1, 24, 25)
    capture_document = json.loads(parse.capture.document_json)
    parse = replace(
        parse,
        capture=build_fpi_capture(
            body=b"synthetic Monthly retained response",
            source_url="https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
            requested_at=datetime.fromisoformat(capture_document["requested_at"]),
            retrieved_at=datetime.fromisoformat(capture_document["retrieved_at"]),
            http_status=200,
        ),
    )
    records = [] if empty else [build_fpi_parse_record(parse, source_evidence_documents=sources)]
    artifacts = [("PARSER", parser), ("SELECTOR", selector)]
    if alternatives:
        alternate = build_fpi_artifact(kind="PARSER", body=b"unqualified alternate parser")
        artifacts.append(("PARSER", alternate))
        records.append(
            build_fpi_parse_record(
                replace(parse, parser_sha256=alternate.artifact_sha256),
                source_evidence_documents=sources,
            )
        )
    if diagnostics:
        other = build_fpi_artifact(kind="PARSER", body=b"failed synthetic parser")
        artifacts.append(("PARSER", other))
        failed = replace(
            parse, parser_sha256=other.artifact_sha256, days=(), failure_reason="MALFORMED_REPORT"
        )
        records.append(build_fpi_parse_record(failed, source_evidence_documents=()))
    captures = () if empty else (parse.capture,)
    references = json.loads(expected_bundle(captures, tuple(records)).document_json)
    start = (date(2026, 9, 28) - timedelta(days=age)).isoformat()
    candidate_docs = sorted(
        [
            {
                "membership_id": member["membership_id"],
                "value_sha256": member["value_sha256"],
                "reporting_date": member["reporting_date"],
                "parser_sha256": row["parser_sha256"],
            }
            for row in references["parses"]
            for member in row["memberships"]
            if member["reporting_date"] >= start or member["reporting_date"] == "2026-09-25"
        ],
        key=lambda item: item["membership_id"],
    )
    targets = {
        (kind, member[key])
        for member in candidate_docs
        for kind, key in (
            ("membership", "membership_id"),
            ("value", "value_sha256"),
            ("parser", "parser_sha256"),
            ("date", "reporting_date"),
        )
    }
    events = []
    if event:
        events.append(
            FpiQualificationEventV2(
                FpiQualificationCommand(
                    "membership", candidate_docs[0]["membership_id"], "ACCEPT", "RESEARCH", "5" * 64
                ),
                1,
                datetime(2026, 9, 27, tzinfo=UTC),
            )
        )
    qualification = {
        "version": "fpi-qualification-view-v2",
        "members": candidate_docs,
        "heads": [
            {
                "scope": kind,
                "target": target,
                "event_id": next(
                    (
                        item.event_id
                        for item in events
                        if item.command.scope == kind and item.command.target == target
                    ),
                    None,
                ),
            }
            for kind, target in sorted(targets)
        ],
        "events": [
            json.loads(item.document_json)
            for item in sorted(events, key=lambda item: item.event_id)
        ],
    }
    stored_at = "2026-09-26T00:00:00+00:00"
    artifact_entries = [
        {
            "kind": kind,
            "artifact_sha256": artifact.artifact_sha256,
            "document_size": len(artifact.document_json),
            "body_size": json.loads(artifact.document_json)["body_size"],
            "stored_at": stored_at,
        }
        for kind, artifact in artifacts
    ]
    artifact_entries.sort(key=lambda item: (item["kind"], item["artifact_sha256"]))
    document = {
        "version": "fpi-admin-read-v1",
        "read_id": "",
        "request_sha256": "",
        "request": sr_request_document(""),
        "policy_sha256": "",
        "policy": policy,
        "read_at": "2026-09-28T00:00:00+00:00",
        "scope": {
            "version": "fpi-admin-scope-v1",
            "india_date": "2026-09-28",
            "history_start_date": start,
            "history_start_clamped": False,
            "diagnostic_start_at": "2026-09-21T00:00:00+00:00",
            "diagnostic_start_clamped": False,
            "newest_reporting_date": None if empty else "2026-09-25",
        },
        "status": "COMPLETE",
        "failure": None,
        "data": {
            "candidate_membership_ids": [member["membership_id"] for member in candidate_docs],
            "candidate_dates": sorted({member["reporting_date"] for member in candidate_docs}),
            "diagnostic_parse_ids": sorted(
                row["parse_id"] for row in references["parses"] if row["failure_reason"]
            ),
            "references": references,
            "reference_sha256": "",
            "storage_times": {
                "captures": [
                    {"capture_sha256": row["capture_sha256"], "stored_at": stored_at}
                    for row in references["captures"]
                ],
                "parses": [
                    {"parse_id": row["parse_id"], "stored_at": stored_at}
                    for row in references["parses"]
                ],
            },
            "artifacts": artifact_entries,
            "qualification": qualification,
            "qualification_sha256": "",
        },
        "execution_state": "UNVERIFIED",
        "acquisition_state": "UNVERIFIED",
        "eligible": False,
        "feature": None,
    }
    sr_refresh(document)
    rows = {
        "capture_rows": tuple(
            {
                "capture_sha256": item.capture_sha256,
                "document_json": item.document_json,
                "stored_at": stored_at,
            }
            for item in captures
        ),
        "parse_rows": tuple(
            {
                "parse_id": item.parse_id,
                "record_sha256": item.record_sha256,
                "document_json": item.document_json,
                "stored_at": stored_at,
            }
            for item in records
        ),
        "artifact_rows": tuple(
            {
                "kind": kind,
                "artifact_sha256": item.artifact_sha256,
                "document_json": item.document_json,
                "stored_at": stored_at,
            }
            for kind, item in artifacts
        ),
        "event_rows": tuple(
            {"event_id": item.event_id, "event_document_json": item.document_json}
            for item in events
        ),
    }
    return document, rows


def test_sr_golden_vectors() -> None:
    policy = FpiAdminReadPolicy(sr_test_canonical(sr_policy_document()))
    assert (policy.policy_sha256, len(policy.document_json)) == (
        "005430dfbdde7fb1aacd83d75a8763fe931dbbd7de220a07be14a27dbaac5f87",
        820,
    )
    request = FpiAdminReadRequest(sr_test_canonical(sr_request_document(policy.policy_sha256)))
    assert (request.read_id, len(request.document_json)) == (
        "a4130c1ce37873b7b580e0e15d02cf0fd0bdbad3c656bba6b248779b8436ad27",
        433,
    )
    document, rows = sr_fixture(empty=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    # Independently hashed from the authored fixture, without the codec helpers.
    assert (manifest.read_sha256, len(manifest.document_json)) == (
        "d89e3d48d849e9284b0c70e2310a71a218e4d02211d8c6dfe502a3b8be998852",
        2805,
    )
    assert (
        document["data"]["reference_sha256"]
        == "5043b6cf68a2600dc6ae8f6af32a222a8cfa63a2774f61ec2833060024a81e58"
    )
    assert (
        document["data"]["qualification_sha256"]
        == "4512d5d55af1633da699dbf2578900e14377e99a1acb26d2b6095fd667c5de19"
    )
    assert verify_fpi_admin_read_originals(manifest, **rows) == manifest
    document["read_at"] = "2026-09-28T00:00:00.000001+00:00"
    document["scope"]["diagnostic_start_at"] = "2026-09-21T00:00:00.000001+00:00"
    assert FpiAdminReadManifest(sr_test_canonical(document)).read_at.endswith(".000001+00:00")


@pytest.mark.parametrize(
    "key,value",
    [
        ("version", "v2"),
        ("diagnostic_window_days", True),
        ("max_current_age_days", -1),
        ("max_history_age_days", 6),
        ("max_history_age_days", 100001),
        ("minimum_history", 9),
        ("history_window", 2521),
        ("history_window", 9),
        ("parser_allowlist", []),
        ("parser_allowlist", ["2" * 64] * 2),
        ("parser_allowlist", ["3" * 64, "2" * 64]),
        ("source_rationale", "secret\n"),
        ("source_rationale", "é"),
        ("source_rationale", "\x00"),
        ("source_rule", "TRUSTED"),
        ("selector_version", "EXECUTED"),
        ("allow_withdrawal_fallback", 0),
        ("feature_version", "bad context"),
        ("unknown", "private secret"),
        ("selector_sha256", "A" * 64),
    ],
)
def test_sr_policy_request_corruption(key: str, value: Any) -> None:
    policy = sr_policy_document()
    policy[key] = value
    with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$") as error:
        FpiAdminReadPolicy(sr_test_canonical(policy))
    assert error.value.__cause__ is None
    request = sr_request_document("1" * 64)
    for changed in (
        {"decision_id": "11111111-1111-1111-8111-111111111111"},
        {"run_id": "FFFFFFFF-FFFF-4FFF-8FFF-FFFFFFFFFFFF"},
        {"read_at": "2026-09-28"},
        {"pair": "EURUSD"},
        {"model_sha256": True},
    ):
        with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$"):
            FpiAdminReadRequest(sr_test_canonical({**request, **changed}))


@pytest.mark.parametrize(
    "path,value",
    [
        (("eligible",), True),
        (("eligible",), 0),
        (("feature",), 0),
        (("execution_state",), "VERIFIED"),
        (("acquisition_state",), "VERIFIED"),
        (("read_at",), "2026-09-28T00:00:00.000000+00:00"),
        (("read_at",), "2026-09-28T00:00:00Z"),
        (("read_at",), "2026-09-28T05:30:00+05:30"),
        (("read_at",), "9999-12-31T20:00:00+00:00"),
        (("scope", "history_start_date"), "2026-09-24"),
        (("scope", "history_start_clamped"), 0),
        (("scope", "diagnostic_start_clamped"), 0),
        (("scope", "newest_reporting_date"), None),
        (("scope", "newest_reporting_date"), "2026-09-29"),
        (("data", "candidate_dates"), []),
        (("data", "candidate_membership_ids"), []),
        (("data", "qualification", "heads"), []),
        (("data", "artifacts"), []),
        (("data", "references", "captures", 0, "http_status"), True),
        (("data", "references", "captures", 0, "requested_at"), "2026-09-29T00:00:00+00:00"),
        (("data", "references", "parses", 0, "parse_id"), "f" * 64),
        (("data", "references", "parses", 0, "memberships", 0, "membership_id"), "f" * 64),
        (("data", "storage_times", "captures", 0, "stored_at"), "2026-09-25T00:00:00+00:00"),
        (("data", "storage_times", "parses", 0, "stored_at"), "2026-09-29T00:00:00+00:00"),
    ],
)
def test_sr_manifest_corruption(path: tuple[Any, ...], value: Any) -> None:
    document, _ = sr_fixture()
    current = document
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    sr_refresh(document)
    with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$") as error:
        FpiAdminReadManifest(sr_test_canonical(document))
    assert error.value.__cause__ is None


@pytest.mark.parametrize("category", ["capture_rows", "parse_rows", "artifact_rows", "event_rows"])
@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "extra", "document", "projection", "subclass"]
)
def test_sr_original_corruption(category: str, change: str) -> None:
    document, rows = sr_fixture(event=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    assert verify_fpi_admin_read_originals(manifest, **rows) == manifest
    original = rows[category]
    row = original[0].copy()
    if change == "missing":
        rows[category] = original[1:]
    elif change == "duplicate":
        rows[category] = (*original, row)
    elif change == "extra":
        row["private extra"] = "fixture secret"
        rows[category] = (row, *original[1:])
    elif change == "document":
        key = "event_document_json" if category == "event_rows" else "document_json"
        row[key] = row[key].replace("v1", "v9").replace("v2", "v9")
        rows[category] = (row, *original[1:])
    elif change == "projection":
        if category == "event_rows":
            row["event_id"] = "a" * 64
        else:
            row["stored_at"] = "2026-09-27T00:00:00Z"
        rows[category] = (row, *original[1:])
    else:
        rows[category] = list(original)
    with pytest.raises(ValueError, match="^READ_(INTEGRITY_ERROR|DEPENDENCY_MISSING)$") as error:
        verify_fpi_admin_read_originals(manifest, **rows)
    assert error.value.__cause__ is None


def test_sr_once_per_unique_and_detachment() -> None:
    document, rows = sr_fixture(diagnostics=True, event=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    before = deepcopy(rows)
    for category in ("capture_rows", "parse_rows", "artifact_rows"):
        for row in rows[category]:
            row["stored_at"] = "2026-09-26T00:00:00.000Z"
    with (
        patch.object(
            original_codec, "validate_fpi_capture", wraps=validate_fpi_capture
        ) as captures,
        patch.object(original_codec, "_record_parts", wraps=original_codec._record_parts) as parses,
        patch.object(codec, "validate_fpi_artifact", wraps=validate_fpi_artifact) as artifacts,
        patch.object(codec, "build_fpi_read_references", wraps=build_fpi_read_references) as bulk,
        patch.object(codec, "FpiQualificationView", wraps=FpiQualificationView) as view,
    ):
        result = verify_fpi_admin_read_originals(manifest, **rows)
        assert (
            captures.call_count,
            parses.call_count,
            artifacts.call_count,
            bulk.call_count,
            view.call_count,
        ) == (1, 2, 3, 1, 1)
    assert result == manifest and result is not manifest
    rows["capture_rows"][0]["document_json"] = "later mutation"
    assert result.document_json == manifest.document_json
    with pytest.raises(AttributeError):
        result.status = "TRUSTED"  # type: ignore[misc]
    # Support is absent from candidate heads but remains bound by the original parse.
    assert len(document["data"]["references"]["parses"][0]["memberships"]) in (0, 3)
    success = next(row for row in document["data"]["references"]["parses"] if row["memberships"])
    success["memberships"].pop(0)
    sr_refresh(document)
    compact = FpiAdminReadManifest(sr_test_canonical(document))
    with pytest.raises(ValueError, match="^READ_INTEGRITY_ERROR$"):
        verify_fpi_admin_read_originals(compact, **before)
    unchanged_document, mutable_rows = sr_fixture()
    unchanged_manifest = FpiAdminReadManifest(sr_test_canonical(unchanged_document))
    artifact_validation = Mock(wraps=validate_fpi_artifact)
    with patch.object(
        codec,
        "validate_fpi_artifact",
        side_effect=lambda artifact: (
            mutable_rows["capture_rows"][0].update(document_json="mutated during validation"),
            artifact_validation(artifact),
        )[-1],
    ):
        assert (
            verify_fpi_admin_read_originals(unchanged_manifest, **mutable_rows)
            == unchanged_manifest
        )


def test_sr_receipts_and_forgery() -> None:
    document, rows = sr_fixture(empty=True)
    policy = FpiAdminReadPolicy(sr_test_canonical(document["policy"]))
    request = FpiAdminReadRequest(sr_test_canonical(document["request"]))
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    receipt = {
        "version": "fpi-admin-read-receipt-v1",
        "decision_id": request.decision_id,
        "request_sha256": request.request_sha256,
        "read_id": request.read_id,
        "read_sha256": manifest.read_sha256,
        "read_at": manifest.read_at,
        "status": manifest.status,
        "execution_state": "UNVERIFIED",
        "acquisition_state": "UNVERIFIED",
        "eligible": False,
        "inserted": True,
    }
    assert validate_fpi_admin_read_receipt(receipt, request) == receipt
    assert validate_fpi_admin_read_receipt(receipt, request) is not receipt
    for key in receipt:
        bad = receipt.copy()
        bad[key] = 1
        with pytest.raises(ValueError):
            validate_fpi_admin_read_receipt(bad, request)
        bad = receipt.copy()
        del bad[key]
        with pytest.raises(ValueError):
            validate_fpi_admin_read_receipt(bad, request)
    policy_receipt = {
        "version": "fpi-admin-read-policy-receipt-v1",
        "policy_sha256": policy.policy_sha256,
        "inserted": False,
    }
    assert validate_fpi_admin_policy_receipt(policy_receipt, policy) == policy_receipt
    for key in policy_receipt:
        with pytest.raises(ValueError):
            validate_fpi_admin_policy_receipt({**policy_receipt, key: 1}, policy)
    for key in policy.__dataclass_fields__:
        forged_policy = deepcopy(policy)
        object.__setattr__(forged_policy, key, "forged")
        with pytest.raises(ValueError):
            validate_fpi_admin_policy_receipt(policy_receipt, forged_policy)
    for key in request.__dataclass_fields__:
        forged_request = deepcopy(request)
        object.__setattr__(forged_request, key, "forged")
        with pytest.raises(ValueError):
            validate_fpi_admin_read_receipt(receipt, forged_request)
    for key in manifest.__dataclass_fields__:
        forged = deepcopy(manifest)
        object.__setattr__(forged, key, "forged")
        with pytest.raises(ValueError):
            verify_fpi_admin_read_originals(forged, **rows)


def test_sr_failure_and_clamping() -> None:
    document, _ = sr_fixture(empty=True)
    document.update(
        status="READ_SCOPE_EXCEEDED",
        data=None,
        failure={
            "code": "READ_SCOPE_EXCEEDED",
            "dimension": "CANDIDATES",
            "limit": 20000,
            "observed": 20001,
            "measurement": "AT_LEAST",
            "witness": None,
        },
    )
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    assert (manifest.read_sha256, len(manifest.document_json)) == (
        "fdfd74e271e5857a413c738e1766440ad0b0b8cb5a612c419e2f3c9156f4872b",
        2104,
    )
    assert (
        verify_fpi_admin_read_originals(
            manifest, capture_rows=(), parse_rows=(), artifact_rows=(), event_rows=()
        )
        == manifest
    )
    for field, value in (
        ("observed", 20000),
        ("observed", True),
        ("limit", 19999),
        ("observed", 20002),
        ("measurement", "TOTAL"),
        ("witness", {}),
    ):
        altered = deepcopy(document)
        altered["failure"][field] = value
        with pytest.raises(ValueError):
            FpiAdminReadManifest(sr_test_canonical(altered))
    document["read_at"] = "0001-01-01T00:00:00+00:00"
    document["scope"].update(
        india_date="0001-01-01",
        history_start_date="0001-01-01",
        history_start_clamped=True,
        diagnostic_start_at="0001-01-01T00:00:00+00:00",
        diagnostic_start_clamped=True,
    )
    assert FpiAdminReadManifest(sr_test_canonical(document)).read_at.startswith("0001-")


def test_sr_resources_precede_decoding() -> None:
    document, rows = sr_fixture(empty=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    empty_artifact = deepcopy(document)
    metadata = empty_artifact["data"]["artifacts"][0]
    metadata["body_size"] = 0
    metadata["document_size"] = len(
        sr_test_canonical(
            {
                "version": "fpi-implementation-artifact-v1",
                "kind": metadata["kind"],
                "artifact_sha256": metadata["artifact_sha256"],
                "body_size": 0,
                "body_base64": "",
            }
        )
    )
    sr_refresh(empty_artifact)
    with pytest.raises(ValueError):
        FpiAdminReadManifest(sr_test_canonical(empty_artifact))
    with (
        patch.object(codec, "validate_fpi_artifact", side_effect=AssertionError("decode invoked")),
        patch.object(
            codec, "build_fpi_read_references", side_effect=AssertionError("decode invoked")
        ),
    ):
        bad = deepcopy(rows)
        bad["artifact_rows"][0]["document_json"] = "x" * 7_000_001
        with pytest.raises(ValueError):
            verify_fpi_admin_read_originals(manifest, **bad)
        with patch.dict(codec._LIMITS, {"ORIGINAL_BYTES": 1}):
            with pytest.raises(ValueError):
                verify_fpi_admin_read_originals(manifest, **rows)
    for dimension in (
        "ARTIFACTS",
        "ORIGINAL_BYTES",
        "REFERENCE_BYTES",
        "QUALIFICATION_BYTES",
        "MANIFEST_BYTES",
    ):
        actual = {
            "ARTIFACTS": len(document["data"]["artifacts"]),
            "ORIGINAL_BYTES": sum(row["document_size"] for row in document["data"]["artifacts"]),
            "REFERENCE_BYTES": len(sr_test_canonical(document["data"]["references"])),
            "QUALIFICATION_BYTES": len(sr_test_canonical(document["data"]["qualification"])),
            "MANIFEST_BYTES": len(manifest.document_json),
        }[dimension]
        with patch.dict(codec._LIMITS, {dimension: actual}):
            assert FpiAdminReadManifest(manifest.document_json) == manifest
        with patch.dict(codec._LIMITS, {dimension: actual - 1}):
            with pytest.raises(ValueError):
                FpiAdminReadManifest(manifest.document_json)


def test_sr_depth_before_decoder() -> None:
    with patch.object(json, "loads", side_effect=AssertionError("decoder invoked")):
        for text in ("[" * 33 + "0" + "]" * 33, "x" * 32769, '{"x":"é"}'):
            with pytest.raises(ValueError):
                FpiAdminReadPolicy(text)
    policy = sr_test_canonical(sr_policy_document())
    for text in (
        policy + "\n",
        policy.replace('"version":', '"version":"duplicate","version":'),
        policy.replace('"allow_withdrawal_fallback":false', '"allow_withdrawal_fallback":NaN'),
        policy.replace("Neither endpoint", "\\ud800"),
        policy.replace('"minimum_history":10', '"minimum_history":10.0'),
    ):
        with pytest.raises(ValueError):
            FpiAdminReadPolicy(text)
    policy_doc = sr_policy_document()
    policy_doc["source_rationale"] = 'Quotes " and slash \\ are literal; braces [[[]]] are text.'
    assert FpiAdminReadPolicy(sr_test_canonical(policy_doc))
    subclass = type("ReceiptString", (str,), {})
    valid = FpiAdminReadPolicy(policy)
    with pytest.raises(ValueError):
        validate_fpi_admin_policy_receipt(
            {
                subclass("version"): "fpi-admin-read-policy-receipt-v1",
                "policy_sha256": valid.policy_sha256,
                "inserted": False,
            },
            valid,
        )
    with pytest.raises(ValueError):
        FpiAdminReadPolicy(subclass(policy))


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
def test_sr_cancellation_propagates(exception: type[BaseException]) -> None:
    document, rows = sr_fixture(empty=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    with patch.object(codec, "validate_fpi_artifact", side_effect=exception):
        with pytest.raises(exception):
            verify_fpi_admin_read_originals(manifest, **rows)


@pytest.mark.parametrize(
    "dimension,kind,field,value",
    [
        ("NEWEST_DATE", "MEMBERSHIP_DATE", "reporting_date", "2026-09-29"),
        ("FUTURE_FAILURE_STORAGE", "PARSE", "stored_at", "2026-09-29T00:00:00+00:00"),
        ("REFERENCED_TIME", "CAPTURE", "requested_at", "2026-09-29T00:00:00+00:00"),
        ("REFERENCED_TIME", "PARSE", "recorded_at", "2026-09-29T00:00:00.123+00:00"),
        ("REFERENCED_TIME", "ARTIFACT", "stored_at", "2026-09-29T00:00:00+00:00"),
        ("REFERENCED_TIME", "EVENT", "recorded_at", "2026-09-29T00:00:00+00:00"),
        ("INDIA_TIME_RANGE", "CAPTURE", "retrieved_at", "9999-12-31T20:00:00+00:00"),
        ("INDIA_TIME_RANGE", "PARSE", "recorded_at", "9999-12-31T20:00:00+00:00"),
    ],
)
def test_sr_clock_witnesses(dimension: str, kind: str, field: str, value: str) -> None:
    document, rows = sr_fixture(empty=True)
    document.update(
        status="CLOCK_INCONSISTENT",
        data=None,
        failure={
            "code": "CLOCK_INCONSISTENT",
            "dimension": dimension,
            "limit": None,
            "observed": None,
            "measurement": None,
            "witness": {
                "kind": kind,
                "id": None if kind == "MEMBERSHIP_DATE" else "1" * 64,
                "field": field,
                "value": value,
            },
        },
    )
    if dimension == "NEWEST_DATE":
        document["scope"]["newest_reporting_date"] = value
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    assert manifest.status == "CLOCK_INCONSISTENT"
    with pytest.raises(ValueError):
        verify_fpi_admin_read_originals(manifest, **rows)
    document["failure"]["witness"]["value"] = (
        "2026-09-27" if kind == "MEMBERSHIP_DATE" else "2026-09-27T00:00:00+00:00"
    )
    with pytest.raises(ValueError):
        FpiAdminReadManifest(sr_test_canonical(document))


def test_sr_diagnostic_scope() -> None:
    document, rows = sr_fixture(diagnostics=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    assert verify_fpi_admin_read_originals(manifest, **rows) == manifest
    data = document["data"]
    # Retained old failure remains in scope when it shares the fixed candidate capture.
    document["read_at"] = "2026-10-28T00:00:00+00:00"
    document["scope"].update(
        india_date="2026-10-28",
        history_start_date="2026-10-25",
        diagnostic_start_at="2026-10-21T00:00:00+00:00",
    )
    assert FpiAdminReadManifest(sr_test_canonical(document))
    # A failure cannot become support or disappear from the diagnostic ID list.
    data["diagnostic_parse_ids"] = []
    with pytest.raises(ValueError):
        FpiAdminReadManifest(sr_test_canonical(document))
    # Failure-only captures never seed out-of-window diagnostics recursively.
    isolated, _ = sr_fixture(diagnostics=True)
    data = isolated["data"]
    failed_id = data["diagnostic_parse_ids"][0]
    data["references"]["parses"] = [
        row for row in data["references"]["parses"] if row["parse_id"] == failed_id
    ]
    data["storage_times"]["parses"] = [
        row for row in data["storage_times"]["parses"] if row["parse_id"] == failed_id
    ]
    data["candidate_membership_ids"] = []
    data["candidate_dates"] = []
    data["qualification"] = {
        "version": "fpi-qualification-view-v2",
        "members": [],
        "heads": [],
        "events": [],
    }
    isolated["scope"]["newest_reporting_date"] = None
    sr_refresh(isolated)
    assert FpiAdminReadManifest(sr_test_canonical(isolated))
    isolated["read_at"] = "2026-10-28T00:00:00+00:00"
    isolated["scope"].update(
        india_date="2026-10-28",
        history_start_date="2026-10-25",
        diagnostic_start_at="2026-10-21T00:00:00+00:00",
    )
    with pytest.raises(ValueError):
        FpiAdminReadManifest(sr_test_canonical(isolated))


def test_sr_old_sentinel() -> None:
    document, rows = sr_fixture(age=0)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    assert document["data"]["candidate_dates"] == ["2026-09-25"]
    assert len(document["data"]["references"]["parses"][0]["memberships"]) == 3
    assert verify_fpi_admin_read_originals(manifest, **rows) == manifest
    # Date/value/member/head limits are tested at the exact complete bound, then below it.
    document, _ = sr_fixture(age=365, event=True, diagnostics=True)
    manifest = FpiAdminReadManifest(sr_test_canonical(document))
    data = document["data"]
    measured = {
        "CANDIDATES": len(data["candidate_membership_ids"]),
        "PARSES": len(data["references"]["parses"]),
        "CAPTURES": len(data["references"]["captures"]),
        "SUPPORT_MEMBERSHIPS": sum(len(row["memberships"]) for row in data["references"]["parses"]),
        "HEADS": len(data["qualification"]["heads"]),
        "EVENTS": len(data["qualification"]["events"]),
    }
    for dimension, actual in measured.items():
        with patch.dict(codec._LIMITS, {dimension: actual}):
            assert FpiAdminReadManifest(manifest.document_json) == manifest
        with patch.dict(codec._LIMITS, {dimension: actual - 1}):
            with pytest.raises(ValueError):
                FpiAdminReadManifest(manifest.document_json)
    alternate, rows = sr_fixture(alternatives=True)
    alternate["policy"]["source_rule"] = "LATEST"
    sr_refresh(alternate)
    manifest = FpiAdminReadManifest(sr_test_canonical(alternate))
    assert len(alternate["data"]["candidate_membership_ids"]) == 2
    assert (
        len({member["value_sha256"] for member in alternate["data"]["qualification"]["members"]})
        == 1
    )
    assert verify_fpi_admin_read_originals(manifest, **rows) == manifest
    assert json.loads(manifest.document_json)["eligible"] is False
