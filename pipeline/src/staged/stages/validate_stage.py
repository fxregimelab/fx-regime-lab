"""ValidateStage: evaluate prior regime calls at T+5/T+20 horizons."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from typing import Any

from src.staged.contracts import IngestionSnapshot
from src.staged.ports import WriterPort
from src.types import RegimeCall
from src.validation.calendar import add_trading_days


class ValidateStage:
    """Evaluate prior calls against realized spot moves and write validation rows."""

    def __init__(self, writer: WriterPort) -> None:
        self.writer = writer

    def _prior_calls(self, pair: str) -> list[RegimeCall]:
        """Read prior calls from the writer when available (e.g. fake writer)."""

        if hasattr(self.writer, "regime_calls"):
            calls: list[tuple[RegimeCall, dict[str, Any]]] = self.writer.regime_calls
            return [call for call, _meta in calls if call.pair == pair]
        return []

    def _spot_for_date(
        self,
        pair: str,
        target_date: date,
        snapshot: IngestionSnapshot,
    ) -> float | None:
        """Return the spot close for ``target_date`` from the snapshot if present."""

        bars = snapshot.spots.get(pair, ())
        for bar in bars:
            if bar.date == target_date:
                return float(bar.close)
        return None

    def _compute_horizon(
        self,
        s0: float,
        sh: float | None,
        predicted: str,
        confidence: float,
        pair: str,
    ) -> dict[str, Any] | None:
        """Compute T+5/T+20 validation metrics including cost-adjusted returns."""

        if sh is None:
            return None
        bps_gross = 10_000.0 * math.log(sh / s0)
        cost_bps = {"EURUSD": 0.2, "USDJPY": 0.3, "USDINR": 10.0}.get(pair, 0.5)
        bps_net = bps_gross - cost_bps
        realized = (
            "UP"
            if bps_gross > 5.0
            else ("DOWN" if bps_gross < -5.0 else "NEUTRAL")
        )
        pred = predicted.strip().upper()
        if pred == "BULLISH":
            correct = realized == "UP"
        elif pred == "BEARISH":
            correct = realized == "DOWN"
        else:
            correct = realized == "NEUTRAL"
        brier = (confidence - (1.0 if correct else 0.0)) ** 2
        return {
            "log_return_bps": bps_gross,
            "log_return_net_bps": bps_net,
            "realized_direction": realized,
            "correct": correct,
            "correct_net": correct,
            "brier_score": brier,
            "cost_bps": cost_bps,
        }

    def run(
        self,
        as_of: date,
        pairs: Sequence[str],
        *,
        snapshot: IngestionSnapshot,
    ) -> list[dict[str, Any]]:
        """Validate prior calls for ``pairs`` and write rows via the writer port."""

        rows: list[dict[str, Any]] = []
        for pair in pairs:
            bars = snapshot.spots.get(pair, ())
            for call in self._prior_calls(pair):
                s0_bar = next((b for b in bars if b.date == call.date), None)
                if s0_bar is None or s0_bar.close is None:
                    continue
                s0 = float(s0_bar.close)

                payload: dict[str, Any] = {
                    "call_date": call.date.isoformat(),
                    "date": call.date.isoformat(),
                    "pair": pair,
                    "predicted_direction": call.predicted_direction or call.rate_signal,
                    "predicted_regime": call.regime,
                    "confidence": call.confidence,
                }

                t5_date = add_trading_days(call.date, 5)
                if as_of >= t5_date:
                    sh = self._spot_for_date(pair, t5_date, snapshot)
                    stats = self._compute_horizon(
                        s0,
                        sh,
                        call.predicted_direction or call.rate_signal,
                        call.confidence,
                        pair,
                    )
                    if stats is not None:
                        payload["log_return_t5_bps"] = stats["log_return_bps"]
                        payload["correct_t5"] = stats["correct"]
                        payload["brier_score_t5"] = stats["brier_score"]
                        payload["actual_direction_t5"] = stats["realized_direction"]
                        payload["actual_return_5d"] = stats["log_return_bps"] / 10_000.0
                        payload["correct_5d"] = stats["correct"]
                        payload["brier_5d"] = stats["brier_score"]
                        payload["log_return_net_bps_t5"] = stats["log_return_net_bps"]
                        payload["correct_net_t5"] = stats["correct_net"]
                        payload["cost_bps_t5"] = stats["cost_bps"]

                t20_date = add_trading_days(call.date, 20)
                if as_of >= t20_date:
                    sh = self._spot_for_date(pair, t20_date, snapshot)
                    stats = self._compute_horizon(
                        s0,
                        sh,
                        call.predicted_direction or call.rate_signal,
                        call.confidence,
                        pair,
                    )
                    if stats is not None:
                        payload["log_return_t20_bps"] = stats["log_return_bps"]
                        payload["correct_t20"] = stats["correct"]
                        payload["brier_score_t20"] = stats["brier_score"]
                        payload["actual_direction_t20"] = stats["realized_direction"]
                        payload["actual_return_20d"] = stats["log_return_bps"] / 10_000.0
                        payload["correct_20d"] = stats["correct"]
                        payload["brier_20d"] = stats["brier_score"]
                        payload["log_return_net_bps_t20"] = stats["log_return_net_bps"]
                        payload["correct_net_t20"] = stats["correct_net"]
                        payload["cost_bps_t20"] = stats["cost_bps"]

                if (
                    payload.get("log_return_t5_bps") is not None
                    or payload.get("log_return_t20_bps") is not None
                ):
                    rows.append(payload)

        if rows:
            self.writer.write_validation_rows(rows)
        return rows
