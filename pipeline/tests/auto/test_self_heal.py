"""Tests for auto/self_heal.py — post-deploy self-healing engine."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from src.auto.self_heal import self_heal


class TestSelfHeal:
    @patch("src.auto.self_heal._run_monitor")
    def test_healthy_on_first_check(self, mock_monitor: Any) -> None:
        mock_monitor.return_value = ("healthy", [])

        result = self_heal("Add chart", 1, "vercel", "https://example.com")

        assert result.final_status == "healthy"
        assert len(result.attempts) == 1
        assert result.attempts[0]["monitor_status"] == "healthy"
        assert result.attempts[0]["fix_status"] == "skipped"

    @patch("src.auto.self_heal._run_monitor")
    @patch("src.auto.self_heal.auto_fix")
    def test_recovers_after_fix(self, mock_fix: Any, mock_monitor: Any) -> None:
        mock_monitor.side_effect = [
            ("unhealthy", ["main_url: 500 error"]),
            ("healthy", []),
        ]
        mock_fix.return_value = type(
            "R",
            (),
            {"final_status": "fixed", "summary": "Fixed in 1 attempt"},
        )()

        result = self_heal("Add chart", 1, "vercel", "https://example.com")

        assert result.final_status == "recovered"
        assert len(result.attempts) == 2
        assert result.attempts[0]["monitor_status"] == "unhealthy"
        assert result.attempts[1]["monitor_status"] == "healthy"

    @patch("src.auto.self_heal._run_monitor")
    @patch("src.auto.self_heal.auto_fix")
    def test_fails_after_max_attempts(self, mock_fix: Any, mock_monitor: Any) -> None:
        mock_monitor.return_value = ("unhealthy", ["main_url: 500 error"])
        mock_fix.return_value = type(
            "R",
            (),
            {"final_status": "failed", "summary": "Could not fix"},
        )()

        result = self_heal("Add chart", 1, "vercel", "https://example.com", max_attempts=2)

        assert result.final_status == "failed"
        assert len(result.attempts) == 2

    @patch("src.auto.self_heal._run_monitor")
    def test_prefect_target(self, mock_monitor: Any) -> None:
        mock_monitor.return_value = ("healthy", [])

        result = self_heal("Add signal", 2, "prefect", None)

        assert result.final_status == "healthy"
        assert result.tier == 2

    @patch("src.auto.self_heal._run_monitor")
    def test_directive_preserved(self, mock_monitor: Any) -> None:
        mock_monitor.return_value = ("healthy", [])

        result = self_heal("My custom directive", 1, "vercel", "https://example.com")
        assert result.directive == "My custom directive"

    def test_max_attempts_respected(self) -> None:
        with patch("src.auto.self_heal._run_monitor", return_value=("healthy", [])):
            result = self_heal("Test", 1, "vercel", "https://example.com", max_attempts=1)
            assert result.max_attempts == 1
            assert len(result.attempts) == 1
