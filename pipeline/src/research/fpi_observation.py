"""Pure FPI capture-candidate identity, with no I/O.

Inputs are normalized INR fields, not HTML. Construction proves structural
consistency, not source authenticity or durable first-seen provenance.
The former timestamp-only selector is retired; these records are not decisions.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any

FPI_SERIES_ID = "NSDL_FPI_CONFIRMED_REPORTED_ALL7_INR_CRORE_DAILY_V1"
FPI_OBSERVATION_VERSION = "fpi-inr-observation-v1"
FPI_ROUTES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "Equity": ("Stock Exchange", "Primary market & others"),
        "Debt-General Limit": ("Stock Exchange", "Primary market & others"),
        "Debt-VRR": ("Stock Exchange", "Primary market & others"),
        "Debt-FAR": ("Stock Exchange", "Primary market & others"),
        "Hybrid": ("Stock Exchange", "Primary market & others"),
        "Mutual Funds": (
            "Equity schemes",
            "Debt schemes",
            "Hybrid schemes",
            "Solution oriented schemes",
            "Other schemes",
        ),
        "AIFs": ("Stock Exchange", "Primary market & others"),
    }
)
_SOURCES = frozenset(
    {
        "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
        "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
    }
)
_MONEY_FIELDS = ("purchases_cr", "sales_cr", "net_cr")
_IST = timezone(timedelta(hours=5, minutes=30))


@dataclass(frozen=True)
class FpiObservation:
    reporting_date: date
    document_json: str
    observation_sha256: str
    net_hundredths_cr: int
    source_url: str
    raw_sha256: str
    parser_version: str
    retrieved_at: datetime
    first_seen_at: datetime


@dataclass(frozen=True)
class FpiHistory:
    """Structural selection only; this does not certify model eligibility."""

    as_of: datetime
    status: str
    current: FpiObservation | None
    history: tuple[FpiObservation, ...]
    excluded_future_captures: int
    excluded_old_history_dates: int


def _fpi_money(value: object) -> int:
    """Use integer hundredths of crore so Decimal context cannot alter sums."""
    if not isinstance(value, str) or not re.fullmatch(
        r"-?(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,2})?", value
    ):
        raise ValueError("FPI money requires finite decimal text with at most two places")
    whole, _, fraction = value.lstrip("-").partition(".")
    amount = int(whole) * 100 + int(fraction.ljust(2, "0"))
    return -amount if value.startswith("-") else amount


def _fpi_money_text(value: int) -> str:
    whole, fraction = divmod(abs(value), 100)
    return f"{'-' if value < 0 else ''}{whole}.{fraction:02d}"


def _fpi_amounts(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(_MONEY_FIELDS):
        raise ValueError("FPI amounts require exactly purchases_cr, sales_cr and net_cr")
    result = {field: _fpi_money(value[field]) for field in _MONEY_FIELDS}
    if result["purchases_cr"] < 0 or result["sales_cr"] < 0:
        raise ValueError("FPI gross purchases and sales cannot be negative")
    # Three independently rounded 0.01-crore numbers: error bound 3 * 0.005.
    if 2 * abs(result["purchases_cr"] - result["sales_cr"] - result["net_cr"]) > 3:
        raise ValueError("FPI purchases minus sales do not reconcile with net")
    return result


def _fpi_reconcile(children: Sequence[dict[str, int]], parent: dict[str, int]) -> None:
    for field in _MONEY_FIELDS:
        # n children plus parent, each rounded to 0.01 crore: (n+1)/2 hundredths.
        if 2 * abs(sum(child[field] for child in children) - parent[field]) > len(children) + 1:
            raise ValueError("FPI component amounts do not reconcile with published total")


def _fpi_utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("FPI knowledge times must be timezone-aware datetimes")
    try:
        normalized = value.astimezone(UTC)
        normalized.astimezone(_IST)
        return normalized
    except (ValueError, OverflowError) as exc:
        raise ValueError("FPI knowledge time is outside supported range") from exc


def build_fpi_observation(
    *,
    reporting_date: date,
    categories: Mapping[str, Any],
    total: Mapping[str, Any],
    source_url: str,
    raw_sha256: str,
    parser_version: str,
    retrieved_at: datetime,
    first_seen_at: datetime,
) -> FpiObservation:
    """Validate normalized INR components and detach them in a canonical document.

    The persistence boundary must establish first_seen_at from actual evidence.
    This pure function cannot prove the caller's timestamp or hash is authentic.
    """
    if type(reporting_date) is not date:
        raise ValueError("FPI reporting_date must be a date, not a timestamp")
    retrieved, first_seen = _fpi_utc(retrieved_at), _fpi_utc(first_seen_at)
    if first_seen > retrieved:
        raise ValueError("FPI first_seen_at cannot follow retrieval")
    if reporting_date > first_seen.astimezone(_IST).date():
        raise ValueError("FPI reporting date cannot follow first observation in India")
    if not isinstance(source_url, str) or source_url not in _SOURCES:
        raise ValueError("Unsupported FPI source URL")
    if not isinstance(raw_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_sha256):
        raise ValueError("FPI capture requires a lowercase SHA-256 fingerprint")
    if not isinstance(parser_version, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", parser_version
    ):
        raise ValueError("FPI parser version is invalid")
    if not isinstance(categories, Mapping) or set(categories) != set(FPI_ROUTES):
        raise ValueError("FPI observation requires all seven categories exactly once")
    canonical_categories: dict[str, Any] = {}
    subtotals: list[dict[str, int]] = []
    for category, expected_routes in FPI_ROUTES.items():
        group = categories[category]
        if not isinstance(group, Mapping) or set(group) != {"routes", "subtotal"}:
            raise ValueError("FPI category requires routes and subtotal")
        routes = group["routes"]
        if not isinstance(routes, Mapping) or set(routes) != set(expected_routes):
            raise ValueError("FPI category routes are missing or unknown")
        amounts = {name: _fpi_amounts(routes[name]) for name in expected_routes}
        subtotal = _fpi_amounts(group["subtotal"])
        _fpi_reconcile(list(amounts.values()), subtotal)
        subtotals.append(subtotal)
        canonical_categories[category] = {
            "routes": {
                name: {field: _fpi_money_text(number) for field, number in values.items()}
                for name, values in amounts.items()
            },
            "subtotal": {field: _fpi_money_text(number) for field, number in subtotal.items()},
        }
    total_amounts = _fpi_amounts(total)
    _fpi_reconcile(subtotals, total_amounts)
    document = {
        "version": FPI_OBSERVATION_VERSION,
        "series_id": FPI_SERIES_ID,
        "units": "INR_CRORE",
        "date_basis": "reporting_date",
        "reporting_date": reporting_date.isoformat(),
        "categories": canonical_categories,
        "total": {field: _fpi_money_text(number) for field, number in total_amounts.items()},
    }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return FpiObservation(
        reporting_date,
        encoded,
        hashlib.sha256(encoded.encode("ascii")).hexdigest(),
        total_amounts["net_cr"],
        source_url,
        raw_sha256,
        parser_version,
        retrieved,
        first_seen,
    )


def _validate_fpi_observation(value: FpiObservation) -> None:
    if type(value) is not FpiObservation or type(value.net_hundredths_cr) is not int:
        raise ValueError("Expected a complete FPI observation")
    if not isinstance(value.document_json, str) or len(value.document_json) > 32768:
        raise ValueError("FPI canonical document is missing or oversized")
    try:
        document = json.loads(value.document_json)
        if not isinstance(document, dict):
            raise ValueError("FPI document must be an object")
        rebuilt = build_fpi_observation(
            reporting_date=value.reporting_date,
            categories=document["categories"],
            total=document["total"],
            source_url=value.source_url,
            raw_sha256=value.raw_sha256,
            parser_version=value.parser_version,
            retrieved_at=value.retrieved_at,
            first_seen_at=value.first_seen_at,
        )
    except (KeyError, TypeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Malformed FPI canonical document") from exc
    # Exact canonical text also rejects duplicate JSON keys and altered definitions.
    if (
        rebuilt != value
        or rebuilt.retrieved_at.isoformat() != value.retrieved_at.isoformat()
        or rebuilt.first_seen_at.isoformat() != value.first_seen_at.isoformat()
    ):
        raise ValueError("FPI observation does not match its canonical evidence")


def select_fpi_history(
    observations: Sequence[FpiObservation],
    *,
    as_of: datetime,
    max_current_age_days: int,
    max_history_age_days: int,
    window: int = 20,
    minimum_history: int = 10,
) -> FpiHistory:
    """Reject the retired timestamp-only research selector.

    A value's first-seen time cannot order repeated occurrences or establish
    committed decision visibility. Use an exact FPI decision snapshot instead.
    """
    raise RuntimeError(
        "Timestamp-only FPI selection is retired; an exact qualified decision snapshot is required"
    )
