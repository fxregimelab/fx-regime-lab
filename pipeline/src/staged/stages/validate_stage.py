"""ValidateStage: evaluate prior regime calls at T+5/T+20 horizons."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from src.staged.contracts import IngestionSnapshot
from src.staged.ports import WriterPort
from src.types import RegimeCall
from src.validation.calculator import compute_horizon_metrics, horizon_metrics_to_payload
from src.validation.calendar import add_trading_days


class ValidateStage:
    """Evaluate prior calls against realized spot moves and write validation rows."""

    def __init__(self, writer: WriterPort) -> None:
        self.writer = writer

    def _prior_calls(self, pair: str) -> list[RegimeCall]:
        """Read prior calls for ``pair`` via the writer port."""

        return self.writer.get_regime_calls(pair)

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

                predicted = call.predicted_direction or call.rate_signal
                payload: dict[str, Any] = {
                    "call_date": call.date.isoformat(),
                    "date": call.date.isoformat(),
                    "pair": pair,
                    "predicted_direction": predicted,
                    "predicted_regime": call.regime,
                    "confidence": call.confidence,
                }

                t5_date = add_trading_days(call.date, 5)
                if as_of >= t5_date:
                    sh = self._spot_for_date(pair, t5_date, snapshot)
                    metrics = compute_horizon_metrics(
                        s0,
                        sh,
                        predicted,
                        call.confidence,
                        pair,
                    )
                    if metrics is not None:
                        payload.update(horizon_metrics_to_payload(metrics, "t5"))

                t20_date = add_trading_days(call.date, 20)
                if as_of >= t20_date:
                    sh = self._spot_for_date(pair, t20_date, snapshot)
                    metrics = compute_horizon_metrics(
                        s0,
                        sh,
                        predicted,
                        call.confidence,
                        pair,
                    )
                    if metrics is not None:
                        payload.update(horizon_metrics_to_payload(metrics, "t20"))

                if (
                    payload.get("log_return_t5_bps") is not None
                    or payload.get("log_return_t20_bps") is not None
                ):
                    rows.append(payload)

        if rows:
            self.writer.write_validation_rows(rows)
        return rows
