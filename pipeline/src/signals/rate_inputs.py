"""Economic definitions for rate features; source timing is a separate requirement.

Only documented series belong in SOURCE_DEFINITIONS. A symbol that sounds like a
two-year bond is not sufficient evidence. Current foreign inputs do not qualify.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class RateInstrument:
    currency: str
    tenor_years: float
    kind: str
    frequency: str
    unit: str = "percent"


SOURCE_DEFINITIONS = {
    "DGS2": RateInstrument("USD", 2, "government_yield", "daily"),
    "ECBDFR": RateInstrument("EUR", 0, "deposit_facility", "daily"),
    "IRLTLT01JPM156N": RateInstrument("JPY", 10, "government_yield", "monthly"),
    "INDIRLTLT01STM": RateInstrument("INR", 10, "government_yield", "monthly"),
}
CONFIGURED_RATE_SOURCES = {
    "EURUSD": ("DGS2", "ECBDFR"),
    "USDJPY": ("DGS2", "IRLTLT01JPM156N"),
    "USDINR": ("DGS2", "INDIRLTLT01STM"),
}
PAIR_CURRENCIES = {"EURUSD": ("EUR", "USD"), "USDJPY": ("USD", "JPY"), "USDINR": ("USD", "INR")}


def finite_rate(value: object) -> float | None:
    """Preserve zero and negative rates, reject booleans and non-finite values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if isfinite(value) else None


def qualify_rate_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep other history intact while excluding legacy rates from all consumers."""
    return [
        dict(row) if row.get("rate_input_contract") == "pair-2y-v1"
        else {**row, "rate_diff_2y": None}
        for row in rows
    ]


def two_year_spread(
    pair: str,
    values: Mapping[str, float | None],
    source_ids: tuple[str | None, str | None] | None = None,
    *,
    definitions: Mapping[str, RateInstrument] = SOURCE_DEFINITIONS,
) -> float | None:
    """Base-currency minus quote-currency matched 2Y government yields, in pp.

    Definition compatibility does not establish observation/release-time validity.
    Unknown sources, reversed currency assignments and mixed tenors are unavailable.
    """
    currencies = PAIR_CURRENCIES.get(pair)
    ids = source_ids if source_ids is not None else CONFIGURED_RATE_SOURCES.get(pair)
    if currencies is None or ids is None or any(s is None for s in ids):
        return None
    base_id, quote_id = ids
    assert base_id is not None and quote_id is not None
    base, quote = definitions.get(base_id), definitions.get(quote_id)
    if base is None or quote is None:
        return None
    if (base.currency, quote.currency) != currencies:
        return None
    if (
        any(
            s.tenor_years != 2 or s.kind != "government_yield" or s.unit != "percent"
            for s in (base, quote)
        )
        or base.frequency != quote.frequency
    ):
        return None
    b, q = finite_rate(values.get(base_id)), finite_rate(values.get(quote_id))
    return b - q if b is not None and q is not None else None


def nominal_ten_year_context(pair: str, values: Mapping[str, float | None]) -> float | None:
    """Orient legacy 10Y context by currency; not a qualified daily forecast input.

    Legacy aliases lose source date and frequency. Retain the descriptive nominal
    value, but do not substitute it into a two-year or real-yield feature.
    """
    keys = {
        "EURUSD": ("de_10y", "us_10y"),
        "USDJPY": ("us_10y", "jp_10y"),
        "USDINR": ("us_10y", "in_10y"),
    }.get(pair)
    if keys is None:
        return None
    b, q = (finite_rate(values.get(key)) for key in keys)
    return b - q if b is not None and q is not None else None


def real_yield_spread(
    nominal_spread: float | None,
    base_inflation: float | None,
    quote_inflation: float | None,
) -> float | None:
    """Approximate real spread: nominal base-minus-quote minus inflation difference.

    Callers must supply compatible horizon/measure/timing for both expectations.
    Breakevens are inflation compensation proxies, not pure expected inflation.
    """
    n, b, q = map(finite_rate, (nominal_spread, base_inflation, quote_inflation))
    return n - (b - q) if n is not None and b is not None and q is not None else None


def current_real_yield_spread(
    pair: str, nominal_spread: float | None, values: Mapping[str, float | None]
) -> float | None:
    """Only the US inflation leg is configured; foreign expectations are missing."""
    us = finite_rate(values.get("T10YIE"))
    if pair == "EURUSD":
        return real_yield_spread(nominal_spread, None, us)
    if pair in ("USDJPY", "USDINR"):
        return real_yield_spread(nominal_spread, us, None)
    return None
