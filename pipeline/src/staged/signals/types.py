"""Frozen output types for signal family adapters."""

from __future__ import annotations

from dataclasses import dataclass

from src.signals.rate import RateNormZ


@dataclass(frozen=True, slots=True)
class RateFamilyOutput:
    """Rate spread, normalization, and carry outputs."""

    spread_2y: float | None
    spread_10y: float | None
    spread_10y_real: float | None
    norm_z: RateNormZ
    direction: str
    risk_adjusted_carry: float | None
    breakeven_inflation_10y: float | None
    health_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CotFamilyOutput:
    """COT percentile, OI, and positioning breakdown."""

    percentile: float | None
    norm: float | None
    oi_norm: float | None
    oi_delta: int | None
    net_pos: int | None
    asset_mgr_net: int | None
    lev_money_net: int | None
    days_since_cot: int
    health_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VolFamilyOutput:
    """Realized vol, rank, and expansion flag."""

    rv20: float | None
    rv5: float | None
    vol_norm: float | None
    vol_expanding: bool
    implied_vol_30d: float | None
    realized_vol_rank: float | None
    health_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SpecialFamilyOutput:
    """Pair-specific macro / cross-asset special signal."""

    signal: float | None
    health_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FamilyOutput:
    """Aggregate of all signal family slices."""

    rate: RateFamilyOutput | None
    cot: CotFamilyOutput | None
    vol: VolFamilyOutput | None
    special: SpecialFamilyOutput | None
    health_notes: tuple[str, ...] = ()

    @classmethod
    def merge(cls, *partials: FamilyOutput) -> FamilyOutput:
        """Merge partial outputs from individual family adapters."""

        rate: RateFamilyOutput | None = None
        cot: CotFamilyOutput | None = None
        vol: VolFamilyOutput | None = None
        special: SpecialFamilyOutput | None = None
        notes: list[str] = []
        for partial in partials:
            if partial.rate is not None:
                rate = partial.rate
            if partial.cot is not None:
                cot = partial.cot
            if partial.vol is not None:
                vol = partial.vol
            if partial.special is not None:
                special = partial.special
            notes.extend(partial.health_notes)
        return cls(
            rate=rate,
            cot=cot,
            vol=vol,
            special=special,
            health_notes=tuple(notes),
        )
