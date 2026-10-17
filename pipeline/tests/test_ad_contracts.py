"""Strict AD transport contracts: wire parsing, canonicalization, reason codes.

The wire format is JSON with decimal strings and Z-suffixed UTC timestamps.
These tests pin rejection of truthy strings, binary floats, unknown fields,
unknown enums, naive datetimes, bad identifiers and unknown reason codes,
plus byte-stable canonical round-trips and digest behavior.
"""

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.paper.contracts import (
    REASON_CODES,
    SCHEMA_VERSION,
    Alignment,
    Candidate,
    ChildRole,
    ContractError,
    Coverage,
    EvaluationCertificate,
    ExecutionPermit,
    Experiment,
    Mode,
    Money,
    OperatorIdentity,
    Pair,
    ParentTradePlan,
    ReasoningDecision,
    RiskBreakdown,
    Side,
    SnapshotManifest,
    canonical_bytes,
    digest_record,
    kind_of,
    parse_record,
    require_reason_code,
    stop_side_valid,
)

CID = "0f8fad5b-d9cb-469f-a165-70867728950e"
DID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
PID = "550e8400-e29b-41d4-a716-446655440000"
BID = "16fd2706-8baf-433b-82eb-8c7fada847da"
CERT_ID = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"
CHILD_A = "11111111-2222-3333-4444-555555555555"
CHILD_B = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
CHILD_C = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PERMIT_ID = "99999999-8888-7777-6666-555555555555"
RESERVATION_ID = "123e4567-e89b-12d3-a456-426614174000"
CLAIM_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
EPOCH_ID = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
TRIAL_ID = "6ba7b812-9dad-11d1-80b4-00c04fd430c8"
TS = "2026-10-18T12:00:00Z"
LATER = "2026-10-18T12:00:05Z"


def _operator(*, fallback_used: object = False) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": "local",
        "responding_model": "test-model-v1",
        "prompt_digest": "c" * 64,
        "toolset_digest": "d" * 64,
        "renderer_version": "renderer-v1",
        "fallback_used": fallback_used,
    }


def _snapshot() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": "e" * 64,
        "kind": "bars",
        "source_id": "mt5/USDJPYm/H1",
        "pair": "USDJPY",
        "fetched_at": TS,
        "published_at": TS,
        "available_at": TS,
        "valid_from": TS,
        "expires_at": LATER,
        "coverage": "verified",
        "content_digest": "f" * 64,
        "content_relative_path": "snapshots/2026/10/18/usdjpy-h1.jsonl",
        "clock_profile_digest": "0" * 64,
        "collector_version": "collector-v1",
        "licensing_class": "private",
    }


def _candidate() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": CID,
        "created_at": TS,
        "decision_at": TS,
        "pair": "USDJPY",
        "side": "short",
        "setup_id": "SU1",
        "setup_version": 1,
        "artifact_digest": "a" * 64,
        "feature_snapshot_id": "b" * 64,
        "source_snapshot_ids": ["c" * 64],
        "source_cohort": "live",
        "regime": "trending",
        "proposed_entry": "158.0",
        "invalidation_price": "158.5",
        "expires_at": TS,
        "deterministic_trigger_ids": ["SU1.POOL_CONFIRMED"],
    }


def _child(role: str, lots: str, child_id: str, tp: str | None = None) -> dict[str, object]:
    child: dict[str, object] = {
        "child_id": child_id,
        "role": role,
        "lots": lots,
        "initial_sl": "158.1",
    }
    if tp is not None:
        child["initial_tp"] = tp
    return child


