"""AD-T02 protected authority manifest loader and startup verification.

Spec 01 §2: the authority manifest is owner-controlled, never proposed by an
LLM. This is the single loader/validator: strict JSON (unknown, missing or
wrong-typed fields fail), documents bounded to 256 KiB and UTF-8 only, wire
decimals parsed from plain strings to ``Decimal``, every failure a
``ContractError``.

Recorded contract decisions (AD-T02 packet):

- Present-but-invalid digests are ``HASH_MISMATCH``; ``null`` is legal only for
  the provisioning-required fields (evaluator/build digests, strategy
  certificate), which demo modes must have populated.
- ``verify_authority`` checks only presence/shape of the graduation certificate
  id; cryptographic verification is a later task.
- Unknown pair keys are ``UNSUPPORTED_PAIR``; a manifest no longer covering
  ``config.TRADING_PAIRS`` is ``AUTHORITY_MISMATCH``.
- ``canary_risk_factor`` is owner-tunable within ``(0, 1]``; the shipped 0.25
  default is asserted by tests, not re-pinned here.
- ``verify_authority`` is pure: no I/O, no environment reads, no mutation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import partial
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Never, TypeVar

from src.paper.config import LIMITS, RISK, TRADING_PAIRS
from src.paper.contracts import SCHEMA_VERSION, ContractError, Mode

AUTHORITY_VERSION = 1
MAX_MANIFEST_BYTES = 256 * 1024

KNOWN_PRIMITIVE_VERSIONS: frozenset[str] = frozenset(
    {"su1-v1", "su2-v1", "su3-v1", "su4-v1", "management-v1"}
)

_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z")
_DECIMAL_RE = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")

T = TypeVar("T")


@dataclass(frozen=True)
class AuthorityLimits:
    """Owner risk limits mirrored from ``src/paper/config.py`` as exact Decimals.

    ``account_currency``/``day_boundary``/``week_boundary`` are manifest-only
    fields pinned to the spec 01 §2 values at verification time.
    """

    slot_risk_ceilings: tuple[Decimal, ...]
    grade_multipliers: Mapping[str, Decimal]
    min_effective_risk_pct: Decimal
    max_concurrent_positions: int
    max_positions_per_pair: int
    max_same_usd_sign_tickets: int
    max_open_risk_pct: Decimal
    max_new_trades_per_day: int
    daily_stop_pct: Decimal
    weekly_stop_pct: Decimal
    max_gross_leverage: Decimal
    account_currency: str
    day_boundary: str
    week_boundary: str

    def __post_init__(self) -> None:
        frozen = MappingProxyType(dict(self.grade_multipliers))
        object.__setattr__(self, "grade_multipliers", frozen)


@dataclass(frozen=True)
class AuthorityBudgets:
    """Provider/token/monetary budgets plus runtime freshness policy refs."""

    max_provider_attempts_per_day: int
    max_input_tokens: int
    max_output_tokens: int
    max_attempts_per_role: int
    daily_monetary_cap_usd: Decimal
    tick_freshness_ref: str
    bars_freshness_ref: str
    calendar_freshness_ref: str


@dataclass(frozen=True)
class AuthorityPolicy:
    """Loaded authority manifest; construction goes through ``load_authority``."""

    authority_version: int
    schema_version: str
    created_at: datetime
    owner_directive_refs: tuple[str, ...]
    enabled_mode: Mode
    account_identity_ref: str
    pair_symbol_map: Mapping[str, str]
    limits: AuthorityLimits
    canary_risk_factor: Decimal
    session_policy_ref: str
    event_policy_ref: str
    weekend_policy_ref: str
    allowed_primitive_versions: tuple[str, ...]
    allowed_prompt_variables: tuple[str, ...]
    source_allowlist: tuple[str, ...]
    evaluator_policy_digest: str | None
    allowed_execution_build_digest: str | None
    strategy_certificate_id: str | None
    issuer_key_ref: str
    human_stop_marker_path: str
    service_identity: str
    journal_root: str
    budgets: AuthorityBudgets

    def __post_init__(self) -> None:
        frozen = MappingProxyType(dict(self.pair_symbol_map))
        object.__setattr__(self, "pair_symbol_map", frozen)


@dataclass(frozen=True)
class RuntimeState:
    """Provisioning facts known to the loader process; defaults never unlock demo."""

    graduation_certificate_id: str | None = None
    demo_account_verified: bool = False
    paid_model_requested: bool = False

    def __post_init__(self) -> None:
        flags = (self.demo_account_verified, self.paid_model_requested)
        if any(type(flag) is not bool for flag in flags):
            raise ContractError("INVALID_SCHEMA", "RuntimeState: strict boolean flags required")
        if self.graduation_certificate_id is not None:
            _as_id("RuntimeState.graduation_certificate_id", self.graduation_certificate_id)


# --- Low-level converters (name-qualified, fail-closed) -------------------------


def _as_text(name: str, raw: object) -> str:
    if type(raw) is not str or not raw.strip():
        raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string required")
    return raw


def _as_count(name: str, raw: object) -> int:
    if type(raw) is not int or raw < 1:
        raise ContractError("INVALID_SCHEMA", f"{name}: integer >= 1 required")
    return raw


def _as_decimal(name: str, raw: object) -> Decimal:
    if type(raw) is not str or _DECIMAL_RE.fullmatch(raw) is None:
        raise ContractError("INVALID_NUMBER", f"{name}: plain decimal string required")
    return Decimal(raw)


def _as_positive(name: str, raw: object) -> Decimal:
    value = _as_decimal(name, raw)
    if value <= 0:
        raise ContractError("INVALID_NUMBER", f"{name}: positive decimal required")
    return value


def _as_non_negative(name: str, raw: object) -> Decimal:
    value = _as_decimal(name, raw)
    if value < 0:
        raise ContractError("INVALID_NUMBER", f"{name}: non-negative decimal required")
    return value


def _as_canary_factor(name: str, raw: object) -> Decimal:
    value = _as_positive(name, raw)
    if value > 1:
        raise ContractError("INVALID_NUMBER", f"{name}: risk factor must be within (0, 1]")
    return value


def _as_timestamp(name: str, raw: object) -> datetime:
    if type(raw) is not str or _TIMESTAMP_RE.fullmatch(raw) is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: UTC ISO-8601 string ending 'Z' required")
    try:
        return datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError:
        raise ContractError("INVALID_SCHEMA", f"{name}: invalid timestamp") from None


def _as_mode(name: str, raw: object) -> Mode:
    if type(raw) is not str:
        raise ContractError("INVALID_SCHEMA", f"{name}: Mode string required")
    try:
        return Mode(raw)
    except ValueError:
        raise ContractError("INVALID_SCHEMA", f"{name}: unknown Mode value {raw!r}") from None


def _as_schema(name: str, raw: object) -> str:
    if raw != SCHEMA_VERSION:
        raise ContractError("INVALID_SCHEMA", f"{name}: must be exactly {SCHEMA_VERSION!r}")
    return SCHEMA_VERSION


def _as_authority_version(name: str, raw: object) -> int:
    if type(raw) is not int or raw != AUTHORITY_VERSION:
        raise ContractError("INVALID_SCHEMA", f"{name}: must be {AUTHORITY_VERSION}")
    return raw


def _as_digest(name: str, raw: object) -> str:
    if type(raw) is not str or _DIGEST_RE.fullmatch(raw) is None:
        raise ContractError("HASH_MISMATCH", f"{name}: lowercase sha256 hex required")
    return raw


def _as_id(name: str, raw: object) -> str:
    if type(raw) is str and (
        _UUID_RE.fullmatch(raw) is not None or _DIGEST_RE.fullmatch(raw) is not None
    ):
        return raw
    raise ContractError("INVALID_SCHEMA", f"{name}: UUID or content-addressed id required")


def _as_text_list(name: str, raw: object) -> tuple[str, ...]:
    if type(raw) is not list:
        raise ContractError("INVALID_SCHEMA", f"{name}: JSON array of strings required")
    items: list[str] = []
    for index, item in enumerate(raw):
        if type(item) is not str or not item.strip():
            raise ContractError("INVALID_SCHEMA", f"{name}[{index}]: non-empty string required")
        items.append(item)
    if not items:
        raise ContractError("INVALID_SCHEMA", f"{name}: at least one entry required")
    if len(set(items)) != len(items):
        raise ContractError("INVALID_SCHEMA", f"{name}: duplicate values are not allowed")
    return tuple(items)


def _as_decimal_list(name: str, raw: object) -> tuple[Decimal, ...]:
    if type(raw) is not list:
        raise ContractError("INVALID_SCHEMA", f"{name}: JSON array of decimal strings required")
    values = tuple(_as_positive(f"{name}[{index}]", item) for index, item in enumerate(raw))
    if not values:
        raise ContractError("INVALID_SCHEMA", f"{name}: at least one entry required")
    return values


def _as_value_map(name: str, raw: object, convert: Callable[[str, object], T]) -> Mapping[str, T]:
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{name}: JSON object required")
    result: dict[str, T] = {}
    for key, item in raw.items():
        if type(key) is not str or not key.strip():
            raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string keys required")
        result[key] = convert(f"{name}.{key}", item)
    if not result:
        raise ContractError("INVALID_SCHEMA", f"{name}: at least one entry required")
    return result


def _as_decimal_map(name: str, raw: object) -> Mapping[str, Decimal]:
    return _as_value_map(name, raw, _as_positive)


def _as_symbol_map(name: str, raw: object) -> Mapping[str, str]:
    return _as_value_map(name, raw, _as_text)


def _as_object(name: str, raw: object) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise ContractError("INVALID_SCHEMA", f"{name}: JSON object required")
    return raw


def _as_relative_path(name: str, raw: object) -> str:
    text = _as_text(name, raw)
    if text.startswith(("/", "\\")) or "\\" in text or ":" in text:
        raise ContractError("INVALID_SCHEMA", f"{name}: relative POSIX path required")
    segments = PurePosixPath(text).parts
    if any(segment in ("..", ".") for segment in segments):
        raise ContractError("INVALID_SCHEMA", f"{name}: '..' segments are not allowed")
    return text


# --- Strict object helpers ---
def _check_keys(name: str, payload: Mapping[str, object], allowed: frozenset[str]) -> None:
    unknown = [key for key in payload if key not in allowed]
    if unknown:
        raise ContractError("INVALID_SCHEMA", f"{name}: unknown fields {sorted(unknown)!r}")


def _required(name: str, payload: Mapping[str, object], key: str) -> object:
    if key not in payload:
        raise ContractError("INVALID_SCHEMA", f"{name}.{key}: missing required field")
    value = payload[key]
    if value is None:
        raise ContractError("INVALID_SCHEMA", f"{name}.{key}: null required field")
    return value


def _read(
    name: str, payload: Mapping[str, object], key: str, convert: Callable[[str, object], T]
) -> T:
    return convert(f"{name}.{key}", _required(name, payload, key))


def _read_nullable(
    name: str, payload: Mapping[str, object], key: str, convert: Callable[[str, object], T]
) -> T | None:
    if key not in payload:
        raise ContractError("INVALID_SCHEMA", f"{name}.{key}: missing required field")
    raw = payload[key]
    if raw is None:
        return None
    return convert(f"{name}.{key}", raw)


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("INVALID_SCHEMA", f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_number(token: str) -> Never:
    raise ContractError(
        "INVALID_NUMBER", f"non-string JSON number {token!r} is not allowed; use decimal strings"
    )


# --- Loader ---------------------------------------------------------------------

_TOP_LEVEL_FIELDS: frozenset[str] = frozenset(
    {
        "authority_version", "schema_version", "created_at", "owner_directive_refs",
        "enabled_mode", "account_identity_ref", "pair_symbol_map", "limits",
        "canary_risk_factor", "session_policy_ref", "event_policy_ref", "weekend_policy_ref",
        "allowed_primitive_versions", "allowed_prompt_variables", "source_allowlist",
        "evaluator_policy_digest", "allowed_execution_build_digest", "strategy_certificate_id",
        "issuer_key_ref", "human_stop_marker_path", "service_identity", "journal_root",
        "budgets",
    }
)

_LIMIT_FIELDS: frozenset[str] = frozenset(
    {
        "slot_risk_ceilings", "grade_multipliers", "min_effective_risk_pct",
        "max_concurrent_positions", "max_positions_per_pair", "max_same_usd_sign_tickets",
        "max_open_risk_pct", "max_new_trades_per_day", "daily_stop_pct", "weekly_stop_pct",
        "max_gross_leverage", "account_currency", "day_boundary", "week_boundary",
    }
)

_BUDGET_FIELDS: frozenset[str] = frozenset(
    {
        "max_provider_attempts_per_day", "max_input_tokens", "max_output_tokens",
        "max_attempts_per_role", "daily_monetary_cap_usd", "tick_freshness_ref",
        "bars_freshness_ref", "calendar_freshness_ref",
    }
)


def _load_document(path: Path) -> Mapping[str, object]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ContractError("INVALID_SCHEMA", f"authority manifest unreadable: {error}") from None
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ContractError(
            "INVALID_SCHEMA", f"authority manifest exceeds {MAX_MANIFEST_BYTES} bytes"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ContractError("INVALID_SCHEMA", "authority manifest must be UTF-8") from None
    try:
        parsed: object = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_number,
            parse_float=_reject_number,
        )
    except json.JSONDecodeError as error:
        raise ContractError(
            "INVALID_SCHEMA", f"authority manifest is not valid JSON: {error}"
        ) from None
    if not isinstance(parsed, dict):
        raise ContractError("INVALID_SCHEMA", "authority manifest must be a JSON object")
    return parsed


def _parse_limits(payload: Mapping[str, object]) -> AuthorityLimits:
    name = "authority.limits"
    _check_keys(name, payload, _LIMIT_FIELDS)
    read = partial(_read, name, payload)
    return AuthorityLimits(
        slot_risk_ceilings=read("slot_risk_ceilings", _as_decimal_list),
        grade_multipliers=read("grade_multipliers", _as_decimal_map),
        min_effective_risk_pct=read("min_effective_risk_pct", _as_positive),
        max_concurrent_positions=read("max_concurrent_positions", _as_count),
        max_positions_per_pair=read("max_positions_per_pair", _as_count),
        max_same_usd_sign_tickets=read("max_same_usd_sign_tickets", _as_count),
        max_open_risk_pct=read("max_open_risk_pct", _as_positive),
        max_new_trades_per_day=read("max_new_trades_per_day", _as_count),
        daily_stop_pct=read("daily_stop_pct", _as_positive),
        weekly_stop_pct=read("weekly_stop_pct", _as_positive),
        max_gross_leverage=read("max_gross_leverage", _as_positive),
        account_currency=read("account_currency", _as_text),
        day_boundary=read("day_boundary", _as_text),
        week_boundary=read("week_boundary", _as_text),
    )


def _parse_budgets(payload: Mapping[str, object]) -> AuthorityBudgets:
    name = "authority.budgets"
    _check_keys(name, payload, _BUDGET_FIELDS)
    read = partial(_read, name, payload)
    return AuthorityBudgets(
        max_provider_attempts_per_day=read("max_provider_attempts_per_day", _as_count),
        max_input_tokens=read("max_input_tokens", _as_count),
        max_output_tokens=read("max_output_tokens", _as_count),
        max_attempts_per_role=read("max_attempts_per_role", _as_count),
        daily_monetary_cap_usd=read("daily_monetary_cap_usd", _as_non_negative),
        tick_freshness_ref=read("tick_freshness_ref", _as_text),
        bars_freshness_ref=read("bars_freshness_ref", _as_text),
        calendar_freshness_ref=read("calendar_freshness_ref", _as_text),
    )


def load_authority(path: Path) -> AuthorityPolicy:
    """Load one protected manifest: strict, bounded, UTF-8, fail-closed.

    Present-but-invalid digests raise ``HASH_MISMATCH``; ``null`` is legal only
    for the three provisioning-required fields. Unknown/missing/wrong-typed
    fields raise ``INVALID_SCHEMA``; malformed decimal strings raise
    ``INVALID_NUMBER``. No defaults are guessed from absent data.
    """
    payload = _load_document(path)
    name = "authority"
    _check_keys(name, payload, _TOP_LEVEL_FIELDS)
    read = partial(_read, name, payload)
    read_nullable = partial(_read_nullable, name, payload)
    return AuthorityPolicy(
        authority_version=read("authority_version", _as_authority_version),
        schema_version=read("schema_version", _as_schema),
        created_at=read("created_at", _as_timestamp),
        owner_directive_refs=read("owner_directive_refs", _as_text_list),
        enabled_mode=read("enabled_mode", _as_mode),
        account_identity_ref=read("account_identity_ref", _as_text),
        pair_symbol_map=read("pair_symbol_map", _as_symbol_map),
        limits=_parse_limits(read("limits", _as_object)),
        canary_risk_factor=read("canary_risk_factor", _as_canary_factor),
        session_policy_ref=read("session_policy_ref", _as_text),
        event_policy_ref=read("event_policy_ref", _as_text),
        weekend_policy_ref=read("weekend_policy_ref", _as_text),
        allowed_primitive_versions=read("allowed_primitive_versions", _as_text_list),
        allowed_prompt_variables=read("allowed_prompt_variables", _as_text_list),
        source_allowlist=read("source_allowlist", _as_text_list),
        evaluator_policy_digest=read_nullable("evaluator_policy_digest", _as_digest),
        allowed_execution_build_digest=read_nullable("allowed_execution_build_digest", _as_digest),
        strategy_certificate_id=read_nullable("strategy_certificate_id", _as_id),
        issuer_key_ref=read("issuer_key_ref", _as_text),
        human_stop_marker_path=read("human_stop_marker_path", _as_relative_path),
        service_identity=read("service_identity", _as_text),
        journal_root=read("journal_root", _as_relative_path),
        budgets=_parse_budgets(read("budgets", _as_object)),
    )


# --- Startup verification ---
def _verify_owner_limits(policy: AuthorityPolicy) -> None:
    limits = policy.limits
    expected: dict[str, object] = {
        "slot_risk_ceilings": tuple(Decimal(str(value)) for value in LIMITS.slot_risk_ceilings),
        "grade_multipliers": {
            grade: Decimal(str(value)) for grade, value in LIMITS.grade_multipliers.items()
        },
        "min_effective_risk_pct": Decimal(str(LIMITS.min_effective_risk_pct)),
        "max_concurrent_positions": LIMITS.max_concurrent_positions,
        "max_positions_per_pair": LIMITS.max_positions_per_pair,
        "max_same_usd_sign_tickets": LIMITS.max_same_usd_sign_tickets,
        "max_open_risk_pct": Decimal(str(LIMITS.max_open_risk_pct)),
        "max_new_trades_per_day": LIMITS.max_new_trades_per_day,
        "daily_stop_pct": Decimal(str(LIMITS.daily_stop_pct)),
        "weekly_stop_pct": Decimal(str(LIMITS.weekly_stop_pct)),
        "max_gross_leverage": Decimal(str(RISK.max_leverage)),
        # Manifest-only fields pinned to spec 01 §2.
        "account_currency": "USD",
        "day_boundary": "UTC",
        "week_boundary": "UTC_MONDAY",
    }
    for field, owner_value in expected.items():
        manifest_value: object = getattr(limits, field)
        if manifest_value != owner_value:
            raise ContractError(
                "AUTHORITY_MISMATCH",
                f"authority.limits.{field}: manifest {manifest_value!r} != owner {owner_value!r}",
            )


def _verify_demo_provisioning(policy: AuthorityPolicy, runtime: RuntimeState) -> None:
    if policy.enabled_mode not in (Mode.demo_canary, Mode.demo_active):
        return
    if runtime.graduation_certificate_id is None:
        raise ContractError(
            "CERTIFICATE_INVALID",
            "demo mode requires a graduation certificate id (presence/shape check only)",
        )
    if policy.strategy_certificate_id is None:
        raise ContractError(
            "CERTIFICATE_INVALID", "demo mode requires a provisioned strategy certificate id"
        )
    if policy.evaluator_policy_digest is None or policy.allowed_execution_build_digest is None:
        raise ContractError(
            "CERTIFICATE_INVALID", "demo mode requires provisioned policy/build digests"
        )
    if not runtime.demo_account_verified:
        raise ContractError("NON_DEMO_ACCOUNT", "demo mode requires a verified demo account")


def _verify_pairs(policy: AuthorityPolicy) -> None:
    allowed = set(TRADING_PAIRS)
    configured = set(policy.pair_symbol_map)
    unknown = sorted(configured - allowed)
    if unknown:
        raise ContractError(
            "UNSUPPORTED_PAIR", f"authority.pair_symbol_map: unsupported pair(s) {unknown!r}"
        )
    missing = sorted(allowed - configured)
    if missing:
        raise ContractError(
            "AUTHORITY_MISMATCH", f"authority.pair_symbol_map: missing required pair(s) {missing!r}"
        )


def _verify_primitive_versions(policy: AuthorityPolicy) -> None:
    unknown = sorted(set(policy.allowed_primitive_versions) - KNOWN_PRIMITIVE_VERSIONS)
    if unknown:
        raise ContractError("AUTHORITY_MISMATCH", f"unknown primitive version(s): {unknown!r}")


def _verify_paid_model_budget(policy: AuthorityPolicy, runtime: RuntimeState) -> None:
    if runtime.paid_model_requested and policy.budgets.daily_monetary_cap_usd == 0:
        raise ContractError(
            "BUDGET_EXHAUSTED", "paid inference requested with daily_monetary_cap_usd == 0"
        )


def verify_authority(policy: AuthorityPolicy, runtime: RuntimeState) -> None:
    """Startup/activation gate re-checking the loaded policy against owner facts.

    (a) owner limits equal ``src/paper/config.py`` exactly (Decimal compare),
        manifest-only fields pinned to spec 01 §2; else ``AUTHORITY_MISMATCH``;
    (b) demo modes need the graduation certificate id (presence/shape only;
        cryptographic verification is a later task), non-null provisioning
        fields and a verified demo account (``CERTIFICATE_INVALID`` /
        ``NON_DEMO_ACCOUNT``);
    (c) pair keys supported (``UNSUPPORTED_PAIR``) and covering
        ``config.TRADING_PAIRS`` (``AUTHORITY_MISMATCH``);
    (d) primitive versions within ``KNOWN_PRIMITIVE_VERSIONS``;
    (e) paid inference with a zero daily monetary cap is ``BUDGET_EXHAUSTED``.
    Pure: no I/O, no environment reads, no mutation; repeat calls match.
    """
    _verify_owner_limits(policy)
    _verify_demo_provisioning(policy, runtime)
    _verify_pairs(policy)
    _verify_primitive_versions(policy)
    _verify_paid_model_budget(policy, runtime)
