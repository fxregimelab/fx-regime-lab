"""Rate spread signal family adapter."""

from __future__ import annotations

from src.signals.rate import (
    RateNormZ,
    compute_risk_adjusted_carry_v2,
    normalize_rate_signal,
    rate_direction_from_spreads,
)
from src.staged.contracts import IngestionSnapshot
from src.staged.signals.rate_history import RateHistoryProvider, SnapshotRateHistoryProvider
from src.staged.signals.types import FamilyOutput, RateFamilyOutput


def _rate_spread_2y(pair: str, yields: dict[str, float | None]) -> float | None:
    if pair == "EURUSD":
        base, quote = yields.get("DGS2"), yields.get("ECBDFR")
    elif pair == "USDJPY":
        base, quote = yields.get("DGS2"), yields.get("IRLTLT01JPM156N")
    elif pair == "USDINR":
        base, quote = yields.get("DGS2"), yields.get("INDIRLTLT01STM")
    else:
        return None
    if base is None or quote is None:
        return None
    return float(base) - float(quote)


def _rate_spread_10y(pair: str, yields: dict[str, float | None]) -> float | None:
    us = yields.get("us_10y")
    if us is None:
        return None
    qk = {"EURUSD": "de_10y", "USDJPY": "jp_10y", "USDINR": "in_10y"}.get(pair)
    if qk is None:
        return None
    qv = yields.get(qk)
    if qv is None:
        return None
    return float(us) - float(qv)


def _real_yield_spread_10y(
    spread_10y: float | None,
    breakeven: float | None,
) -> float | None:
    if spread_10y is None:
        return None
    if breakeven is None:
        return spread_10y
    return float(spread_10y) - float(breakeven)


class RateFamily:
    """Compute rate spreads, normalization, direction, and risk-adjusted carry."""

    def __init__(self, history_provider: RateHistoryProvider | None = None) -> None:
        self._history_provider = history_provider

    def compute(
        self,
        pair: str,
        snapshot: IngestionSnapshot,
        *,
        rv20: float | None = None,
    ) -> FamilyOutput:
        """Return rate family outputs; ``rv20`` is supplied by VolFamily when available."""

        history = self._history_provider or SnapshotRateHistoryProvider(snapshot)
        bei = snapshot.yields.get("T10YIE")
        spread_2y = _rate_spread_2y(pair, snapshot.yields)
        spread_10y = _rate_spread_10y(pair, snapshot.yields)
        spread_10y_real = _real_yield_spread_10y(spread_10y, bei)

        risk_adjusted_carry = compute_risk_adjusted_carry_v2(
            spread_2y,
            rv20,
            None,
            pair,
        )
        rate_norm_z = self._normalize(
            pair, risk_adjusted_carry, spread_10y_real, history
        )
        direction = rate_direction_from_spreads(
            spread_2y,
            spread_10y,
            z_tactical=rate_norm_z.z_blended,
        )

        return FamilyOutput(
            rate=RateFamilyOutput(
                spread_2y=spread_2y,
                spread_10y=spread_10y,
                spread_10y_real=spread_10y_real,
                norm_z=rate_norm_z,
                direction=direction,
                risk_adjusted_carry=risk_adjusted_carry,
                breakeven_inflation_10y=bei,
            ),
            cot=None,
            vol=None,
            special=None,
        )

    def _normalize(
        self,
        pair: str,
        spread: float | None,
        spread_structural: float | None,
        history: RateHistoryProvider,
    ) -> RateNormZ:
        if spread is None:
            return RateNormZ(z_tactical=None, z_structural=None, z_blended=None)
        tactical = history.spread_history(pair, spread)
        structural = history.structural_history(spread_structural)
        return normalize_rate_signal(
            spread=spread,
            pair=pair,
            historical_spreads=tactical,
            spread_structural=spread_structural,
            historical_structural=structural,
        )
