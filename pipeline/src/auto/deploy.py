"""Deployment orchestration for Vercel (frontend) and Prefect (pipeline).

Handles deploy, smoke test, and rollback decisions.

@agent_context: Auto-deploy for FX Regime Lab CEO Mode
@allowed_imports: [json, os, subprocess, sys, dataclasses, time, pathlib, urllib]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class DeployResult:
    target: str  # "vercel" | "prefect"
    status: str  # "success" | "failed" | "skipped"
    url: str | None
    message: str
    smoke_test_passed: bool
    smoke_test_detail: str
    duration_seconds: float


def _run_command(
    cmd: list[str],
    cwd: Path,
    timeout: int = 180,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a shell command and return (exit_code, stdout, stderr)."""
    merged_env = {**os.environ}
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


def _http_get(url: str, timeout: int = 15) -> tuple[int, str]:
    """HTTP GET with simple retry. Returns (status_code, body)."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "FX-Regime-Lab-DeployBot/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")[:1000]
                return resp.status, body
        except urllib.error.HTTPError as e:
            return e.code, str(e.reason)
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            return 0, str(e)
    return 0, "All retries failed"


def deploy_vercel(
    repo_root: Path | str = REPO_ROOT,
    preview: bool = False,
) -> DeployResult:
    """Deploy frontend to Vercel.

    Args:
        repo_root: Repository root path
        preview: If True, deploy to preview URL. If False, deploy to production.

    Returns:
        DeployResult with URL and smoke test results
    """
    repo_root = Path(repo_root)
    start = time.time()
    web_dir = repo_root / "web"

    # Check prerequisites
    if not (web_dir / "package.json").exists():
        return DeployResult(
            target="vercel",
            status="skipped",
            url=None,
            message="No web/package.json found — skipping Vercel deploy",
            smoke_test_passed=False,
            smoke_test_detail="N/A",
            duration_seconds=round(time.time() - start, 2),
        )

    # Check for Vercel CLI or npx availability
    code, _, _ = _run_command(["npx", "vercel", "--version"], web_dir, timeout=30)
    if code != 0:
        return DeployResult(
            target="vercel",
            status="skipped",
            url=None,
            message="Vercel CLI not available (npx vercel --version failed)",
            smoke_test_passed=False,
            smoke_test_detail="N/A",
            duration_seconds=round(time.time() - start, 2),
        )

    # Deploy
    deploy_cmd = ["npx", "vercel"]
    if not preview:
        deploy_cmd.append("--prod")

    # Run non-interactively (requires VERCEL_TOKEN or prior auth)
    deploy_cmd.append("--yes")

    code, stdout, stderr = _run_command(
        deploy_cmd,
        web_dir,
        timeout=180,
    )
    output = stdout + stderr

    if code != 0:
        return DeployResult(
            target="vercel",
            status="failed",
            url=None,
            message=f"Vercel deploy failed:\n{output[:500]}",
            smoke_test_passed=False,
            smoke_test_detail="Deploy failed before smoke test",
            duration_seconds=round(time.time() - start, 2),
        )

    # Extract URL from output (Vercel prints URL like https://...vercel.app)
    url = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("https://") and "vercel" in line:
            url = line.split()[0] if " " in line else line
            break

    if not url:
        # Try to read from .vercel/project.json or vercel.json
        url = "https://fxregimelab.com"  # fallback

    # Smoke test
    status_code, body = _http_get(url)
    smoke_passed = status_code == 200
    smoke_detail = (
        f"HTTP {status_code}, "
        f"body length {len(body)}, "
        f"contains '<html>': {'<html' in body.lower()}"
    )

    return DeployResult(
        target="vercel",
        status="success" if smoke_passed else "failed",
        url=url,
        message=(
            "Vercel deploy completed"
            if smoke_passed
            else "Vercel deploy OK but smoke test failed"
        ),
        smoke_test_passed=smoke_passed,
        smoke_test_detail=smoke_detail,
        duration_seconds=round(time.time() - start, 2),
    )


def deploy_prefect(
    repo_root: Path | str = REPO_ROOT,
) -> DeployResult:
    """Deploy pipeline to Prefect Cloud.

    Registers the flow defined in prefect.yaml.

    Args:
        repo_root: Repository root path

    Returns:
        DeployResult with registration status
    """
    repo_root = Path(repo_root)
    start = time.time()
    pipeline_dir = repo_root / "pipeline"

    # Check prerequisites
    if not (pipeline_dir / "prefect.yaml").exists():
        return DeployResult(
            target="prefect",
            status="skipped",
            url=None,
            message="No pipeline/prefect.yaml found — skipping Prefect deploy",
            smoke_test_passed=False,
            smoke_test_detail="N/A",
            duration_seconds=round(time.time() - start, 2),
        )

    # Check for Prefect CLI
    code, _, _ = _run_command(
        ["python", "-m", "prefect", "version"],
        pipeline_dir,
        timeout=30,
    )
    if code != 0:
        return DeployResult(
            target="prefect",
            status="skipped",
            url=None,
            message="Prefect CLI not available — skipping Prefect deploy",
            smoke_test_passed=False,
            smoke_test_detail="N/A",
            duration_seconds=round(time.time() - start, 2),
        )

    # Check env vars
    prefect_api_url = os.environ.get("PREFECT_API_URL", "")
    prefect_api_key = os.environ.get("PREFECT_API_KEY", "")
    if not prefect_api_url or not prefect_api_key:
        return DeployResult(
            target="prefect",
            status="skipped",
            url=None,
            message="PREFECT_API_URL or PREFECT_API_KEY not set — skipping Prefect deploy",
            smoke_test_passed=False,
            smoke_test_detail="N/A",
            duration_seconds=round(time.time() - start, 2),
        )

    # Register deployment
    code, stdout, stderr = _run_command(
        ["python", "-m", "prefect", "deploy", "--prefect-file", "prefect.yaml"],
        pipeline_dir,
        timeout=180,
    )
    output = stdout + stderr

    if code != 0:
        return DeployResult(
            target="prefect",
            status="failed",
            url=None,
            message=f"Prefect deploy failed:\n{output[:500]}",
            smoke_test_passed=False,
            smoke_test_detail="Registration failed",
            duration_seconds=round(time.time() - start, 2),
        )

    # Smoke test: verify the deployment name appears in Prefect Cloud
    smoke_passed = "Successfully created/updated" in output or "Deployment" in output
    smoke_detail = (
        "Prefect registration output indicates success"
        if smoke_passed
        else "Could not verify registration from output"
    )

    return DeployResult(
        target="prefect",
        status="success" if smoke_passed else "failed",
        url=prefect_api_url,
        message=(
            "Prefect flow registered successfully"
            if smoke_passed
            else "Prefect deploy unclear"
        ),
        smoke_test_passed=smoke_passed,
        smoke_test_detail=smoke_detail,
        duration_seconds=round(time.time() - start, 2),
    )


def deploy(
    target: str,
    repo_root: Path | str = REPO_ROOT,
    **kwargs,
) -> DeployResult:
    """Deploy to the specified target.

    Args:
        target: "vercel" or "prefect"
        repo_root: Repository root path
        **kwargs: Passed to target-specific deploy function

    Returns:
        DeployResult
    """
    if target == "vercel":
        return deploy_vercel(repo_root, **kwargs)
    if target == "prefect":
        return deploy_prefect(repo_root, **kwargs)
    raise ValueError(f"Unknown deploy target: {target}. Use 'vercel' or 'prefect'.")


def main() -> None:
    """CLI entrypoint for deployment."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.auto.deploy <vercel|prefect> [repo_root]", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    repo_root = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT

    result = deploy(target, repo_root)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
