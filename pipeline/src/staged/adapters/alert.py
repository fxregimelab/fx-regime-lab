"""Production AlertPort adapter wrapping the existing Slack alerting module."""

from __future__ import annotations

import datetime
import re

from src.monitoring import alerts as alerts_module
from src.staged.contracts import StageHealth
from src.staged.ports import AlertPort
from src.types import RegimeCall

__all__ = ["ProductionAlertPort", "alerts_module"]

_CREDENTIAL_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*\S+"
)
_EXCEPTION_DETAIL = re.compile(
    r"(?i)\b(?:[A-Za-z_][\w.]*Error|[A-Za-z_][\w.]*Exception|Traceback)\b"
)
_SLACK_WEBHOOK = re.compile(r"https://hooks\.slack\.com/services/\S+", re.IGNORECASE)


def _safe_status_note(note: str) -> str:
    exception = _EXCEPTION_DETAIL.search(note)
    if exception is not None:
        exception_class = exception.group(0)
        if note.strip() == exception_class:
            return exception_class
        return f"{exception_class}: details withheld"
    redacted = _SLACK_WEBHOOK.sub("[REDACTED_WEBHOOK]", note)
    return _CREDENTIAL_VALUE.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        redacted,
    )


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

    def send_status(
        self,
        as_of: datetime.date,
        health: StageHealth,
        *,
        pair: str | None = None,
    ) -> None:
        if health.status == "OK":
            raise ValueError("send_status accepts only DEGRADED or FAILED health")

        missing_fields = ", ".join(health.missing_fields) or "none reported"
        notes = "; ".join(_safe_status_note(note) for note in health.notes) or "none reported"
        pair_line = f"\nPair: {pair}" if pair is not None else ""
        message = (
            f"{health.status} staged pipeline status\n"
            f"Date: {as_of}\n"
            f"Stage: {health.stage_name}{pair_line}\n"
            f"Missing fields: {missing_fields}\n"
            f"Notes: {notes}"
        )
        alerts_module.send_slack_alert(message)

    def send_low_dqs(
        self,
        as_of: datetime.date,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        alerts_module.alert_on_low_dqs(str(as_of), dqs_score, stale_sources)