def _plan(children: list[dict[str, object]] | None = None) -> dict[str, object]:
    specs = children if children is not None else [
        _child("A", "0.6", CHILD_A, tp="157.9"),
        _child("B", "0.4", CHILD_B),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "parent_id": PID,
        "candidate_id": CID,
        "decision_id": DID,
        "pair": "USDJPY",
        "side": "short",
        "artifact_digest": "a" * 64,
        "management_policy_digest": "b" * 64,
        "signal_model_version": "2.0-live",
        "source_cohort": "live",
        "entry_snapshot_id": "c" * 64,
        "stop_price": "158.1",
        "target_a_price": "157.9",
        "requested_risk_fraction": "0.05",
        "immutable_initial_risk_usd": {"currency": "USD", "amount": "500.00"},
        "initial_stop_distance": "0.1",
        "child_specs": specs,
        "expiry_at": TS,
        "falsifiers": ["daily close back inside the prior range"],
        "grade": "A+",
        "operator_identity": _operator(),
        "spec_bundle_digest": "d" * 64,
    }


def _decision(
    *,
    rejection_codes: list[str] | None = None,
    operator: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_id": DID,
        "candidate_id": CID,
        "decision_at": TS,
        "verdict": "propose",
        "supported_claims": [
            {
                "claim_id": CLAIM_ID,
                "text": "Pool was confirmed before the retest",
                "fact_refs": ["e" * 64 + "#/confirmed"],
                "derived_metric_refs": [],
            }
        ],
        "bull_case": "Breakout holds above the broken level",
        "bear_case": "Failed retest returns to the range",
        "wait_case": "No completed retest bar yet",
        "falsifiers": ["daily close back inside the range"],
        "evidence_ids": ["c" * 64],
        "spec_bundle_digest": "d" * 64,
        "operator_identity": operator if operator is not None else _operator(),
        "latency_ms": 1200,
        "budget_receipt_id": BID,
        "rejection_codes": rejection_codes if rejection_codes is not None else [],
    }


def _money(amount: str) -> dict[str, str]:
    return {"currency": "USD", "amount": amount}


def _risk() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "open_residual_stop_usd": _money("80"),
        "pending_all_in_usd": _money("0"),
        "proposed_stop_usd": _money("120"),
        "open_future_cost_usd": _money("4"),
        "proposed_future_cost_usd": _money("6"),
        "proposed_all_in_usd": _money("126"),
        "slot_budget_usd": _money("500"),
        "immutable_initial_risk_usd": _money("120"),
        "valuation_snapshot_ids": ["e" * 64],
    }


def _permit() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "permit_id": PERMIT_ID,
        "parent_id": PID,
        "plan_digest": "a" * 64,
        "authority_digest": "b" * 64,
        "evaluator_certificate_id": CERT_ID,
        "broker_state_digest": "c" * 64,
        "reservation_id": RESERVATION_ID,
        "issued_at": TS,
        "expires_at": LATER,
        "allowed_operations": ["send_child_a", "send_child_b"],
        "max_child_volume": "0.6",
        "consumed_sequence": 0,
        "issuer_key_id": "key-v1",
        "signature": "signed-transport-value",
    }


def _experiment() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "hypothesis": "Shorter retest window improves fill quality",
        "parent_artifact_digest": "a" * 64,
        "changed_fields": ["retest_window_bars"],
        "registered_at": TS,
        "epoch_id": EPOCH_ID,
        "trial_id": TRIAL_ID,
        "input_cohort": "live-2026q4",
        "training_partition_ids": ["1" * 64],
        "validation_partition_ids": ["2" * 64],
        "holdout_partition_ids": ["3" * 64],
        "metric_definitions": {"accuracy": "directional hit rate"},
        "cost_model": "cost-model-v1",
        "random_seed": 7,
        "stop_rule": "stop after 20 variants",
        "trial_budget": 20,
        "invalidation_rule": "invalidate on any schema change",
    }


def _certificate() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_digest": "a" * 64,
        "experiment_id": TRIAL_ID,
        "input_digests": ["1" * 64, "2" * 64, "3" * 64],
        "evaluator_build_digest": "b" * 64,
        "evaluator_policy_digest": "c" * 64,
        "evaluation_cutoff": TS,
        "sample_count": 120,
        "block_count": 12,
        "metrics": {"accuracy": "0.58"},
        "verdict": "PASS",
        "reason_codes": ["OK"],
        "expires_at": LATER,
        "issuer_identity": "evaluator-service-1",
        "issuer_signature": "signed-certificate-blob",
    }


