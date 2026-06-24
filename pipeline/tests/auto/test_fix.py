"""Tests for auto/fix.py — auto-fix loop engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from src.auto.fix import auto_fix


class TestAutoFix:
    """Test the auto-fix loop behavior."""

    @patch("src.auto.fix._run_pytest")
    @patch("src.auto.fix._run_ruff")
    def test_tier_2_all_clean_first_attempt(self, mock_ruff: Any, mock_pytest: Any) -> None:
        mock_pytest.return_value = (True, [])
        mock_ruff.return_value = (True, [])

        result = auto_fix("Add a new signal", 2, max_attempts=3, repo_root=Path("."))

        assert result.final_status == "fixed"
        assert len(result.attempts) == 1
        assert result.attempts[0]["status"] == "passed"
        assert result.attempts[0]["fix_applied"] == "No fix needed — already clean"
        assert result.total_duration_seconds >= 0

    @patch("src.auto.fix._run_pytest")
    @patch("src.auto.fix._run_ruff")
    def test_tier_2_pytest_fails_then_fixed(self, mock_ruff: Any, mock_pytest: Any) -> None:
        # First attempt: pytest fails, ruff passes
        # Second attempt: both pass
        mock_pytest.side_effect = [(False, ["test_foo.py:42: error"]), (True, [])]
        mock_ruff.return_value = (True, [])

        result = auto_fix("Fix a broken signal", 2, max_attempts=3, repo_root=Path("."))

        assert result.final_status == "fixed"
        assert len(result.attempts) == 2
        assert result.attempts[0]["status"] == "failed"
        assert result.attempts[1]["status"] == "passed"

    @patch("src.auto.fix._run_pytest")
    @patch("src.auto.fix._run_ruff")
    def test_tier_2_always_fails(self, mock_ruff: Any, mock_pytest: Any) -> None:
        mock_pytest.return_value = (False, ["test_foo.py:42: error"])
        mock_ruff.return_value = (True, [])

        result = auto_fix("Broken signal", 2, max_attempts=3, repo_root=Path("."))

        assert result.final_status == "failed"
        assert len(result.attempts) == 3
        assert all(a["status"] == "failed" for a in result.attempts)

    @patch("src.auto.fix._run_npm_build")
    @patch("src.auto.fix._run_npm_lint")
    def test_tier_1_all_clean(self, mock_lint: Any, mock_build: Any) -> None:
        mock_build.return_value = (True, [])
        mock_lint.return_value = (True, [])

        result = auto_fix("Add a new page", 1, max_attempts=3, repo_root=Path("."))

        assert result.final_status == "fixed"
        assert len(result.attempts) == 1
        assert result.attempts[0]["status"] == "passed"

    @patch("src.auto.fix._run_npm_build")
    @patch("src.auto.fix._run_npm_lint")
    def test_tier_1_build_fails(self, mock_lint: Any, mock_build: Any) -> None:
        mock_build.return_value = (False, ["Build error"])
        mock_lint.return_value = (True, [])

        result = auto_fix("Broken page", 1, max_attempts=3, repo_root=Path("."))

        assert result.final_status == "failed"
        assert len(result.attempts) == 3

    @patch("src.auto.fix._run_pytest")
    @patch("src.auto.fix._run_ruff")
    def test_max_attempts_respected(self, mock_ruff: Any, mock_pytest: Any) -> None:
        mock_pytest.return_value = (False, ["error"])
        mock_ruff.return_value = (True, [])

        result = auto_fix("Test", 2, max_attempts=2, repo_root=Path("."))

        assert len(result.attempts) == 2
        assert result.max_attempts == 2

    def test_directive_preserved(self) -> None:
        with patch("src.auto.fix._run_pytest", return_value=(True, [])):
            with patch("src.auto.fix._run_ruff", return_value=(True, [])):
                result = auto_fix("My custom directive", 2, max_attempts=1, repo_root=Path("."))
                assert result.directive == "My custom directive"

    def test_summary_contains_counts(self) -> None:
        with patch("src.auto.fix._run_pytest", return_value=(True, [])):
            with patch("src.auto.fix._run_ruff", return_value=(True, [])):
                result = auto_fix("Test", 2, max_attempts=1, repo_root=Path("."))
                assert "1 attempt" in result.summary or "1 attempt" in result.summary
                assert "fixed" in result.summary.lower()


class TestQuickFixes:
    """Test the _apply_quick_fixes helper."""

    def test_missing_module_detected(self) -> None:
        from src.auto.fix import _apply_quick_fixes
        result = _apply_quick_fixes(["ImportError: No module named 'foo'"], Path("."), 2)
        assert "Missing module" in result

    def test_unused_import_detected(self) -> None:
        from src.auto.fix import _apply_quick_fixes
        result = _apply_quick_fixes(
            ["src/signals/foo.py:5:5: F401 `numpy` imported but unused"],
            Path("."), 2
        )
        assert "unused import" in result.lower() or "Remove" in result

    def test_no_fixes_applicable(self) -> None:
        from src.auto.fix import _apply_quick_fixes
        result = _apply_quick_fixes(["some random error"], Path("."), 2)
        assert "No quick fixes" in result
