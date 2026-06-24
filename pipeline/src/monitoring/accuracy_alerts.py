"""Accuracy alert system for rolling validation accuracy thresholds.

Triggers Slack alerts when per-pair rolling 90-day directional accuracy
drops below configurable gates.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from src.db import writer
from src.monitoring.alerts import send_slack_alert

logger = logging.getLogger(__name__)

_DEFAULT_T5_THRESHOLD = 0.50
_EURUSD_EXPANSION_GATE = 0.55


@dataclass
class AccuracyAlert:
    pair: str
    horizon: str
    current_accuracy: float
    threshold: float
    alert_type: str  # "BELOW_THRESHOLD", "TRENDING_DOWN"
    triggered_at: str


def check_accuracy_alerts() -> list[AccuracyAlert]:
    """Check latest validation_stats for pairs below accuracy thresholds.

    Returns alerts for:
      * Any pair with T+5 rolling 90d accuracy < 0.50
      * EUR/USD T+5 rolling 90d accuracy < 0.55 (expansion gate)
    """
    alerts: list[AccuracyAlert] = []
    triggered_at = datetime.now(UTC).isoformat()

    try:
        rows = writer.get_latest_validation_stats_per_pair()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch validation stats for accuracy alerts: %s", exc)
        return alerts

    for row in rows:
        pair = str(row.get("pair", ""))
        if not pair:
            continue

        acc = row.get("t5_rolling_90d_accuracy")
        if acc is None:
            continue
        try:
            current = float(acc)
        except (TypeError, ValueError):
            continue

        # General threshold
        if current < _DEFAULT_T5_THRESHOLD:
            alerts.append(
                AccuracyAlert(
                    pair=pair,
                    horizon="T+5",
                    current_accuracy=round(current, 4),
                    threshold=_DEFAULT_T5_THRESHOLD,
                    alert_type="BELOW_THRESHOLD",
                    triggered_at=triggered_at,
                )
            )

        # EUR/USD expansion gate
        if pair == "EURUSD" and current < _EURUSD_EXPANSION_GATE:
            alerts.append(
                AccuracyAlert(
                    pair=pair,
                    horizon="T+5",
                    current_accuracy=round(current, 4),
                    threshold=_EURUSD_EXPANSION_GATE,
                    alert_type="BELOW_THRESHOLD",
                    triggered_at=triggered_at,
                )
            )

    return alerts


def format_alert_slack(alerts: list[AccuracyAlert]) -> str:
    """Format a list of accuracy alerts into a Slack message string."""
    if not alerts:
        return ""

    lines: list[str] = [
        "🎯 *FX Regime Lab — Accuracy Alert*",
        "",
    ]
    for alert in alerts:
        emoji = "🚨" if alert.pair == "EURUSD" else "⚠️"
        lines.append(
            f"{emoji} *{alert.pair}* {alert.horizon} rolling accuracy "
            f"is *{alert.current_accuracy:.2%}* (threshold: {alert.threshold:.2%}) "
            f"— {alert.alert_type}"
        )
    lines.append("")
    lines.append(f"_Triggered at: {alerts[0].triggered_at}_")
    return "\n".join(lines)


def send_accuracy_alerts(alerts: list[AccuracyAlert]) -> None:
    """Send accuracy alerts via Slack webhook if configured.

    Falls back silently if the webhook env var is missing or the post fails.
    """
    if not alerts:
        return

    message = format_alert_slack(alerts)
    url = os.environ.get("ALERTS_SLACK_WEBHOOK_URL") or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        logger.debug("No Slack webhook configured — logging accuracy alerts locally")
        for alert in alerts:
            logger.warning(
                "Accuracy alert: %s %s=%.4f < %.4f (%s)",
                alert.pair,
                alert.horizon,
                alert.current_accuracy,
                alert.threshold,
                alert.alert_type,
            )
        return

    try:
        send_slack_alert(message)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to send accuracy alert Slack message: %s", exc)