KINDS: list[tuple[str, Callable[[], dict[str, object]]]] = [
    ("SnapshotManifest", _snapshot),
    ("Candidate", _candidate),
    ("ReasoningDecision", _decision),
    ("OperatorIdentity", _operator),
    ("ParentTradePlan", _plan),
    ("RiskBreakdown", _risk),
    ("ExecutionPermit", _permit),
    ("Experiment", _experiment),
    ("EvaluationCertificate", _certificate),
]

RECORD_TYPES: dict[str, type[object]] = {
    "SnapshotManifest": SnapshotManifest,
    "Candidate": Candidate,
    "ReasoningDecision": ReasoningDecision,
    "OperatorIdentity": OperatorIdentity,
    "ParentTradePlan": ParentTradePlan,
    "RiskBreakdown": RiskBreakdown,
    "ExecutionPermit": ExecutionPermit,
    "Experiment": Experiment,
    "EvaluationCertificate": EvaluationCertificate,
}


def test_rejects_string_false() -> None:
    payload = _operator(fallback_used="false")
    with pytest.raises(ContractError) as excinfo:
        parse_record(payload, "OperatorIdentity")
    assert excinfo.value.code == "INVALID_SCHEMA"


def test_rejects_nan_and_unknown_schema() -> None:
    nan = _candidate()
    nan["proposed_entry"] = float("nan")
    with pytest.raises(ContractError) as nan_error:
        parse_record(nan, "Candidate")
    assert nan_error.value.code == "INVALID_NUMBER"

    infinity = _candidate()
    infinity["invalidation_price"] = float("inf")
    with pytest.raises(ContractError) as inf_error:
        parse_record(infinity, "Candidate")
    assert inf_error.value.code == "INVALID_NUMBER"

    wrong_schema = _candidate()
    wrong_schema["schema_version"] = "ad/2"
    with pytest.raises(ContractError) as schema_error:
        parse_record(wrong_schema, "Candidate")
    assert schema_error.value.code == "INVALID_SCHEMA"

    missing_schema = _candidate()
    del missing_schema["schema_version"]
    with pytest.raises(ContractError):
        parse_record(missing_schema, "Candidate")


def test_normalizes_utc_and_decimal() -> None:
    payload = _candidate()
    payload["proposed_entry"] = "1.105000"
    payload["decision_at"] = "2026-10-18T12:00:00.000000Z"
    record = parse_record(payload, "Candidate")
    assert isinstance(record, Candidate)
    assert record.proposed_entry == Decimal("1.105")
    assert record.decision_at == datetime(2026, 10, 18, 12, tzinfo=UTC)
    encoded = canonical_bytes(record).decode("utf-8")
    assert '"proposed_entry":"1.105"' in encoded
    assert '"decision_at":"2026-10-18T12:00:00Z"' in encoded


def test_canonical_roundtrip() -> None:
    for kind, builder in KINDS:
        record = parse_record(builder(), kind)
        first = canonical_bytes(record)
        reparsed = parse_record(json.loads(first), kind)
        assert canonical_bytes(reparsed) == first
        assert digest_record(reparsed) == digest_record(record)


def test_unknown_field_rejected() -> None:
    payload = _candidate()
    payload["confidence"] = "92%"
    with pytest.raises(ContractError) as excinfo:
        parse_record(payload, "Candidate")
    assert excinfo.value.code == "INVALID_SCHEMA"


def test_missing_required_field_rejected() -> None:
    payload = _plan()
    del payload["stop_price"]
    with pytest.raises(ContractError) as excinfo:
        parse_record(payload, "ParentTradePlan")
    assert "stop_price" in str(excinfo.value)


def test_unknown_record_kind_rejected() -> None:
    with pytest.raises(ContractError):
        parse_record(_candidate(), "MysteryRecord")


