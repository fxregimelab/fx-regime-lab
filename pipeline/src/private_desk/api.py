"""Loopback private desk with password authentication and CSRF-protected refresh."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import secrets
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.private_desk.journal import journal_view, sync_journal
from src.private_desk.readiness import PAIRS, assess_readiness
from src.private_desk.report import ROOT, STATE_DIR, atomic_json, build_report


def _decision_clock() -> datetime:
    return datetime.now(UTC)


def _reject_nonfinite(value: str) -> NoReturn:
    raise ValueError("Non-finite JSON is unavailable")


def _load_current_report(state_dir: Path) -> dict[str, Any] | None:
    try:
        with (state_dir / "report.json").open("rb") as stream:
            body = stream.read(128 * 1024 * 1024 + 1)
    except FileNotFoundError:
        return None
    if len(body) > 128 * 1024 * 1024:
        raise ValueError("Report size exceeds the local response bound")
    value = json.loads(body.decode("utf-8"), parse_constant=_reject_nonfinite)
    if not isinstance(value, dict):
        raise ValueError("Report must be an object")
    rows = value.get("pair_reports", [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Report rows must be objects")
    historical = value.get("historical_policy", {})
    if not isinstance(historical, dict):
        raise ValueError("Historical policy must be an object")
    series = historical.get("series_audits", [])
    if not isinstance(series, list) or any(not isinstance(item, dict) for item in series):
        raise ValueError("Historical series must be objects")
    for row in rows:
        if row.get("pair") not in PAIRS:
            raise ValueError("A report row has no supported pair identity")
        features = row.get("historical_policy_features")
        if features is not None:
            if not isinstance(features, dict) or not isinstance(features.get("rows", []), list):
                raise ValueError("Historical features must contain row objects")
            if any(
                not isinstance(item, dict)
                or not isinstance(item.get("observation_date"), str)
                or "change_unavailable_reason" not in item
                for item in features.get("rows", [])
            ):
                raise ValueError("Historical feature rows are incomplete")
        backtest = row.get("backtest", {})
        if not isinstance(backtest, dict) or not isinstance(backtest.get("trades", []), list):
            raise ValueError("Backtest must contain trade objects")
        if any(not isinstance(trade, dict) for trade in backtest.get("trades", [])):
            raise ValueError("Backtest trades must be objects")
        for trade in backtest.get("trades", []):
            if "pair" in trade and trade["pair"] != row["pair"]:
                raise ValueError("Trade pair does not match its report owner")
            if "entry_time" in trade and not isinstance(trade["entry_time"], str):
                raise ValueError("Trade identity must use a recorded time string")
    for audit_key in ("portfolio_audit", "correlation_audit"):
        audit = value.get(audit_key, {})
        if not isinstance(audit, dict):
            raise ValueError("Portfolio audit must be an object")
        for bucket in ("accepted", "skipped"):
            entries = audit.get(bucket, [])
            if not isinstance(entries, list):
                raise ValueError("Portfolio audit entries must be objects")
            for entry in entries:
                if (
                    not isinstance(entry, dict)
                    or entry.get("pair") not in PAIRS
                    or not isinstance(entry.get("entry_time"), str)
                    or (bucket == "skipped" and not isinstance(entry.get("reason"), str))
                ):
                    raise ValueError("Portfolio audit identity is incomplete")
    return value


def _live_readiness(report: dict[str, Any] | None) -> dict[str, Any]:
    return assess_readiness(report if report is not None else {}, now=_decision_clock())


def _project_operational_hold(value: dict[str, Any]) -> dict[str, Any]:
    readiness = _live_readiness(value)
    value["operations_readiness"] = readiness
    if readiness["status"] == "CURRENT":
        return readiness
    held_pairs = {row["pair"] for row in readiness["pair_checks"] if row["status"] != "CURRENT"}
    warning = (
        "Current research is on hold because report structure or report/context age checks failed. "
        "Refresh and review the input evidence; fresh clocks do not validate a trade."
        if readiness["global_hold"]
        else "Input age checks hold these pairs: " + ", ".join(sorted(held_pairs)) + ". "
        "Other pairs retain their saved research status. Refresh to review new observations."
    )
    warnings = value.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    value["warnings"] = [*warnings, warning]
    for pair in value.get("pair_reports", []):
        if not readiness["global_hold"] and pair.get("pair") not in held_pairs:
            continue
        candidate = pair.get("candidate")
        if not isinstance(candidate, dict):
            candidate = {}
            pair["candidate"] = candidate
        candidate["status"] = "ABSTAIN"
        for key in (
            "direction",
            "bias",
            "entry",
            "stop",
            "tp1",
            "tp2",
            "probability",
            "expected_r",
            "probability_ci95",
            "expected_r_ci95_approx",
        ):
            if key in candidate:
                candidate[key] = None
        if "execution_status" in candidate:
            candidate["execution_status"] = "UNAVAILABLE"
        reasons = candidate.get("reasons")
        candidate["reasons"] = [*(reasons if isinstance(reasons, list) else []), warning]
    return readiness


def initialize_access(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    if (state_dir / "auth.json").exists():
        return
    password = secrets.token_urlsafe(24)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()
    atomic_json(state_dir / "auth.json", {"salt": salt.hex(), "digest": digest})
    (state_dir / "access.txt").write_text(
        "Private desk login password (local file; do not share):\n" + password + "\n",
        encoding="utf-8",
    )


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def create_app(state_dir: Path = STATE_DIR) -> FastAPI:
    initialize_access(state_dir)
    auth = json.loads((state_dir / "auth.json").read_text(encoding="utf-8"))
    sessions: dict[str, tuple[float, str]] = {}
    attempts: dict[str, list[float]] = defaultdict(list)
    lock = threading.Lock()
    job: dict[str, Any] = {"running": False, "message": "Ready", "error": None}
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )

    @app.middleware("http")
    async def headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
            }
        )
        return response

    def same_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        allowed = str(request.base_url).rstrip("/")
        if origin and origin != allowed:
            raise HTTPException(403, "Origin rejected")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Cross-site request rejected")

    def authenticated(request: Request, *, csrf: bool = False) -> str:
        token = request.cookies.get("private_fx_session", "")
        with lock:
            session = sessions.get(token)
            if not session or session[0] < time.time():
                sessions.pop(token, None)
                raise HTTPException(401, "Login required")
        if csrf:
            same_origin(request)
            supplied = request.headers.get("X-CSRF-Token", "")
            if not hmac.compare_digest(session[1], supplied):
                raise HTTPException(403, "CSRF token required")
        return session[1]

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        content = (ROOT / "private-desk" / "index.html").read_text(encoding="utf-8")
        # Pin inline scripts by content hash; chart styling is generated by trusted code.
        import base64
        import re

        hashes = [
            "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
            for script in re.findall(r"<script[^>]*>(.*?)</script>", content, re.S)
        ]
        response = HTMLResponse(content)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src "
            + " ".join(hashes)
            + "; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.post("/api/login")
    def login(body: LoginBody, request: Request, response: Response) -> dict[str, str]:
        same_origin(request)
        client = request.client.host if request.client else "unknown"
        now = time.time()
        with lock:
            attempts[client] = [t for t in attempts[client] if now - t < 60]
            if len(attempts[client]) >= 5:
                raise HTTPException(429, "Wait a minute before retrying")
            attempts[client].append(now)
        digest = hashlib.scrypt(
            body.password.encode(),
            salt=bytes.fromhex(auth["salt"]),
            n=2**14,
            r=8,
            p=1,
        ).hex()
        if not hmac.compare_digest(auth["digest"], digest):
            raise HTTPException(401, "Incorrect password")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with lock:
            # Reap expired sessions on each successful login.
            for key in [k for k, v in sessions.items() if v[0] < now]:
                sessions.pop(key, None)
            sessions[token] = (now + 43200, csrf)
            attempts.pop(client, None)
        response.set_cookie(
            "private_fx_session",
            token,
            httponly=True,
            samesite="strict",
            max_age=43200,
            secure=False,  # Local HTTP loopback only; never expose this listener externally.
        )
        return {"csrf_token": csrf}

    @app.post("/api/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        authenticated(request, csrf=True)
        with lock:
            sessions.pop(request.cookies.get("private_fx_session", ""), None)
        response.delete_cookie("private_fx_session")
        return {"ok": True}

    @app.get("/api/report")
    def report(request: Request) -> JSONResponse:
        csrf = authenticated(request)
        try:
            value = _load_current_report(state_dir)
        except (OSError, ValueError):
            return JSONResponse(
                {
                    "detail": "Saved research is unavailable. Refresh to capture a new report.",
                    "operations_readiness": _live_readiness(None),
                    "csrf_token": csrf,
                },
                status_code=503,
            )
        if value is None:
            return JSONResponse(
                {
                    "schema_version": "private-fx-v1",
                    "pair_reports": [],
                    "news": [],
                    "warnings": ["No report yet. Refresh research to capture actual sources."],
                    "research_status": "NO_REPORT",
                    "operations_readiness": _live_readiness(None),
                    "csrf_token": csrf,
                }
            )
        _project_operational_hold(value)
        # Full histories stay in the saved artifact; the desk renders summaries and recent rows.
        for series in value.get("historical_policy", {}).get("series_audits", []):
            series.pop("rows", None)
        for pair in value.get("pair_reports", []):
            features = pair.get("historical_policy_features")
            if features is not None:
                rows = features.pop("rows", [])
                features["recent_rows"] = rows[-6:]
                features["last_observed_feature_date"] = (
                    rows[-1]["observation_date"] if rows else None
                )
                features["definition_break_windows"] = sum(
                    row["change_unavailable_reason"] == "INSTRUMENT_DEFINITION_BREAK"
                    for row in rows
                )
        value["csrf_token"] = csrf
        return JSONResponse(value)

    @app.get("/api/status")
    def status(request: Request) -> dict[str, Any]:
        authenticated(request)
        with lock:
            current = dict(job)
        try:
            readiness = _live_readiness(_load_current_report(state_dir))
        except (OSError, ValueError):
            readiness = _live_readiness(None)
            if not current["running"]:
                current.update(error="REPORT_UNAVAILABLE", message="Saved research is unavailable.")
        current["operations_readiness"] = readiness
        current["refresh_status"] = (
            "RUNNING" if current["running"] else "FAILED" if current["error"] else "IDLE"
        )
        if current["running"]:
            current["status"] = "REFRESHING"
        else:
            current["status"] = readiness["status"]
            if readiness["status"] == "CURRENT":
                if not current["error"]:
                    current["message"] = "Input age checks pass; this does not validate a trade."
            else:
                held_pairs = [
                    r["pair"] for r in readiness["pair_checks"] if r["status"] != "CURRENT"
                ]
                current["message"] = (
                    "Research input checks are on hold. Refresh and review report/context evidence."
                    if readiness["global_hold"]
                    else "Input age checks hold " + ", ".join(held_pairs) + ". Other pairs retain "
                    "their saved research status."
                )
                current["error"] = current["error"] or current["message"]
        return current

    @app.get("/api/journal")
    def journal(request: Request) -> dict[str, Any]:
        authenticated(request)
        try:
            return journal_view(state_dir)
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(
                503, "Decision journal is unavailable; original files retained"
            ) from None

    @app.post("/api/journal/update")
    def update_journal(request: Request) -> dict[str, Any]:
        authenticated(request, csrf=True)
        with lock:
            if job["running"]:
                raise HTTPException(409, "Wait for research refresh before updating outcomes")
            try:
                return sync_journal(state_dir, state_dir / "report.json")
            except (OSError, ValueError, KeyError, TypeError):
                raise HTTPException(
                    503, "Decision journal update is unavailable; files retained"
                ) from None

    @app.get("/api/journal.csv")
    def journal_csv(request: Request) -> Response:
        authenticated(request)
        try:
            value = journal_view(state_dir)
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(503, "Decision journal is unavailable") from None
        fields = [
            "decision_id",
            "primary_decision_id",
            "repeated_publication",
            "primary_entry_date",
            "report_sha256",
            "pair",
            "recorded_at",
            "as_of",
            "decision",
            "frozen_direction",
            "reasons",
            "earliest_entry_date",
            "evaluation_status",
            "evaluation_reason",
            "benchmark_direction",
            "benchmark_kind",
            "net_r",
            "tp1_hit",
            "exit_time",
            "ambiguous_bars",
            "execution_state",
            "candidate_plan_net_r",
            "candidate_plan_kind",
        ]
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in value["rows"]:
            candidate, result = row["candidate"], row["evaluation"]["result"]
            base = {
                "decision_id": row["decision_id"],
                "primary_decision_id": row["primary_decision_id"],
                "repeated_publication": row["repeated_publication"],
                "primary_entry_date": row["primary_entry_date"],
                "report_sha256": row["report_sha256"],
                "pair": row["pair"],
                "recorded_at": row["recorded_at"],
                "as_of": candidate.get("as_of"),
                "decision": candidate.get("status", "UNKNOWN"),
                "frozen_direction": candidate.get("direction"),
                "reasons": json.dumps(candidate.get("reasons", []), ensure_ascii=False),
                "earliest_entry_date": row["earliest_entry_date"],
                "evaluation_status": result["status"],
                "evaluation_reason": result["reason"],
                "execution_state": "NOT_RECORDED",
                "candidate_plan_net_r": (result.get("candidate_plan_outcome") or {}).get("net_r"),
                "candidate_plan_kind": (result.get("candidate_plan_outcome") or {}).get("kind"),
            }
            for outcome in result["outcomes"] or [{}]:
                item = dict(
                    base,
                    **{
                        key: outcome.get(key)
                        for key in ("net_r", "tp1_hit", "exit_time", "ambiguous_bars")
                    },
                    benchmark_direction=outcome.get("benchmark_direction"),
                    benchmark_kind="COUNTERFACTUAL_RESEARCH",
                )
                safe = {
                    key: "'" + str(val)
                    if isinstance(val, str)
                    and val.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
                    else val
                    for key, val in item.items()
                }
                writer.writerow(safe)
        return Response(
            stream.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="private-decisions-outcomes.csv"'
            },
        )

    @app.post("/api/refresh")
    def refresh_report(request: Request) -> dict[str, Any]:
        authenticated(request, csrf=True)
        with lock:
            if job["running"]:
                return {"running": True, "message": job["message"]}
            job.update(running=True, error=None, message="Starting source capture")

        def progress(message: str) -> None:
            with lock:
                job["message"] = message

        def worker() -> None:
            try:
                build_report(state_dir, refresh=True, progress=progress)
            except Exception as exc:
                with lock:
                    job.update(error=type(exc).__name__, message="Refresh failed; report retained")
            finally:
                with lock:
                    job["running"] = False

        threading.Thread(target=worker, daemon=True, name="private-fx-refresh").start()
        return {"running": True, "message": "Starting source capture"}

    @app.get("/api/export.csv")
    def export(request: Request) -> Response:
        authenticated(request)
        try:
            value = _load_current_report(state_dir)
        except (OSError, ValueError):
            raise HTTPException(503, "Saved research is unavailable") from None
        if value is None:
            raise HTTPException(404, "No report")
        rows = [
            {**trade, "pair": pair["pair"]}
            for pair in value["pair_reports"]
            for trade in pair.get("backtest", {}).get("trades", [])
        ]
        audit = value.get("portfolio_audit", {})
        accepted = {(row["pair"], row["entry_time"]) for row in audit.get("accepted", [])}
        skipped = {
            (row["pair"], row["entry_time"]): row["reason"] for row in audit.get("skipped", [])
        }
        for row in rows:
            identity = (row["pair"], row.get("entry_time"))
            row["overlap_audit_decision"] = (
                "ACCEPTED"
                if identity in accepted
                else "SKIPPED"
                if identity in skipped
                else "UNAVAILABLE"
            )
            row["overlap_audit_reason"] = skipped.get(identity, "")
            row["overlap_audit_qualification"] = "UNQUALIFIED"
        risk = value.get("correlation_audit", {})
        risk_accepted = {(r["pair"], r["entry_time"]) for r in risk.get("accepted", [])}
        risk_skipped = {(r["pair"], r["entry_time"]): r["reason"] for r in risk.get("skipped", [])}
        for row in rows:
            identity = row["pair"], row.get("entry_time")
            row["correlation_audit_decision"] = (
                "ADMITTED_RESEARCH"
                if identity in risk_accepted
                else "SKIPPED"
                if identity in risk_skipped
                else "UNAVAILABLE"
            )
            row["correlation_audit_reason"] = risk_skipped.get(identity, "")
            row["correlation_audit_qualification"] = "UNQUALIFIED"
        columns = sorted({key for row in rows for key in row}) or ["pair", "net_r"]
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            safe = {
                k: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v
                for k, v in row.items()
            }
            writer.writerow(safe)
        return Response(
            stream.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="private-fx-trades.csv"'},
        )

    return app
