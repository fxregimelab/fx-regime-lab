"""PublishStage: persist a RegimeCall and emit alerts."""

from __future__ import annotations

from src.staged.contracts import PublishOutput, StageHealth
from src.staged.ports import AlertPort, WriterPort
from src.types import RegimeCall


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

    async def run(self, pair: str, regime_call: RegimeCall) -> PublishOutput:
        """Write the call, send success alert, and return a PublishOutput."""

        alerts_sent: list[str] = []
        call_id = self.writer.write_regime_call(
            regime_call,
            correlation_id=self.correlation_id,
        )
        if call_id is not None:
            alerts_sent.append(f"wrote_regime_call:{call_id}")

        self.alert.send_success(regime_call)
        alerts_sent.append("success_alert")

        dqs = regime_call.data_quality_score
        if dqs is not None and dqs < 0.75:
            stale_sources: list[str] = []
            self.alert.send_low_dqs(regime_call.date, dqs, stale_sources)
            alerts_sent.append("low_dqs_alert")

        return PublishOutput(
            pair=pair,
            date=regime_call.date,
            regime_call=regime_call,
            brief_markdown=None,
            desk_card=None,
            alerts_sent=alerts_sent,
            health=StageHealth("PublishStage", "OK"),
        )
