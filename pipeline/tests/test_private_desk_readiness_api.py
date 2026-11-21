"""Request-time age holds must reach the authenticated browser projection."""

from __future__ import annotations

import csv
import io
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.private_desk import api
from src.private_desk.report import atomic_json
from src.private_desk.universe import PAIRS as CURRENT_PAIRS

NOW = datetime(2026, 10, 1, 16, tzinfo=UTC)

PAIRS = list(CURRENT_PAIRS)


def saved_report() -> dict[str, Any]:
    return {
        "schema_version": "private-fx-v1",
        "universe": list(PAIRS),
        "generated_at": "2026-10-01T15:00:00Z",
        "current_context_updated_at": "2026-10-01T15:01:00Z",
        "warnings": ["Original research restriction."],
        "pair_reports": [
            {
                "pair": pair,
                "data_coverage": {"status": "VALID", "interval": "1d", "last_bar": "2026-09-30"},
                "candidate": {
                    "status": "RESEARCH_CANDIDATE",
                    "direction": "BUY",
                    "as_of": "2026-09-30",
                    "entry": 1.0,
                    "stop": 0.99,
                    "tp1": 1.01,
                    "tp2": 1.03,
                    "probability": 0.65,
                    "expected_r": 0.2,
                    "probability_ci95": [0.6, 0.7],
                    "expected_r_ci95_approx": [0.1, 0.3],
                    "reasons": [],
                },
                "backtest": {"trades": [{"entry_time": "2024-01-04", "net_r": -1.1}]},
                "ai_analysis": {"thesis": "Original conditional scenario."},
            }
            for pair in PAIRS
        ],
    }


def test_export_distinguishes_new_risk_admission_from_trade_qualification(
    session: tuple[TestClient, Path],
) -> None:
    client, directory = session
    value = saved_report()
    value["correlation_audit"] = {
        "accepted": [{"pair": "USDJPY", "entry_time": "2024-01-04"}],
        "skipped": [{"pair": "EURUSD", "entry_time": "2024-01-04", "reason": "WEEKLY_CAP"}],
    }
    atomic_json(directory / "report.json", value)
    before = (directory / "report.json").read_bytes()
    response = client.get("/api/export.csv")
    assert response.status_code == 200
    rows = {r["pair"]: r for r in csv.DictReader(io.StringIO(response.text))}
    assert rows["USDJPY"]["correlation_audit_decision"] == "ADMITTED_RESEARCH"
    assert rows["USDJPY"]["correlation_audit_qualification"] == "UNQUALIFIED"
    assert rows["EURUSD"]["correlation_audit_reason"] == "WEEKLY_CAP"
    assert (directory / "report.json").read_bytes() == before


def test_malformed_new_risk_audit_fails_closed_on_export(
    session: tuple[TestClient, Path],
) -> None:
    client, directory = session
    value = saved_report()
    value["correlation_audit"] = {"accepted": ["invalid"]}
    atomic_json(directory / "report.json", value)
    assert client.get("/api/export.csv").status_code == 503


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path]:
    monkeypatch.setattr(api, "_decision_clock", lambda: NOW, raising=False)
    app = api.create_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    password = (tmp_path / "access.txt").read_text(encoding="utf-8").splitlines()[1]
    assert client.post("/api/login", json={"password": password}).status_code == 200
    return client, tmp_path


def test_old_candidate_is_held_on_actual_report_endpoint(
    session: tuple[TestClient, Path],
) -> None:
    client, directory = session
    value = saved_report()
    value["generated_at"] = "2026-09-25T15:00:00Z"
    atomic_json(directory / "report.json", value)
    original = (directory / "report.json").read_bytes()
    response = client.get("/api/report")
    assert response.status_code == 200
    projected = response.json()
    assert projected["operations_readiness"]["status"] == "HOLD"
    for pair in projected["pair_reports"]:
        assert pair["candidate"]["status"] == "ABSTAIN"
        for key in (
            "direction",
            "entry",
            "stop",
            "tp1",
            "tp2",
            "probability",
            "expected_r",
            "probability_ci95",
            "expected_r_ci95_approx",
        ):
            assert pair["candidate"][key] is None
    assert (directory / "report.json").read_bytes() == original


def test_legacy_candidate_aliases_are_cleared(session: tuple[TestClient, Path]) -> None:
    client, directory = session
    value = saved_report()
    value["generated_at"] = "2026-09-20T10:00:00Z"
    value["pair_reports"][0]["candidate"].update(bias="SELL", execution_status="READY")
    atomic_json(directory / "report.json", value)
    candidate = client.get("/api/report").json()["pair_reports"][0]["candidate"]
    assert candidate["status"] == "ABSTAIN"
    assert candidate["bias"] is None
    assert candidate["execution_status"] == "UNAVAILABLE"


