"""Layer 1 deterministic regime gate — Aris priorities, composite hysteresis, Marcus invalidation."""

from __future__ import annotations

import numpy as np

from src.logic.math_utils import (
    hysteresis_tier_composite,
    log_return_series,
    momentum_last,
    rolling_zscore_last,
)
from src.models.regime_enums import FxRegime
from src.types import Layer1ClassifierContext, Layer1GateOutput

# Keep aligned with ``src.regime.classifier.VOL_EXPANDING_SUFFIX``.
VOL_EXPANDING_SUFFIX_LOCAL = "__VOL_EXPANDING"

_Z_WINDOW = 252
_Z_MIN_PERIODS = 90
_SPOT_RET_WINDOW = 21
_MOM_LAG = 20
_DELTA_PI_WINDOW = 5
_Z_POLICY = 2.0
_DELTA_PI_SHOCK_ABS = 0.12
_Z_CARRY_ELEVATED = 1.15
_M_CARRY_FADE_NEG = -0.25
_D_SPOT_STRESS_ABS = 2.5


def _strip_vol_suffix(label: str) -> str:
    return label.split(VOL_EXPANDING_SUFFIX_LOCAL, maxsplit=1)[0]


def prior_tier_from_regime(label: str | None, pair: str) -> int | None:
    """Infer composite tier used for hysteresis memory from yesterday's persisted label."""

    if not label:
        return None
    base = _strip_vol_suffix(label)

    tier_map: dict[str, int] = {
        "NEUTRAL": 2,
        "RISK_OFF_DOLLAR_BID": 4,
        "GROWTH_SURPRISE_USD": 3,
        "RISK_ON_DOLLAR_OFF": 1,
        "LIQUIDITY_SHOCK": 2,
        "USD_POLICY_BREAKOUT": 4,
        "CARRY_COLLAPSE": 2,
        "INR_NEUTRAL": 2,
        "INR_DEPRECIATION_MODERATE": 3,
        "INR_DEPRECIATION_STRONG": 4,
        "INR_APPRECIATION_MODERATE": 1,
        "INR_APPRECIATION_STRONG": 0,
        "USD_STRENGTH_STRONG": 4,
        "USD_STRENGTH_MODERATE": 3,
        "USD_WEAKNESS_MODERATE": 1,
        "USD_WEAKNESS_STRONG": 0,
        "INR_DEPR_STRONG": 4,
        "INR_DEPR_MODERATE": 3,
        "INR_APPR_MODERATE": 1,
        "INR_APPR_STRONG": 0,
    }
    mapped = tier_map.get(base)
    if mapped is None and pair.upper() == "USDINR":
        return tier_map.get(base.upper())
    return mapped


def _neutral_label_for_pair(pair: str) -> str:
    return FxRegime.INR_NEUTRAL.value if pair.upper() == "USDINR" else FxRegime.NEUTRAL.value


def _tier_to_regime(pair: str, tier: int) -> str:
    if pair.upper() == "USDINR":
        if tier >= 4:
            return FxRegime.INR_DEPRECIATION_STRONG.value
        if tier == 3:
            return FxRegime.INR_DEPRECIATION_MODERATE.value
        if tier == 2:
            return FxRegime.INR_NEUTRAL.value
        if tier == 1:
            return FxRegime.INR_APPRECIATION_MODERATE.value
        return FxRegime.INR_APPRECIATION_STRONG.value

    if tier >= 4:
        return FxRegime.RISK_OFF_DOLLAR_BID.value
    if tier == 3:
        return FxRegime.GROWTH_SURPRISE_USD.value
    if tier == 2:
        return FxRegime.NEUTRAL.value
    if tier == 1:
        return FxRegime.RISK_ON_DOLLAR_OFF.value
    return FxRegime.RISK_ON_DOLLAR_OFF.value


def _apply_vol_neutral_overlay(raw_label: str, vol_expanding: bool) -> str:
    if not vol_expanding:
        return raw_label
    if raw_label in (FxRegime.NEUTRAL.value, FxRegime.INR_NEUTRAL.value):
        return f"{raw_label}{VOL_EXPANDING_SUFFIX_LOCAL}"
    return raw_label


