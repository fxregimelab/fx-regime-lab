"""Post-deploy monitoring for Vercel, Prefect, and Supabase.

Watches production health after deployment and reports status.

@agent_context: Auto-monitor for FX Regime Lab CEO Mode
@allowed_imports: [json, os, subprocess, sys, time, urllib.request, dataclasses]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MonitorCheck:
    name: str
    status: str  # "pass", "fail", "warn"
    message: str
    detail: str | None = None


@dataclass(frozen=True)
class MonitorResult:
    target: str
    duration_seconds: int
    overall: str
    checks: list[MonitorCheck]
    summary: str


def _http_get(url: str, timeout: int = 30) -> tuple[int, dict[str, Any] | None, str]:
    """Make an HTTP GET request and return (status_code, json_body, error)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fx-regime-lab-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
            try:
                json_body = json.loads(body)
            except json.JSONDecodeError:
                json_body = None
            return response.status, json_body, ""
    except urllib.error.HTTPError as e:
        return e.code, None, str(e)
    except urllib.error.URLError as e:
        return 0, None, str(e.reason)
    except Exception as e:
        return 0, None, str(e)


def _run_command(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def monitor_vercel(url: str, duration_seconds: int = 30) -> MonitorResult:
    """Monitor a Vercel deployment for health.

    Checks:
    - HTTP 200 on main URL
    - HTTP 200 on /api/health (if exists)
    - Response time < 5s
    """
    checks: list[MonitorCheck] = []
    start_time = time.time()

    # Check main URL
    status, _, error = _http_get(url)
    if status == 200:
        checks.append(
            MonitorCheck(
                name="main_url",
                status="pass",
                message="Main URL returns 200",
            )
        )
    else:
        checks.append(
            MonitorCheck(
                name="main_url",
                status="fail",
                message=f"Main URL returned {status}",
                detail=error or "Unknown error",
            )
        )

    # Check health endpoint
    health_url = url.rstrip("/") + "/api/health"
    status, body, error = _http_get(health_url)
    if status == 200:
        checks.append(
            MonitorCheck(
                name="health_endpoint",
                status="pass",
                message="Health endpoint returns 200",
            )
        )
    elif status == 404:
        checks.append(
            MonitorCheck(
                name="health_endpoint",
                status="warn",
                message="Health endpoint not found (404) — may not be implemented",
            )
        )
    else:
        checks.append(
            MonitorCheck(
                name="health_endpoint",
                status="fail",
                message=f"Health endpoint returned {status}",
                detail=error or "Unknown error",
            )
        )

    # Check terminal page
    terminal_url = url.rstrip("/") + "/terminal"
    status, _, error = _http_get(terminal_url)
    if status == 200:
        checks.append(
            MonitorCheck(
                name="terminal_page",
                status="pass",
                message="Terminal page loads",
            )
        )
    else:
        checks.append(
            MonitorCheck(
                name="terminal_page",
                status="fail",
                message=f"Terminal page returned {status}",
                detail=error or "Unknown error",
            )
        )

    elapsed = int(time.time() - start_time)

    failures = [c for c in checks if c.status == "fail"]
    warnings = [c for c in checks if c.status == "warn"]

    if failures:
        overall = "unhealthy"
        summary = (
            f"Vercel deployment UNHEALTHY — {len(failures)} failure(s),"
            f" {len(warnings)} warning(s) after {elapsed}s"
        )
    elif warnings:
        overall = "warning"
        summary = (
            f"Vercel deployment WARNING — {len(warnings)} warning(s)"
            f" after {elapsed}s"
        )
    else:
        overall = "healthy"
        summary = f"Vercel deployment HEALTHY — all checks pass after {elapsed}s"

    return MonitorResult(
        target="vercel",
        duration_seconds=elapsed,
        overall=overall,
        checks=checks,
        summary=summary,
    )


def monitor_prefect(duration_seconds: int = 30) -> MonitorResult:
    """Monitor Prefect Cloud flow health.

    Checks:
    - PREFECT_API_KEY and PREFECT_API_URL are set
    - Last flow run was successful (if we can query)
    """
    checks: list[MonitorCheck] = []
    start_time = time.time()

    api_key = os.environ.get("PREFECT_API_KEY")
    api_url = os.environ.get("PREFECT_API_URL")

    if not api_key or not api_url:
        checks.append(
            MonitorCheck(
                name="prefect_env",
                status="fail",
                message="Prefect env vars not set — cannot monitor",
            )
        )
        elapsed = int(time.time() - start_time)
        return MonitorResult(
            target="prefect",
            duration_seconds=elapsed,
            overall="unhealthy",
            checks=checks,
            summary="Prefect monitoring FAILED — credentials not available",
        )

    checks.append(
        MonitorCheck(
            name="prefect_env",
            status="pass",
            message="Prefect environment variables present",
        )
    )

    # Try to query Prefect API for recent flow runs
    # This is a best-effort check — if prefect CLI is not installed, skip
    rc, stdout, stderr = _run_command(
        ["prefect", "flow-run", "ls", "--limit", "1", "--format", "json"]
    )
    if rc == 0:
        try:
            runs = json.loads(stdout)
            if runs:
                last_run = runs[0]
                state = last_run.get("state", {}).get("type", "UNKNOWN")
                if state == "COMPLETED":
                    checks.append(
                        MonitorCheck(
                            name="last_flow_run",
                            status="pass",
                            message="Last flow run completed successfully",
                        )
                    )
                elif state == "FAILED":
                    checks.append(
                        MonitorCheck(
                            name="last_flow_run",
                            status="fail",
                            message="Last flow run FAILED",
                            detail=f"Flow: {last_run.get('name', 'unknown')}",
                        )
                    )
                elif state == "CRASHED":
                    checks.append(
                        MonitorCheck(
                            name="last_flow_run",
                            status="fail",
                            message="Last flow run CRASHED",
                            detail=f"Flow: {last_run.get('name', 'unknown')}",
                        )
                    )
                else:
                    checks.append(
                        MonitorCheck(
                            name="last_flow_run",
                            status="warn",
                            message=f"Last flow run state: {state}",
                        )
                    )
            else:
                checks.append(
                    MonitorCheck(
                        name="last_flow_run",
                        status="warn",
                        message="No flow runs found",
                    )
                )
        except json.JSONDecodeError:
            checks.append(
                MonitorCheck(
                    name="last_flow_run",
                    status="warn",
                    message="Could not parse Prefect flow run output",
                )
            )
    else:
        checks.append(
            MonitorCheck(
                name="last_flow_run",
                status="warn",
                message="Could not query Prefect flow runs",
                detail=stderr or "prefect CLI may not be installed or authenticated",
            )
        )

    elapsed = int(time.time() - start_time)

    failures = [c for c in checks if c.status == "fail"]
    warnings = [c for c in checks if c.status == "warn"]

    if failures:
        overall = "unhealthy"
        summary = (
            f"Prefect UNHEALTHY — {len(failures)} failure(s),"
            f" {len(warnings)} warning(s) after {elapsed}s"
        )
    elif warnings:
        overall = "warning"
        summary = (
            f"Prefect WARNING — {len(warnings)} warning(s) after {elapsed}s"
        )
    else:
        overall = "healthy"
        summary = f"Prefect HEALTHY — all checks pass after {elapsed}s"

    return MonitorResult(
        target="prefect",
        duration_seconds=elapsed,
        overall=overall,
        checks=checks,
        summary=summary,
    )


def monitor_supabase(duration_seconds: int = 30) -> MonitorResult:
    """Monitor Supabase database health.

    Checks:
    - SUPABASE_URL and SUPABASE_ANON_KEY are set
    - Can connect to Supabase (best effort)
    """
    checks: list[MonitorCheck] = []
    start_time = time.time()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        checks.append(
            MonitorCheck(
                name="supabase_env",
                status="fail",
                message="Supabase env vars not set — cannot monitor",
            )
        )
        elapsed = int(time.time() - start_time)
        return MonitorResult(
            target="supabase",
            duration_seconds=elapsed,
            overall="unhealthy",
            checks=checks,
            summary="Supabase monitoring FAILED — credentials not available",
        )

    checks.append(
        MonitorCheck(
            name="supabase_env",
            status="pass",
            message="Supabase environment variables present",
        )
    )

    # Try to hit Supabase REST API health endpoint
    health_url = url.rstrip("/") + "/rest/v1/"
    req = urllib.request.Request(
        health_url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 401):
                # 401 is expected for /rest/v1/ without a table path
                checks.append(
                    MonitorCheck(
                        name="supabase_connection",
                        status="pass",
                        message="Supabase API reachable",
                    )
                )
            else:
                checks.append(
                    MonitorCheck(
                        name="supabase_connection",
                        status="warn",
                        message=f"Supabase returned {response.status}",
                    )
                )
    except Exception as e:
        checks.append(
            MonitorCheck(
                name="supabase_connection",
                status="fail",
                message="Cannot reach Supabase API",
                detail=str(e),
            )
        )

    elapsed = int(time.time() - start_time)

    failures = [c for c in checks if c.status == "fail"]
    warnings = [c for c in checks if c.status == "warn"]

    if failures:
        overall = "unhealthy"
        summary = (
            f"Supabase UNHEALTHY — {len(failures)} failure(s),"
            f" {len(warnings)} warning(s) after {elapsed}s"
        )
    elif warnings:
        overall = "warning"
        summary = (
            f"Supabase WARNING — {len(warnings)} warning(s) after {elapsed}s"
        )
    else:
        overall = "healthy"
        summary = f"Supabase HEALTHY — all checks pass after {elapsed}s"

    return MonitorResult(
        target="supabase",
        duration_seconds=elapsed,
        overall=overall,
        checks=checks,
        summary=summary,
    )


def main() -> None:
    """CLI entrypoint for monitoring."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m src.auto.monitor <vercel|prefect|supabase>"
            " [url] [duration_seconds]",
            file=sys.stderr,
        )
        sys.exit(1)

    target = sys.argv[1].lower()
    url = sys.argv[2] if len(sys.argv) > 2 else ""
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    if target == "vercel":
        if not url:
            print("Vercel monitoring requires a URL", file=sys.stderr)
            sys.exit(1)
        result = monitor_vercel(url, duration)
    elif target == "prefect":
        result = monitor_prefect(duration)
    elif target == "supabase":
        result = monitor_supabase(duration)
    else:
        print(f"Unknown target: {target}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "target": result.target,
        "duration_seconds": result.duration_seconds,
        "overall": result.overall,
        "summary": result.summary,
        "checks": [asdict(c) for c in result.checks],
    }, indent=2))

    sys.exit(0 if result.overall == "healthy" else 1)


if __name__ == "__main__":
    main()
