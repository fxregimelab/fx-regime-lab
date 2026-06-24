"""Tests for auto/monitor.py — post-deploy health monitoring."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from src.auto.monitor import monitor_prefect, monitor_vercel


class TestMonitorVercel:
    @patch("src.auto.monitor._http_get")
    def test_all_healthy(self, mock_http: Any) -> None:
        mock_http.return_value = (200, None, "")

        result = monitor_vercel("https://example.com")

        assert result.overall == "healthy"
        assert any(c.name == "main_url" and c.status == "pass" for c in result.checks)

    @patch("src.auto.monitor._http_get")
    def test_main_url_fails(self, mock_http: Any) -> None:
        mock_http.side_effect = [
            (500, None, "Server Error"),  # main_url
            (200, None, ""),  # health endpoint
            (200, None, ""),  # terminal page
        ]

        result = monitor_vercel("https://example.com")

        assert result.overall == "unhealthy"
        assert any(c.name == "main_url" and c.status == "fail" for c in result.checks)

    @patch("src.auto.monitor._http_get")
    def test_health_endpoint_404_warn(self, mock_http: Any) -> None:
        mock_http.side_effect = [
            (200, None, ""),  # main_url
            (404, None, ""),  # health endpoint
            (200, None, ""),  # terminal page
        ]

        result = monitor_vercel("https://example.com")

        assert result.overall == "warning"
        assert any(c.name == "health_endpoint" and c.status == "warn" for c in result.checks)


class TestMonitorPrefect:
    @patch.dict("os.environ", {"PREFECT_API_KEY": "test", "PREFECT_API_URL": "https://api.prefect.io"})
    @patch("src.auto.monitor._run_command")
    def test_env_present(self, mock_run: Any) -> None:
        mock_run.return_value = (
            0,
            '[{"state": {"type": "COMPLETED"}, "name": "test-flow"}]',
            "",
        )

        result = monitor_prefect()

        assert result.overall == "healthy"
        assert any(c.name == "prefect_env" and c.status == "pass" for c in result.checks)
        assert any(c.name == "last_flow_run" and c.status == "pass" for c in result.checks)

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_env(self) -> None:
        result = monitor_prefect()

        assert result.overall == "unhealthy"
        assert any(c.name == "prefect_env" and c.status == "fail" for c in result.checks)
