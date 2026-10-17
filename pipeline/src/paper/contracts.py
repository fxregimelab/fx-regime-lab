"""Strict AD transport contracts: typed records, wire parsing, canonical bytes.

This is the AD-T01 boundary layer: broker/model JSON is parsed at the edge into
frozen records, validated against spec 01 (unknown fields, unknown enums, wrong
schema versions, binary floats, naive datetimes and missing currency all fail),
then re-encoded to deterministic canonical bytes for hashing. Normalization
(timestamps to ``...Z``, decimals to plain canonical form) happens in
``canonical_bytes``. Records carry no self digest; ``digest_record`` hashes the
full canonical bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum, StrEnum
from functools import partial
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TypeVar

SCHEMA_VERSION = "ad/1"

_REASON_CODE_LIST: tuple[str, ...] = (
    "OK", "INVALID_SCHEMA", "INVALID_NUMBER", "UNSUPPORTED_PAIR", "ACCOUNT_MISMATCH",
    "NON_DEMO_ACCOUNT", "NETTING_UNSUPPORTED", "CLOCK_UNVERIFIED", "CLOCK_SKEW",
    "TICK_STALE", "BROKER_STATE_STALE", "SOURCE_INCOMPLETE", "SOURCE_STALE",
    "CALENDAR_UNKNOWN", "EVENT_BLACKOUT", "NEWS_UNVERIFIED", "SIGNAL_STALE",
    "MODEL_VERSION_MISMATCH", "BAR_INCOMPLETE", "BAR_GAP", "SNAPSHOT_NOT_AVAILABLE",
    "HASH_MISMATCH", "SPEC_UNACKNOWLEDGED", "UNKNOWN_ALIGNMENT", "OPPOSED_ALIGNMENT",
    "NO_CANDIDATE", "SETUP_INVALID", "RETEST_EXPIRED", "ENTRY_CHASE", "GRADE_INELIGIBLE",
    "CANARY_GRADE_INELIGIBLE", "RISK_FLOOR", "SLOT_RISK_CAP", "OPEN_RISK_CAP",
    "DAILY_LOSS_CAPACITY", "WEEKLY_LOSS_CAPACITY", "PAIR_CAP", "USD_EXPOSURE_CAP",
    "POSITION_CAP", "DAILY_TRADE_CAP", "LEVERAGE_CAP", "MARGIN_REJECTED", "LOT_SPLIT_INVALID",
    "STOP_INVALID", "STOP_NOT_PROTECTED", "OWNER_STOP", "OPERATOR_PAUSED", "INTEGRITY_LATCH",
    "JOURNAL_UNAVAILABLE", "AUTHORITY_MISMATCH", "NO_VALID_CHAMPION", "CERTIFICATE_INVALID",
    "CERTIFICATE_EXPIRED", "PERMIT_EXPIRED", "PERMIT_REPLAY", "FENCE_STALE", "ORDER_UNKNOWN",
    "UNOWNED_POSITION", "CASHFLOW_UNCLASSIFIED", "BUDGET_EXHAUSTED", "MODEL_UNAVAILABLE",
    "UNSUPPORTED_CLAIM", "DEADLINE_EXCEEDED", "TRIAL_BUDGET_EXHAUSTED", "HOLDOUT_LEAKAGE",
    "INSUFFICIENT_DATA", "INSUFFICIENT_PRECISION", "SUPERIORITY_NOT_PROVEN", "STRESS_FAILED",
    "DRIFT_SHUTDOWN", "STALE_STATE", "CAPACITY_EXHAUSTED", "CONFLICT",
)

REASON_CODES: frozenset[str] = frozenset(_REASON_CODE_LIST)


class ContractError(ValueError):
    """Typed transport error carrying a stable uppercase reason code."""

    def __init__(self, code: str, detail: str) -> None:
        if code not in REASON_CODES:
            raise ValueError(f"unknown reason code for ContractError: {code!r}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def require_reason_code(code: str) -> str:
    """Return the reason code when it belongs to the frozen vocabulary, else fail."""
    if type(code) is not str or code not in REASON_CODES:
        raise ContractError("INVALID_SCHEMA", f"unknown reason code {code!r}")
    return code


class _WireEnum(StrEnum):
    """Str-based enum whose unknown values are a typed schema error, not a guess."""

    @classmethod
    def _missing_(cls, value: object) -> None:
        raise ContractError("INVALID_SCHEMA", f"{cls.__name__}: unknown value {value!r}")


class Pair(_WireEnum):
    EURUSD = "EURUSD"
    USDJPY = "USDJPY"


class Side(_WireEnum):
    long = "long"
    short = "short"


class Coverage(_WireEnum):
    verified = "verified"
    incomplete = "incomplete"
    stale = "stale"
    unavailable = "unavailable"


class Alignment(_WireEnum):
    aligned = "aligned"
    neutral = "neutral"
    opposed = "opposed"
    unknown = "unknown"


class Mode(_WireEnum):
    shadow = "shadow"
    demo_canary = "demo_canary"
    demo_active = "demo_active"
    paused = "paused"


class SnapshotKind(_WireEnum):
    bars = "bars"
    tick = "tick"
    instrument = "instrument"
    account = "account"
    calendar = "calendar"
    headline = "headline"
    signal = "signal"
    features = "features"
    spec = "spec"


class Verdict(_WireEnum):
    propose = "propose"
    wait = "wait"
    reject = "reject"


class ChildRole(_WireEnum):
    A = "A"
    B = "B"


class CertificateVerdict(_WireEnum):
    PASS = "PASS"
    REJECT = "REJECT"
    COLLECTING = "COLLECTING"
    INVALID = "INVALID"


T = TypeVar("T")
E = TypeVar("E", bound=Enum)

_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z")
_DECIMAL_RE = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")
_ZERO_OFFSET = timedelta(0)


def _text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string required")
    return value


def _digest(name: str, value: object) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: lowercase sha256 hex required")
    return value


def _uuid(name: str, value: object) -> str:
    if type(value) is not str or _UUID_RE.fullmatch(value) is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: lowercase UUID string required")
    return value


def _id(name: str, value: object) -> str:
    if type(value) is str and (
        _UUID_RE.fullmatch(value) is not None or _DIGEST_RE.fullmatch(value) is not None
    ):
        return value
    raise ContractError("INVALID_SCHEMA", f"{name}: UUID or content-addressed id required")


def _timestamp(name: str, value: object) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: timezone-aware datetime required")
    if value.utcoffset() != _ZERO_OFFSET:
        raise ContractError("INVALID_SCHEMA", f"{name}: only UTC datetimes are accepted")
    return value


def _decimal(name: str, value: object) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ContractError("INVALID_NUMBER", f"{name}: finite decimal required")
    return value


def _positive(name: str, value: object) -> Decimal:
    amount = _decimal(name, value)
    if amount <= 0:
        raise ContractError("INVALID_NUMBER", f"{name}: positive decimal required")
    return amount


def _amount(name: str, value: object) -> Decimal:
    amount = _decimal(name, value)
    if amount < 0:
        raise ContractError("INVALID_NUMBER", f"{name}: non-negative decimal required")
    return amount


def _count(name: str, value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ContractError("INVALID_SCHEMA", f"{name}: integer >= {minimum} required")
    return value


def _flag(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise ContractError("INVALID_SCHEMA", f"{name}: strict boolean required")
    return value


def _member(name: str, value: object, enum_cls: type[E]) -> E:
    if not isinstance(value, enum_cls):
        raise ContractError("INVALID_SCHEMA", f"{name}: {enum_cls.__name__} member required")
    return value


def _member_opt(name: str, value: object | None, enum_cls: type[E]) -> E | None:
    if value is None:
        return None
    return _member(name, value, enum_cls)


def _require_money(name: str, value: object) -> Money:
    if not isinstance(value, Money):
        raise ContractError("INVALID_SCHEMA", f"{name}: USD Money required")
    return value


def _schema(value: object) -> str:
    if value != SCHEMA_VERSION:
        raise ContractError("INVALID_SCHEMA", f"schema_version must be exactly {SCHEMA_VERSION!r}")
    return SCHEMA_VERSION


def _items(
    name: str,
    value: object,
    convert: Callable[[str, object], str],
    *,
    minimum: int = 1,
    unique: bool = True,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ContractError("INVALID_SCHEMA", f"{name}: tuple required")
    items = [convert(f"{name}[]", item) for item in value]
    if len(items) < minimum:
        raise ContractError("INVALID_SCHEMA", f"{name}: at least {minimum} item(s) required")
    if unique and len(set(items)) != len(items):
        raise ContractError("INVALID_SCHEMA", f"{name}: duplicate values are not allowed")
    return tuple(items)


def _fact_ref(name: str, value: object) -> str:
    if type(value) is not str or value.count("#/") != 1:
        raise ContractError("INVALID_SCHEMA", f"{name}: 'snapshot_id#/field' reference required")
    source, _, pointer = value.partition("#/")
    _id(f"{name}.source", source)
    if not pointer.strip() or "#" in pointer:
        raise ContractError("INVALID_SCHEMA", f"{name}: non-empty field pointer required")
    return value


def _reason_item(name: str, value: object) -> str:
    if type(value) is not str:
        raise ContractError("INVALID_SCHEMA", f"{name}: reason code string required")
    return require_reason_code(value)


def _relative_path(name: str, value: object) -> str:
    text = _text(name, value)
    if text.startswith(("/", "\\")) or "\\" in text or ":" in text:
        raise ContractError("INVALID_SCHEMA", f"{name}: relative POSIX path required")
    segments = PurePosixPath(text).parts
    if any(segment in ("..", ".") for segment in segments):
        raise ContractError("INVALID_SCHEMA", f"{name}: '..' segments are not allowed")
    return text


def _text_map(name: str, value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{name}: mapping required")
    result: dict[str, str] = {}
    for key, item in value.items():
        if type(key) is not str or not key.strip():
            raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string keys required")
        result[key] = _text(f"{name}.{key}", item)
    if not result:
        raise ContractError("INVALID_SCHEMA", f"{name}: at least one entry required")
    return result


def _decimal_map(name: str, value: object) -> Mapping[str, Decimal]:
    if not isinstance(value, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{name}: mapping required")
    result: dict[str, Decimal] = {}
    for key, item in value.items():
        if type(key) is not str or not key.strip():
            raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string keys required")
        result[key] = _decimal(f"{name}.{key}", item)
    if not result:
        raise ContractError("INVALID_SCHEMA", f"{name}: at least one entry required")
    return result


def _freeze_text_map(record: object, name: str, value: object) -> None:
    frozen = _text_map(name, value)
    object.__setattr__(record, name, MappingProxyType(dict(frozen)))


def _freeze_decimal_map(record: object, name: str, value: object) -> None:
    frozen = _decimal_map(name, value)
    object.__setattr__(record, name, MappingProxyType(dict(frozen)))


def _format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _format_timestamp(value: datetime) -> str:
    if value.microsecond:
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    return value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


@dataclass(frozen=True)
class Money:
    """A currency amount that is an exact decimal string on the wire."""

    currency: str
    amount: Decimal

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise ContractError("INVALID_SCHEMA", "Money.currency: only USD is accepted")
        _amount("Money.amount", self.amount)


@dataclass(frozen=True)
class ChildSpec:
    """One scale-out child of a parent plan; exactly one A and one B per plan."""

    child_id: str
    role: ChildRole
    lots: Decimal
    initial_sl: Decimal
    initial_tp: Decimal | None = None

    def __post_init__(self) -> None:
        _uuid("ChildSpec.child_id", self.child_id)
        _member("ChildSpec.role", self.role, ChildRole)
        _positive("ChildSpec.lots", self.lots)
        _positive("ChildSpec.initial_sl", self.initial_sl)
        if self.initial_tp is not None:
            _positive("ChildSpec.initial_tp", self.initial_tp)


@dataclass(frozen=True)
class Claim:
    """A reasoning claim grounded in snapshot fields or derived metric references."""

    claim_id: str
    text: str
    fact_refs: tuple[str, ...]
    derived_metric_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _uuid("Claim.claim_id", self.claim_id)
        _text("Claim.text", self.text)
        facts = _items("Claim.fact_refs", self.fact_refs, _fact_ref, minimum=0, unique=False)
        metrics = _items(
            "Claim.derived_metric_refs", self.derived_metric_refs, _text, minimum=0, unique=False
        )
        if not facts and not metrics:
            raise ContractError(
                "INVALID_SCHEMA", "Claim: at least one fact or metric reference required"
            )


@dataclass(frozen=True)
class OperatorIdentity:
    """Who produced a reasoning artifact; unreported revision stays unknown."""

    provider: str
    responding_model: str
    prompt_digest: str
    toolset_digest: str
    renderer_version: str
    fallback_used: bool
    model_revision: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text("OperatorIdentity.provider", self.provider)
        _text("OperatorIdentity.responding_model", self.responding_model)
        _digest("OperatorIdentity.prompt_digest", self.prompt_digest)
        _digest("OperatorIdentity.toolset_digest", self.toolset_digest)
        _text("OperatorIdentity.renderer_version", self.renderer_version)
        _flag("OperatorIdentity.fallback_used", self.fallback_used)
        if self.model_revision is not None:
            _text("OperatorIdentity.model_revision", self.model_revision)
        _schema(self.schema_version)


@dataclass(frozen=True)
class SnapshotManifest:
    """Committed archive manifest; content must exist before this row is parsed."""

    snapshot_id: str
    kind: SnapshotKind
    source_id: str
    fetched_at: datetime
    available_at: datetime
    valid_from: datetime
    expires_at: datetime
    coverage: Coverage
    content_digest: str
    content_relative_path: str
    clock_profile_digest: str
    collector_version: str
    licensing_class: str
    pair: Pair | None = None
    published_at: datetime | None = None
    revision_of: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _id("SnapshotManifest.snapshot_id", self.snapshot_id)
        _member("SnapshotManifest.kind", self.kind, SnapshotKind)
        _text("SnapshotManifest.source_id", self.source_id)
        _timestamp("SnapshotManifest.fetched_at", self.fetched_at)
        _timestamp("SnapshotManifest.available_at", self.available_at)
        _timestamp("SnapshotManifest.valid_from", self.valid_from)
        _timestamp("SnapshotManifest.expires_at", self.expires_at)
        _member("SnapshotManifest.coverage", self.coverage, Coverage)
        _digest("SnapshotManifest.content_digest", self.content_digest)
        _relative_path("SnapshotManifest.content_relative_path", self.content_relative_path)
        _digest("SnapshotManifest.clock_profile_digest", self.clock_profile_digest)
        _text("SnapshotManifest.collector_version", self.collector_version)
        _text("SnapshotManifest.licensing_class", self.licensing_class)
        _member_opt("SnapshotManifest.pair", self.pair, Pair)
        if self.published_at is not None:
            _timestamp("SnapshotManifest.published_at", self.published_at)
        if self.revision_of is not None:
            _id("SnapshotManifest.revision_of", self.revision_of)
        _schema(self.schema_version)


@dataclass(frozen=True)
class Candidate:
    """A deterministic setup trigger; no model output may originate this record."""

    candidate_id: str
    created_at: datetime
    decision_at: datetime
    pair: Pair
    side: Side
    setup_id: str
    setup_version: int
    artifact_digest: str
    feature_snapshot_id: str
    source_snapshot_ids: tuple[str, ...]
    source_cohort: str
    regime: str
    proposed_entry: Decimal
    invalidation_price: Decimal
    expires_at: datetime
    deterministic_trigger_ids: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _uuid("Candidate.candidate_id", self.candidate_id)
        _timestamp("Candidate.created_at", self.created_at)
        _timestamp("Candidate.decision_at", self.decision_at)
        _member("Candidate.pair", self.pair, Pair)
        _member("Candidate.side", self.side, Side)
        _text("Candidate.setup_id", self.setup_id)
        _count("Candidate.setup_version", self.setup_version)
        _digest("Candidate.artifact_digest", self.artifact_digest)
        _id("Candidate.feature_snapshot_id", self.feature_snapshot_id)
        _items("Candidate.source_snapshot_ids", self.source_snapshot_ids, _id)
        _text("Candidate.source_cohort", self.source_cohort)
        _text("Candidate.regime", self.regime)
        _positive("Candidate.proposed_entry", self.proposed_entry)
        _positive("Candidate.invalidation_price", self.invalidation_price)
        _timestamp("Candidate.expires_at", self.expires_at)
        _items("Candidate.deterministic_trigger_ids", self.deterministic_trigger_ids, _text)
        _schema(self.schema_version)


@dataclass(frozen=True)
class ReasoningDecision:
    """Bounded reasoning result; claims must cite snapshots or derived metrics."""

    decision_id: str
    candidate_id: str
    decision_at: datetime
    verdict: Verdict
    supported_claims: tuple[Claim, ...]
    bull_case: str
    bear_case: str
    wait_case: str
    falsifiers: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    spec_bundle_digest: str
    operator_identity: OperatorIdentity
    latency_ms: int
    budget_receipt_id: str
    rejection_codes: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _uuid("ReasoningDecision.decision_id", self.decision_id)
        _uuid("ReasoningDecision.candidate_id", self.candidate_id)
        _timestamp("ReasoningDecision.decision_at", self.decision_at)
        _member("ReasoningDecision.verdict", self.verdict, Verdict)
        if type(self.supported_claims) is not tuple or not all(
            isinstance(claim, Claim) for claim in self.supported_claims
        ):
            raise ContractError(
                "INVALID_SCHEMA", "ReasoningDecision.supported_claims: tuple of Claim required"
            )
        _text("ReasoningDecision.bull_case", self.bull_case)
        _text("ReasoningDecision.bear_case", self.bear_case)
        _text("ReasoningDecision.wait_case", self.wait_case)
        _items("ReasoningDecision.falsifiers", self.falsifiers, _text, unique=False)
        _items("ReasoningDecision.evidence_ids", self.evidence_ids, _id)
        _digest("ReasoningDecision.spec_bundle_digest", self.spec_bundle_digest)
        if not isinstance(self.operator_identity, OperatorIdentity):
            raise ContractError(
                "INVALID_SCHEMA", "ReasoningDecision.operator_identity: OperatorIdentity required"
            )
        _count("ReasoningDecision.latency_ms", self.latency_ms)
        _uuid("ReasoningDecision.budget_receipt_id", self.budget_receipt_id)
        _items(
            "ReasoningDecision.rejection_codes",
            self.rejection_codes,
            _reason_item,
            minimum=0,
        )
        _schema(self.schema_version)


@dataclass(frozen=True)
class ParentTradePlan:
    """One thesis owns one immutable parent plan with exactly two initial children."""

    parent_id: str
    candidate_id: str
    decision_id: str
    pair: Pair
    side: Side
    artifact_digest: str
    management_policy_digest: str
    signal_model_version: str
    source_cohort: str
    entry_snapshot_id: str
    stop_price: Decimal
    target_a_price: Decimal
    requested_risk_fraction: Decimal
    immutable_initial_risk_usd: Money
    initial_stop_distance: Decimal
    child_specs: tuple[ChildSpec, ...]
    expiry_at: datetime
    falsifiers: tuple[str, ...]
    grade: str
    operator_identity: OperatorIdentity
    spec_bundle_digest: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _uuid("ParentTradePlan.parent_id", self.parent_id)
        _uuid("ParentTradePlan.candidate_id", self.candidate_id)
        _uuid("ParentTradePlan.decision_id", self.decision_id)
        _member("ParentTradePlan.pair", self.pair, Pair)
        _member("ParentTradePlan.side", self.side, Side)
        _digest("ParentTradePlan.artifact_digest", self.artifact_digest)
        _digest("ParentTradePlan.management_policy_digest", self.management_policy_digest)
        _text("ParentTradePlan.signal_model_version", self.signal_model_version)
        _text("ParentTradePlan.source_cohort", self.source_cohort)
        _id("ParentTradePlan.entry_snapshot_id", self.entry_snapshot_id)
        _positive("ParentTradePlan.stop_price", self.stop_price)
        _positive("ParentTradePlan.target_a_price", self.target_a_price)
        _positive("ParentTradePlan.requested_risk_fraction", self.requested_risk_fraction)
        _require_money(
            "ParentTradePlan.immutable_initial_risk_usd", self.immutable_initial_risk_usd
        )
        _positive("ParentTradePlan.initial_stop_distance", self.initial_stop_distance)
        if type(self.child_specs) is not tuple or not all(
            isinstance(child, ChildSpec) for child in self.child_specs
        ):
            raise ContractError(
                "INVALID_SCHEMA", "ParentTradePlan.child_specs: tuple of ChildSpec required"
            )
        if len(self.child_specs) != 2:
            raise ContractError(
                "LOT_SPLIT_INVALID",
                "ParentTradePlan.child_specs: exactly two initial children required",
            )
        if sorted(child.role.value for child in self.child_specs) != ["A", "B"]:
            raise ContractError(
                "LOT_SPLIT_INVALID", "ParentTradePlan.child_specs: one A and one B role required"
            )
        if len({child.child_id for child in self.child_specs}) != 2:
            raise ContractError(
                "LOT_SPLIT_INVALID", "ParentTradePlan.child_specs: child ids must be unique"
            )
        if any(
            child.role is ChildRole.B and child.initial_tp is not None
            for child in self.child_specs
        ):
            raise ContractError(
                "LOT_SPLIT_INVALID", "ParentTradePlan.child_specs: child B must not carry a TP"
            )
        _timestamp("ParentTradePlan.expiry_at", self.expiry_at)
        _items("ParentTradePlan.falsifiers", self.falsifiers, _text, unique=False)
        _text("ParentTradePlan.grade", self.grade)
        if not isinstance(self.operator_identity, OperatorIdentity):
            raise ContractError(
                "INVALID_SCHEMA", "ParentTradePlan.operator_identity: OperatorIdentity required"
            )
        _digest("ParentTradePlan.spec_bundle_digest", self.spec_bundle_digest)
        _schema(self.schema_version)


@dataclass(frozen=True)
class RiskBreakdown:
    """All-in risk buckets; proposed all-in is stop plus proposed future cost."""

    open_residual_stop_usd: Money
    pending_all_in_usd: Money
    proposed_stop_usd: Money
    open_future_cost_usd: Money
    proposed_future_cost_usd: Money
    proposed_all_in_usd: Money
    slot_budget_usd: Money
    immutable_initial_risk_usd: Money
    valuation_snapshot_ids: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        money_fields = (
            self.open_residual_stop_usd,
            self.pending_all_in_usd,
            self.proposed_stop_usd,
            self.open_future_cost_usd,
            self.proposed_future_cost_usd,
            self.proposed_all_in_usd,
            self.slot_budget_usd,
            self.immutable_initial_risk_usd,
        )
        if not all(isinstance(field, Money) for field in money_fields):
            raise ContractError(
                "INVALID_SCHEMA", "RiskBreakdown: USD Money required for every amount"
            )
        if self.proposed_all_in_usd.amount != (
            self.proposed_stop_usd.amount + self.proposed_future_cost_usd.amount
        ):
            raise ContractError(
                "INVALID_NUMBER",
                "RiskBreakdown: proposed all-in must equal proposed stop plus proposed future cost",
            )
        _items("RiskBreakdown.valuation_snapshot_ids", self.valuation_snapshot_ids, _id)
        _schema(self.schema_version)


@dataclass(frozen=True)
class ExecutionPermit:
    """Single-use local permit; a plain file hash is not a trade permit."""

    permit_id: str
    parent_id: str
    plan_digest: str
    authority_digest: str
    evaluator_certificate_id: str
    broker_state_digest: str
    reservation_id: str
    issued_at: datetime
    expires_at: datetime
    allowed_operations: tuple[str, ...]
    max_child_volume: Decimal
    consumed_sequence: int
    issuer_key_id: str
    signature: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _uuid("ExecutionPermit.permit_id", self.permit_id)
        _uuid("ExecutionPermit.parent_id", self.parent_id)
        _digest("ExecutionPermit.plan_digest", self.plan_digest)
        _digest("ExecutionPermit.authority_digest", self.authority_digest)
        _id("ExecutionPermit.evaluator_certificate_id", self.evaluator_certificate_id)
        _digest("ExecutionPermit.broker_state_digest", self.broker_state_digest)
        _uuid("ExecutionPermit.reservation_id", self.reservation_id)
        _timestamp("ExecutionPermit.issued_at", self.issued_at)
        _timestamp("ExecutionPermit.expires_at", self.expires_at)
        if not self.expires_at > self.issued_at:
            raise ContractError(
                "INVALID_SCHEMA", "ExecutionPermit: expires_at must follow issued_at"
            )
        _items("ExecutionPermit.allowed_operations", self.allowed_operations, _text)
        _positive("ExecutionPermit.max_child_volume", self.max_child_volume)
        _count("ExecutionPermit.consumed_sequence", self.consumed_sequence)
        _text("ExecutionPermit.issuer_key_id", self.issuer_key_id)
        _text("ExecutionPermit.signature", self.signature)
        _schema(self.schema_version)


@dataclass(frozen=True)
class Experiment:
    """Immutable trial registration; changed fields are declared before data."""

    hypothesis: str
    parent_artifact_digest: str
    changed_fields: tuple[str, ...]
    registered_at: datetime
    epoch_id: str
    trial_id: str
    input_cohort: str
    training_partition_ids: tuple[str, ...]
    validation_partition_ids: tuple[str, ...]
    holdout_partition_ids: tuple[str, ...]
    metric_definitions: Mapping[str, str]
    cost_model: str
    random_seed: int
    stop_rule: str
    trial_budget: int
    invalidation_rule: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text("Experiment.hypothesis", self.hypothesis)
        _digest("Experiment.parent_artifact_digest", self.parent_artifact_digest)
        _items("Experiment.changed_fields", self.changed_fields, _text)
        _timestamp("Experiment.registered_at", self.registered_at)
        _uuid("Experiment.epoch_id", self.epoch_id)
        _uuid("Experiment.trial_id", self.trial_id)
        _text("Experiment.input_cohort", self.input_cohort)
        training = _items("Experiment.training_partition_ids", self.training_partition_ids, _id)
        validation = _items(
            "Experiment.validation_partition_ids", self.validation_partition_ids, _id
        )
        holdout = _items("Experiment.holdout_partition_ids", self.holdout_partition_ids, _id)
        overlaps = (
            set(training) & set(validation)
            or set(training) & set(holdout)
            or set(validation) & set(holdout)
        )
        if overlaps:
            raise ContractError(
                "INVALID_SCHEMA",
                "Experiment: training/validation/holdout partitions must not overlap",
            )
        _freeze_text_map(self, "metric_definitions", self.metric_definitions)
        _text("Experiment.cost_model", self.cost_model)
        _count("Experiment.random_seed", self.random_seed)
        _text("Experiment.stop_rule", self.stop_rule)
        _count("Experiment.trial_budget", self.trial_budget, minimum=1)
        _text("Experiment.invalidation_rule", self.invalidation_rule)
        _schema(self.schema_version)


@dataclass(frozen=True)
class EvaluationCertificate:
    """Deterministic evaluation outcome; no LLM-written PASS is consumable."""

    artifact_digest: str
    experiment_id: str
    input_digests: tuple[str, ...]
    evaluator_build_digest: str
    evaluator_policy_digest: str
    evaluation_cutoff: datetime
    sample_count: int
    block_count: int
    metrics: Mapping[str, Decimal]
    verdict: CertificateVerdict
    reason_codes: tuple[str, ...]
    expires_at: datetime
    issuer_identity: str
    issuer_signature: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _digest("EvaluationCertificate.artifact_digest", self.artifact_digest)
        _uuid("EvaluationCertificate.experiment_id", self.experiment_id)
        _items("EvaluationCertificate.input_digests", self.input_digests, _digest)
        _digest("EvaluationCertificate.evaluator_build_digest", self.evaluator_build_digest)
        _digest("EvaluationCertificate.evaluator_policy_digest", self.evaluator_policy_digest)
        _timestamp("EvaluationCertificate.evaluation_cutoff", self.evaluation_cutoff)
        _count("EvaluationCertificate.sample_count", self.sample_count)
        _count("EvaluationCertificate.block_count", self.block_count)
        _freeze_decimal_map(self, "metrics", self.metrics)
        _member("EvaluationCertificate.verdict", self.verdict, CertificateVerdict)
        _items("EvaluationCertificate.reason_codes", self.reason_codes, _reason_item, minimum=0)
        _timestamp("EvaluationCertificate.expires_at", self.expires_at)
        _text("EvaluationCertificate.issuer_identity", self.issuer_identity)
        _text("EvaluationCertificate.issuer_signature", self.issuer_signature)
        _schema(self.schema_version)


AdRecord = (
    SnapshotManifest
    | Candidate
    | ReasoningDecision
    | OperatorIdentity
    | ParentTradePlan
    | ChildSpec
    | RiskBreakdown
    | ExecutionPermit
    | Experiment
    | EvaluationCertificate
    | Claim
)


def _scan_wire(value: object, path: str) -> None:
    if value is None or type(value) is bool or type(value) is str:
        return
    if type(value) is int:
        return
    if type(value) is float:
        raise ContractError("INVALID_NUMBER", f"{path}: binary floats are not allowed on the wire")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise ContractError("INVALID_SCHEMA", f"{path}: mapping keys must be strings")
            _scan_wire(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_wire(item, f"{path}[{index}]")
        return
    raise ContractError("INVALID_SCHEMA", f"{path}: unsupported wire value {type(value).__name__}")


def _check_keys(kind: str, payload: Mapping[str, object], allowed: Set[str]) -> None:
    unknown = [key for key in payload if key not in allowed]
    if unknown:
        raise ContractError("INVALID_SCHEMA", f"{kind}: unknown fields {sorted(unknown)!r}")


def _required(kind: str, payload: Mapping[str, object], key: str) -> object:
    if key not in payload:
        raise ContractError("INVALID_SCHEMA", f"{kind}.{key}: missing required field")
    value = payload[key]
    if value is None:
        raise ContractError("INVALID_SCHEMA", f"{kind}.{key}: null required field")
    return value


def _read(
    kind: str, payload: Mapping[str, object], key: str, convert: Callable[[object], T]
) -> T:
    raw = _required(kind, payload, key)
    try:
        return convert(raw)
    except ContractError as error:
        raise ContractError(error.code, f"{kind}.{key}: {error.detail}") from None


def _read_opt(
    kind: str, payload: Mapping[str, object], key: str, convert: Callable[[object], T]
) -> T | None:
    raw = payload.get(key)
    if raw is None:
        return None
    try:
        return convert(raw)
    except ContractError as error:
        raise ContractError(error.code, f"{kind}.{key}: {error.detail}") from None


def _as_text(raw: object) -> str:
    if type(raw) is not str or not raw.strip():
        raise ContractError("INVALID_SCHEMA", "non-empty string required")
    return raw


def _as_flag(raw: object) -> bool:
    if type(raw) is not bool:
        raise ContractError("INVALID_SCHEMA", "strict boolean required")
    return raw


def _as_int(raw: object) -> int:
    if type(raw) is not int:
        raise ContractError("INVALID_SCHEMA", "JSON integer required")
    return raw


def _as_decimal(raw: object) -> Decimal:
    if type(raw) is not str or _DECIMAL_RE.fullmatch(raw) is None:
        raise ContractError("INVALID_NUMBER", "plain decimal string required")
    value = Decimal(raw)
    if not value.is_finite():
        raise ContractError("INVALID_NUMBER", "finite decimal required")
    return value


def _as_timestamp(raw: object) -> datetime:
    if type(raw) is not str or _TIMESTAMP_RE.fullmatch(raw) is None:
        raise ContractError("INVALID_SCHEMA", "UTC ISO-8601 string ending 'Z' required")
    try:
        return datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError:
        raise ContractError("INVALID_SCHEMA", f"invalid timestamp {raw!r}") from None


def _enum_converter(enum_cls: type[E]) -> Callable[[object], E]:
    def convert(raw: object) -> E:
        if type(raw) is not str:
            raise ContractError("INVALID_SCHEMA", f"{enum_cls.__name__} string required")
        try:
            return enum_cls(raw)
        except ValueError:
            raise ContractError(
                "INVALID_SCHEMA", f"unknown {enum_cls.__name__} value {raw!r}"
            ) from None

    return convert


def _as_text_tuple(raw: object) -> tuple[str, ...]:
    if type(raw) is not list:
        raise ContractError("INVALID_SCHEMA", "JSON array required")
    items: list[str] = []
    for item in raw:
        if type(item) is not str:
            raise ContractError("INVALID_SCHEMA", "string items required")
        items.append(item)
    return tuple(items)


_as_pair = _enum_converter(Pair)
_as_side = _enum_converter(Side)
_as_coverage = _enum_converter(Coverage)
_as_snapshot_kind = _enum_converter(SnapshotKind)
_as_verdict = _enum_converter(Verdict)
_as_certificate_verdict = _enum_converter(CertificateVerdict)
_as_child_role = _enum_converter(ChildRole)


def _as_money(raw: object) -> Money:
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", "Money object required")
    _check_keys("Money", raw, frozenset(("currency", "amount")))
    read = partial(_read, "Money", raw)
    return Money(
        currency=read("currency", _as_text),
        amount=read("amount", _as_decimal),
    )


def _as_text_map(raw: object) -> Mapping[str, str]:
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", "JSON object required")
    result: dict[str, str] = {}
    for key, item in raw.items():
        if type(key) is not str:
            raise ContractError("INVALID_SCHEMA", "string keys required")
        result[key] = _as_text(item)
    return result


def _as_decimal_map(raw: object) -> Mapping[str, Decimal]:
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", "JSON object required")
    result: dict[str, Decimal] = {}
    for key, item in raw.items():
        if type(key) is not str:
            raise ContractError("INVALID_SCHEMA", "string keys required")
        result[key] = _as_decimal(item)
    return result


def _as_children(raw: object) -> tuple[ChildSpec, ...]:
    if type(raw) is not list:
        raise ContractError("INVALID_SCHEMA", "child_specs: JSON array required")
    children: list[ChildSpec] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ContractError("INVALID_SCHEMA", f"child_specs[{index}]: object required")
        children.append(_parse_child(item))
    return tuple(children)


def _as_claims(raw: object) -> tuple[Claim, ...]:
    if type(raw) is not list:
        raise ContractError("INVALID_SCHEMA", "supported_claims: JSON array required")
    claims: list[Claim] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ContractError("INVALID_SCHEMA", f"supported_claims[{index}]: object required")
        claims.append(_parse_claim(item))
    return tuple(claims)


def _as_operator(raw: object) -> OperatorIdentity:
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", "operator_identity: object required")
    return _parse_operator(raw)


def _parse_child(payload: Mapping[str, object]) -> ChildSpec:
    name = "ChildSpec"
    _check_keys(name, payload, {field.name for field in fields(ChildSpec)})
    read = partial(_read, name, payload)
    return ChildSpec(
        child_id=read("child_id", _as_text),
        role=read("role", _as_child_role),
        lots=read("lots", _as_decimal),
        initial_sl=read("initial_sl", _as_decimal),
        initial_tp=_read_opt(name, payload, "initial_tp", _as_decimal),
    )


def _parse_claim(payload: Mapping[str, object]) -> Claim:
    name = "Claim"
    _check_keys(name, payload, {field.name for field in fields(Claim)})
    read = partial(_read, name, payload)
    return Claim(
        claim_id=read("claim_id", _as_text),
        text=read("text", _as_text),
        fact_refs=read("fact_refs", _as_text_tuple),
        derived_metric_refs=read("derived_metric_refs", _as_text_tuple),
    )


def _parse_operator(payload: Mapping[str, object]) -> OperatorIdentity:
    name = "OperatorIdentity"
    _check_keys(name, payload, {field.name for field in fields(OperatorIdentity)})
    read = partial(_read, name, payload)
    return OperatorIdentity(
        provider=read("provider", _as_text),
        responding_model=read("responding_model", _as_text),
        model_revision=_read_opt(name, payload, "model_revision", _as_text),
        prompt_digest=read("prompt_digest", _as_text),
        toolset_digest=read("toolset_digest", _as_text),
        renderer_version=read("renderer_version", _as_text),
        fallback_used=read("fallback_used", _as_flag),
        schema_version=read("schema_version", _as_text),
    )


def _parse_snapshot_manifest(payload: Mapping[str, object]) -> SnapshotManifest:
    name = "SnapshotManifest"
    _check_keys(name, payload, {field.name for field in fields(SnapshotManifest)})
    read = partial(_read, name, payload)
    return SnapshotManifest(
        snapshot_id=read("snapshot_id", _as_text),
        kind=read("kind", _as_snapshot_kind),
        source_id=read("source_id", _as_text),
        fetched_at=read("fetched_at", _as_timestamp),
        available_at=read("available_at", _as_timestamp),
        valid_from=read("valid_from", _as_timestamp),
        expires_at=read("expires_at", _as_timestamp),
        coverage=read("coverage", _as_coverage),
        content_digest=read("content_digest", _as_text),
        content_relative_path=read("content_relative_path", _as_text),
        clock_profile_digest=read("clock_profile_digest", _as_text),
        collector_version=read("collector_version", _as_text),
        licensing_class=read("licensing_class", _as_text),
        pair=_read_opt(name, payload, "pair", _as_pair),
        published_at=_read_opt(name, payload, "published_at", _as_timestamp),
        revision_of=_read_opt(name, payload, "revision_of", _as_text),
        schema_version=read("schema_version", _as_text),
    )


def _parse_candidate(payload: Mapping[str, object]) -> Candidate:
    name = "Candidate"
    _check_keys(name, payload, {field.name for field in fields(Candidate)})
    read = partial(_read, name, payload)
    return Candidate(
        candidate_id=read("candidate_id", _as_text),
        created_at=read("created_at", _as_timestamp),
        decision_at=read("decision_at", _as_timestamp),
        pair=read("pair", _as_pair),
        side=read("side", _as_side),
        setup_id=read("setup_id", _as_text),
        setup_version=read("setup_version", _as_int),
        artifact_digest=read("artifact_digest", _as_text),
        feature_snapshot_id=read("feature_snapshot_id", _as_text),
        source_snapshot_ids=read("source_snapshot_ids", _as_text_tuple),
        source_cohort=read("source_cohort", _as_text),
        regime=read("regime", _as_text),
        proposed_entry=read("proposed_entry", _as_decimal),
        invalidation_price=read("invalidation_price", _as_decimal),
        expires_at=read("expires_at", _as_timestamp),
        deterministic_trigger_ids=read("deterministic_trigger_ids", _as_text_tuple),
        schema_version=read("schema_version", _as_text),
    )


def _parse_decision(payload: Mapping[str, object]) -> ReasoningDecision:
    name = "ReasoningDecision"
    _check_keys(name, payload, {field.name for field in fields(ReasoningDecision)})
    read = partial(_read, name, payload)
    return ReasoningDecision(
        decision_id=read("decision_id", _as_text),
        candidate_id=read("candidate_id", _as_text),
        decision_at=read("decision_at", _as_timestamp),
        verdict=read("verdict", _as_verdict),
        supported_claims=read("supported_claims", _as_claims),
        bull_case=read("bull_case", _as_text),
        bear_case=read("bear_case", _as_text),
        wait_case=read("wait_case", _as_text),
        falsifiers=read("falsifiers", _as_text_tuple),
        evidence_ids=read("evidence_ids", _as_text_tuple),
        spec_bundle_digest=read("spec_bundle_digest", _as_text),
        operator_identity=read("operator_identity", _as_operator),
        latency_ms=read("latency_ms", _as_int),
        budget_receipt_id=read("budget_receipt_id", _as_text),
        rejection_codes=read("rejection_codes", _as_text_tuple),
        schema_version=read("schema_version", _as_text),
    )


def _parse_plan(payload: Mapping[str, object]) -> ParentTradePlan:
    name = "ParentTradePlan"
    _check_keys(name, payload, {field.name for field in fields(ParentTradePlan)})
    read = partial(_read, name, payload)
    return ParentTradePlan(
        parent_id=read("parent_id", _as_text),
        candidate_id=read("candidate_id", _as_text),
        decision_id=read("decision_id", _as_text),
        pair=read("pair", _as_pair),
        side=read("side", _as_side),
        artifact_digest=read("artifact_digest", _as_text),
        management_policy_digest=read("management_policy_digest", _as_text),
        signal_model_version=read("signal_model_version", _as_text),
        source_cohort=read("source_cohort", _as_text),
        entry_snapshot_id=read("entry_snapshot_id", _as_text),
        stop_price=read("stop_price", _as_decimal),
        target_a_price=read("target_a_price", _as_decimal),
        requested_risk_fraction=read("requested_risk_fraction", _as_decimal),
        immutable_initial_risk_usd=read("immutable_initial_risk_usd", _as_money),
        initial_stop_distance=read("initial_stop_distance", _as_decimal),
        child_specs=read("child_specs", _as_children),
        expiry_at=read("expiry_at", _as_timestamp),
        falsifiers=read("falsifiers", _as_text_tuple),
        grade=read("grade", _as_text),
        operator_identity=read("operator_identity", _as_operator),
        spec_bundle_digest=read("spec_bundle_digest", _as_text),
        schema_version=read("schema_version", _as_text),
    )


def _parse_risk(payload: Mapping[str, object]) -> RiskBreakdown:
    name = "RiskBreakdown"
    _check_keys(name, payload, {field.name for field in fields(RiskBreakdown)})
    read = partial(_read, name, payload)
    return RiskBreakdown(
        open_residual_stop_usd=read("open_residual_stop_usd", _as_money),
        pending_all_in_usd=read("pending_all_in_usd", _as_money),
        proposed_stop_usd=read("proposed_stop_usd", _as_money),
        open_future_cost_usd=read("open_future_cost_usd", _as_money),
        proposed_future_cost_usd=read("proposed_future_cost_usd", _as_money),
        proposed_all_in_usd=read("proposed_all_in_usd", _as_money),
        slot_budget_usd=read("slot_budget_usd", _as_money),
        immutable_initial_risk_usd=read("immutable_initial_risk_usd", _as_money),
        valuation_snapshot_ids=read("valuation_snapshot_ids", _as_text_tuple),
        schema_version=read("schema_version", _as_text),
    )


def _parse_permit(payload: Mapping[str, object]) -> ExecutionPermit:
    name = "ExecutionPermit"
    _check_keys(name, payload, {field.name for field in fields(ExecutionPermit)})
    read = partial(_read, name, payload)
    return ExecutionPermit(
        permit_id=read("permit_id", _as_text),
        parent_id=read("parent_id", _as_text),
        plan_digest=read("plan_digest", _as_text),
        authority_digest=read("authority_digest", _as_text),
        evaluator_certificate_id=read("evaluator_certificate_id", _as_text),
        broker_state_digest=read("broker_state_digest", _as_text),
        reservation_id=read("reservation_id", _as_text),
        issued_at=read("issued_at", _as_timestamp),
        expires_at=read("expires_at", _as_timestamp),
        allowed_operations=read("allowed_operations", _as_text_tuple),
        max_child_volume=read("max_child_volume", _as_decimal),
        consumed_sequence=read("consumed_sequence", _as_int),
        issuer_key_id=read("issuer_key_id", _as_text),
        signature=read("signature", _as_text),
        schema_version=read("schema_version", _as_text),
    )


def _parse_experiment(payload: Mapping[str, object]) -> Experiment:
    name = "Experiment"
    _check_keys(name, payload, {field.name for field in fields(Experiment)})
    read = partial(_read, name, payload)
    return Experiment(
        hypothesis=read("hypothesis", _as_text),
        parent_artifact_digest=read("parent_artifact_digest", _as_text),
        changed_fields=read("changed_fields", _as_text_tuple),
        registered_at=read("registered_at", _as_timestamp),
        epoch_id=read("epoch_id", _as_text),
        trial_id=read("trial_id", _as_text),
        input_cohort=read("input_cohort", _as_text),
        training_partition_ids=read("training_partition_ids", _as_text_tuple),
        validation_partition_ids=read("validation_partition_ids", _as_text_tuple),
        holdout_partition_ids=read("holdout_partition_ids", _as_text_tuple),
        metric_definitions=read("metric_definitions", _as_text_map),
        cost_model=read("cost_model", _as_text),
        random_seed=read("random_seed", _as_int),
        stop_rule=read("stop_rule", _as_text),
        trial_budget=read("trial_budget", _as_int),
        invalidation_rule=read("invalidation_rule", _as_text),
        schema_version=read("schema_version", _as_text),
    )


def _parse_certificate(payload: Mapping[str, object]) -> EvaluationCertificate:
    name = "EvaluationCertificate"
    _check_keys(name, payload, {field.name for field in fields(EvaluationCertificate)})
    read = partial(_read, name, payload)
    return EvaluationCertificate(
        artifact_digest=read("artifact_digest", _as_text),
        experiment_id=read("experiment_id", _as_text),
        input_digests=read("input_digests", _as_text_tuple),
        evaluator_build_digest=read("evaluator_build_digest", _as_text),
        evaluator_policy_digest=read("evaluator_policy_digest", _as_text),
        evaluation_cutoff=read("evaluation_cutoff", _as_timestamp),
        sample_count=read("sample_count", _as_int),
        block_count=read("block_count", _as_int),
        metrics=read("metrics", _as_decimal_map),
        verdict=read("verdict", _as_certificate_verdict),
        reason_codes=read("reason_codes", _as_text_tuple),
        expires_at=read("expires_at", _as_timestamp),
        issuer_identity=read("issuer_identity", _as_text),
        issuer_signature=read("issuer_signature", _as_text),
        schema_version=read("schema_version", _as_text),
    )


_PARSERS: dict[str, Callable[[Mapping[str, object]], AdRecord]] = {
    "SnapshotManifest": _parse_snapshot_manifest,
    "Candidate": _parse_candidate,
    "ReasoningDecision": _parse_decision,
    "OperatorIdentity": _parse_operator,
    "ParentTradePlan": _parse_plan,
    "ChildSpec": _parse_child,
    "RiskBreakdown": _parse_risk,
    "ExecutionPermit": _parse_permit,
    "Experiment": _parse_experiment,
    "EvaluationCertificate": _parse_certificate,
    "Claim": _parse_claim,
}

_KIND_BY_TYPE: dict[type, str] = {
    SnapshotManifest: "SnapshotManifest",
    Candidate: "Candidate",
    ReasoningDecision: "ReasoningDecision",
    OperatorIdentity: "OperatorIdentity",
    ParentTradePlan: "ParentTradePlan",
    ChildSpec: "ChildSpec",
    RiskBreakdown: "RiskBreakdown",
    ExecutionPermit: "ExecutionPermit",
    Experiment: "Experiment",
    EvaluationCertificate: "EvaluationCertificate",
    Claim: "Claim",
}


def parse_record(payload: Mapping[str, object], kind: str) -> AdRecord:
    """Parse broker/model JSON into a strict frozen record; unknown data fails."""
    if not isinstance(payload, Mapping):
        raise ContractError("INVALID_SCHEMA", "payload must be a JSON object")
    parser = _PARSERS.get(kind)
    if parser is None:
        raise ContractError("INVALID_SCHEMA", f"unknown record kind {kind!r}")
    _scan_wire(payload, kind)
    return parser(payload)


def kind_of(record: AdRecord) -> str:
    """Return the transport kind name for a parsed record."""
    name = _KIND_BY_TYPE.get(type(record))
    if name is None:
        raise ContractError("INVALID_SCHEMA", f"unknown record type {type(record).__name__}")
    return name


def _wire_value(value: object) -> object:
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if isinstance(value, Decimal):
        return _format_decimal(value)
    if isinstance(value, datetime):
        return _format_timestamp(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_wire_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _wire_value(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _wire_value(getattr(value, field.name))
            for field in fields(value)
            if getattr(value, field.name) is not None
        }
    raise ContractError("INVALID_SCHEMA", f"unserializable value of type {type(value).__name__}")


def canonical_bytes(record: AdRecord) -> bytes:
    """Deterministic UTF-8 compact JSON: sorted keys, normalized Z/decimals, no floats."""
    document = _wire_value(record)
    text = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def digest_record(record: AdRecord) -> str:
    """Lowercase sha256 hex of the full canonical bytes; no self digest field exists."""
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def _maybe_decimal(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not value.is_finite():
        return None
    return value


def stop_side_valid(side: Side, entry: str, stop: str) -> bool:
    """long: stop below entry; short: stop above entry; equal/invalid is wrong side."""
    if not isinstance(side, Side):
        return False
    entry_value = _maybe_decimal(entry)
    stop_value = _maybe_decimal(stop)
    if entry_value is None or stop_value is None:
        return False
    if entry_value <= 0 or stop_value <= 0:
        return False
    if side is Side.long:
        return stop_value < entry_value
    return stop_value > entry_value
