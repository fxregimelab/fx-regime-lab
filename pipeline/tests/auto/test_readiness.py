"""Tests for auto/readiness.py — pre-deploy readiness checks."""

from __future__ import annotations

from pathlib import Path

from src.auto.readiness import check_prefect_readiness, check_vercel_readiness


class TestCheckVercel:
    def test_returns_result_structure(self):
        # Smoke test: function runs and returns a ReadinessResult
        result = check_vercel_readiness(Path("."))
        assert result.target == "vercel"
        assert result.overall in ("ready", "warning", "not_ready")
        assert isinstance(result.checks, list)
        assert len(result.checks) > 0
        assert all(hasattr(c, "name") and hasattr(c, "status") for c in result.checks)

    def test_missing_package_json_all_skipped(self):
        # When there's no web directory, all checks are skipped
        result = check_vercel_readiness(Path("/nonexistent"))
        assert all(c.status == "skip" for c in result.checks)


class TestCheckPrefect:
    def test_returns_result_structure(self):
        result = check_prefect_readiness(Path("."))
        assert result.target == "prefect"
        assert result.overall in ("ready", "warning", "not_ready")
        assert isinstance(result.checks, list)

    def test_missing_prefect_yaml_is_not_ready(self):
        result = check_prefect_readiness(Path("/nonexistent"))
        assert result.overall != "ready"
