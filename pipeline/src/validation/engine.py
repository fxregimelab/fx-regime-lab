from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

from src.db import writer
from src.types import load_universe
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)


def log_return_bps(s0: float, sh: float) -> float:
    """Log-return in basis points: 10_000 * ln(sh / s0)."""
    return 10_000.0 * math.log(sh / s0)


def realized_direction(bps: float, deadband: float = 5.0) -> str:
    """Map log-return bps to realized directional label."""
    if bps > deadband:
        return "UP"
    if bps < -deadband:
        return "DOWN"
    return "NEUTRAL"


def is_correct(predicted: str, realized: str) -> bool:
    """Check if predicted direction matches realized direction."""
    p = predicted.strip().upper()
    r = realized.strip().upper()
    if p == "BULLISH":
        return r == "UP"
    if p == "BEARISH":
        return r == "DOWN"
    if p == "NEUTRAL":
        return r == "NEUTRAL"
    return False


def brier_score(confidence: float, correct: bool) -> float | None:
    """Brier score: (p - y)^2.  Returns None for neutral predictions."""
    p = float(confidence)
    y = 1.0 if correct else 0.0
    return (p - y) ** 2


def _date_from_raw(raw: Any) -> date:
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw)[:10])


def run_validation(as_of_date: date | None = None) -> None:
    """Scan regime_calls for unvalidated T+5/T+20 horizons and write to validation_log."""
    if as_of_date is None:
        as_of_date = date.today()

    universe = load_universe()
    pairs = sorted(
        k
        for k, meta in universe.items()
        if isinstance(meta, dict) and meta.get("class") == "FX"
    )

    for pair in pairs:
        calls = writer.get_historical_regime_calls(pair, limit=30)
        for call in calls:
            call_date = _date_from_raw(call.get("date"))
            t5_date = add_trading_days(call_date, 5)
            t20_date = add_trading_days(call_date, 20)

            if as_of_date < t5_date:
                continue

            s0_row = writer.get_signal_for_pair_date(pair, call_date.isoformat())
            if s0_row is None or s0_row.get("spot") is None:
                logger.warning(
                    "Validation skip: missing spot for %s on %s", pair, call_date.isoformat()
                )
                continue
            s0 = float(s0_row["spot"])

            existing = writer.get_validation_log_entry(call_date, pair)

            payload: dict[str, Any] = {
                "call_date": call_date.isoformat(),
                "date": call_date.isoformat(),
                "pair": pair,
                "predicted_direction": call.get("rate_signal"),
                "predicted_regime": call.get("regime"),
                "confidence": call.get("confidence"),
            }

            # Backward compatibility fields
            payload["actual_return_1d"] = None
            payload["actual_return_5d"] = None
            payload["correct_1d"] = None
            payload["correct_5d"] = None

            if existing:
                # Carry forward existing T20 if already written
                for key in ("actual_return_5d", "correct_5d"):
                    if existing.get(key) is not None:
                        payload[key] = existing[key]

            # T+5 horizon
            if existing and existing.get("actual_return_5d") is not None:
                # Already validated T+5; carry forward
                payload["actual_return_5d"] = existing["actual_return_5d"]
                payload["correct_5d"] = existing["correct_5d"]
            else:
                sh_row = writer.get_signal_for_pair_date(pair, t5_date.isoformat())
                if sh_row is not None and sh_row.get("spot") is not None:
                    sh = float(sh_row["spot"])
                    bps = log_return_bps(s0, sh)
                    realized = realized_direction(bps)
                    predicted = str(call.get("rate_signal") or "")
                    correct = is_correct(predicted, realized)
                    payload["actual_return_5d"] = bps / 10_000.0
                    payload["correct_5d"] = correct
                    payload["actual_direction"] = realized
                else:
                    logger.warning(
                        "Validation skip: missing T+5 spot for %s on %s",
                        pair,
                        t5_date.isoformat(),
                    )

            # T+20 horizon (map to same columns for now — latest write wins)
            if as_of_date >= t20_date:
                sh_row = writer.get_signal_for_pair_date(pair, t20_date.isoformat())
                if sh_row is not None and sh_row.get("spot") is not None:
                    sh = float(sh_row["spot"])
                    bps = log_return_bps(s0, sh)
                    realized = realized_direction(bps)
                    predicted = str(call.get("rate_signal") or "")
                    correct = is_correct(predicted, realized)
                    payload["actual_return_5d"] = bps / 10_000.0
                    payload["correct_5d"] = correct
                    payload["actual_direction"] = realized
                else:
                    logger.warning(
                        "Validation skip: missing T+20 spot for %s on %s",
                        pair,
                        t20_date.isoformat(),
                    )

            # Only write if we have at least one horizon populated
            has_t5 = payload.get("actual_return_5d") is not None
            has_t20 = payload.get("correct_5d") is not None
            if has_t5 or has_t20:
                writer.write_validation_row(payload)
