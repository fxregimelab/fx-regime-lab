"""Next-day (or latest bar) validation for stored regime calls."""

from __future__ import annotations

from typing import Any

from src.types import RegimeCall, SpotBar


def validate_call(prior_call: RegimeCall, today_spots: dict[str, list[SpotBar]]) -> dict[str, Any]:
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
            "actual_direction": "flat",
        }

    bars_sorted = sorted(bars, key=lambda b: b.date)
    today_bar = bars_sorted[-1]
    if len(bars_sorted) >= 2:
        yest_bar = bars_sorted[-2]
    else:
        yest_bar = next((b for b in bars_sorted if b.date == prior_call.date), today_bar)

    yest_close = yest_bar.close
    today_close = today_bar.close
    if yest_close == 0:
        return_pct = 0.0
        ret_frac = 0.0
    else:
        ret_frac = (today_close - yest_close) / yest_close
        return_pct = ret_frac * 100.0

    regime = prior_call.regime
    outcome = "incorrect"

    if "NEUTRAL" in regime and "VOL_EXPANDING" in regime:
        outcome = "correct" if abs(return_pct) < 0.25 else "incorrect"
    elif "DEPRECIATION PRESSURE" in regime:
        outcome = "correct" if return_pct > 0 else "incorrect"
    elif "APPRECIATION PRESSURE" in regime:
        outcome = "correct" if return_pct < 0 else "incorrect"
    elif "USD STRENGTH" in regime:
        outcome = "correct" if return_pct > 0 else "incorrect"
    elif "USD WEAKNESS" in regime:
        outcome = "correct" if return_pct < 0 else "incorrect"
    elif regime == "NEUTRAL":
        outcome = "correct" if abs(return_pct) < 0.25 else "incorrect"

    return {
        "date": today_bar.date.isoformat(),
        "pair": pair,
        "predicted_regime": regime,
        "predicted_direction": prior_call.rate_signal,
        "confidence": prior_call.confidence,
        "correct_1d": outcome == "correct",
        "actual_return_1d": float(ret_frac),
        "actual_direction": (
            "up" if return_pct > 0 else "down" if return_pct < 0 else "flat"
        ),
    }
