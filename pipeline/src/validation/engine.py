from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.db import writer
from src.types import load_universe
from src.validation.calculator import (
    COST_BPS_ROUND_TRIP,
    DEADBAND_BPS,
    HorizonMetrics,
    brier_score,
    compute_horizon_metrics,
    horizon_metrics_to_payload,
    is_correct,
    is_correct_net,
    log_return_bps,
    realized_direction,
)
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)

__all__ = [
    "COST_BPS_ROUND_TRIP",
    "DEADBAND_BPS",
    "HorizonMetrics",
    "brier_score",
    "compute_horizon_metrics",
    "horizon_metrics_to_payload",
    "is_correct",
    "is_correct_net",
    "log_return_bps",
    "realized_direction",
    "run_validation",
]


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
    """Backward-compatible dict wrapper around compute_horizon_metrics."""
    if sh_row is None or sh_row.get("spot") is None:
        return None

    metrics = compute_horizon_metrics(
        s0,
        float(sh_row["spot"]),
        predicted,
        confidence,
        pair,
    )
    if metrics is None:
        return None

    return {
        "log_return_bps": metrics.log_return_bps,
        "log_return_net_bps": metrics.log_return_net_bps,
        "realized_direction": metrics.realized_direction,
        "correct": metrics.correct,
        "correct_net": metrics.correct_net,
        "brier_score": metrics.brier_score,
        "cost_bps": metrics.cost_bps,
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

            if existing and existing.get("log_return_t5_bps") is not None:
                for key in (
                    "log_return_t5_bps",
                    "correct_t5",
                    "brier_score_t5",
                    "actual_direction_t5",
                    "actual_return_5d",
                    "correct_5d",
                    "brier_5d",
                    "log_return_net_bps_t5",
                    "correct_net_t5",
                    "cost_bps_t5",
                ):
                    if existing.get(key) is not None:
                        payload[key] = existing[key]
            else:
                sh_row = writer.get_signal_for_pair_date(pair, t5_date.isoformat())
                t5_metrics = compute_horizon_metrics(
                    s0,
                    float(sh_row["spot"]) if sh_row and sh_row.get("spot") is not None else None,
                    predicted,
                    confidence,
                    pair,
                )
                if t5_metrics is not None:
                    payload.update(horizon_metrics_to_payload(t5_metrics, "t5"))
                else:
                    logger.warning(
                        "Validation skip: missing T+5 spot for %s on %s",
                        pair,
                        t5_date.isoformat(),
                    )

            if as_of_date >= t20_date:
                if existing and existing.get("log_return_t20_bps") is not None:
                    for key in (
                        "log_return_t20_bps",
                        "correct_t20",
                        "brier_score_t20",
                        "actual_direction_t20",
                        "actual_return_20d",
                        "correct_20d",
                        "brier_20d",
                        "log_return_net_bps_t20",
                        "correct_net_t20",
                        "cost_bps_t20",
                    ):
                        if existing.get(key) is not None:
                            payload[key] = existing[key]
                else:
                    sh_row = writer.get_signal_for_pair_date(pair, t20_date.isoformat())
                    t20_spot = (
                        float(sh_row["spot"])
                        if sh_row and sh_row.get("spot") is not None
                        else None
                    )
                    t20_metrics = compute_horizon_metrics(
                        s0,
                        t20_spot,
                        predicted,
                        confidence,
                        pair,
                    )
                    if t20_metrics is not None:
                        payload.update(horizon_metrics_to_payload(t20_metrics, "t20"))
                    else:
                        logger.warning(
                            "Validation skip: missing T+20 spot for %s on %s",
                            pair,
                            t20_date.isoformat(),
                        )

            has_t5 = payload.get("log_return_t5_bps") is not None
            has_t20 = payload.get("log_return_t20_bps") is not None
            if has_t5 or has_t20:
                writer.write_validation_row(payload)