def test_enum_values_strict() -> None:
    for pair in Pair:
        assert Pair(pair.value) is pair
    for side in Side:
        assert Side(side.value) is side
    for coverage in Coverage:
        assert Coverage(coverage.value) is coverage
    for alignment in Alignment:
        assert Alignment(alignment.value) is alignment
    for mode in Mode:
        assert Mode(mode.value) is mode

    candidate = _candidate()
    candidate["pair"] = "GBPUSD"
    with pytest.raises(ContractError):
        parse_record(candidate, "Candidate")
    candidate = _candidate()
    candidate["side"] = "buy"
    with pytest.raises(ContractError):
        parse_record(candidate, "Candidate")
    snapshot = _snapshot()
    snapshot["coverage"] = "clean"
    with pytest.raises(ContractError):
        parse_record(snapshot, "SnapshotManifest")
    with pytest.raises(ValueError):
        Alignment("mixed")
    with pytest.raises(ValueError):
        Mode("live")


def test_bool_as_int_rejected() -> None:
    decision = _decision()
    decision["latency_ms"] = True
    with pytest.raises(ContractError):
        parse_record(decision, "ReasoningDecision")
    decision = _decision()
    decision["latency_ms"] = "1200"
    with pytest.raises(ContractError):
        parse_record(decision, "ReasoningDecision")
    candidate = _candidate()
    candidate["setup_version"] = True
    with pytest.raises(ContractError):
        parse_record(candidate, "Candidate")


def test_naive_datetime_rejected() -> None:
    payload = _candidate()
    payload["decision_at"] = "2026-10-18T12:00:00"
    with pytest.raises(ContractError):
        parse_record(payload, "Candidate")
    payload = _candidate()
    payload["decision_at"] = "2026-10-18T14:00:00+02:00"
    with pytest.raises(ContractError):
        parse_record(payload, "Candidate")
    record = parse_record(_candidate(), "Candidate")
    assert isinstance(record, Candidate)
    with pytest.raises(ContractError):
        replace(record, decision_at=datetime(2026, 10, 18, 12))
    with pytest.raises(ContractError):
        replace(
            record,
            decision_at=datetime(2026, 10, 18, 14, tzinfo=timezone(timedelta(hours=2))),
        )


def test_non_uuid_id_rejected() -> None:
    payload = _candidate()
    payload["candidate_id"] = "candidate-1"
    with pytest.raises(ContractError):
        parse_record(payload, "Candidate")
    payload = _candidate()
    payload["candidate_id"] = CID.upper()
    with pytest.raises(ContractError):
        parse_record(payload, "Candidate")
    content_addressed = parse_record(_snapshot(), "SnapshotManifest")
    assert isinstance(content_addressed, SnapshotManifest)


def test_money_missing_currency_or_negative_amount_rejected() -> None:
    plan = _plan()
    plan["immutable_initial_risk_usd"] = {"amount": "500.00"}
    with pytest.raises(ContractError):
        parse_record(plan, "ParentTradePlan")
    plan = _plan()
    plan["immutable_initial_risk_usd"] = {"currency": "EUR", "amount": "500.00"}
    with pytest.raises(ContractError):
        parse_record(plan, "ParentTradePlan")
    plan = _plan()
    plan["immutable_initial_risk_usd"] = {"currency": "USD", "amount": "-0.01"}
    with pytest.raises(ContractError):
        parse_record(plan, "ParentTradePlan")
    with pytest.raises(ContractError):
        Money(currency="USD", amount=Decimal("-1"))


def test_unknown_reason_code_rejected() -> None:
    assert len(REASON_CODES) == 73
    assert "OK" in REASON_CODES
    assert "CONFLICT" in REASON_CODES
    assert all(code.isupper() and code.replace("_", "").isalpha() for code in REASON_CODES)
    assert require_reason_code("CONFLICT") == "CONFLICT"
    with pytest.raises(ContractError):
        require_reason_code("lowercase")
    decision = _decision(rejection_codes=["NOT_A_REASON"])
    with pytest.raises(ContractError) as excinfo:
        parse_record(decision, "ReasoningDecision")
    assert excinfo.value.code == "INVALID_SCHEMA"
    certificate = _certificate()
    certificate["reason_codes"] = ["OK", "MADE_UP"]
    with pytest.raises(ContractError):
        parse_record(certificate, "EvaluationCertificate")


