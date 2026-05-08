"""Pipeline alerting — Slack, email, and heartbeat.

All functions are failure-silent: an alerting failure is logged but never
raised, so a broken webhook cannot crash the daily pipeline.
"""

from __future__ import annotations

import logging
import os
import traceback
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15


def _slack_webhook_url() -> str | None:
    return os.environ.get("SLACK_WEBHOOK_URL")


def _resend_api_key() -> str | None:
    return os.environ.get("RESEND_API_KEY")


def _alert_email_from() -> str:
    return os.environ.get("ALERT_EMAIL_FROM", "alerts@fxregimelab.com")


def _alert_email_to() -> str:
    return os.environ.get("ALERT_EMAIL_TO", "ops@fxregimelab.com")


def send_slack_alert(
    message: str,
    blocks: list[dict[str, Any]] | None = None,
) -> None:
    """Post a plain-text or block-formatted message to the configured Slack webhook.

    Silently logs and swallows all errors so the pipeline never crashes
    because of a broken alerting channel.
    """
    url = _slack_webhook_url()
    if not url:
        logger.debug("Slack webhook not configured — skipping alert")
        return

    payload: dict[str, Any] = {"text": message}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        logger.info("Slack alert sent (%s)", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Slack alert failed: %s", exc)


def send_email_alert(subject: str, body: str) -> None:
    """Send an email via Resend REST API.

    Silently logs and swallows all errors.
    """
    api_key = _resend_api_key()
    if not api_key:
        logger.debug("Resend API key not configured — skipping email")
        return

    payload = {
        "from": _alert_email_from(),
        "to": _alert_email_to(),
        "subject": subject,
        "text": body,
    }

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        logger.info("Email alert sent (%s)", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email alert failed: %s", exc)


def _format_failure_blocks(
    date_str: str,
    failed_step: str,
    error_message: str,
    traceback_summary: str,
    dqs_score: float | None = None,
) -> list[dict[str, Any]]:
    """Build Slack Block Kit payload for a pipeline failure."""
    fields = [
        {"type": "mrkdwn", "text": f"*Date:*\n{date_str}"},
        {"type": "mrkdwn", "text": f"*Step:*\n{failed_step}"},
    ]
    if dqs_score is not None:
        fields.append(
            {"type": "mrkdwn", "text": f"*DQS:*\n{dqs_score:.2f}"}
        )
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 FX Regime Lab Pipeline Failure",
            },
        },
        {"type": "section", "fields": fields},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Error:*\n```{error_message[:500]}```"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Traceback:*\n```{traceback_summary[:1500]}```",
            },
        },
    ]


def alert_on_failure(
    date_str: str,
    failed_step: str,
    exception: BaseException,
    dqs_score: float | None = None,
) -> None:
    """Send a Slack alert when the pipeline crashes."""
    error_message = str(exception)
    traceback_summary = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    blocks = _format_failure_blocks(
        date_str=date_str,
        failed_step=failed_step,
        error_message=error_message,
        traceback_summary=traceback_summary,
        dqs_score=dqs_score,
    )
    send_slack_alert(
        message=f"Pipeline failure on {date_str} at step {failed_step}: {error_message[:200]}",
        blocks=blocks,
    )


def alert_on_low_dqs(
    date_str: str,
    dqs_score: float,
    stale_sources: list[str],
) -> None:
    """Send an email alert when the Data Quality Score drops below threshold."""
    subject = f"[FX Regime Lab] Low DQS {dqs_score:.2f} on {date_str}"
    body_lines = [
        f"Date: {date_str}",
        f"Data Quality Score: {dqs_score:.2f} (threshold: 0.70)",
        "",
        "Stale sources:",
        *(f"  - {s}" for s in stale_sources),
        "",
        "This is an automated alert from the FX Regime Lab pipeline.",
    ]
    send_email_alert(subject, "\n".join(body_lines))


def send_success_heartbeat(
    date_str: str,
    pairs_processed: int,
    regime_calls_count: int,
    dqs_score: float,
) -> None:
    """Send a daily success heartbeat to Slack.

    Creates "silence = problem" observability: if the heartbeat stops,
    something is wrong.
    """
    message = (
        f"✅ FX Regime Lab daily run complete for *{date_str}*\n"
        f"• Pairs processed: {pairs_processed}\n"
        f"• Regime calls: {regime_calls_count}\n"
        f"• DQS: {dqs_score:.2f}"
    )
    send_slack_alert(message)
