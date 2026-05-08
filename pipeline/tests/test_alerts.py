"""Tests for the alerting module.

All tests mock external HTTP calls so no real Slack messages or emails are sent.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.monitoring.alerts import (
    alert_on_failure,
    alert_on_low_dqs,
    send_email_alert,
    send_slack_alert,
    send_success_heartbeat,
)


class TestSendSlackAlert:
    def test_sends_post_to_webhook(self) -> None:
        with patch(
            "src.monitoring.alerts._slack_webhook_url", return_value="https://hooks.slack.com/test"
        ), patch("src.monitoring.alerts.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            send_slack_alert("Hello Slack")
            mock_post.assert_called_once()
            args = mock_post.call_args
            assert args[1]["json"]["text"] == "Hello Slack"

    def test_skips_when_no_webhook(self) -> None:
        with patch("src.monitoring.alerts._slack_webhook_url", return_value=None), patch(
            "src.monitoring.alerts.requests.post"
        ) as mock_post:
            send_slack_alert("Hello Slack")
            mock_post.assert_not_called()

    def test_failure_is_silent(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(
            "src.monitoring.alerts._slack_webhook_url", return_value="https://hooks.slack.com/test"
        ), patch("src.monitoring.alerts.requests.post", side_effect=RuntimeError("boom")):
            send_slack_alert("Hello Slack")
        assert any("Slack alert failed" in r.message for r in caplog.records)


class TestSendEmailAlert:
    def test_sends_post_to_resend(self) -> None:
        with patch(
            "src.monitoring.alerts._resend_api_key", return_value="re_test_key"
        ), patch("src.monitoring.alerts.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            send_email_alert("Subject", "Body")
            mock_post.assert_called_once()
            args = mock_post.call_args
            assert args[1]["headers"]["Authorization"] == "Bearer re_test_key"
            assert args[1]["json"]["subject"] == "Subject"

    def test_skips_when_no_api_key(self) -> None:
        with patch("src.monitoring.alerts._resend_api_key", return_value=None), patch(
            "src.monitoring.alerts.requests.post"
        ) as mock_post:
            send_email_alert("Subject", "Body")
            mock_post.assert_not_called()

    def test_failure_is_silent(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(
            "src.monitoring.alerts._resend_api_key", return_value="re_test_key"
        ), patch("src.monitoring.alerts.requests.post", side_effect=RuntimeError("boom")):
            send_email_alert("Subject", "Body")
        assert any("Email alert failed" in r.message for r in caplog.records)


class TestAlertOnFailure:
    def test_sends_slack_with_blocks(self) -> None:
        with patch("src.monitoring.alerts.send_slack_alert") as mock_slack:
            exc = RuntimeError("something broke")
            alert_on_failure(
                date_str="2026-05-08",
                failed_step="orchestrator",
                exception=exc,
                dqs_score=0.85,
            )
            mock_slack.assert_called_once()
            args = mock_slack.call_args
            text = args[1].get("message", "") or args[1].get("text", "")
            assert "Pipeline failure" in text
            assert "2026-05-08" in text
            assert args[1].get("blocks") is not None


class TestAlertOnLowDqs:
    def test_sends_email(self) -> None:
        with patch("src.monitoring.alerts.send_email_alert") as mock_email:
            alert_on_low_dqs("2026-05-08", 0.55, stale_sources=["cot", "vol"])
            mock_email.assert_called_once()
            subject = mock_email.call_args[0][0]
            body = mock_email.call_args[0][1]
            assert "Low DQS" in subject
            assert "0.55" in subject
            assert "cot" in body


class TestSendSuccessHeartbeat:
    def test_sends_slack_message(self) -> None:
        with patch("src.monitoring.alerts.send_slack_alert") as mock_slack:
            send_success_heartbeat("2026-05-08", 7, 3, 0.85)
            mock_slack.assert_called_once()
            args = mock_slack.call_args
            text = args[0][0] if args[0] else args[1].get("message", "")
            assert "daily run complete" in text.lower()
            assert "2026-05-08" in text
            assert "7" in text
            assert "0.85" in text