def test_stop_side_valid_cases() -> None:
    assert stop_side_valid(Side.long, "1.1000", "1.0900") is True
    assert stop_side_valid(Side.long, "1.1000", "1.1100") is False
    assert stop_side_valid(Side.short, "158.0", "158.1") is True
    assert stop_side_valid(Side.short, "158.0", "157.9") is False
    assert stop_side_valid(Side.short, "158.0", "158.0") is False
    assert stop_side_valid(Side.long, "1.1", "1.1") is False
    assert stop_side_valid(Side.long, "not-a-price", "1.0") is False
    assert stop_side_valid(Side.long, "1.1", "Infinity") is False
    assert stop_side_valid(Side.long, "0", "0.5") is False


def test_parent_plan_two_children_share_one_parent() -> None:
    record = parse_record(_plan(), "ParentTradePlan")
    assert isinstance(record, ParentTradePlan)
    assert record.parent_id == PID
    assert len(record.child_specs) == 2
    first, second = record.child_specs
    assert {first.role, second.role} == {ChildRole.A, ChildRole.B}
    assert {first.lots, second.lots} == {Decimal("0.6"), Decimal("0.4")}
    assert sum(child.lots for child in record.child_specs) == Decimal("1.0")
    assert {child.child_id for child in record.child_specs} == {CHILD_A, CHILD_B}
    assert first.initial_tp is not None
    assert second.initial_tp is None


def test_parent_plan_rejects_invalid_splits() -> None:
    three_children = [
        _child("A", "0.4", CHILD_A, tp="157.9"),
        _child("B", "0.3", CHILD_B),
        _child("B", "0.3", CHILD_C),
    ]
    with pytest.raises(ContractError) as excinfo:
        parse_record(_plan(children=three_children), "ParentTradePlan")
    assert excinfo.value.code == "LOT_SPLIT_INVALID"

    duplicate_roles = [_child("A", "0.6", CHILD_A, tp="157.9"), _child("A", "0.4", CHILD_B)]
    with pytest.raises(ContractError):
        parse_record(_plan(children=duplicate_roles), "ParentTradePlan")

    duplicate_ids = [_child("A", "0.6", CHILD_A, tp="157.9"), _child("B", "0.4", CHILD_A)]
    with pytest.raises(ContractError):
        parse_record(_plan(children=duplicate_ids), "ParentTradePlan")

    b_with_tp = [
        _child("A", "0.6", CHILD_A, tp="157.9"),
        _child("B", "0.4", CHILD_B, tp="157.9"),
    ]
    with pytest.raises(ContractError):
        parse_record(_plan(children=b_with_tp), "ParentTradePlan")


def test_digest_stability_and_sensitivity() -> None:
    record = parse_record(_plan(), "ParentTradePlan")
    same = parse_record(_plan(), "ParentTradePlan")
    assert digest_record(record) == digest_record(same)
    assert len(digest_record(record)) == 64
    rewritten = _plan()
    rewritten["stop_price"] = "158.10"
    assert digest_record(parse_record(rewritten, "ParentTradePlan")) == digest_record(record)
    changed_payload = _plan()
    changed_payload["stop_price"] = "158.2"
    changed = parse_record(changed_payload, "ParentTradePlan")
    assert digest_record(record) != digest_record(changed)


@pytest.mark.parametrize(("kind", "builder"), KINDS)
def test_kind_of_matches_parsed_kind(
    kind: str, builder: Callable[[], dict[str, object]]
) -> None:
    record = parse_record(builder(), kind)
    assert kind_of(record) == kind
    assert isinstance(record, RECORD_TYPES[kind])
