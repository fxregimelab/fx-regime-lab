"""Asymmetry engine for crowding pain and squeeze-risk conditions."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from src.types import CotRow, SpotBar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PainIndexResult:
    pair: str
    as_of_date: str
    pain_index: float | None
    cot_is_stale: bool
    cot_age_days: int | None
    cot_percentile: float | None
    regime_direction: int
    vwap_8w: float | None
    spot: float | None
    underwater_triggered: bool
    realized_vol_20d: float | None
    vwap_distance_pct: float | None
    underwater_vol_buffer_pct: float | None


def _regime_direction(regime: str) -> int:
    regime_upper = regime.upper()
    if "STRENGTH" in regime_upper or "DEPR" in regime_upper:
        return 1
    if "WEAKNESS" in regime_upper or "APPR" in regime_upper:
        return -1
    return 0


def _vwap_8w_base(spot_bars: Sequence[SpotBar]) -> float | None:
    """Simple 8-week (~40 session) average close (carry-neutral baseline)."""

    if len(spot_bars) < 40:
        return None
    window = spot_bars[-40:]
    numerator = sum(bar.close for bar in window)
    if numerator <= 0.0:
        return None
    return numerator / float(len(window))


def _cumulative_swap_return_price(
    spot_bars: Sequence[SpotBar],
    carry_by_date: Mapping[date, float],
) -> float:
    """Sum of daily carry accrual in price space: spot * (rate_diff_2y/365)/100."""

    if len(spot_bars) < 40:
        return 0.0
    window = spot_bars[-40:]
    total = 0.0
    for bar in window:
        r2 = carry_by_date.get(bar.date)
        if r2 is None or bar.close <= 0.0:
            continue
        total += float(bar.close) * (float(r2) / 365.0) / 100.0
    return total


def compute_pain_index(
    pair: str,
    as_of_date: date,
    regime: str,
    cot_percentile: float | None,
    cot_rows: list[CotRow],
    spot_bars: Sequence[SpotBar],
    realized_vol_20d: float | None = None,
    implied_vol_30d: float | None = None,
    carry_by_date: Mapping[date, float] | None = None,
) -> PainIndexResult:
    direction = _regime_direction(regime)
    latest_cot = max((r.date for r in cot_rows if r.pair == pair), default=None)
    cot_age_days = None if latest_cot is None else (as_of_date - latest_cot).days
    cot_is_stale = cot_age_days is None or cot_age_days > 7
    if cot_is_stale:
        logger.info("Pain_Index unavailable for %s: stale COT (%s days)", pair, cot_age_days)
        return PainIndexResult(
            pair=pair,
            as_of_date=as_of_date.isoformat(),
            pain_index=None,
            cot_is_stale=True,
            cot_age_days=cot_age_days,
            cot_percentile=cot_percentile,
            regime_direction=direction,
            vwap_8w=None,
            spot=spot_bars[-1].close if spot_bars else None,
            underwater_triggered=False,
            realized_vol_20d=realized_vol_20d,
            vwap_distance_pct=None,
            underwater_vol_buffer_pct=None,
        )

    if cot_percentile is None:
        logger.info("Pain_Index unavailable for %s: missing COT percentile", pair)
        return PainIndexResult(
            pair=pair,
            as_of_date=as_of_date.isoformat(),
            pain_index=None,
            cot_is_stale=False,
            cot_age_days=cot_age_days,
            cot_percentile=None,
            regime_direction=direction,
            vwap_8w=None,
            spot=spot_bars[-1].close if spot_bars else None,
            underwater_triggered=False,
            realized_vol_20d=realized_vol_20d,
            vwap_distance_pct=None,
            underwater_vol_buffer_pct=None,
        )

    directional_crowding = ((cot_percentile - 50.0) / 50.0) * -1.0
    divergence = abs(float(direction) - directional_crowding)
    base_pain = min(100.0, max(0.0, (divergence / 2.0) * 100.0))

    current_spot = spot_bars[-1].close if spot_bars else None
    base_vwap = _vwap_8w_base(spot_bars)
    swap_accum = (
        _cumulative_swap_return_price(spot_bars, carry_by_date)
        if carry_by_date is not None
        else 0.0
    )
    vwap_eff = (base_vwap + swap_accum) if base_vwap is not None else None

    vwap_distance_pct: float | None = None
    buffer_pct: float | None = None
    underwater = False
    vol_premium: float | None = None
    if (
        implied_vol_30d is not None
        and realized_vol_20d is not None
        and implied_vol_30d > 0.0
        and realized_vol_20d > 0.0
    ):
        vol_premium = float(implied_vol_30d) - float(realized_vol_20d)

    if (
        current_spot is not None
        and vwap_eff is not None
        and vwap_eff > 0.0
    ):
        vwap_distance_pct = abs(current_spot - vwap_eff) / vwap_eff * 100.0
        crowded_long_usd = cot_percentile >= 50.0
        wrong_side = (
            current_spot < vwap_eff if crowded_long_usd else current_spot > vwap_eff
        )
        if realized_vol_20d is None or realized_vol_20d <= 0.0:
            buffer_pct = None
        else:
            buffer_pct = 0.5 * float(realized_vol_20d)
        premium_ok = vol_premium is not None and vol_premium > 0.0
        underwater = (
            wrong_side
            and buffer_pct is not None
            and vwap_distance_pct >= buffer_pct
            and premium_ok
        )

    if base_pain > 80.0 and not underwater:
        logger.info("Pain_Index capped at 80 for %s: underwater trigger not met", pair)
        base_pain = 80.0

    return PainIndexResult(
        pair=pair,
        as_of_date=as_of_date.isoformat(),
        pain_index=base_pain,
        cot_is_stale=False,
        cot_age_days=cot_age_days,
        cot_percentile=cot_percentile,
        regime_direction=direction,
        vwap_8w=vwap_eff,
        spot=current_spot,
        underwater_triggered=underwater,
        realized_vol_20d=realized_vol_20d,
        vwap_distance_pct=vwap_distance_pct,
        underwater_vol_buffer_pct=buffer_pct,
    )
