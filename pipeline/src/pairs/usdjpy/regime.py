"""USDJPY pair-specific regime detection.

BoJ intervention regime detection and intervention-proximity threshold
modification.
"""

from __future__ import annotations

from typing import Literal

BojInterventionRegime = Literal["ACTIVE", "PROXIMAL", "DORMANT"]

# USDJPY hysteresis thresholds
_HYSTERESIS_TIER4 = 1.0
_HYSTERESIS_TIER3 = 0.40
_HYSTERESIS_TIER2 = -0.40
_HYSTERESIS_TIER1 = -1.0

_VOL_RANK_ENTER_MAX = 0.90
_CONVICTION_ENTER_MIN = 3

# BoJ intervention proximity bands (USDJPY pips from recent extremes)
_INTERVENTION_ACTIVE_ZONE = 100.0  # within 100 pips of recent intervention level
_INTERVENTION_WARN_ZONE = 250.0  # within 250 pips


def usdjpy_hysteresis_tier(
    composite: float,
    prior_tier: int | None,
) -> int:
    """Five-tier Schmitt trigger for USDJPY (0=strong bear … 4=strong bull)."""

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
    if pt == 3 and composite < 0.25:
        return t_new

    if pt == 1 and composite < _HYSTERESIS_TIER1:
        return 0
    if pt == 1 and composite > -0.25:
        return t_new

    if pt == 2 and abs(composite) < 0.15:
        return 2

    return t_new


def detect_boj_intervention_regime(
    spot: float | None,
    last_intervention_high: float | None,
    last_intervention_low: float | None,
    days_since_last_intervention: int | None,
) -> BojInterventionRegime:
    """Classify BoJ intervention threat level.

    Parameters
    ----------
    spot:
        Current USDJPY spot.
    last_intervention_high:
        Level of the most recent BoJ intervention to strengthen JPY (sell USD).
    last_intervention_low:
        Level of the most recent BoJ intervention to weaken JPY (buy USD).
    days_since_last_intervention:
        Days since the last confirmed intervention.

    Returns
    -------
    ``"ACTIVE"`` when spot is inside the active intervention zone,
    ``"PROXIMAL"`` when inside the warning zone,
    ``"DORMANT"`` otherwise.
    """
    if spot is None:
        return "DORMANT"

    # Interventions lose relevance after 180 days
    if days_since_last_intervention is not None and days_since_last_intervention > 180:
        return "DORMANT"

    s = float(spot)
    distances: list[float] = []
    if last_intervention_high is not None:
        distances.append(abs(s - float(last_intervention_high)))
    if last_intervention_low is not None:
        distances.append(abs(s - float(last_intervention_low)))

    if not distances:
        return "DORMANT"

    min_dist = min(distances)
    if min_dist <= _INTERVENTION_ACTIVE_ZONE:
        return "ACTIVE"
    if min_dist <= _INTERVENTION_WARN_ZONE:
        return "PROXIMAL"
    return "DORMANT"


def intervention_adjusted_thresholds(
    base_thresholds: dict[str, float | int],
    boj_regime: BojInterventionRegime,
) -> dict[str, float | int]:
    """Tighten entry thresholds near intervention levels.

    When BoJ intervention risk is elevated, require higher conviction and
    lower vol rank before entering.  Also widen effective stops via
    ``mie_multiplier``.
    """
    adjusted = dict(base_thresholds)
    if boj_regime == "ACTIVE":
        adjusted["conviction_enter_min"] = max(int(adjusted.get("conviction_enter_min", 3)) + 1, 4)
        adjusted["vol_rank_enter_max"] = float(adjusted.get("vol_rank_enter_max", 0.90)) * 0.85
        adjusted["mie_multiplier"] = float(adjusted.get("mie_multiplier", 1.0)) * 1.3
    elif boj_regime == "PROXIMAL":
        adjusted["conviction_enter_min"] = max(int(adjusted.get("conviction_enter_min", 3)) + 0, 3)
        adjusted["vol_rank_enter_max"] = float(adjusted.get("vol_rank_enter_max", 0.90)) * 0.92
        adjusted["mie_multiplier"] = float(adjusted.get("mie_multiplier", 1.0)) * 1.15
    return adjusted


def get_usdjpy_thresholds(
    boj_regime: BojInterventionRegime = "DORMANT",
) -> dict[str, float | int]:
    """Return USDJPY-specific execution and regime thresholds."""
    base = {
        "hysteresis_tier4": _HYSTERESIS_TIER4,
        "hysteresis_tier3": _HYSTERESIS_TIER3,
        "hysteresis_tier2": _HYSTERESIS_TIER2,
        "hysteresis_tier1": _HYSTERESIS_TIER1,
        "vol_rank_enter_max": _VOL_RANK_ENTER_MAX,
        "conviction_enter_min": _CONVICTION_ENTER_MIN,
        "adr_multiplier": 1.5,
        "mie_multiplier": 1.2,
        "intervention_proximity_discount": True,
    }
    return intervention_adjusted_thresholds(base, boj_regime)
