"""Report integrity controls and independent-cohort failure isolation."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from src.private_desk.cli import verify_report
from src.private_desk.report import (
    PAIRS,
    atomic_json,
    attach_bidask_evidence,
    attach_historical_evidence,
    attach_policy_history,
    attach_release_evidence,
    build_report,
    recalculate_report,
)
from src.private_desk.universe import UNIVERSE_VERSION


def minimal_report() -> dict[str, Any]:
    return {
        "schema_version": "private-fx-v1",
        "universe_version": UNIVERSE_VERSION,
        "universe": list(PAIRS),
        "policy": {"full_target_gross_r": 2.0},
        "pair_reports": [
            {"pair": pair, "candidate": {"probability": None}, "backtest": {"trades": []}}
            for pair in PAIRS
        ],
    }


def test_capture_tampering_is_rejected(tmp_path: Path) -> None:
    capture = tmp_path / "capture.json"
    capture.write_bytes(b'{"source":"fixture"}')
    report = minimal_report()
    report["pair_reports"][0]["source_metadata"] = {
        "capture_path": str(capture),
        "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
    }
    path = tmp_path / "report.json"
    atomic_json(path, report)
    verify_report(path)
    capture.write_bytes(b'{"source":"changed"}')
    with pytest.raises(AssertionError):
        verify_report(path)


def test_risk_off_text_is_not_mistaken_for_an_api_key(tmp_path: Path) -> None:
    report = minimal_report()
    report["summary"] = "A conditional risk-off thesis, no numeric probability."
    path = tmp_path / "report.json"
    atomic_json(path, report)
    verify_report(path)
    report["summary"] = "sk-" + "a" * 32
    atomic_json(path, report)
    with pytest.raises(AssertionError):
        verify_report(path)


def test_hourly_failure_preserves_daily_and_reference_research(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.private_desk import data, engine

    monkeypatch.setattr(data, "fetch_fundamentals", lambda _path: {})
    monkeypatch.setattr(data, "fetch_news", lambda: [])
    monkeypatch.setattr(data, "load_reference_history", lambda *_args, **_kwargs: ([], {}))
    monkeypatch.setattr(
        engine, "analyze_reference_pair", lambda _pair, _bars: {"status": "REFERENCE_RECEIPT"}
    )

    def load(
        _pair: str, *, interval: str = "1d", **_kwargs: Any
    ) -> tuple[list[Any], dict[str, Any]]:
        if interval == "1h":
            raise ValueError("Unavailable hourly source")
        return [], {"status": "DAILY_RECEIPT"}

    monkeypatch.setattr(data, "load_history", load)
    monkeypatch.setattr(
        engine,
        "analyze_pair",
        lambda pair, _bars: {"pair": pair, "candidate": {}, "backtest": {"status": "DAILY_RESULT"}},
    )
    result = build_report(tmp_path, use_ai=False)
    for pair in result["pair_reports"]:
        assert pair["backtest"]["status"] == "DAILY_RESULT"
        assert pair["long_history"]["status"] == "REFERENCE_RECEIPT"
        assert pair["session"]["status"] == "UNAVAILABLE"
    assert (tmp_path / "report.json").exists()


def test_offline_recalculation_preserves_sources_and_detaches_old_ai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.private_desk import engine

    report = minimal_report()
    report["generated_at"] = "2026-09-30T00:00:00Z"
    report["news"] = [{"title": "Original dated source"}]
    report["historical_releases"] = {"status": "ORIGINAL_RELEASE_AUDIT"}
    report["historical_fundamentals"] = {"status": "ORIGINAL_VINTAGE_AUDIT"}
    report["ai_summary"] = {"status": "CAPTURED_REVIEW", "text": "Previous conditional thesis"}
    capture = tmp_path / "capture.json"
    capture.write_text('{"bars":[]}', encoding="utf-8")
    for item in report["pair_reports"]:
        item["source_metadata"] = {
            "capture_path": str(capture),
            "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
        }
        item["long_history"] = {"status": "ORIGINAL_REFERENCE"}
        item["session"] = {"status": "ORIGINAL_SESSION"}
        item["bidask_evidence"] = {"status": "ORIGINAL_BIDASK"}
        item["ai_analysis"] = {"status": "OLD_PAIR_REVIEW"}
    path = tmp_path / "report.json"
    atomic_json(path, report)
    before_bytes = path.read_bytes()

    def analyze(pair: str, _bars: list[Any]) -> dict[str, Any]:
        return {
            "data_coverage": {"status": "VALID"},
            "backtest": {"method_version": engine.METHOD_VERSION, "trades": []},
            "candidate": {"probability": None, "status": "ABSTAIN"},
            "chart": {"equity": []},
        }

    monkeypatch.setattr(engine, "analyze_pair", analyze)
    result = recalculate_report(tmp_path)
    assert result["news"] == report["news"]
    assert result["historical_releases"] == report["historical_releases"]
    assert result["historical_fundamentals"] == report["historical_fundamentals"]
    assert result["prior_ai_summary"] == report["ai_summary"]
    assert result["ai_summary"]["status"] == "UNAVAILABLE"
    assert (
        result["quantitative_recalculation"]["previous_report_sha256"]
        == hashlib.sha256(before_bytes).hexdigest()
    )
    for old, new in zip(report["pair_reports"], result["pair_reports"], strict=True):
        for key in ("source_metadata", "long_history", "session", "bidask_evidence"):
            assert old[key] == new[key]
        assert new["prior_ai_analysis"] == old["ai_analysis"]
        assert new["ai_analysis"]["status"] == "UNAVAILABLE"
    assert json.loads(path.read_bytes()) == result
    assert len(list((tmp_path / "reports").glob("*-recalculate-*.json"))) == 1
    # A repeated offline run retains the original archived review, without pretending it is fresh.
    repeated = recalculate_report(tmp_path)
    assert repeated["prior_ai_summary"] == report["ai_summary"]


def test_recalculation_rejects_changed_capture_without_replacing_report(tmp_path: Path) -> None:
    report = minimal_report()
    report["generated_at"] = "2026-09-30T00:00:00Z"
    capture = tmp_path / "capture.json"
    capture.write_bytes(b'{"bars":[]}')
    report["pair_reports"][0]["source_metadata"] = {
        "capture_path": str(capture),
        "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
    }
    path = tmp_path / "report.json"
    atomic_json(path, report)
    original = path.read_bytes()
    capture.write_bytes(b'{"bars":["changed"]}')
    with pytest.raises(ValueError, match="hash changed"):
        recalculate_report(tmp_path)
    assert path.read_bytes() == original
    assert not (tmp_path / "reports").exists()


@pytest.mark.parametrize("corrupt", [False, True])
def test_bidask_attachment_preserves_existing_research_and_failures_are_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt: bool
) -> None:
    from src.private_desk import bidask

    report = minimal_report()
    before = deepcopy(report)

    def load(_root: Path) -> dict[str, Any]:
        if corrupt:
            raise ValueError("Test-only sensitive provider message")
        return {"EURUSD": {"pair": "EURUSD", "status": "INDICATIVE_SOURCE_AUDIT"}}

    monkeypatch.setattr(bidask, "load_evidence", load)
    attach_bidask_evidence(report, tmp_path)
    for item in report["pair_reports"]:
        evidence = item.pop("bidask_evidence")
        if corrupt or item["pair"] != "EURUSD":
            assert evidence["status"] == "UNAVAILABLE"
            assert "sensitive" not in evidence.get("reason", "")
        else:
            assert evidence["status"] == "INDICATIVE_SOURCE_AUDIT"
    assert report == before


@pytest.mark.parametrize("failure", ["none", "load", "features"])
def test_policy_history_is_separate_and_failed_features_cannot_break_price_research(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from src.private_desk import policy_history

    report = minimal_report()
    report["ai_summary"] = {"status": "PRESERVED_REVIEW"}
    report["historical_releases"] = {"status": "PRESERVED_RELEASE"}
    before = deepcopy(report)

    def load(_root: Path) -> dict[str, Any]:
        if failure == "load":
            raise ValueError("Test-only sensitive source detail")
        return {"status": "RETROSPECTIVE_POLICY_HISTORY"}

    def features(_evidence: dict[str, Any], pair: str) -> dict[str, Any]:
        if failure == "features":
            raise ValueError("Test-only sensitive feature detail")
        return {"pair": pair, "status": "RETROSPECTIVE_ONLY", "rows": []}

    monkeypatch.setattr(policy_history, "load_evidence", load)
    monkeypatch.setattr(policy_history, "pair_policy_features", features)
    attach_policy_history(report, tmp_path)
    evidence = report.pop("historical_policy")
    assert evidence["status"] == (
        "RETROSPECTIVE_POLICY_HISTORY" if failure == "none" else "UNAVAILABLE"
    )
    assert "sensitive" not in evidence.get("reason", "")
    for item in report["pair_reports"]:
        feature = item.pop("historical_policy_features")
        assert feature["status"] == ("RETROSPECTIVE_ONLY" if failure == "none" else "UNAVAILABLE")
    assert report == before


@pytest.mark.parametrize("corrupt", [False, True])
def test_release_attachment_preserves_all_research_and_sanitizes_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt: bool
) -> None:
    from src.private_desk import releases

    report = minimal_report()
    report["historical_fundamentals"] = {"status": "CALENDAR_ONLY"}
    report["ai_summary"] = {"status": "CONDITIONAL_SCENARIO"}
    before = deepcopy(report)

    def load(_root: Path) -> dict[str, Any]:
        if corrupt:
            raise ValueError("Test-only sensitive source details")
        return {"status": "SOURCE_CLOCK_AUDIT", "covered_currencies": ["USD"]}

    monkeypatch.setattr(releases, "load_evidence", load)
    attach_release_evidence(report, tmp_path)
    evidence = report.pop("historical_releases")
    assert evidence["status"] == ("UNAVAILABLE" if corrupt else "SOURCE_CLOCK_AUDIT")
    assert "sensitive" not in evidence.get("reason", "")
    assert report == before


@pytest.mark.parametrize("corrupt", [False, True])
def test_historical_attachment_preserves_all_pair_research_and_source_failure_is_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt: bool
) -> None:
    from src.private_desk import vintage

    report = minimal_report()
    report["historical_ai_review"] = "Test-only preserved scenario"
    before = deepcopy(report)

    def load(_root: Path) -> dict[str, Any]:
        if corrupt:
            raise ValueError("Test-only sensitive source details")
        return {"status": "CALENDAR_DATE_SOURCE_AUDIT", "covered_currencies": ["USD"]}

    monkeypatch.setattr(vintage, "load_evidence", load)
    attach_historical_evidence(report, tmp_path)
    evidence = report.pop("historical_fundamentals")
    assert evidence["status"] == ("UNAVAILABLE" if corrupt else "CALENDAR_DATE_SOURCE_AUDIT")
    assert "sensitive" not in evidence.get("reason", "")
    assert report == before
