"""USDINR pair-specific regime detection.

RBI management regime detection and FPI flow regime classification.
"""

from __future__ import annotations

from typing import Literal

RbiManagementRegime = Literal["ACTIVE_DEFENCE", "LIGHT_TOUCH", "ACCUMULATION"]
FpiFlowRegime = Literal[
    "STRONG_INFLOW",
    "MODERATE_INFLOW",
    "NEUTRAL",
    "MODERATE_OUTFLOW",
    "STRONG_OUTFLOW",
]

# USDINR hysteresis thresholds
_HYSTERESIS_TIER4 = 1.0
_HYSTERESIS_TIER3 = 0.50
_HYSTERESIS_TIER2 = -0.30
_HYSTERESIS_TIER1 = -1.0

_VOL_RANK_ENTER_MAX = 0.82
_CONVICTION_ENTER_MIN = 4

# RBI intervention proxies
_RBI_DEFENCE_RESERVES_DROP_PCT = 3.0  # 3% monthly drop = active defence
_RBI_ACCUMULATION_RESERVES_RISE_PCT = 2.0


def usdinr_hysteresis_tier(
    composite: float,
    prior_tier: int | None,
) -> int:
    """Five-tier Schmitt trigger for USDINR (0=strong bear … 4=strong bull)."""

    def _snap(c: float) -> int:
        if c > _HYSTERESIS_TIER4:
            return 4
        if c > _HYSTERESIS_TIER3:
            return 3
        if c >= _HYSTERESIS_TIER2:
            return 2
        if c >= _HYSTERESIS_TIER1:
            return 1
        return 0

    t_new = _snap(composite)
    if prior_tier is None or not (0 <= prior_tier <= 4):
        return t_new

    pt = prior_tier
    if abs(t_new - pt) >= 2:
        return t_new

    if pt == 4 and composite >= 0.85:
        return 4
    if pt == 0 and composite <= -0.85:
        return 0

    if pt == 4 and composite < 0.85:
        return min(t_new, 3)
    if pt == 0 and composite > -0.85:
        return max(t_new, 1)

    if pt == 3 and composite > _HYSTERESIS_TIER4:
        return 4
    if pt == 3 and composite < 0.30:
        return t_new

    if pt == 1 and composite < _HYSTERESIS_TIER1:
        return 0
    if pt == 1 and composite > -0.30:
        return t_new

    if pt == 2 and abs(composite) < 0.15:
        return 2

    return t_new


def detect_rbi_management_regime(
    reserves_mom_pct: float | None,
    fwd_premium_z: float | None,
    spot_vol_20d: float | None,
) -> RbiManagementRegime:
    """Classify RBI management stance.

    Parameters
    ----------
    reserves_mom_pct:
        Month-over-month change in RBI FX reserves (%).
    fwd_premium_z:
        Z-score of 1-month forward premium (elevated = RBI defending).
    spot_v realized_vol_20d:
        Current spot volatility (annualised, %).

    Returns
    -------
    ``"ACTIVE_DEFENCE"`` when RBI is burning reserves or forward premium is
    elevated, ``"ACCUMULATION"`` when reserves are rising steadily,
    ``"LIGHT_TOUCH"`` otherwise.
    """
    if reserves_mom_pct is not None:
        if reserves_mom_pct < -_RBI_DEFENCE_RESERVES_DROP_PCT:
            return "ACTIVE_DEFENCE"
        if reserves_mom_pct > _RBI_ACCUMULATION_RESERVES_RISE_PCT:
            return "ACCUMULATION"

    if fwd_premium_z is not None and fwd_premium_z > 2.0:
        return "ACTIVE_DEFENCE"

    return "LIGHT_TOUCH"


def detect_fpi_flow_regime(
    fpi_equity_mom_usd_bn: float | None,
    fpi_debt_mom_usd_bn: float | None,
) -> FpiFlowRegime:
    """Classify FPI flow regime from monthly equity + debt flows.

    Parameters
    ----------
    fpi_equity_mom_usd_bn:
        Monthly FPI equity flow (USD bn, positive = inflow).
    fpi_debt_mom_usd_bn:
        Monthly FPI debt flow (USD bn, positive = inflow).

    Returns
    -------
    One of five FPI flow regimes based on total monthly flow magnitude.
    """
    total = 0.0
    if fpi_equity_mom_usd_bn is not None:
        total += float(fpi_equity_mom_usd_bn)
    if fpi_debt_mom_usd_bn is not None:
        total += float(fpi_debt_mom_usd_bn)

    if total > 3.0:
        return "STRONG_INFLOW"
    if total > 1.0:
        return "MODERATE_INFLOW"
    if total < -3.0:
        return "STRONG_OUTFLOW"
    if total < -1.0:
        return "MODERATE_OUTFLOW"
    return "NEUTRAL"


def rbi_adjusted_thresholds(
    base_thresholds: dict[str, float | int],
    rbi_regime: RbiManagementRegime,
) -> dict[str, float | int]:
    """Adjust thresholds under RBI management.

    When RBI is in active defence mode, tighten entry conditions and reduce
    position size to respect the central bank wall.
    """
    adjusted = dict(base_thresholds)
    if rbi_regime == "ACTIVE_DEFENCE":
        adjusted["conviction_enter_min"] = max(int(adjusted.get("conviction_enter_min", 4)) + 1, 5)
        adjusted["vol_rank_enter_max"] = float(adjusted.get("vol_rank_enter_max", 0.82)) * 0.80
        adjusted["adr_multiplier"] = float(adjusted.get("adr_multiplier", 1.2)) * 0.90
    elif rbi_regime == "ACCUMULATION":
        # RBI buying USD → INR depreciation pressure; slightly easier to go long USD
        adjusted["conviction_enter_min"] = max(int(adjusted.get("conviction_enter_min", 4)) - 0, 3)
    return adjusted


def get_usdinr_thresholds(
    rbi_regime: RbiManagementRegime = "LIGHT_TOUCH",
) -> dict[str, float | int]:
    """Return USDINR-specific execution and regime thresholds."""
    base = {
        "hysteresis_tier4": _HYSTERESIS_TIER4,
        "hysteresis_tier3": _HYSTERESIS_TIER3,
        "hysteresis_tier2": _HYSTERESIS_TIER2,
        "hysteresis_tier1": _HYSTERESIS_TIER1,
        "vol_rank_enter_max": _VOL_RANK_ENTER_MAX,
        "conviction_enter_min": _CONVICTION_ENTER_MIN,
        "adr_multiplier": 1.2,
        "mie_multiplier": 1.0,
        "rbi_management_discount": True,
    }
    return rbi_adjusted_thresholds(base, rbi_regime)
