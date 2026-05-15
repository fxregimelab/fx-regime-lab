"""EURUSD pair-specific regime detection.

Tighter hysteresis thresholds than the universal default, plus ECB policy
regime detection (QE / QT / Neutral).
"""

from __future__ import annotations

from typing import Literal

EcbPolicyRegime = Literal["QE", "QT", "NEUTRAL"]

# Tighter EURUSD hysteresis thresholds (vs universal defaults in math_core)
_HYSTERESIS_TIER4 = 1.0
_HYSTERESIS_TIER3 = 0.45
_HYSTERESIS_TIER2 = -0.35
_HYSTERESIS_TIER1 = -1.0

_VOL_RANK_ENTER_MAX = 0.85
_CONVICTION_ENTER_MIN = 3


def eurusd_hysteresis_tier(
    composite: float,
    prior_tier: int | None,
) -> int:
    """Five-tier Schmitt trigger for EURUSD (0=strong bear … 4=strong bull).

    Thresholds are slightly tighter than the universal defaults to reflect
    EURUSD's lower realised volatility and higher signal-to-noise in rates.
    """

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
    if pt == 3 and composite < 0.28:
        return t_new

    if pt == 1 and composite < _HYSTERESIS_TIER1:
        return 0
    if pt == 1 and composite > -0.28:
        return t_new

    if pt == 2 and abs(composite) < 0.15:
        return 2

    return t_new


def detect_ecb_policy_regime(
    ecb_deposit_rate: float | None,
    ecb_balance_sheet_yoy: float | None,
    ecb_net_purchases_12m: float | None,
) -> EcbPolicyRegime:
    """Classify ECB policy stance into QE, QT, or Neutral.

    Parameters
    ----------
    ecb_deposit_rate:
        Current ECB deposit facility rate (%).
    ecb_balance_sheet_yoy:
        Year-over-year change in ECB balance sheet (%).
    ecb_net_purchases_12m:
        Rolling 12-month net asset purchases (EUR bn, positive = buying).

    Returns
    -------
    ``"QE"`` when the ECB is actively expanding the balance sheet,
    ``"QT"`` when contracting, ``"NEUTRAL"`` otherwise.
    """
    if ecb_net_purchases_12m is not None and ecb_balance_sheet_yoy is not None:
        if ecb_net_purchases_12m > 50.0 and ecb_balance_sheet_yoy > 2.0:
            return "QE"
        if ecb_net_purchases_12m < -50.0 and ecb_balance_sheet_yoy < -2.0:
            return "QT"

    # Fallback using deposit rate + balance sheet growth
    if ecb_deposit_rate is not None and ecb_balance_sheet_yoy is not None:
        if ecb_deposit_rate < 0.0 and ecb_balance_sheet_yoy > 0.0:
            return "QE"
        if ecb_deposit_rate > 2.0 and ecb_balance_sheet_yoy < -1.0:
            return "QT"

    return "NEUTRAL"


def ecb_regime_adjustment_factor(
    ecb_regime: EcbPolicyRegime,
    composite: float,
) -> float:
    """Return a multiplier that scales the composite based on ECB regime.

    QT amplifies USD strength signals (negative composite) because balance
    sheet contraction tightens EUR liquidity.  QE does the opposite.
    """
    if ecb_regime == "QT":
        # Amplify bearish EUR (negative composite), dampen bullish
        return 1.15 if composite < 0.0 else 0.90
    if ecb_regime == "QE":
        # Amplify bullish EUR, dampen bearish
        return 1.15 if composite > 0.0 else 0.90
    return 1.0


def get_eurusd_thresholds() -> dict[str, float | int]:
    """Return EURUSD-specific execution and regime thresholds."""
    return {
        "hysteresis_tier4": _HYSTERESIS_TIER4,
        "hysteresis_tier3": _HYSTERESIS_TIER3,
        "hysteresis_tier2": _HYSTERESIS_TIER2,
        "hysteresis_tier1": _HYSTERESIS_TIER1,
        "vol_rank_enter_max": _VOL_RANK_ENTER_MAX,
        "conviction_enter_min": _CONVICTION_ENTER_MIN,
        "adr_multiplier": 1.3,
        "mie_multiplier": 1.0,
    }
