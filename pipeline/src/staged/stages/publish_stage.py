"""PublishStage: persist a RegimeCall and emit alerts."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

from src.staged.contracts import PublishOutput, StageHealth, combine_stage_health
from src.staged.ports import AlertPort, WriterPort
from src.types import RegimeCall, SignalRow


class PublishStage:
    """Persist a regime call via the writer port and notify via the alert port."""

    def __init__(
        self,
        writer: WriterPort,
        alert: AlertPort,
        *,
        correlation_id: str | None = None,
    ) -> None:
        self.writer = writer
        self.alert = alert
        self.correlation_id = correlation_id

    async def run(
        self,
        pair: str,
        regime_call: RegimeCall,
        *,
        signal_row: SignalRow,
        upstream_health: Sequence[StageHealth],
    ) -> PublishOutput:
        """Publish the call and evidence atomically, then report input quality."""

        if not upstream_health:
            raise ValueError("Publication requires upstream stage health evidence")
        if pair != regime_call.pair or (signal_row.pair, signal_row.date) != (
            regime_call.pair,
            regime_call.date,
        ):
            raise ValueError("Publication call and signal identity must match")
        dqs = regime_call.data_quality_score
        quality = StageHealth("DataQuality", "OK")
        if dqs is None or not isfinite(dqs) or not 0 <= dqs <= 1:
            quality = StageHealth("DataQuality", "DEGRADED", missing_fields=["valid_dqs_score"])
        elif dqs < 0.75:
            quality = StageHealth("DataQuality", "DEGRADED", notes=["low_dqs"])
        health = combine_stage_health("PublishStage", *upstream_health, quality)
        if health.status == "FAILED":
            raise ValueError("Cannot publish after a failed input stage")

        alerts_sent: list[str] = []
        call_id = self.writer.publish_regime_call(
            regime_call,
            signal_row,
            correlation_id=self.correlation_id,
        )
        if (
            call_id is None
            or isinstance(call_id, bool)
            or str(call_id).strip() == ""
            or (isinstance(call_id, int) and call_id <= 0)
        ):
            raise RuntimeError("Call publication returned no durable row id")
        alerts_sent.append(f"wrote_regime_call:{call_id}")

        if health.status == "OK":
            self.alert.send_success(regime_call)
            alerts_sent.append("success_alert")
        else:
            self.alert.send_status(regime_call.date, health, pair=pair)
            alerts_sent.append("status_alert")

        if dqs is not None and isfinite(dqs) and 0 <= dqs < 0.75:
            self.alert.send_low_dqs(regime_call.date, dqs, health.missing_fields)
            alerts_sent.append("low_dqs_alert")

        return PublishOutput(
            pair=pair,
            date=regime_call.date,
            regime_call=regime_call,
            brief_markdown=None,
            desk_card=None,
            alerts_sent=alerts_sent,
            health=health,
            stage_health=tuple(upstream_health) + (quality, StageHealth("PublicationWrite", "OK")),
        )
