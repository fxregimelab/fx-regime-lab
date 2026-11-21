"""Coordinator arithmetic and preservation audit; no outcome tuning or publication."""

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from src.private_desk.fomc_study import load_study
from src.private_desk.journal import journal_view

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".private-fx"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


before = json.loads((ROOT / "reports/private-fomc-before.json").read_bytes())
raw = (STATE / "report.json").read_bytes()
report = json.loads(raw)
parent_raw = Path(report["fomc_publication"]["parent_path"]).read_bytes()
parent = json.loads(parent_raw)
assert sha(parent_raw) == before["parent_report_sha256"]
assert sha(parent_raw) == report["fomc_publication"]["parent_sha256"]
allowed = {"fomc_history", "fomc_study", "fomc_publication", "ai_summary", "current_review", "pair_reports"}
changes = [key for key in set(parent) | set(report) if parent.get(key) != report.get(key)]
assert set(changes) <= allowed, changes
pair_changes = {}
for old, new in zip(parent["pair_reports"], report["pair_reports"], strict=True):
    changed = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    assert changed == ["ai_analysis"], (new["pair"], changed)
    assert old["ai_analysis"]["status"] == new["ai_analysis"]["status"] == "UNAVAILABLE"
    assert new["ai_analysis"]["reason"] == "FOMC development evidence added; prior AI retained."
    pair_changes[new["pair"]] = changed
assert parent["prior_ai_summary"] == report["prior_ai_summary"]
assert parent["prior_current_review"] == report["prior_current_review"]
assert all(sha(Path(p).read_bytes()) == digest for p, digest in before["journal_files"].items())
result = load_study(STATE)
assert result == report["fomc_study"]
manifest_path = Path(result["manifest_reference"]["capture_path"])
manifest = json.loads(manifest_path.read_bytes())
pointer = json.loads((STATE / "fomc-history/studies/latest.json").read_bytes())
result_path = Path(pointer["capture_path"])
assert manifest_path.stat().st_mtime_ns <= result_path.stat().st_mtime_ns
assert datetime.fromisoformat(manifest["registered_at_utc"]) < datetime.fromisoformat(
    report["fomc_publication"]["at"]
)
missing = sum(
    e["reason"] in ("MISSING_RISK_WINDOW", "MISSING_OR_QUARANTINED_WINDOW")
    for e in result["exclusions"]
)
assert len(result["paths"]) + missing == result["selected_event_count"] * 7 * 2
for aggregate in result["results"]:
    selected = [
        p for p in result["paths"]
        if p["horizon"] == aggregate["horizon"]
        and p["release_date"] in aggregate["complete_event_dates"]
    ]
    assert len(selected) == 7 * aggregate["complete_event_count"]
    mean = sum(p["hypothesis"]["net_r"] - p["opposite"]["net_r"] for p in selected) / len(selected)
    assert math.isclose(mean, aggregate["event_average_paired_difference_r"], abs_tol=1e-12)
    for cell in aggregate["pair_results"]:
        values = [p for p in selected if p["pair"] == cell["pair"]]
        assert len(values) == cell["count"]
        for field, leg in (("hypothesis_mean_net_r", "hypothesis"), ("opposite_mean_net_r", "opposite")):
            assert math.isclose(
                sum(p[leg]["net_r"] for p in values) / len(values), cell[field], abs_tol=1e-12
            )
    if len(aggregate["complete_event_dates"]) < 8:
        assert aggregate["event_block_interval95_descriptive_r"] is None
assert sum(w["distinct_change_events"] for w in result["weekly"]) == result["selected_event_count"]
assert sum(w["distinct_change_events"] == 0 for w in result["weekly"]) == result["zero_event_weeks"]
assert result["probability"] is None and result["forecast_qualification"] == "UNQUALIFIED"
view = journal_view(STATE)
fields = ("decision_count", "unique_observation_count", "repeated_publication_count", "outcome_status_counts")
assert view["decision_count"] == before["journal_counts"]["decision_count"] + 8
assert view["unique_observation_count"] == before["journal_counts"]["unique_observation_count"]
assert view["outcome_status_counts"] == before["journal_counts"]["outcome_status_counts"]
receipt = {
    "verified_at_utc": datetime.now(UTC).isoformat(),
    "report_sha256": sha(raw), "parent_sha256": sha(parent_raw),
    "changed_top_level_fields": sorted(changes), "pair_changes": pair_changes,
    "all_old_pair_research_identical_except_ai_unavailable_reason": True,
    "prior_ai_preserved": True, "old_journal_files_preserved": len(before["journal_files"]),
    "frozen_study_replayed": True, "manifest_written_before_result": True,
    "manifest_registered_before_publication": True,
    "source_counts": {k: report["fomc_history"][k] for k in (
        "status", "inventory_statement_count", "captured_statement_count",
        "exact_clock_count", "target_change_count")},
    "selected_changes": result["selected_event_count"],
    "valid_pair_horizon_paths": len(result["paths"]),
    "exclusion_counts": dict(Counter(e["reason"] for e in result["exclusions"])),
    "horizons": [{k: a[k] for k in (
        "horizon", "complete_event_count", "complete_event_dates", "valid_pair_alternatives",
        "event_average_paired_difference_r", "event_block_interval95_descriptive_r")}
        for a in result["results"]],
    "calendar_weeks": result["complete_calendar_weeks"], "zero_event_weeks": result["zero_event_weeks"],
    "mean_policy_events_per_week": result["mean_policy_events_per_week"],
    "journal_counts": {k: view[k] for k in fields},
    "current_candidates": {p["pair"]: {
        "status": p["candidate"]["status"], "probability": p["candidate"].get("probability")}
        for p in report["pair_reports"]},
    "qualification": "UNQUALIFIED", "model_calls": 0, "execution": "NOT_RECORDED"
}
(ROOT / "reports/private-fomc-final-audit.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
print("PRIVATE_FOMC_ACTUAL_PRESERVATION_OK")
