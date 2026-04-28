"""Next-day (or latest bar) validation for stored regime calls."""

from __future__ import annotations

import math
from typing import Any

from src.types import RegimeCall, SpotBar


def _neutral_threshold_pct(realized_vol_20d: float | None) -> float:
    """Daily neutral band in pct points: 0.5 * daily realized vol."""
    if realized_vol_20d is None or realized_vol_20d <= 0:
        return 0.25
    daily_vol_pct = realized_vol_20d / math.sqrt(252.0)
    return max(0.05, 0.5 * daily_vol_pct)


def _is_correct_direction(regime: str, return_pct: float, neutral_threshold_pct: float) -> bool:
    if "NEUTRAL" in regime:
        return abs(return_pct) < neutral_threshold_pct
    if "DEPRECIATION_PRESSURE" in regime or "USD_STRENGTH" in regime or "INR_DEPR" in regime:
        return return_pct > 0
    if "APPRECIATION_PRESSURE" in regime or "USD_WEAKNESS" in regime or "INR_APPR" in regime:
        return return_pct < 0
    return False


def validate_call(
    prior_call: RegimeCall,
    today_spots: dict[str, list[SpotBar]],
    *,
    realized_vol_20d: float | None = None,
) -> dict[str, Any]:
    """Return a row dict aligned with Supabase `validation_log` (Phase 3 schema)."""
    pair = prior_call.pair
    bars = today_spots.get(pair, [])
    if not bars:
        return {
            "date": prior_call.date.isoformat(),
            "pair": pair,
            "predicted_regime": prior_call.regime,
            "predicted_direction": prior_call.rate_signal,
            "confidence": prior_call.confidence,
            "correct_1d": False,
            "actual_return_1d": 0.0,
            "correct_5d": None,
            "actual_return_5d": None,
            "actual_direction": "flat",
        }

    bars_sorted = sorted(bars, key=lambda b: b.date)
    call_idx = next(
        (idx for idx, bar in enumerate(bars_sorted) if bar.date == prior_call.date),
        max(0, len(bars_sorted) - 2),
    )
    base_bar = bars_sorted[call_idx]
    one_day_idx = min(call_idx + 1, len(bars_sorted) - 1)
    one_day_bar = bars_sorted[one_day_idx]

    if base_bar.close == 0:
        return_1d_frac = 0.0
    else:
        return_1d_frac = (one_day_bar.close - base_bar.close) / base_bar.close
    return_1d_pct = return_1d_frac * 100.0

    return_5d_frac: float | None = None
    five_day_idx = call_idx + 5
    if base_bar.close != 0 and five_day_idx < len(bars_sorted):
        five_day_bar = bars_sorted[five_day_idx]
        return_5d_frac = (five_day_bar.close - base_bar.close) / base_bar.close
    return_5d_pct = return_5d_frac * 100.0 if return_5d_frac is not None else None

    regime = prior_call.regime
    neutral_threshold_pct = _neutral_threshold_pct(realized_vol_20d)
    correct_1d = _is_correct_direction(regime, return_1d_pct, neutral_threshold_pct)
    correct_5d = (
        _is_correct_direction(regime, return_5d_pct, neutral_threshold_pct)
        if return_5d_pct is not None
        else None
    )

    return {
        "date": one_day_bar.date.isoformat(),
        "pair": pair,
        "predicted_regime": regime,
        "predicted_direction": prior_call.rate_signal,
        "confidence": prior_call.confidence,
        "correct_1d": correct_1d,
        "actual_return_1d": float(return_1d_frac),
        "correct_5d": correct_5d,
        "actual_return_5d": float(return_5d_frac) if return_5d_frac is not None else None,
        "actual_direction": (
            "up" if return_1d_pct > 0 else "down" if return_1d_pct < 0 else "flat"
        ),
    }
