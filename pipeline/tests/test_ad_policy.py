"""AD-T02 protected authority policy: strict loading, disabled defaults, verification.

Fixture manifests are dictionaries written into ``tmp_path``; the shipped
manifest at ``pipeline/config/desk/authority.v1.json`` is only ever read. The
suite covers the mandated fail-first matrix — config disagreement across all 14
mirrored limit fields, demo mode without provisioning (runtime state cannot
substitute manifest provisioning), forbidden pair, unknown primitive, malformed
hash, unpriced paid model, active mode without a graduation certificate — plus
the safe-default, secret-scan, size-limit and purity properties.
"""

import copy
import json
import re
from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.paper.config import LIMITS, RISK
from src.paper.contracts import ContractError, Mode
from src.paper.policy import (
    MAX_MANIFEST_BYTES,
    AuthorityLimits,
    RuntimeState,
    load_authority,
    verify_authority,
)

SHIPPED = Path(__file__).resolve().parents[1] / "config" / "desk" / "authority.v1.json"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
CERT_ID = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"
STAMP = "2026-10-18T00:00:00Z"
CREDENTIAL_RE = re.compile(
    r"\b(?:password|passwd|secret|token|bearer|credential|authorization|login)\b"
    r"|\bapi[_-]?key\b|\bprivate[_-]?key\b",
    re.IGNORECASE,
)


def _manifest() -> dict[str, object]:
    """Independent fixture mirroring the shipped manifest (never the real file)."""
    return {
        "authority_version": 1,
        "schema_version": "ad/1",
        "created_at": STAMP,
        "owner_directive_refs": [
            "owner-directive-2026-10-17-desk-pair-subset",
            "owner-directive-2026-10-17-risk-model-v2",
            "owner-decision-2026-10-18-autonomous-demo-desk",
            "owner-budget-policy-2026-10-18-autonomy-v1",
        ],
        "enabled_mode": "shadow",
        "account_identity_ref": "demo-account-alias-1",
        "pair_symbol_map": {"EURUSD": "EURUSDm", "USDJPY": "USDJPYm"},
        "limits": {
            "slot_risk_ceilings": ["0.05", "0.04", "0.03", "0.03"],
            "grade_multipliers": {"A+": "1.0", "A": "0.8", "B+": "0.6", "B": "0.45"},
            "min_effective_risk_pct": "0.01",
            "max_concurrent_positions": 4,
            "max_positions_per_pair": 2,
            "max_same_usd_sign_tickets": 2,
            "max_open_risk_pct": "0.15",
            "max_new_trades_per_day": 5,
            "daily_stop_pct": "0.10",
            "weekly_stop_pct": "0.25",
            "max_gross_leverage": "50",
            "account_currency": "USD",
            "day_boundary": "UTC",
            "week_boundary": "UTC_MONDAY",
        },
        "canary_risk_factor": "0.25",
        "session_policy_ref": "spec02-session-v1",
        "event_policy_ref": "spec02-event-blackout-v1",
        "weekend_policy_ref": "spec03-weekend-exit-v1",
        "allowed_primitive_versions": [
            "su1-v1", "su2-v1", "su3-v1", "su4-v1", "management-v1",
        ],
        "allowed_prompt_variables": [
            "alignment", "candidate_summary", "coverage", "grade", "pair", "regime", "side",
        ],
        "source_allowlist": [
            "mt5-bars", "mt5-tick", "mt5-instrument", "mt5-account",
            "calendar-authoritative", "headline-authoritative",
        ],
        "evaluator_policy_digest": None,
        "allowed_execution_build_digest": None,
        "strategy_certificate_id": None,
        "issuer_key_ref": "issuer-key-local-v1",
        "human_stop_marker_path": "data/desk/OWNER_STOP",
        "service_identity": "desk-control-plane-local",
        "journal_root": "data/desk",
        "budgets": {
            "max_provider_attempts_per_day": 60,
            "max_input_tokens": 8000,
            "max_output_tokens": 2000,
            "max_attempts_per_role": 2,
            "daily_monetary_cap_usd": "0",
            "tick_freshness_ref": "spec03-tick-freshness-v1",
            "bars_freshness_ref": "spec02-bar-freshness-v1",
            "calendar_freshness_ref": "spec02-calendar-freshness-v1",
        },
    }


