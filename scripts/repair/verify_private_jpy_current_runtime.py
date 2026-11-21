"""Read-only actual current-JPY runtime receipt; no model, fetch, refresh or order."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import requests

root = Path(__file__).resolve().parents[2]
state = root / ".private-fx"
base = "http://127.0.0.1:8765"
report_path = state / "report.json"
before_report = hashlib.sha256(report_path.read_bytes()).hexdigest()
assert before_report == "1af3f4192c4086b73ad468d32ad4fff493d75561d6fbc7359b0a7d90372f6a2c"
before_events = {
    path: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (state / "journal").rglob("*.json")
}
anonymous = requests.Session()
for route in ("/api/report", "/api/journal", "/api/journal.csv"):
    assert anonymous.get(base + route, timeout=30).status_code == 401
client = requests.Session()
password = (state / "access.txt").read_text(encoding="utf-8").splitlines()[1]
login = client.post(base + "/api/login", json={"password": password}, timeout=30)
login.raise_for_status()
token = login.json()["csrf_token"]
response = client.get(base + "/api/report", timeout=30)
response.raise_for_status()
report = response.json()
if "report" in report:
    report = report["report"]
assert len(report["pair_reports"]) == 8
assert all(x["candidate"]["status"] == "ABSTAIN" for x in report["pair_reports"])
assert all(x["candidate"]["probability"] is None for x in report["pair_reports"])
fundamentals = report["pair_reports"][0]["fundamentals"]
assert fundamentals["status"] == "PARTIAL"
assert fundamentals["policy_status"] == "COMPLETE" and fundamentals["missing_currencies"] == []
jpy = fundamentals["indicators"]["jpy_call_rate_guideline"]
assert jpy["value"] == 1.25 and jpy["policy_target_qualifier"] == "around"
assert jpy["published_at"] is None and jpy["effective_from"] is None
assert jpy["decision_date"] is None and jpy["point_in_time"] is False
assert jpy["source_body"]["sha256"] == (
    "5dcdd87286d207642eb3df49c2adb3fbdd4fad498aefc3e8b582d7879316424d"
)
assert report["current_review"]["method_version"] == "private-current-headline-v4"
assert report["ai_summary"]["status"] == "GENERATED_UNVALIDATED"
assert report["prior_ai_summary"]["method_version"] == "private-current-headline-v3"
assert report["current_review"]["forecast_qualification"] == "UNQUALIFIED"
boj = [x for x in report["news"] if x["source"] == "Bank of Japan"]
assert len(boj) == 52
assert all(x["original_url"].startswith("http://www.boj.or.jp/en/") for x in boj)
assert all(x["url"].startswith("https://www.boj.or.jp/en/") for x in boj)
history_response = client.get(base + "/api/journal", timeout=30)
history_response.raise_for_status()
history = history_response.json()
assert history["decision_count"] == 24
assert history["unique_observation_count"] == 8
assert history["repeated_publication_count"] == 16
assert history["unpublished_report_count"] == 0
assert history["outcome_status_counts"] == {"PENDING": 5, "UNAVAILABLE": 3}
exported = client.get(base + "/api/journal.csv", timeout=30)
exported.raise_for_status()
rows = list(csv.DictReader(io.StringIO(exported.text)))
assert len(rows) == 24 and all(x["decision"] == "ABSTAIN" for x in rows)
assert client.post(base + "/api/journal/update", timeout=30).status_code == 403
logout = client.post(base + "/api/logout", headers={"X-CSRF-Token": token}, timeout=30)
logout.raise_for_status()
assert client.get(base + "/api/report", timeout=30).status_code == 401
assert hashlib.sha256(report_path.read_bytes()).hexdigest() == before_report
assert before_events == {
    path: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (state / "journal").rglob("*.json")
}
receipt = {
    "scope": "Actual current Japanese descriptive policy/headlines and publication journal",
    "verified_at": datetime.now(UTC).isoformat(),
    "url": base,
    "server_pid": int((state / "server.pid").read_text(encoding="utf-8")),
    "report_sha256": before_report,
    "policy_original_sha256": jpy["source_body"]["sha256"],
    "feed_original_sha256": boj[0]["source_body"]["sha256"],
    "boj_headlines": len(boj),
    "current_ai_status": report["ai_summary"]["status"],
    "current_ai_method": report["current_review"]["method_version"],
    "policy_currencies_missing": fundamentals["missing_currencies"],
    "overall_fundamentals_status": fundamentals["status"],
    "journal_publications": history["decision_count"],
    "distinct_observations": history["unique_observation_count"],
    "repeat_publications": history["repeated_publication_count"],
    "outcome_status_counts": history["outcome_status_counts"],
    "csv_rows": len(rows),
    "forecast_qualification": "UNQUALIFIED",
    "authentication_csrf_export_logout": "PASS",
    "report_and_events_unchanged": True,
}
(root / "reports/private-jpy-current-runtime.json").write_text(
    json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8"
)
print(json.dumps(receipt, indent=2))
print("PRIVATE_JPY_CURRENT_RUNTIME_VERIFIED")
