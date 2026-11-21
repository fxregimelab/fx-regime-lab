"""Read-only authenticated daily-risk and immutable journal verification."""

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
before_events = {
    path: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (state / "journal").rglob("*.json")
}
saved_before = json.loads(
    (root / "reports/private-daily-risk-before.json").read_bytes()
)
for filename, digest in saved_before["journal_files"].items():
    assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest
anonymous = requests.Session()
for route in ("/api/report", "/api/journal", "/api/journal.csv"):
    assert anonymous.get(base + route, timeout=30).status_code == 401
client = requests.Session()
password = (state / "access.txt").read_text(encoding="utf-8").splitlines()[1]
login = client.post(base + "/api/login", json={"password": password}, timeout=30)
login.raise_for_status()
token = login.json()["csrf_token"]
response = client.get(base + "/api/report", timeout=60)
response.raise_for_status()
report = response.json()
report = report.get("report", report)
assert len(report["pair_reports"]) == 8
assert all(item["candidate"]["status"] == "ABSTAIN" for item in report["pair_reports"])
assert all(item["candidate"]["probability"] is None for item in report["pair_reports"])
assert report["ai_summary"]["status"] == "UNAVAILABLE"
assert report["current_review"]["status"] == "DETACHED"
assert report["prior_current_review"]["method_version"] == "private-current-headline-v4"
assert report["prior_ai_summary"]["status"] == "GENERATED_UNVALIDATED"
audit = report["daily_risk_audit"]
assert audit["status"] == "DEVELOPMENT_DAILY_RISK_COUNTERFACTUAL"
assert audit["continuous_control"] == audit["execution_qualification"] == "UNQUALIFIED"
assert audit["executable_forced_exit_return"] is None and audit["hedge_return"] is None
assert audit["mean_modelled_net_r"] < 0
assert audit["post_decision_breach_days"] == audit["post_decision_unknown_days"] == 0
assert all(
    len(group) <= 2 for row in audit["daily_reviews"] for group in row["after_groups"]
)
assert all(
    len(row["active_pairs_after_decision"]) <= 5 for row in audit["daily_reviews"]
)
assert all(len(row["reserved_pairs"]) <= 5 for row in audit["daily_reviews"])
assert all(row["admitted_research_calls"] <= 5 for row in audit["weekly"])
parent_path = Path(report["daily_risk_publication"]["parent_path"])
parent_bytes = parent_path.read_bytes()
assert hashlib.sha256(parent_bytes).hexdigest() == saved_before["parent_report_sha256"]
parent = json.loads(parent_bytes)
stored_report = json.loads(report_path.read_bytes())
assert stored_report["daily_risk_audit"] == audit
assert parent["correlation_audit"] == stored_report["correlation_audit"]
assert parent["portfolio_audit"] == stored_report["portfolio_audit"]
assert parent["news"] == stored_report["news"]
assert parent["historical_policy"] == stored_report["historical_policy"]
for old, new in zip(parent["pair_reports"], stored_report["pair_reports"], strict=True):
    for key, value in old.items():
        if key not in ("ai_analysis", "prior_ai_analysis"):
            assert new[key] == value, (old["pair"], key)
    assert new["prior_ai_analysis"] == old["ai_analysis"]
history_response = client.get(base + "/api/journal", timeout=30)
history_response.raise_for_status()
history = history_response.json()
assert history["decision_count"] == saved_before["journal_counts"]["decision_count"] + 8
assert (
    history["unique_observation_count"]
    == saved_before["journal_counts"]["unique_observation_count"]
)
assert (
    history["repeated_publication_count"]
    == saved_before["journal_counts"]["repeated_publication_count"] + 8
)
assert history["unpublished_report_count"] == 0
assert (
    history["outcome_status_counts"]
    == saved_before["journal_counts"]["outcome_status_counts"]
)
exported = client.get(base + "/api/journal.csv", timeout=30)
exported.raise_for_status()
rows = list(csv.DictReader(io.StringIO(exported.text)))
assert len(rows) == history["decision_count"] and all(
    row["decision"] == "ABSTAIN" for row in rows
)
assert client.post(base + "/api/journal/update", timeout=30).status_code == 403
assert client.get(base + "/api/status", timeout=30).json()["running"] is False
logout = client.post(base + "/api/logout", headers={"X-CSRF-Token": token}, timeout=30)
logout.raise_for_status()
assert client.get(base + "/api/report", timeout=30).status_code == 401
assert hashlib.sha256(report_path.read_bytes()).hexdigest() == before_report
assert before_events == {
    path: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (state / "journal").rglob("*.json")
}
receipt = {
    "verified_at": datetime.now(UTC).isoformat(),
    "url": base,
    "server_pid": int((state / "server.pid").read_text(encoding="utf-8")),
    "report_sha256": before_report,
    "parent_report_sha256": saved_before["parent_report_sha256"],
    "method_version": audit["method_version"],
    "accepted_calls": audit["accepted_call_count"],
    "skipped_calls": audit["skipped_call_count"],
    "daily_boundaries": audit["checked_daily_boundaries"],
    "modelled_exit_requests": audit["modelled_exit_request_count"],
    "post_decision_breach_days": audit["post_decision_breach_days"],
    "mean_modelled_net_r": audit["mean_modelled_net_r"],
    "common_coverage_frequency": audit["common_coverage_frequency"],
    "journal_publications": history["decision_count"],
    "distinct_observations": history["unique_observation_count"],
    "repeat_publications": history["repeated_publication_count"],
    "outcome_status_counts": history["outcome_status_counts"],
    "csv_rows": len(rows),
    "authentication_csrf_export_logout": "PASS",
    "report_and_events_unchanged": True,
    "original_research_preserved": True,
    "execution_and_intraday_qualification": "UNQUALIFIED",
}
(root / "reports/private-daily-risk-runtime.json").write_text(
    json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8"
)
print(json.dumps(receipt, indent=2))
print("PRIVATE_DAILY_RISK_RUNTIME_VERIFIED")