def _nested(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    assert isinstance(value, dict)
    return value


def _write(tmp_path: Path, payload: dict[str, object], name: str = "authority.v1.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _load_error(tmp_path: Path, payload: dict[str, object]) -> ContractError:
    path = _write(tmp_path, payload)
    with pytest.raises(ContractError) as excinfo:
        load_authority(path)
    return excinfo.value


def _verify_error(tmp_path: Path, payload: dict[str, object]) -> ContractError:
    policy = load_authority(_write(tmp_path, payload))
    with pytest.raises(ContractError) as excinfo:
        verify_authority(policy, RuntimeState())
    return excinfo.value


def _provisioned_demo(mode: str) -> dict[str, object]:
    payload = copy.deepcopy(_manifest())
    payload["enabled_mode"] = mode
    payload["strategy_certificate_id"] = CERT_ID
    payload["evaluator_policy_digest"] = DIGEST_A
    payload["allowed_execution_build_digest"] = DIGEST_B
    return payload


def test_shipped_manifest_loads_shadow_defaults() -> None:
    policy = load_authority(SHIPPED)
    assert policy.authority_version == 1
    assert policy.schema_version == "ad/1"
    assert policy.created_at == datetime(2026, 10, 18, tzinfo=UTC)
    assert policy.enabled_mode is Mode.shadow
    assert policy.account_identity_ref == "demo-account-alias-1"
    assert dict(policy.pair_symbol_map) == {"EURUSD": "EURUSDm", "USDJPY": "USDJPYm"}
    assert policy.canary_risk_factor == Decimal("0.25")
    assert policy.limits.slot_risk_ceilings == tuple(
        Decimal(str(value)) for value in LIMITS.slot_risk_ceilings
    )
    assert dict(policy.limits.grade_multipliers) == {
        grade: Decimal(str(value)) for grade, value in LIMITS.grade_multipliers.items()
    }
    assert policy.limits.min_effective_risk_pct == Decimal(str(LIMITS.min_effective_risk_pct))
    assert policy.limits.max_concurrent_positions == LIMITS.max_concurrent_positions
    assert policy.limits.max_positions_per_pair == LIMITS.max_positions_per_pair
    assert policy.limits.max_same_usd_sign_tickets == LIMITS.max_same_usd_sign_tickets
    assert policy.limits.max_open_risk_pct == Decimal(str(LIMITS.max_open_risk_pct))
    assert policy.limits.max_new_trades_per_day == LIMITS.max_new_trades_per_day
    assert policy.limits.daily_stop_pct == Decimal(str(LIMITS.daily_stop_pct))
    assert policy.limits.weekly_stop_pct == Decimal(str(LIMITS.weekly_stop_pct))
    assert policy.limits.max_gross_leverage == Decimal(str(RISK.max_leverage))
    assert policy.limits.account_currency == "USD"
    assert policy.limits.day_boundary == "UTC"
    assert policy.limits.week_boundary == "UTC_MONDAY"
    assert isinstance(policy.limits.max_open_risk_pct, Decimal)
    assert policy.budgets.max_provider_attempts_per_day == 60
    assert policy.budgets.max_input_tokens == 8000
    assert policy.budgets.max_output_tokens == 2000
    assert policy.budgets.max_attempts_per_role == 2
    assert policy.budgets.daily_monetary_cap_usd == Decimal("0")
    assert policy.evaluator_policy_digest is None
    assert policy.allowed_execution_build_digest is None
    assert policy.strategy_certificate_id is None
    assert policy.issuer_key_ref == "issuer-key-local-v1"
    assert policy.human_stop_marker_path == "data/desk/OWNER_STOP"
    assert policy.service_identity == "desk-control-plane-local"
    assert policy.journal_root == "data/desk"
    assert set(policy.allowed_primitive_versions) == {
        "su1-v1", "su2-v1", "su3-v1", "su4-v1", "management-v1",
    }
    verify_authority(policy, RuntimeState())


def test_shipped_manifest_has_no_credentials() -> None:
    raw = SHIPPED.read_bytes().decode("utf-8")
    assert CREDENTIAL_RE.search(raw) is None
    assert re.search(r"\d{8,}", raw) is None


def test_config_disagreement_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["max_open_risk_pct"] = "0.16"
    assert _verify_error(tmp_path, payload).code == "AUTHORITY_MISMATCH"

    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["slot_risk_ceilings"] = ["0.05", "0.04", "0.03", "0.05"]
    assert _verify_error(tmp_path, payload).code == "AUTHORITY_MISMATCH"

    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["grade_multipliers"] = {"A+": "1.0", "A": "0.8", "B+": "0.6"}
    assert _verify_error(tmp_path, payload).code == "AUTHORITY_MISMATCH"

    payload = copy.deepcopy(_manifest())
    payload["limits"] = "limits"
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"


# AD spec 01 §2 mirrors exactly 14 owner-limit fields into AuthorityLimits.
# One parametrized case per field mutates that single JSON value; every case
# must fail verification with AUTHORITY_MISMATCH attributable to that field.
_LIMIT_DISAGREEMENTS: dict[str, object] = {
    "slot_risk_ceilings": ["0.05", "0.04", "0.03", "0.05"],
    "grade_multipliers": {"A+": "1.0", "A": "0.8", "B+": "0.6", "B": "0.5"},
    "min_effective_risk_pct": "0.02",
    "max_concurrent_positions": 3,
    "max_positions_per_pair": 1,
    "max_same_usd_sign_tickets": 1,
    "max_open_risk_pct": "0.16",
    "max_new_trades_per_day": 4,
    "daily_stop_pct": "0.11",
    "weekly_stop_pct": "0.26",
    "max_gross_leverage": "51",
    "account_currency": "EUR",
    "day_boundary": "UTC+1",
    "week_boundary": "UTC_SUNDAY",
}
_LIMITS_FIELDS: tuple[str, ...] = tuple(field.name for field in fields(AuthorityLimits))
assert len(_LIMITS_FIELDS) == 14, "spec 01 §2 mirrors exactly 14 owner-limit fields"
assert set(_LIMIT_DISAGREEMENTS) == set(_LIMITS_FIELDS), (
    "disagreement matrix must mutate every AuthorityLimits field"
)


@pytest.mark.parametrize("limit_field", _LIMITS_FIELDS)
def test_config_disagreement_matrix_all_limit_fields(tmp_path: Path, limit_field: str) -> None:
    payload = copy.deepcopy(_manifest())
    limits = _nested(payload, "limits")
    assert limits[limit_field] != _LIMIT_DISAGREEMENTS[limit_field]
    limits[limit_field] = _LIMIT_DISAGREEMENTS[limit_field]
    error = _verify_error(tmp_path, payload)
    assert error.code == "AUTHORITY_MISMATCH"
    assert f"authority.limits.{limit_field}" in error.detail


def test_demo_mode_not_provisioned(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    payload["enabled_mode"] = "demo_active"
    policy = load_authority(_write(tmp_path, payload))
    with pytest.raises(ContractError) as excinfo:
        verify_authority(policy, RuntimeState())
    assert excinfo.value.code == "CERTIFICATE_INVALID"

    with pytest.raises(ContractError) as excinfo:
        verify_authority(policy, RuntimeState(graduation_certificate_id=CERT_ID))
    assert excinfo.value.code == "CERTIFICATE_INVALID"

    provisioned = _provisioned_demo("demo_canary")
    canary = load_authority(_write(tmp_path, provisioned, "canary.json"))
    with pytest.raises(ContractError) as excinfo:
        verify_authority(canary, RuntimeState(graduation_certificate_id=CERT_ID))
    assert excinfo.value.code == "NON_DEMO_ACCOUNT"


def test_active_mode_without_graduation_certificate(tmp_path: Path) -> None:
    payload = _provisioned_demo("demo_active")
    policy = load_authority(_write(tmp_path, payload))
    runtime = RuntimeState(demo_account_verified=True)
    with pytest.raises(ContractError) as excinfo:
        verify_authority(policy, runtime)
    assert excinfo.value.code == "CERTIFICATE_INVALID"


def test_provisioned_demo_mode_verifies(tmp_path: Path) -> None:
    payload = _provisioned_demo("demo_active")
    policy = load_authority(_write(tmp_path, payload))
    runtime = RuntimeState(graduation_certificate_id=CERT_ID, demo_account_verified=True)
    verify_authority(policy, runtime)


def test_demo_mode_requires_manifest_provisioning(tmp_path: Path) -> None:
    # A fully provisioned runtime cannot substitute for manifest provisioning.
    payload = copy.deepcopy(_manifest())
    payload["enabled_mode"] = "demo_canary"
    payload["evaluator_policy_digest"] = DIGEST_A
    payload["allowed_execution_build_digest"] = DIGEST_B
    assert payload["strategy_certificate_id"] is None
    policy = load_authority(_write(tmp_path, payload))
    assert policy.strategy_certificate_id is None
    runtime = RuntimeState(graduation_certificate_id=CERT_ID, demo_account_verified=True)

    with pytest.raises(ContractError) as excinfo:
        verify_authority(policy, runtime)
    assert excinfo.value.code == "CERTIFICATE_INVALID"
    assert "strategy certificate" in excinfo.value.detail

    # Same runtime, manifest now provisioned: only the manifest permits demo.
    provisioned = load_authority(
        _write(tmp_path, _provisioned_demo("demo_canary"), "provisioned.json")
    )
    verify_authority(provisioned, runtime)


def test_forbidden_pair_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    payload["pair_symbol_map"] = {"EURUSD": "EURUSDm", "GBPUSD": "GBPUSDm"}
    assert _verify_error(tmp_path, payload).code == "UNSUPPORTED_PAIR"

    payload = copy.deepcopy(_manifest())
    payload["pair_symbol_map"] = {"USDJPY": "USDJPYm"}
    assert _verify_error(tmp_path, payload).code == "AUTHORITY_MISMATCH"


def test_unknown_primitive_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    payload["allowed_primitive_versions"] = [
        "su1-v1", "su2-v1", "su3-v1", "su4-v1", "management-v1", "su9-v9",
    ]
    assert _verify_error(tmp_path, payload).code == "AUTHORITY_MISMATCH"


def test_malformed_hash_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    payload["evaluator_policy_digest"] = "not-a-digest"
    assert _load_error(tmp_path, payload).code == "HASH_MISMATCH"

    payload = copy.deepcopy(_manifest())
    payload["allowed_execution_build_digest"] = DIGEST_A.upper()
    assert _load_error(tmp_path, payload).code == "HASH_MISMATCH"

    payload = copy.deepcopy(_manifest())
    payload["evaluator_policy_digest"] = 123
    assert _load_error(tmp_path, payload).code == "HASH_MISMATCH"

    payload = copy.deepcopy(_manifest())
    payload["evaluator_policy_digest"] = DIGEST_A
    policy = load_authority(_write(tmp_path, payload))
    assert policy.evaluator_policy_digest == DIGEST_A


def test_unpriced_paid_model_rejected(tmp_path: Path) -> None:
    policy = load_authority(_write(tmp_path, _manifest()))
    assert policy.budgets.daily_monetary_cap_usd == 0
    with pytest.raises(ContractError) as excinfo:
        verify_authority(policy, RuntimeState(paid_model_requested=True))
    assert excinfo.value.code == "BUDGET_EXHAUSTED"

    payload = copy.deepcopy(_manifest())
    _nested(payload, "budgets")["daily_monetary_cap_usd"] = "5"
    priced = load_authority(_write(tmp_path, payload, "priced.json"))
    verify_authority(priced, RuntimeState(paid_model_requested=True))


def test_unknown_manifest_field_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    payload["confidence"] = "92%"
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["max_pairs"] = 3
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    _nested(payload, "budgets")["max_attempts_per_job"] = 2
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"


def test_oversized_manifest_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    payload["account_identity_ref"] = "x" * (MAX_MANIFEST_BYTES + 1)
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"


def test_missing_or_null_required_fields_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    del payload["limits"]
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    del _nested(payload, "budgets")["max_output_tokens"]
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    payload["enabled_mode"] = None
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["max_open_risk_pct"] = None
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    # The provisioning-required fields are explicitly nullable in shadow.
    payload = copy.deepcopy(_manifest())
    del payload["evaluator_policy_digest"]
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"


def test_wrong_types_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["max_concurrent_positions"] = True
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    payload["canary_risk_factor"] = 0.25
    assert _load_error(tmp_path, payload).code == "INVALID_NUMBER"

    payload = copy.deepcopy(_manifest())
    payload["enabled_mode"] = "live"
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    payload["canary_risk_factor"] = "1.5"
    assert _load_error(tmp_path, payload).code == "INVALID_NUMBER"

    payload = copy.deepcopy(_manifest())
    payload["authority_version"] = 2
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"

    payload = copy.deepcopy(_manifest())
    payload["schema_version"] = "ad/2"
    assert _load_error(tmp_path, payload).code == "INVALID_SCHEMA"


def test_non_plain_decimal_rejected(tmp_path: Path) -> None:
    for literal in ("1e-2", ".25", "1.", "+1", "Infinity", "NaN", "-0.5"):
        payload = copy.deepcopy(_manifest())
        payload["canary_risk_factor"] = literal
        assert _load_error(tmp_path, payload).code == "INVALID_NUMBER"


def test_non_utf8_or_non_object_document_rejected(tmp_path: Path) -> None:
    path = tmp_path / "authority.v1.json"
    path.write_bytes(b"\xff\xfe{}")
    with pytest.raises(ContractError) as excinfo:
        load_authority(path)
    assert excinfo.value.code == "INVALID_SCHEMA"

    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ContractError) as excinfo:
        load_authority(path)
    assert excinfo.value.code == "INVALID_SCHEMA"

    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ContractError) as excinfo:
        load_authority(path)
    assert excinfo.value.code == "INVALID_SCHEMA"


def test_verify_is_pure_and_repeatable(tmp_path: Path) -> None:
    path = _write(tmp_path, _manifest())
    policy = load_authority(path)
    assert policy == load_authority(path)
    runtime = RuntimeState(paid_model_requested=False)

    def state() -> tuple[object, ...]:
        return (
            policy.enabled_mode,
            policy.limits.max_open_risk_pct,
            dict(policy.limits.grade_multipliers),
            dict(policy.pair_symbol_map),
            policy.allowed_primitive_versions,
        )

    before = state()
    verify_authority(policy, runtime)
    verify_authority(policy, runtime)
    assert state() == before

    payload = copy.deepcopy(_manifest())
    _nested(payload, "limits")["daily_stop_pct"] = "0.12"
    bad = load_authority(_write(tmp_path, payload, "bad.json"))
    codes: list[str] = []
    for _ in range(2):
        with pytest.raises(ContractError) as excinfo:
            verify_authority(bad, runtime)
        codes.append(excinfo.value.code)
    assert codes == ["AUTHORITY_MISMATCH", "AUTHORITY_MISMATCH"]


def test_runtime_state_safe_defaults() -> None:
    runtime = RuntimeState()
    assert runtime.graduation_certificate_id is None
    assert runtime.demo_account_verified is False
    assert runtime.paid_model_requested is False
    verify_authority(load_authority(SHIPPED), runtime)

    with pytest.raises(ContractError) as excinfo:
        RuntimeState(graduation_certificate_id="not-an-id")
    assert excinfo.value.code == "INVALID_SCHEMA"
