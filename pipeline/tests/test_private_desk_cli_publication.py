"""Every evidence CLI publication must record decisions and archive its old AI binding."""

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from src.private_desk import bidask, cli, journal, policy_history, releases, vintage
from src.private_desk.report import atomic_json, detach_current_review
from tests.test_private_desk_journal import NOW, make_report


@pytest.mark.parametrize(
    "command, args, module, attach",
    [
        ("bidask", ["--week", "2024-01-01", "--pair", "USDJPY"], bidask, "attach_bidask_evidence"),
        ("vintage", ["--series", "DGS2", "--vintage", "2023-02-14",
                     "--observation-start", "2023-02-01", "--observation-end", "2023-02-14"],
         vintage, "attach_historical_evidence"),
        ("release", ["--release-source", "FOMC", "--release-date", "2023-02-01"],
         releases, "attach_release_evidence"),
        ("policy-history", ["--currency", "JPY", "--policy-start", "1999-01-05",
                            "--policy-end", "2026-09-30"], policy_history, "attach_policy_history"),
    ],
)
def test_evidence_cli_uses_real_shared_journal_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str,
    args: list[str], module: Any, attach: str,
) -> None:
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> "FixedClock":
            return cls.fromtimestamp(NOW.timestamp(), tz)

    monkeypatch.setattr(journal, "datetime", FixedClock)
    path = make_report(tmp_path)
    report = json.loads(path.read_bytes())
    report.update(
        schema_version="private-fx-v1", policy={"full_target_gross_r": 2.0},
        ai_summary={"status": "GENERATED_UNVALIDATED", "summary": "Fixture old AI"},
        current_review={"status": "GENERATED_UNVALIDATED", "input_id": "old-fixture"},
    )
    for row in report["pair_reports"]:
        row["ai_analysis"] = {"status": "GENERATED_UNVALIDATED", "thesis": "Old fixture"}
    atomic_json(path, report)
    original = path.read_bytes()
    monkeypatch.setattr(cli, "STATE_DIR", tmp_path)
    calls = []

    def capture(*positional: Any, **keywords: Any) -> dict[str, Any]:
        calls.append((positional, keywords))
        return {
            "status": "TEST_ONLY", "pair_audits": [], "series_audits": [],
            "events": [], "failures": [],
        }

    def attach_evidence(value: dict[str, Any], _directory: Path) -> None:
        value["new_evidence"] = {"status": "TEST_ONLY", "command": command}

    monkeypatch.setattr(module, "capture_cohort", capture)
    monkeypatch.setattr(cli, attach, attach_evidence)
    monkeypatch.setattr(sys, "argv", ["private-desk", command, *args])
    cli.main()
    assert len(calls) == 1
    if command == "policy-history":
        assert calls[0][0][1][0]["currency"] == "JPY"
    updated = json.loads(path.read_bytes())
    assert path.read_bytes() != original
    assert updated["current_review"]["status"] == "DETACHED"
    assert updated["prior_current_review"] == report["current_review"]
    assert updated["ai_summary"]["status"] == "UNAVAILABLE"
    assert updated["prior_ai_summary"] == report["ai_summary"]
    for before, after in zip(report["pair_reports"], updated["pair_reports"], strict=True):
        assert after["candidate"] == before["candidate"]
        assert after["backtest"] == before["backtest"]
        assert after["source_metadata"] == before["source_metadata"]
        assert after["prior_ai_analysis"] == before["ai_analysis"]
        assert after["ai_analysis"]["status"] == "UNAVAILABLE"
    history = journal.journal_view(tmp_path)
    assert history["decision_count"] == 8
    assert history["decision_status_counts"] == {"ABSTAIN": 8}
    assert history["unique_observation_count"] == 8
    assert history["unpublished_report_count"] == 0
    assert {row["earliest_entry_date"] for row in history["rows"]} == {"2026-10-02"}


def test_repeated_detachment_never_overwrites_archived_review() -> None:
    original: dict[str, Any] = {
        "current_review": {"status": "GENERATED_UNVALIDATED", "reference": "exact-old"},
        "ai_summary": {"status": "GENERATED_UNVALIDATED", "summary": "old"},
        "pair_reports": [{"pair": "USDJPY", "ai_analysis": {"status": "GENERATED_UNVALIDATED"}}],
    }
    report = deepcopy(original)
    detach_current_review(report, reason="First evidence change")
    detach_current_review(report, reason="Second evidence change")
    assert report["prior_current_review"] == original["current_review"]
    assert report["prior_ai_summary"] == original["ai_summary"]
    assert (
        report["pair_reports"][0]["prior_ai_analysis"]
        == original["pair_reports"][0]["ai_analysis"]
    )
    assert report["ai_summary"]["reason"] == "Second evidence change"
