"""Production AlertPort adapter wrapping the existing Slack alerting module."""

from __future__ import annotations

import datetime

from src.monitoring import alerts as alerts_module
from src.staged.ports import AlertPort
from src.types import RegimeCall

__all__ = ["ProductionAlertPort", "alerts_module"]


class ProductionAlertPort(AlertPort):
    """Emit Slack/email alerts via ``src.monitoring.alerts``."""

    def send_heartbeat(
        self,
        as_of: datetime.date,
        *,
        pairs_processed: int,
        regime_calls_count: int,
        dqs_score: float,
    ) -> None:
        alerts_module.send_success_heartbeat(
            str(as_of),
            pairs_processed=pairs_processed,
            regime_calls_count=regime_calls_count,
            dqs_score=dqs_score,
        )

    def send_success(self, call: RegimeCall) -> None:
        message = (
            f"✅ Regime call published: *{call.pair}* on {call.date}\n"
            f"• Regime: {call.regime}\n"
            f"• Confidence: {call.confidence:.2f}\n"
            f"• Bias: {call.directional_bias or 'N/A'}"
        )
        alerts_module.send_slack_alert(message)

    def send_low_dqs(
        self,
        as_of: datetime.date,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        alerts_module.alert_on_low_dqs(str(as_of), dqs_score, stale_sources)
