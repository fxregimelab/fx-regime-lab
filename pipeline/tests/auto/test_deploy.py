"""Tests for auto/deploy.py — deployment engine."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.auto.deploy import deploy, deploy_prefect, deploy_vercel


@pytest.fixture
def temp_repo() -> Any:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "web").mkdir()
        (repo / "web" / "package.json").write_text("{}")
        (repo / "pipeline").mkdir()
        (repo / "pipeline" / "prefect.yaml").write_text("deployments: []")
        yield repo


class TestDeployVercel:
    @patch("src.auto.deploy._run_command")
    @patch("src.auto.deploy._http_get")
    def test_successful_deploy(self, mock_http: Any, mock_run: Any, temp_repo: Path) -> None:
        mock_run.side_effect = [
            (0, "33.0.0", ""),  # vercel --version
            (0, "https://fxregimelab-abc.vercel.app", ""),  # vercel deploy
        ]
        mock_http.return_value = (200, "<html>Test</html>")

        result = deploy_vercel(repo_root=temp_repo)

        assert result.target == "vercel"
        assert result.status == "success"
        assert result.smoke_test_passed is True
        assert result.url == "https://fxregimelab-abc.vercel.app"

    def test_no_package_json_skips(self, temp_repo: Path) -> None:
        # Remove package.json
        (temp_repo / "web" / "package.json").unlink()
        result = deploy_vercel(repo_root=temp_repo)

        assert result.status == "skipped"
        assert "No web/package.json" in result.message

    @patch("src.auto.deploy._run_command")
    def test_no_vercel_cli_skips(self, mock_run: Any, temp_repo: Path) -> None:
        mock_run.return_value = (1, "", "not found")
        result = deploy_vercel(repo_root=temp_repo)

        assert result.status == "skipped"
        assert "Vercel CLI not available" in result.message

    @patch("src.auto.deploy._run_command")
    @patch("src.auto.deploy._http_get")
    def test_smoke_test_fails(self, mock_http: Any, mock_run: Any, temp_repo: Path) -> None:
        mock_run.side_effect = [
            (0, "33.0.0", ""),
            (0, "https://fxregimelab-abc.vercel.app", ""),
        ]
        mock_http.return_value = (500, "Internal Server Error")

        result = deploy_vercel(repo_root=temp_repo)

        assert result.status == "failed"
        assert result.smoke_test_passed is False


class TestDeployPrefect:
    @patch("src.auto.deploy._run_command")
    @patch.dict(
        "os.environ",
        {"PREFECT_API_URL": "https://api.prefect.io", "PREFECT_API_KEY": "test-key"},
    )
    def test_successful_deploy(self, mock_run: Any, temp_repo: Path) -> None:
        mock_run.side_effect = [
            (0, "3.0.0", ""),  # prefect version
            (0, "Successfully created/updated deployment", ""),  # prefect deploy
        ]

        result = deploy_prefect(repo_root=temp_repo)

        assert result.target == "prefect"
        assert result.status == "success"
        assert result.smoke_test_passed is True

    def test_no_prefect_yaml_skips(self, temp_repo: Path) -> None:
        (temp_repo / "pipeline" / "prefect.yaml").unlink()
        result = deploy_prefect(repo_root=temp_repo)

        assert result.status == "skipped"
        assert "No pipeline/prefect.yaml" in result.message

    @patch("src.auto.deploy._run_command")
    def test_missing_env_vars_skips(self, mock_run: Any, temp_repo: Path) -> None:
        mock_run.return_value = (0, "3.0.0", "")
        with patch.dict("os.environ", {}, clear=True):
            result = deploy_prefect(repo_root=temp_repo)

        assert result.status == "skipped"
        assert "PREFECT_API_URL or PREFECT_API_KEY not set" in result.message

    @patch("src.auto.deploy._run_command")
    @patch.dict(
        "os.environ",
        {"PREFECT_API_URL": "https://api.prefect.io", "PREFECT_API_KEY": "test-key"},
    )
    def test_deploy_failure(self, mock_run: Any, temp_repo: Path) -> None:
        mock_run.side_effect = [
            (0, "3.0.0", ""),
            (1, "", "Authentication failed"),
        ]

        result = deploy_prefect(repo_root=temp_repo)

        assert result.status == "failed"
        assert "Authentication failed" in result.message


class TestDeployRouter:
    def test_routes_to_vercel(self, temp_repo: Path) -> None:
        with patch("src.auto.deploy.deploy_vercel") as mv:
            mv.return_value = type(
                "R", (), {"target": "vercel", "status": "skipped"}
            )()
            deploy("vercel", temp_repo)
            mv.assert_called_once()

    def test_routes_to_prefect(self, temp_repo: Path) -> None:
        with patch("src.auto.deploy.deploy_prefect") as mp:
            mp.return_value = type(
                "R", (), {"target": "prefect", "status": "skipped"}
            )()
            deploy("prefect", temp_repo)
            mp.assert_called_once()

    def test_invalid_target_raises(self, temp_repo: Path) -> None:
        try:
            deploy("invalid", temp_repo)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "invalid" in str(e)
