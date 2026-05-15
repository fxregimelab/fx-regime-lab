"""Tests for src.scheduler.run_pipeline v3 shadow integration."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.scheduler import run_pipeline as rp


class TestRunV3Shadow:
    @patch("subprocess.run")
    def test_runs_v3_when_flag_set(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="ok")
        code = rp._run_v3_shadow("2026-05-12", "cid-123")
        assert code == 0
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "src.pairs.runner" in cmd
        assert "--all" in cmd
        assert "--dry-run" in cmd

    @patch("subprocess.run")
    def test_logs_nonzero_exit(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="boom", stdout="")
        code = rp._run_v3_shadow("2026-05-12", "cid-123")
        assert code == 1

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=600))
    def test_timeout_returns_124(self, mock_run: MagicMock) -> None:
        code = rp._run_v3_shadow("2026-05-12", "cid-123")
        assert code == 124


class TestMainArgParse:
    def test_no_flag_defaults_false(self) -> None:
        # Just verify argparse accepts the flag
        parser = pytest.importorskip("argparse").ArgumentParser()
        parser.add_argument("date", nargs="?", default=None)
        parser.add_argument("--v3-shadow", action="store_true", dest="v3_shadow")
        ns = parser.parse_args(["2026-05-12"])
        assert ns.v3_shadow is False
        ns2 = parser.parse_args(["--v3-shadow"])
        assert ns2.v3_shadow is True
