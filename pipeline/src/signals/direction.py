"""Convert raw economic hypotheses to the quoted pair's direction exactly once."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from src.types import normalize_fx_pair_key

DIRECTIONAL_MODEL_VERSION = "3.0-directional-reference"
DIRECTIONAL_STRATEGY_VERSION = "pair-direction-v1"


@dataclass(frozen=True)
class DirectionalInputs:
    rate: float | None
    cot: float | None
    special: float | None
    fpi: float | None


def currency_strength_to_pair(
    value: float | None, *, currency: str, pair: str
) -> float | None:
    """Positive currency strength raises the base/quote price only for the base."""

    key = normalize_fx_pair_key(pair)
    if key not in ("EURUSD", "USDJPY", "USDINR"):
        raise ValueError(f"Unsupported FX pair: {pair!r}")
    currency = currency.strip().upper()
    if currency not in (key[:3], key[3:]):
        raise ValueError(f"Currency {currency!r} is outside {key}")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError("Directional input must be a finite real number or None")
    return float(value) if currency == key[:3] else -float(value)


def directional_inputs(
    pair: str,
    *,
    rate: float | None,
    cot: float | None,
    special: float | None,
    fpi: float | None,
) -> DirectionalInputs:
    """Orient pair-up rates, EUR/JPY futures, USD special and normalized INR demand.

    FPI must already be a normalized demand deviation, never a raw cash-flow total.
    The returned values are inputs to the composite and public directional labels.
    """

    key = normalize_fx_pair_key(pair)
    if key not in ("EURUSD", "USDJPY", "USDINR"):
        raise ValueError(f"Unsupported FX pair: {pair!r}")
    if key == "USDINR" and cot is not None:
        raise ValueError("USDINR has no supported COT directional input")
    if key != "USDINR" and fpi is not None:
        raise ValueError("FPI directional input is supported only for USDINR")
    return DirectionalInputs(
        rate=currency_strength_to_pair(rate, currency=key[:3], pair=key),
        cot=(
            currency_strength_to_pair(cot, currency="EUR" if key == "EURUSD" else "JPY", pair=key)
            if key != "USDINR"
            else None
        ),
        special=currency_strength_to_pair(special, currency="USD", pair=key),
        fpi=currency_strength_to_pair(fpi, currency="INR", pair=key) if key == "USDINR" else None,
    )
