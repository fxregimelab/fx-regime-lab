"""Tests for auto/report.py — execution reporting."""

from __future__ import annotations

from src.auto.report import ExecutionContext, generate_report


class TestGenerateReport:
    def test_complete_status(self):
        ctx = ExecutionContext(
            directive="Add chart",
            tier=1,
            tier_name="Terminal Polish",
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T00:01:00Z",
            files_changed=[{"path": "web/src/app/chart/page.tsx", "status": "A"}],
            test_results={"pytest": "PASS", "ruff": "PASS"},
            deploy_target="vercel",
            deploy_url="https://example.com",
            warnings=[],
            errors=[],
        )
        report = generate_report(ctx)
        assert "Add chart" in report
        assert "vercel" in report.lower()
        assert "PASS" in report

    def test_with_errors(self):
        ctx = ExecutionContext(
            directive="Add signal",
            tier=2,
            tier_name="Signal & Logic",
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T00:01:00Z",
            files_changed=[],
            test_results={"pytest": "FAIL"},
            deploy_target="prefect",
            deploy_url="",
            warnings=["Some warning"],
            errors=["Test failed"],
        )
        report = generate_report(ctx)
        assert "Add signal" in report
        assert "FAIL" in report
        assert "Test failed" in report

    def test_empty_context(self):
        ctx = ExecutionContext(
            directive="Test",
            tier=1,
            tier_name="Terminal Polish",
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T00:01:00Z",
        )
        report = generate_report(ctx)
        assert "Test" in report
        assert "COMPLETE" in report
