"""Verify the actual eight-leg JPY extension without refreshes, AI or source acquisition."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".private-fx"
BASE = "http://127.0.0.1:8765"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    before_report = digest(STATE / "report.json")
    before_events = {path: digest(path) for path in (STATE / "journal").rglob("*.json")}
    anonymous = requests.Session()
    assert anonymous.get(BASE + "/api/report", timeout=30).status_code == 401
    assert anonymous.get(BASE + "/api/journal", timeout=30).status_code == 401
    client = requests.Session()
    password = (STATE / "access.txt").read_text(encoding="utf-8").splitlines()[1]
    login = client.post(BASE + "/api/login", json={"password": password}, timeout=30)
    login.raise_for_status()
    token = login.json()["csrf_token"]
    response = client.get(BASE + "/api/report", timeout=30)
    response.raise_for_status()
    report = response.json()
    if "report" in report:
        report = report["report"]
    assert len(report["pair_reports"]) == 8
    jp = next(x for x in report["historical_policy"]["series_audits"] if x["currency"] == "JPY")
    assert len(report["historical_policy"]["series_audits"]) == 8
    assert jp["numeric_count"] == 5532 and jp["sha256"] == (
        "75146b9afa795f2e27e6f47b2af5303879ccd7604857512848793cedd6c5984a"
    )
    assert jp["last_numeric"]["observation_date"] == "2026-09-29"
    assert jp["last_numeric"]["value"] == 1.25
    pair = next(x for x in report["pair_reports"] if x["pair"] == "USDJPY")
    assert pair["historical_policy_features"]["matched_numeric_count"] == 4642
    assert pair["historical_policy_features"]["change_numeric_count"] == 4597
    assert pair["historical_policy_features"]["forecast_qualification"] == "UNQUALIFIED"
    assert report["current_review"]["status"] == "DETACHED"
    assert report["ai_summary"]["status"] == "UNAVAILABLE"
    assert report["prior_ai_summary"]["status"] == "GENERATED_UNVALIDATED"
    assert all(x["candidate"]["status"] == "ABSTAIN" for x in report["pair_reports"])
    assert all(x["candidate"]["probability"] is None for x in report["pair_reports"])
    history_response = client.get(BASE + "/api/journal", timeout=30)
    history_response.raise_for_status()
    history = history_response.json()
    assert history["decision_count"] == 16
    assert history["unique_observation_count"] == 8
    assert history["repeated_publication_count"] == 8
    assert history["unpublished_report_count"] == 0
    assert history["outcome_status_counts"] == {"PENDING": 5, "UNAVAILABLE": 3}
    exported = client.get(BASE + "/api/journal.csv", timeout=30)
    exported.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 16 and all(x["decision"] == "ABSTAIN" for x in rows)
    assert client.post(BASE + "/api/journal/update", timeout=30).status_code == 403
    logout = client.post(BASE + "/api/logout", headers={"X-CSRF-Token": token}, timeout=30)
    logout.raise_for_status()
    assert client.get(BASE + "/api/report", timeout=30).status_code == 401
    assert digest(STATE / "report.json") == before_report
    assert before_events == {path: digest(path) for path in (STATE / "journal").rglob("*.json")}
    receipt = {
        "scope": "First actual eight-leg JPY policy extension; hypothetical journal, no model/fetch/order",
        "verified_at": datetime.now(UTC).isoformat(),
        "url": BASE,
        "server_pid": int((STATE / "server.pid").read_text(encoding="utf-8")),
        "report_sha256": before_report,
        "source_sha256": jp["sha256"],
        "jpy_numeric_count": jp["numeric_count"],
        "usd_jpy_matched_markers": 4642,
        "usd_jpy_five_weekday_changes": 4597,
        "current_ai_status": report["ai_summary"]["status"],
        "journal_publications": 16,
        "distinct_observations": 8,
        "repeat_publications": 8,
        "csv_rows": len(rows),
        "source_availability": "UNKNOWN",
        "forecast_qualification": "UNQUALIFIED",
        "authentication_and_csrf": "PASS",
        "report_and_events_unchanged": True,
    }
    target = ROOT / "reports/private-jpy-policy-runtime.json"
    target.write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    print("PRIVATE_JPY_POLICY_RUNTIME_VERIFIED")


if __name__ == "__main__":
    main()
