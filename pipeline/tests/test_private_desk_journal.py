"""Prospective clocks and both-sided counterfactuals must survive immutable storage."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from src.private_desk import journal
from src.private_desk.report import atomic_json
from src.private_desk.universe import PAIRS, UNIVERSE_VERSION

NOW = datetime(2026, 10, 1, 18, tzinfo=UTC)
LATER = datetime(2026, 10, 8, 18, tzinfo=UTC)


def make_report(directory: Path, *, source_clock: datetime = NOW) -> Path:
    days = []
    day = date(2026, 9, 1)
    while day <= date(2026, 10, 20):
        if day.weekday() < 5:
            days.append(day.isoformat())
        day += timedelta(days=1)
    rows = []
    for pair in PAIRS:
        price = 150.0 if pair.endswith("JPY") else 1.2
        radius = price * 0.01
        bars = [
            {
                "time": day,
                "open": price,
                "close": price,
                "high": price + radius,
                "low": price - radius,
            }
            for day in days
        ]
        capture = directory / "sources" / (pair + ".json")
        atomic_json(
            capture,
            {
                "pair": pair,
                "interval": "1d",
                "bars": bars,
                "metadata": {"received_at": source_clock.isoformat()},
            },
        )
        rows.append(
            {
                "pair": pair,
                "candidate": {
                    "status": "ABSTAIN",
                    "direction": "BUY" if pair == "EURUSD" else None,
                    "holding_days": 3,
                    "as_of": "2026-09-30",
                    "policy": "fixture",
                    "probability": None,
                    "reasons": ["NOT_VALIDATED", "=unsafe reason"],
                },
                "source_metadata": {
                    "pair": pair,
                    "interval": "1d",
                    "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
                    "capture_path": str(capture),
                    "received_at": source_clock.isoformat(),
                },
                "backtest": {"method_version": "fixture-method"},
            }
        )
    path = directory / "report.json"
    atomic_json(
        path,
        {
            "universe": list(PAIRS),
            "universe_version": UNIVERSE_VERSION,
            "generated_at": NOW.isoformat(),
            "pair_reports": rows,
        },
    )
    return path


def later_sources(path: Path) -> None:
    report = json.loads(path.read_bytes())
    for row in report["pair_reports"]:
        prior = Path(row["source_metadata"]["capture_path"])
        body = json.loads(prior.read_bytes())
        body["metadata"]["received_at"] = LATER.isoformat()
        target = prior.with_name(row["pair"] + "-later.json")
        atomic_json(target, body)
        row["source_metadata"]["capture_path"] = str(target)
        row["source_metadata"]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        row["source_metadata"]["received_at"] = LATER.isoformat()
    atomic_json(path, report)


def test_every_abstention_frozen_and_identical_report_idempotent(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    before = path.read_bytes()
    result = journal.sync_journal(tmp_path, path, now=NOW)
    assert result["decision_count"] == 8
    assert result["outcome_status_counts"] == {"PENDING": 8}
    assert result["decision_status_counts"] == {"ABSTAIN": 8}
    assert result["execution_state"] == "NOT_RECORDED"
    original = {p: p.read_bytes() for p in (tmp_path / "journal").rglob("*.json")}
    journal.sync_journal(tmp_path, path, now=NOW + timedelta(hours=1))
    assert all(p.read_bytes() == raw for p, raw in original.items())
    assert path.read_bytes() == before
    assert all(row["earliest_entry_date"] == "2026-10-02" for row in result["rows"])


@pytest.mark.parametrize(
    "offset, expected", [(1, "2026-10-05"), (2, "2026-10-05"), (3, "2026-10-05"), (4, "2026-10-06")]
)
def test_real_recording_date_defines_earliest_entry(
    tmp_path: Path, offset: int, expected: str
) -> None:
    path = make_report(tmp_path)
    result = journal.record_report(tmp_path, path, now=NOW + timedelta(days=offset))
    assert {d["earliest_entry_date"] for d in result["decisions"]} == {expected}


@pytest.mark.parametrize("bad", ["missing", "duplicate", "extra", "universe", "version"])
def test_incomplete_identity_writes_no_decision(tmp_path: Path, bad: str) -> None:
    path = make_report(tmp_path)
    value = json.loads(path.read_bytes())
    if bad == "missing":
        value["pair_reports"].pop()
    elif bad == "duplicate":
        value["pair_reports"][-1] = value["pair_reports"][0]
    elif bad == "extra":
        value["pair_reports"].append({"pair": "USDINR"})
    elif bad == "universe":
        value["universe"] = list(reversed(PAIRS))
    else:
        value["universe_version"] = "unknown"
    atomic_json(path, value)
    with pytest.raises(ValueError):
        journal.record_report(tmp_path, path, now=NOW)
    assert not list((tmp_path / "journal").rglob("*.json"))


def test_later_results_keep_both_directions_and_frozen_candidate(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    frozen = {p: p.read_bytes() for p in (tmp_path / "journal" / "decisions").glob("*.json")}
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    value = journal.journal_view(tmp_path)
    assert value["outcome_status_counts"] == {"EVALUATED": 8}
    assert value["evaluation_event_count"] == 16
    assert all(p.read_bytes() == raw for p, raw in frozen.items())
    for row in value["rows"]:
        result = row["evaluation"]["result"]
        assert [r["benchmark_direction"] for r in result["outcomes"]] == ["BUY", "SELL"]
        assert all(r["entry_time"] == "2026-10-02" for r in result["outcomes"])
        assert all(r["kind"] == "COUNTERFACTUAL_RESEARCH" for r in result["outcomes"])
        if row["pair"] != "EURUSD":
            assert row["frozen_direction_benchmark"] is None
        else:
            assert row["frozen_direction_benchmark"]["direction"] == "BUY"
    assert journal.evaluate_pending(tmp_path, path, now=LATER + timedelta(hours=1)) == 0


@pytest.mark.parametrize("fault", ["missing", "gap", "price", "hash"])
def test_evaluation_bad_source_does_not_become_a_win(tmp_path: Path, fault: str) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    report = json.loads(path.read_bytes())
    row = report["pair_reports"][0]
    old = Path(row["source_metadata"]["capture_path"])
    body = json.loads(old.read_bytes())
    revised = tmp_path / "sources" / "revised.json"
    if fault == "missing":
        body["bars"] = [b for b in body["bars"] if b["time"] != "2026-10-02"]
    elif fault == "gap":
        next(b for b in body["bars"] if b["time"] == "2026-10-05")["gap_before"] = True
    elif fault == "price":
        body["bars"][0]["close"] = float("inf")
    revised.write_text(json.dumps(body), encoding="utf-8")
    row["source_metadata"]["capture_path"] = str(revised)
    if fault != "hash":
        row["source_metadata"]["sha256"] = hashlib.sha256(revised.read_bytes()).hexdigest()
    atomic_json(path, report)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    result = next(r for r in journal.journal_view(tmp_path)["rows"] if r["pair"] == "EURUSD")[
        "evaluation"
    ]["result"]
    assert result["status"] == "UNAVAILABLE"
    assert result["outcomes"] == []


@pytest.mark.parametrize("target", ["decision", "evaluation", "report", "source"])
def test_journal_tampering_fails_closed(tmp_path: Path, target: str) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    choices = {
        "decision": list((tmp_path / "journal" / "decisions").glob("*.json")),
        "evaluation": list((tmp_path / "journal" / "evaluations").glob("*.json")),
        "report": list((tmp_path / "journal" / "reports").glob("*.json")),
        "source": list((tmp_path / "journal" / "sources").glob("*.json")),
    }
    selected = choices[target][0]
    selected.write_bytes(selected.read_bytes() + b"changed")
    with pytest.raises((ValueError, KeyError)):
        journal.journal_view(tmp_path)


def test_future_or_naive_recording_is_rejected(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    with pytest.raises(ValueError):
        journal.record_report(tmp_path, path, now=NOW - timedelta(days=1))
    with pytest.raises(ValueError):
        journal.record_report(tmp_path, path, now=NOW.replace(tzinfo=None))


def test_invalid_atr_stays_unavailable_even_after_future_prices(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    report = json.loads(path.read_bytes())
    report["pair_reports"][0]["candidate"]["as_of"] = "2020-01-01"
    atomic_json(path, report)
    journal.sync_journal(tmp_path, path, now=NOW)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    row = next(r for r in journal.journal_view(tmp_path)["rows"] if r["pair"] == "EURUSD")
    assert row["evaluation"]["result"]["reason"] == "FROZEN_BENCHMARK_UNAVAILABLE"
    assert row["evaluation"]["result"]["outcomes"] == []


def test_revisions_keep_original_decision_and_count_same_observation(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    report = json.loads(path.read_bytes())
    changed = deepcopy(report)
    changed["pair_reports"][0]["candidate"]["reasons"].append("NEW_REVIEW")
    atomic_json(path, changed)
    view = journal.sync_journal(tmp_path, path, now=NOW + timedelta(hours=1))
    assert view["report_count"] == 2 and view["decision_count"] == 16
    assert view["unique_pair_observation_dates"] == 8


def test_out_of_order_evaluation_cannot_append(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.record_report(tmp_path, path, now=NOW)
    with pytest.raises(ValueError):
        journal.evaluate_pending(tmp_path, path, now=NOW - timedelta(seconds=1))
    assert not list((tmp_path / "journal" / "evaluations").glob("*.json"))


def test_context_revision_does_not_inflate_reason_groups_or_evaluations(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    value = json.loads(path.read_bytes())
    value["news"] = [{"title": "Changed context only"}]
    atomic_json(path, value)
    assert journal.evaluate_pending(tmp_path, path, now=NOW + timedelta(hours=1)) == 0
    view = journal.sync_journal(tmp_path, path, now=NOW + timedelta(hours=1))
    assert view["decision_count"] == 16
    assert view["unique_observation_count"] == 8
    assert view["repeated_publication_count"] == 8
    assert {g["observations"] for g in view["reason_groups"]} == {8}


def test_source_copy_survives_original_capture_deletion(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    for source in (tmp_path / "sources").glob("*.json"):
        source.unlink()
    assert journal.journal_view(tmp_path)["outcome_status_counts"] == {"EVALUATED": 8}


def test_old_source_or_failed_attempt_does_not_erase_completed_outcomes(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    original = path.read_bytes()
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    path.write_bytes(original)
    journal.evaluate_pending(tmp_path, path, now=LATER + timedelta(days=1))
    assert journal.journal_view(tmp_path)["outcome_status_counts"] == {"EVALUATED": 8}


def test_unpublished_artifact_never_counts_as_displayed_decision(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    artifact = tmp_path / "unpublished.json"
    artifact.write_bytes(path.read_bytes())
    original = json.loads(path.read_bytes())
    original["news"] = ["Other current report"]
    atomic_json(path, original)
    journal.record_report(tmp_path, artifact, now=NOW)
    with pytest.raises(ValueError):
        journal.commit_publication(tmp_path, artifact, now=NOW)
    value = journal.journal_view(tmp_path)
    assert value["decision_count"] == 0 and value["unpublished_report_count"] == 1


@pytest.mark.parametrize("change", ["result", "source"])
def test_rehashed_forged_outcome_still_fails_source_replay(tmp_path: Path, change: str) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    for event_path in (tmp_path / "journal" / "evaluations").glob("*.json"):
        event = journal._read(event_path)
        if event["result"]["status"] == "EVALUATED":
            if change == "result":
                event["result"]["outcomes"][0]["net_r"] = 999.0
            else:
                event["source_sha256"] = "0" * 64
            identity = {key: event[key] for key in ("decision_id", "source_sha256", "result")}
            revised = event_path.with_name(journal._hash(journal._json(identity)) + ".json")
            event_path.unlink()
            revised.write_bytes(journal._envelope(event))
            break
    with pytest.raises(ValueError):
        journal.journal_view(tmp_path)


def test_future_bars_in_an_old_capture_cannot_supply_later_outcomes(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    assert journal.journal_view(tmp_path)["outcome_status_counts"] == {"PENDING": 8}
    assert {
        r["evaluation"]["result"]["reason"] for r in journal.journal_view(tmp_path)["rows"]
    } == {"SOURCE_NOT_YET_READY"}


def test_source_receipt_cannot_be_advanced_without_a_new_capture(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    value = json.loads(path.read_bytes())
    for row in value["pair_reports"]:
        row["source_metadata"]["received_at"] = LATER.isoformat()
    atomic_json(path, value)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    assert journal.journal_view(tmp_path)["outcome_status_counts"] == {"UNAVAILABLE": 8}


def test_own_candidate_plan_is_distinct_from_uniform_benchmarks(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    value = json.loads(path.read_bytes())
    value["pair_reports"][0]["candidate"].update(entry=1.2, stop=1.185, tp1=1.215, tp2=1.245)
    atomic_json(path, value)
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    row = next(r for r in journal.journal_view(tmp_path)["rows"] if r["pair"] == "EURUSD")
    result = row["evaluation"]["result"]
    plan = result["candidate_plan_outcome"]
    assert plan["kind"] == "FROZEN_CANDIDATE_COUNTERFACTUAL"
    assert plan["qualification"] == "UNQUALIFIED"
    assert plan["stop"] == pytest.approx(1.185)
    assert result["outcomes"][0]["stop"] != plan["stop"]
    assert row["candidate"]["status"] == "ABSTAIN"
    assert plan["entry_time"] == "2026-10-02"


@pytest.mark.parametrize(
    "field,value", [("tp1", 1.22), ("tp2", 1.3), ("stop", 1.3), ("entry", True)]
)
def test_inconsistent_candidate_plan_remains_unavailable(
    tmp_path: Path, field: str, value: object
) -> None:
    path = make_report(tmp_path)
    report = json.loads(path.read_bytes())
    candidate = report["pair_reports"][0]["candidate"]
    candidate.update(entry=1.2, stop=1.185, tp1=1.215, tp2=1.245)
    candidate[field] = value
    atomic_json(path, report)
    journal.sync_journal(tmp_path, path, now=NOW)
    later_sources(path)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    row = next(r for r in journal.journal_view(tmp_path)["rows"] if r["pair"] == "EURUSD")
    assert row["evaluation"]["result"]["candidate_plan_outcome"] is None


def test_unique_status_counts_exclude_repeated_publications(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    value = json.loads(path.read_bytes())
    value["other_context"] = "Changed"
    atomic_json(path, value)
    view = journal.sync_journal(tmp_path, path, now=NOW + timedelta(hours=1))
    assert view["decision_status_counts"] == {"ABSTAIN": 8}
    assert view["publication_row_status_counts"] == {"ABSTAIN": 16}
    assert view["outcome_status_counts"] == {"PENDING": 8}


def test_failure_reasons_distinguish_missing_file_and_bad_hash(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    report = json.loads(path.read_bytes())
    report["pair_reports"][0]["source_metadata"]["capture_path"] = str(tmp_path / "missing.json")
    report["pair_reports"][1]["source_metadata"]["sha256"] = "0" * 64
    atomic_json(path, report)
    journal.evaluate_pending(tmp_path, path, now=LATER)
    rows = {r["pair"]: r for r in journal.journal_view(tmp_path)["rows"]}
    assert rows["EURUSD"]["evaluation"]["result"]["reason"] == "SOURCE_FILE_MISSING"
    assert rows["GBPUSD"]["evaluation"]["result"]["reason"] == "SOURCE_HASH_MISMATCH"
