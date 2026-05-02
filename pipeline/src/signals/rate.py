"""Yield spread signal and normalization (robust MAD Z-score, dual horizon)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

MAD_NORMAL_SCALE = 1.4826
MAD_NOISE_FLOOR = 0.0001
CARRY_LOOKBACK_DAYS = 1260
TACTICAL_MAD_DAYS = 252
STRUCTURAL_MAD_DAYS = 2520


@dataclass(frozen=True)
class RateNormZ:
    """Dual-horizon robust Z on the same carry series (clipped composite inputs)."""

    z_tactical: float | None
    z_structural: float | None


def _to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_carry_history_from_rows(
    historical_rows: list[dict[str, Any]],
    *,
    max_points: int = CARRY_LOOKBACK_DAYS,
) -> list[float]:
    """Risk-adjusted carry (2Y / RV20) oldest-first, at most ``max_points`` most recent points."""

    parsed: list[tuple[date, float]] = []
    for row in historical_rows:
        dt = _to_date(row.get("date"))
        if dt is None:
            continue
        rate_2y = _to_float(row.get("rate_diff_2y"))
        rv20f = _to_float(row.get("realized_vol_20d"))
        if rate_2y is None or rv20f is None or rv20f <= 0.0:
            continue
        parsed.append((dt, rate_2y / rv20f))
    parsed.sort(key=lambda x: x[0])
    tail = parsed[-max_points:] if len(parsed) > max_points else parsed
    return [v for _, v in tail]


def build_real_yield_10y_spread_history_from_rows(
    historical_rows: list[dict[str, Any]],
    *,
    max_points: int = CARRY_LOOKBACK_DAYS,
) -> list[float]:
    """Nominal 10Y pair spread minus same-day breakeven (when present); oldest-first.

    Real_Yield_10Y ≈ ``rate_diff_10y - breakeven_inflation_10y``. Missing breakeven falls back
    to nominal ``rate_diff_10y`` so backfilled history still produces a structural series.
    """

    parsed: list[tuple[date, float]] = []
    for row in historical_rows:
        dt = _to_date(row.get("date"))
        if dt is None:
            continue
        r10 = _to_float(row.get("rate_diff_10y"))
        if r10 is None:
            continue
        bei = _to_float(row.get("breakeven_inflation_10y"))
        real = float(r10) - float(bei) if bei is not None else float(r10)
        parsed.append((dt, real))
    parsed.sort(key=lambda x: x[0])
    tail = parsed[-max_points:] if len(parsed) > max_points else parsed
    return [v for _, v in tail]


def median_abs_deviation(values: npt.NDArray[np.float64]) -> float:
    """MAD about the median (raw, not scaled by 1.4826)."""

    if values.size == 0:
        return 0.0
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med)))
    return mad


def structural_instability_from_carry_history(carry_chronological: list[float]) -> bool:
    """True when short-horizon carry dispersion materially exceeds long-horizon (regime shift)."""

    arr = np.asarray(carry_chronological, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size < 252:
        return False
    tail_long = arr[-1260:] if arr.size >= 1260 else arr
    tail_short = arr[-252:]
    mad_long = median_abs_deviation(tail_long)
    mad_short = median_abs_deviation(tail_short)
    if mad_long < 1e-12:
        return False
    return bool(mad_short > 1.5 * mad_long)


def rate_direction_from_spreads(
    spread_2y: float | None,
    spread_10y: float | None,
) -> str:
    """Map 2Y (preferred) or 10Y spread in pp to BULLISH / BEARISH / NEUTRAL."""

    directional = spread_2y if spread_2y is not None else spread_10y
    if directional is None:
        return "NEUTRAL"
    if directional > 0.5:
        return "BULLISH"
    if directional < -0.5:
        return "BEARISH"
    return "NEUTRAL"


def _mad_z_from_series(
    spread: float,
    arr: npt.NDArray[np.float64],
    lookback: int,
    label: str,
    pair: str,
) -> float | None:
    n = min(lookback, int(arr.size))
    tail = arr[-n:]
    if tail.size == 0:
        return None
    med = float(np.median(tail))
    mad = float(np.median(np.abs(tail - med)))
    if mad < MAD_NOISE_FLOOR:
        logger.info("Rate normalization %s noise floor: MAD=%s for %s — Z=0", label, mad, pair)
        return 0.0
    z = (float(spread) - med) / (mad * MAD_NORMAL_SCALE)
    z_clipped = float(np.clip(z, -2.0, 2.0))
    return z_clipped / 2.0


def normalize_rate_signal(
    spread: float,
    pair: str,
    historical_spreads: list[float],
    *,
    spread_structural: float | None = None,
    historical_structural: list[float] | None = None,
) -> RateNormZ:
    """252d tactical MAD Z on carry; 2520d structural on real 10Y spread when available.

    Tactical input ``spread`` is typically risk-adjusted carry (2Y / RV20). Structural uses
    ``spread_structural`` (nominal 10Y pair spread minus breakeven) against
    ``historical_structural`` (same construction on past days). If structural history is
    omitted, structural Z reuses the tactical series (legacy behavior).
    """

    arr = np.asarray(historical_spreads[-CARRY_LOOKBACK_DAYS:], dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        logger.info("Rate normalization fallback: empty history for %s", pair)
        return RateNormZ(z_tactical=None, z_structural=None)

    z_tactical = _mad_z_from_series(
        spread, arr, TACTICAL_MAD_DAYS, "tactical", pair
    )
    hist_s = historical_structural
    ss = spread_structural
    use_real_structural = ss is not None and hist_s is not None and len(hist_s) > 0
    if use_real_structural:
        assert hist_s is not None and ss is not None
        arr_s = np.asarray(hist_s[-CARRY_LOOKBACK_DAYS:], dtype=np.float64)
        arr_s = arr_s[np.isfinite(arr_s)]
        if arr_s.size == 0:
            z_structural = _mad_z_from_series(
                spread, arr, STRUCTURAL_MAD_DAYS, "structural", pair
            )
        else:
            z_structural = _mad_z_from_series(
                ss,
                arr_s,
                STRUCTURAL_MAD_DAYS,
                "structural_real10y",
                pair,
            )
    else:
        z_structural = _mad_z_from_series(
            spread, arr, STRUCTURAL_MAD_DAYS, "structural", pair
        )

    return RateNormZ(z_tactical=z_tactical, z_structural=z_structural)


def compute_risk_adjusted_carry(
    rate_diff_2y: float | None, realized_vol_20d: float | None, pair: str
) -> float | None:
    """Return carry normalized by realized volatility."""

    if rate_diff_2y is None:
        logger.info("Risk_Adjusted_Carry unavailable for %s: missing rate_diff_2y", pair)
        return None
    if realized_vol_20d is None or realized_vol_20d <= 0.0:
        logger.info("Risk_Adjusted_Carry unavailable for %s: invalid realized_vol_20d", pair)
        return None
    return rate_diff_2y / realized_vol_20d