def regime_from_composite_snapshot(
    composite: float,
    pair: str,
    *,
    vol_expanding: bool = False,
    prior_regime_label: str | None = None,
) -> str:
    """Composite hysteresis tiers only (Marcus staleness skipped — notebooks / regressions)."""

    prior_tier = prior_tier_from_regime(prior_regime_label, pair)
    tier = hysteresis_tier_composite(composite, prior_tier)
    raw = _tier_to_regime(pair, tier)
    return _apply_vol_neutral_overlay(raw, vol_expanding)


def run_layer1_gate(ctx: Layer1ClassifierContext) -> Layer1GateOutput:
    """Produce Layer 1 state; Marcus invalidates the gate when staleness violates Rule 3.3."""

    stale_fields: list[str] = []

    carry = np.asarray(ctx.carry_risk_adjusted_chronological, dtype=np.float64)
    spots = np.asarray(ctx.spot_closes_chronological, dtype=np.float64)

    if ctx.rate_diff_2y is None:
        stale_fields.append("rate_diff_2y")
    if ctx.realized_vol_20d is None:
        stale_fields.append("realized_vol_20d")
    if carry.size < _Z_WINDOW:
        stale_fields.append("carry_series_short")
    if spots.size < _SPOT_RET_WINDOW + 1:
        stale_fields.append("spot_series_short")

    invalidated = len(stale_fields) > 0

    z_rate: float | None = None
    m_rate: float | None = None
    delta_pi: float | None = None
    d_spot: float | None = None

    if not invalidated:
        z_rate = rolling_zscore_last(carry, _Z_WINDOW, min_periods=_Z_MIN_PERIODS)
        m_rate = momentum_last(carry, _MOM_LAG)

        bei = ctx.breakeven_inflation_chronological
        if bei is not None and len(bei) >= _DELTA_PI_WINDOW + 1:
            bei_arr = np.asarray(bei[-(_DELTA_PI_WINDOW + 1) :], dtype=np.float64)
            first_b = bei_arr[0]
            last_b = bei_arr[-1]
            if np.isfinite(first_b) and np.isfinite(last_b):
                delta_pi = float(last_b - first_b)

        rets = log_return_series(spots)
        if int(rets.size) >= _SPOT_RET_WINDOW:
            tail_rets = rets[-_SPOT_RET_WINDOW :]
            if bool(np.all(np.isfinite(tail_rets))) and float(np.nanstd(tail_rets)) > 1e-18:
                d_spot = rolling_zscore_last(
                    tail_rets,
                    _SPOT_RET_WINDOW,
                    min_periods=min(12, _SPOT_RET_WINDOW - 1),
                )

    if invalidated:
        raw = _neutral_label_for_pair(ctx.pair)
        return Layer1GateOutput(
            regime=_apply_vol_neutral_overlay(raw, ctx.vol_expanding),
            invalidated=True,
            z_rate=None,
            m_rate=None,
            delta_pi=None,
            d_spot=None,
            stale_fields=stale_fields,
            raw_regime=raw,
        )

    raw_regime_candidate: str
    if ctx.structural_instability:
        raw_regime_candidate = FxRegime.CARRY_COLLAPSE.value
    elif (
        delta_pi is not None
        and abs(delta_pi) >= _DELTA_PI_SHOCK_ABS
        and z_rate is not None
        and abs(z_rate) >= _Z_POLICY
    ):
        raw_regime_candidate = FxRegime.USD_POLICY_BREAKOUT.value
    elif (
        z_rate is not None
        and m_rate is not None
        and z_rate >= _Z_CARRY_ELEVATED
        and m_rate <= _M_CARRY_FADE_NEG
    ):
        raw_regime_candidate = FxRegime.CARRY_COLLAPSE.value
    elif d_spot is not None and abs(d_spot) >= _D_SPOT_STRESS_ABS:
        raw_regime_candidate = FxRegime.LIQUIDITY_SHOCK.value
    else:
        prior_tier = prior_tier_from_regime(ctx.prior_regime_label, ctx.pair)
        tier = hysteresis_tier_composite(ctx.composite, prior_tier)
        raw_regime_candidate = _tier_to_regime(ctx.pair, tier)

    overlay = _apply_vol_neutral_overlay(raw_regime_candidate, ctx.vol_expanding)

    return Layer1GateOutput(
        regime=overlay,
        invalidated=False,
        z_rate=z_rate,
        m_rate=m_rate,
        delta_pi=delta_pi,
        d_spot=d_spot,
        stale_fields=stale_fields,
        raw_regime=raw_regime_candidate,
    )
