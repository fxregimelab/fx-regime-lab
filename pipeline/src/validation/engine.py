from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

from src.db import writer
from src.types import load_universe
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)

# v2.1: Transaction cost assumptions for realistic performance reporting
COST_BPS_ROUND_TRIP = {
    "EURUSD": 0.2,   # 0.1 bps each way
    "USDJPY": 0.3,
    "USDINR": 10.0,  # EM spread
}


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


def _compute_horizon(
    s0: float,
    sh_row: dict[str, Any] | None,
    predicted: str,
    confidence: float,
    pair: str,
) -> dict[str, Any] | None:
    """Compute validation metrics including cost-adjusted returns."""
    if sh_row is None or sh_row.get("spot") is None:
        return None
    
    sh = float(sh_row["spot"])
    bps_gross = log_return_bps(s0, sh)
    
    # v2.1: Cost-adjusted metrics
    cost_bps = COST_BPS_ROUND_TRIP.get(pair, 0.5)
    bps_net = bps_gross - cost_bps
    
    realized_gross = realized_direction(bps_gross)
    # v2.1 fix: Net correctness uses SAME realized direction as gross.
    # Costs affect P&L and returns, not directional accuracy.
    correct_gross = is_correct(predicted, realized_gross)
    correct_net = correct_gross
    
    brier = brier_score(confidence, correct_gross)  # Brier on gross (existing)
    
    return {
        "log_return_bps": bps_gross,
        "log_return_net_bps": bps_net,
        "realized_direction": realized_gross,
        "correct": correct_gross,
        "correct_net": correct_net,
        "brier_score": brier,
        "cost_bps": cost_bps,
    }


def run_validation(as_of_date: date | None = None) -> None:
    """Scan regime_calls for unvalidated T+5/T+20 horizons and write to validation_log.

    For every historical regime call that has reached its T+5 or T+20 horizon,
    fetch the spot price on that horizon date, compute the log-return in bps,
    realized direction, correctness flag, and Brier score, then write (or
    update) a single ``validation_log`` row per call.

    T+5 and T+20 metrics are stored in separate columns so they coexist.
    """
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
            call_id = call.get("id")
            t5_date = add_trading_days(call_date, 5)
            t20_date = add_trading_days(call_date, 20)

            # Skip if we haven't even reached T+5 yet
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

            predicted = str(call.get("predicted_direction") or call.get("rate_signal") or "")
            confidence = float(call.get("confidence") or 0.0)

            payload: dict[str, Any] = {
                "call_date": call_date.isoformat(),
                "date": call_date.isoformat(),
                "pair": pair,
                "predicted_direction": predicted,
                "predicted_regime": call.get("regime"),
                "confidence": confidence,
            }

            if call_id is not None:
                payload["call_id"] = call_id

            # ── T+5 horizon ──────────────────────────────────────────────
            t5_stats: dict[str, Any] | None = None
            if existing and existing.get("log_return_t5_bps") is not None:
                # T+5 already validated — carry forward all T+5 fields
                for key in (
                    "log_return_t5_bps",
                    "correct_t5",
                    "brier_score_t5",
                    "actual_direction_t5",
                    "actual_return_5d",
                    "correct_5d",
                    "brier_5d",
                ):
                    if existing.get(key) is not None:
                        payload[key] = existing[key]
            else:
                sh_row = writer.get_signal_for_pair_date(pair, t5_date.isoformat())
                t5_stats = _compute_horizon(s0, sh_row, predicted, confidence, pair)
                if t5_stats is not None:
                    payload["log_return_t5_bps"] = t5_stats["log_return_bps"]
                    payload["correct_t5"] = t5_stats["correct"]
                    payload["brier_score_t5"] = t5_stats["brier_score"]
                    payload["actual_direction_t5"] = t5_stats["realized_direction"]
                    # Legacy columns (decimal fraction)
                    payload["actual_return_5d"] = t5_stats["log_return_bps"] / 10_000.0
                    payload["correct_5d"] = t5_stats["correct"]
                    payload["brier_5d"] = t5_stats["brier_score"]
                    payload["log_return_net_bps_t5"] = t5_stats["log_return_net_bps"]
                    payload["correct_net_t5"] = t5_stats["correct_net"]
                    payload["cost_bps_t5"] = t5_stats["cost_bps"]
                else:
                    logger.warning(
                        "Validation skip: missing T+5 spot for %s on %s",
                        pair,
                        t5_date.isoformat(),
                    )

            # ── T+20 horizon ─────────────────────────────────────────────
            t20_stats: dict[str, Any] | None = None
            if as_of_date >= t20_date:
                if existing and existing.get("log_return_t20_bps") is not None:
                    # T+20 already validated — carry forward
                    for key in (
                        "log_return_t20_bps",
                        "correct_t20",
                        "brier_score_t20",
                        "actual_direction_t20",
                        "actual_return_20d",
                        "correct_20d",
                        "brier_20d",
                    ):
                        if existing.get(key) is not None:
                            payload[key] = existing[key]
                else:
                    sh_row = writer.get_signal_for_pair_date(pair, t20_date.isoformat())
                    t20_stats = _compute_horizon(s0, sh_row, predicted, confidence, pair)
                    if t20_stats is not None:
                        payload["log_return_t20_bps"] = t20_stats["log_return_bps"]
                        payload["correct_t20"] = t20_stats["correct"]
                        payload["brier_score_t20"] = t20_stats["brier_score"]
                        payload["actual_direction_t20"] = t20_stats["realized_direction"]
                        # Legacy-style T+20 columns
                        payload["actual_return_20d"] = t20_stats["log_return_bps"] / 10_000.0
                        payload["correct_20d"] = t20_stats["correct"]
                        payload["brier_20d"] = t20_stats["brier_score"]
                        payload["log_return_net_bps_t20"] = t20_stats["log_return_net_bps"]
                        payload["correct_net_t20"] = t20_stats["correct_net"]
                        payload["cost_bps_t20"] = t20_stats["cost_bps"]
                    else:
                        logger.warning(
                            "Validation skip: missing T+20 spot for %s on %s",
                            pair,
                            t20_date.isoformat(),
                        )

            # ── Write ────────────────────────────────────────────────────
            has_t5 = payload.get("log_return_t5_bps") is not None
            has_t20 = payload.get("log_return_t20_bps") is not None
            if has_t5 or has_t20:
                writer.write_validation_row(payload)
