"""Verify the authorized loopback journal without refreshing sources or invoking AI."""

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
URL = "http://127.0.0.1:8765"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    report_bytes = (STATE / "report.json").read_bytes()
    saved = json.loads(report_bytes)
    expected_pairs = set(saved["universe"])
    before_events = {path: digest(path) for path in (STATE / "journal").rglob("*.json")}
    for endpoint in ("/api/journal", "/api/journal.csv"):
        assert requests.get(URL + endpoint, timeout=30).status_code == 401
    assert requests.post(URL + "/api/journal/update", timeout=30).status_code == 401
    session = requests.Session()
    password = (STATE / "access.txt").read_text(encoding="utf-8").splitlines()[1]
    login = session.post(URL + "/api/login", json={"password": password}, timeout=30)
    del password
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    assert session.post(URL + "/api/journal/update", timeout=30).status_code == 403
    assert session.post(URL + "/api/journal/update", headers={"X-CSRF-Token": "invalid"}, timeout=30).status_code == 403
    report = session.get(URL + "/api/report", timeout=60)
    assert report.status_code == 200
    projected = report.json()
    assert {row["pair"] for row in projected["pair_reports"]} == expected_pairs
    assert all(row["candidate"]["status"] == "ABSTAIN" and row["candidate"]["probability"] is None for row in projected["pair_reports"])
    history = session.get(URL + "/api/journal", timeout=60)
    assert history.status_code == 200
    value = history.json()
    assert value["decision_count"] == 8 and value["unique_observation_count"] == 8
    assert {row["pair"] for row in value["rows"]} == expected_pairs
    assert value["decision_status_counts"] == {"ABSTAIN": 8}
    assert value["outcome_status_counts"] == {"PENDING": 5, "UNAVAILABLE": 3}
    assert all(row["execution_state"] == "NOT_RECORDED" for row in value["rows"])
    update = session.post(URL + "/api/journal/update", headers={"X-CSRF-Token": csrf}, timeout=60)
    assert update.status_code == 200
    assert update.json()["evaluation_event_count"] == value["evaluation_event_count"]
    exported = session.get(URL + "/api/journal.csv", timeout=60)
    assert exported.status_code == 200
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 8 and {row["pair"] for row in rows} == expected_pairs
    assert all(row["execution_state"] == "NOT_RECORDED" and not row["net_r"] for row in rows)
    assert (STATE / "report.json").read_bytes() == report_bytes
    assert before_events == {path: digest(path) for path in (STATE / "journal").rglob("*.json")}
    assert session.post(URL + "/api/logout", headers={"X-CSRF-Token": csrf}, timeout=30).status_code == 200
    assert session.get(URL + "/api/journal", timeout=30).status_code == 401
    receipt = {
        "verified_at": datetime.now(UTC).isoformat(), "url": URL,
        "server_pid": int((STATE / "server.pid").read_text(encoding="utf-8").strip()),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "pairs": sorted(expected_pairs), "decision_count": value["decision_count"],
        "unique_observation_count": value["unique_observation_count"],
        "outcome_status_counts": value["outcome_status_counts"],
        "evaluation_event_count": value["evaluation_event_count"],
        "earliest_entry_dates": sorted({row["earliest_entry_date"] for row in value["rows"]}),
        "recorded_at": sorted({row["recorded_at"] for row in value["rows"]}),
        "csv_sha256": hashlib.sha256(exported.content).hexdigest(), "csv_rows": len(rows),
        "report_and_events_unchanged": True, "authentication_and_csrf_checks": "PASS",
        "execution_state": "NOT_RECORDED", "forecast_qualification": "UNQUALIFIED",
        "journal_files": {str(path.relative_to(ROOT)): sha for path, sha in before_events.items()},
        "verification_scope": "Existing eight-record initial packet; no source refresh, AI or orders.",
    }
    target = ROOT / "reports" / "private-outcomes-runtime.json"
    target.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("PRIVATE_OUTCOMES_RUNTIME_OK", value["outcome_status_counts"], digest(target))


if __name__ == "__main__":
    main()