@pytest.mark.parametrize("corruption", ["cross-pair", "audit-type", "accepted-row", "skip-row"])
def test_cross_pair_export_identity_is_rejected(
    session: tuple[TestClient, Path],
    corruption: str,
) -> None:
    client, directory = session
    value = saved_report()
    if corruption == "cross-pair":
        value["pair_reports"][0]["backtest"]["trades"][0]["pair"] = "GBPUSD"
    elif corruption == "audit-type":
        value["portfolio_audit"] = []
    elif corruption == "accepted-row":
        value["portfolio_audit"] = {"accepted": [None]}
    else:
        value["portfolio_audit"] = {"skipped": [{"pair": "EURUSD", "entry_time": "2024-01-04"}]}
    atomic_json(directory / "report.json", value)
    assert client.get("/api/report").status_code == 503
    assert client.get("/api/export.csv").status_code == 503


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("generated_at",), "2026-09-28T15:00:00Z"),
        (("generated_at",), "2026-10-01T17:00:00Z"),
        (("generated_at",), "2026-10-01"),
        (("generated_at",), None),
        (("current_context_updated_at",), "2026-09-28T15:00:00Z"),
        (("current_context_updated_at",), "2026-10-01T17:00:00Z"),
        (("current_context_updated_at",), "2026-10-01"),
        (("current_context_updated_at",), None),
        (("schema_version",), "unknown"),
        (("universe",), PAIRS[:-1] + ["USDJPY"]),
        (("pair_reports",), []),
    ],
    ids=[
        "old-report",
        "future-report",
        "date-only-report",
        "missing-report-clock",
        "old-context",
        "future-context",
        "date-only-context",
        "missing-context",
        "wrong-schema",
        "foreign-pair",
        "missing-pair-rows",
    ],
)
def test_clock_and_structure_holds_reach_api(
    session: tuple[TestClient, Path],
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    client, directory = session
    value = saved_report()
    value[path[0]] = replacement
    atomic_json(directory / "report.json", value)
    before = (directory / "report.json").read_bytes()
    result = client.get("/api/report")
    assert result.status_code == 200
    body = result.json()
    assert body["operations_readiness"]["status"] == "HOLD"
    assert body["operations_readiness"]["global_hold"] is True
    assert all(p["candidate"]["status"] == "ABSTAIN" for p in body["pair_reports"])
    assert (directory / "report.json").read_bytes() == before
    status = client.get("/api/status").json()
    assert status["running"] is False
    assert status["status"] == "HOLD"
    assert status["operations_readiness"]["global_hold"] is True


def test_fresh_projection_preserves_research_and_never_promotes(
    session: tuple[TestClient, Path],
) -> None:
    client, directory = session
    value = saved_report()
    value["pair_reports"][1]["candidate"]["status"] = "ABSTAIN"
    atomic_json(directory / "report.json", value)
    before = (directory / "report.json").read_bytes()
    body = client.get("/api/report").json()
    assert body["operations_readiness"]["status"] == "CURRENT"
    assert body["operations_readiness"]["global_hold"] is False
    assert body["pair_reports"] == value["pair_reports"]
    assert body["warnings"] == value["warnings"]
    assert body["pair_reports"][1]["candidate"]["status"] == "ABSTAIN"
    assert (directory / "report.json").read_bytes() == before


@pytest.mark.parametrize("last_bar", ["2026-09-29", "2026-10-01", "bad-date", None])
def test_one_stale_pair_does_not_veto_fresh_pairs(
    session: tuple[TestClient, Path],
    last_bar: Any,
) -> None:
    client, directory = session
    value = saved_report()
    value["pair_reports"][0]["data_coverage"]["last_bar"] = last_bar
    value["pair_reports"][0]["candidate"]["as_of"] = last_bar
    original_pairs = deepcopy(value["pair_reports"])
    atomic_json(directory / "report.json", value)
    body = client.get("/api/report").json()
    assert body["operations_readiness"]["status"] == "PARTIAL"
    assert body["operations_readiness"]["global_hold"] is False
    assert body["pair_reports"][0]["candidate"]["status"] == "ABSTAIN"
    assert body["pair_reports"][1:] == original_pairs[1:]
    assert body["pair_reports"][0]["backtest"] == original_pairs[0]["backtest"]
    assert body["pair_reports"][0]["ai_analysis"] == original_pairs[0]["ai_analysis"]
    assert client.get("/api/status").json()["status"] == "PARTIAL"


def test_status_and_restart_recheck_clock(
    session: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, directory = session
    value = saved_report()
    atomic_json(directory / "report.json", value)
    before = (directory / "report.json").read_bytes()
    assert client.get("/api/status").json()["status"] == "CURRENT"
    monkeypatch.setattr(api, "_decision_clock", lambda: datetime(2026, 10, 2, 16, tzinfo=UTC))
    assert client.get("/api/status").json()["status"] == "HOLD"
    restarted = TestClient(api.create_app(directory), raise_server_exceptions=False)
    assert restarted.get("/api/status").status_code == 401
    password = (directory / "access.txt").read_text(encoding="utf-8").splitlines()[1]
    assert restarted.post("/api/login", json={"password": password}).status_code == 200
    assert restarted.get("/api/status").json()["status"] == "HOLD"
    assert all(
        p["candidate"]["status"] == "ABSTAIN"
        for p in restarted.get("/api/report").json()["pair_reports"]
    )
    assert (directory / "report.json").read_bytes() == before


@pytest.mark.parametrize(
    "payload",
    [
        b'{"private-fixture-value":',
        b"null",
        b"[]",
        b'{"x":NaN}',
        b"\xff",
        b'{"pair_reports":["invalid-row"]}',
        b'{"historical_policy":"bad"}',
        b'{"pair_reports":[{"historical_policy_features":{"rows":[{}]}}]}',
        b'{"pair_reports":[{"backtest":"bad"}]}',
        b"[" * 1100 + b"0" + b"]" * 1100,
    ],
    ids=[
        "broken-json",
        "null",
        "array",
        "nonfinite",
        "bad-utf8",
        "bad-row",
        "bad-history",
        "bad-feature-row",
        "bad-backtest",
        "too-deep",
    ],
)
def test_unreadable_reports_are_sanitized(
    session: tuple[TestClient, Path],
    payload: bytes,
) -> None:
    client, directory = session
    (directory / "report.json").write_bytes(payload)
    result = client.get("/api/report")
    assert result.status_code == 503
    assert "private-fixture-value" not in result.text
    assert "operations_readiness" in result.json()
    status = client.get("/api/status")
    assert status.status_code == 200
    assert status.json()["status"] == "HOLD"
    assert status.json()["error"] == "REPORT_UNAVAILABLE"
    assert client.get("/api/export.csv").status_code == 503
    assert (directory / "report.json").read_bytes() == payload


def test_missing_report_is_held(session: tuple[TestClient, Path]) -> None:
    client, _ = session
    body = client.get("/api/report").json()
    assert body["research_status"] == "NO_REPORT"
    assert body["operations_readiness"]["status"] == "HOLD"
    assert client.get("/api/status").json()["status"] == "HOLD"


def test_readiness_does_not_bypass_authorization(session: tuple[TestClient, Path]) -> None:
    client, directory = session
    atomic_json(directory / "report.json", saved_report())
    csrf = client.get("/api/report").json()["csrf_token"]
    assert client.post("/api/refresh").status_code == 403
    assert client.get("/api/export.csv").status_code == 200
    assert client.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/report").status_code == 401
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/export.csv").status_code == 401


@pytest.mark.parametrize("stale_pair", [False, True])
def test_active_refresh_status_still_has_live_job_identity(
    session: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
    stale_pair: bool,
) -> None:
    import threading
    import time

    client, directory = session
    value = saved_report()
    if stale_pair:
        value["pair_reports"][0]["candidate"]["as_of"] = "2026-09-29"
        value["pair_reports"][0]["data_coverage"]["last_bar"] = "2026-09-29"
    atomic_json(directory / "report.json", value)
    before = (directory / "report.json").read_bytes()
    entered, release = threading.Event(), threading.Event()

    def blocked_build(*args: Any, **kwargs: Any) -> None:
        entered.set()
        assert release.wait(5)
        raise TimeoutError("private fixture provider body must not be exposed")

    monkeypatch.setattr(api, "build_report", blocked_build)
    csrf = client.get("/api/report").json()["csrf_token"]
    try:
        result = client.post("/api/refresh", headers={"X-CSRF-Token": csrf})
        assert result.status_code == 200
        assert entered.wait(1)
        status = client.get("/api/status").json()
        assert status["running"] is True
        assert status["status"] == "REFRESHING"
    finally:
        release.set()
    for _ in range(30):
        status = client.get("/api/status").json()
        if not status["running"]:
            break
        time.sleep(0.01)
    assert status["running"] is False
    assert status["error"] == "TimeoutError"
    assert status["status"] == ("PARTIAL" if stale_pair else "CURRENT")
    assert "private fixture provider body" not in str(status)
    assert (directory / "report.json").read_bytes() == before
