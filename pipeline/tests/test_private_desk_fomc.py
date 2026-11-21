"""Official passage, chronology and matched event-study controls."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.private_desk import fomc_history as history
from src.private_desk import fomc_study as study

FRAGMENTS = json.loads(
    (Path(__file__).parent / "fixtures/private_fomc_fragments.json").read_bytes()
)
EXPECTED_BOUNDS = {
    "2015-01-28": (0, 0.25),
    "2016-03-16": (0.25, 0.5),
    "2019-12-11": (1.5, 1.75),
    "2020-03-03": (1, 1.25),
    "2020-03-15": (0, 0.25),
    "2024-09-18": (4.75, 5),
    "2019-10-11": (None, None),
    "2020-03-23": (None, None),
}


@pytest.mark.parametrize("fragment", FRAGMENTS, ids=lambda f: f["release_date"])
def test_original_official_wording(fragment: dict[str, Any]) -> None:
    result = history.parse_statement(
        fragment["article_fragment"].encode(), fragment["release_date"], fragment["received_at"]
    )
    assert (result["target_lower_percent"], result["target_upper_percent"]) == EXPECTED_BOUNDS[
        fragment["release_date"]
    ]
    assert result["surprise"] is None and result["historical_receipt_at"] is None
    if fragment["release_date"].startswith("2015"):
        assert result["source_stated_release_at"] is None
    if fragment["release_date"] == "2020-03-15":
        assert result["source_stated_release_at"] == "2020-03-15T21:00:00+00:00"
    if fragment["release_date"] == "2020-03-03":
        assert result["source_stated_release_at"] == "2020-03-03T15:00:00+00:00"


def _fragment(day: str = "2020-03-15") -> dict[str, Any]:
    return copy.deepcopy(next(f for f in FRAGMENTS if f["release_date"] == day))


@pytest.mark.parametrize("delta", ["date", "title", "duplicate", "zone", "fraction"])
def test_statement_identity_and_ambiguity_fail_closed(delta: str) -> None:
    item = _fragment()
    text = item["article_fragment"]
    if delta == "date":
        text = text.replace("March 15, 2020", "March 14, 2020")
    elif delta == "title":
        text = text.replace("Federal Reserve issues FOMC statement", "Unofficial commentary")
    elif delta == "duplicate":
        text += text
    elif delta == "zone":
        text = text.replace("EDT", "EST")
    else:
        text = text.replace("0 to 1/4 percent", "0 to 4/4 percent")
    with pytest.raises(ValueError):
        history.parse_statement(text.encode(), item["release_date"], item["received_at"])


def test_committee_conflict_cannot_select_first_range() -> None:
    item = _fragment()
    text = item["article_fragment"].replace(
        "</div>",
        "<p>The Committee decided to maintain the target range for the federal funds rate "
        "at 1 to 2 percent.</p></div>",
    )
    with pytest.raises(ValueError, match="ambiguous Committee"):
        history.parse_statement(text.encode(), item["release_date"], item["received_at"])


def test_index_preserves_meeting_vs_publication_and_cancellation() -> None:
    html = (
        b'<h5>March 2 (unscheduled) - 2020</h5><p><a href="/newsevents/pressreleases/'
        b'monetary20200303a.htm">Statement</a></p><h5>March 17-18 cancelled - 2020</h5>'
    )
    result = history.discover_index(html, history.INDEX_URLS[6])
    assert result["links"][0]["release_date"] == "2020-03-03"
    assert "March 2" in result["links"][0]["meeting_heading"]
    assert result["headings_without_statement"] == ["March 17-18 cancelled - 2020"]
    with pytest.raises(ValueError):
        history.discover_index(
            html.replace(b"/newsevents/", b"https://evil.example/newsevents/"),
            history.INDEX_URLS[6],
        )


def _sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str | None = None
) -> dict[str, Any]:
    indexes: list[dict[str, Any]] = []
    captures: list[dict[str, Any]] = []
    for url in history.INDEX_URLS:
        if "historical" in url:
            year = int(url[-8:-4])
            days = (
                [history.SEED]
                if year == 2014
                else sorted(d for d in history.EXPECTED_DATES if d.startswith(str(year)))
            )
            html = "".join(
                f'<h5>Meeting - {year}</h5><a href="/newsevents/pressreleases/'
                f'monetary{d.replace("-", "")}a.htm">Statement</a>'
                for d in days
            )
        else:
            html = ""
            for year in range(2021, 2025):
                html += (
                    f'<div class="panel"><div class="panel-heading"><h4>{year} '
                    "FOMC Meetings</h4></div>"
                )
                for day in sorted(d for d in history.EXPECTED_DATES if d.startswith(str(year))):
                    html += (
                        '<div class="fomc-meeting"><div class="fomc-meeting__month">Month</div>'
                        '<div class="fomc-meeting__date">1</div><p>Statement: '
                        '<a href="/newsevents/pressreleases/'
                        f'monetary{day.replace("-", "")}a.htm">HTML</a></p></div>'
                    )
                html += "</div>"
        path = tmp_path / (str(len(indexes)) + ".html")
        path.write_text(html)
        record = {
            "url": url,
            "capture_path": str(path),
            "http_status": 200,
            "body_complete": True,
            "content_type": "text/html",
            "receipt_file": {"id": len(indexes)},
        }
        indexes.append(record)
    monkeypatch.setattr(history, "_read_index", lambda root, ref: indexes[ref["id"]])
    for day in sorted(history.EXPECTED_DATES | {history.SEED}):
        if day == missing:
            continue
        path = tmp_path / (day + ".html")
        path.write_text(day)
        record = {
            "request": {"source": "FOMC", "date": day},
            "url": f"{history.HOST}/newsevents/pressreleases/monetary{day.replace('-', '')}a.htm",
            "receipt_file": {"id": len(captures)},
            "capture_path": str(path),
            "http_status": 200,
            "body_complete": True,
            "content_type": "text/html",
            "sha256": day,
            "received_at": "2026-10-01T00:00:00+00:00",
        }
        captures.append(record)
    monkeypatch.setattr(history, "read_receipt", lambda root, ref: captures[ref["id"]])

    def parse(body: bytes, day: str, received: str) -> dict[str, Any]:
        midpoint = 0.125 if day < "2015-12-16" else 0.375
        return {
            "release_date": day,
            "target_midpoint_percent": midpoint,
            "document_class": "OTHER_POLICY_STATEMENT"
            if day in ("2019-10-11", "2020-03-23")
            else "TARGET_DECISION",
            "source_stated_release_at": None,
        }

    monkeypatch.setattr(history, "parse_statement", parse)
    return history.audit_history(tmp_path, indexes, captures)


def test_missing_target_breaks_chain_and_non_target_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = _sequence(tmp_path, monkeypatch, "2015-10-28")
    rows = {e["release_date"]: e for e in evidence["events"]}
    assert evidence["status"] == "PARTIAL"
    assert rows["2015-12-16"]["change_from_prior_statement_pp"] is None
    assert rows["2016-01-27"]["change_from_prior_statement_pp"] == 0
    assert rows["2019-10-30"]["predecessor_release_date"] == "2019-09-18"
    assert rows["2020-04-29"]["predecessor_release_date"] == "2020-03-15"


def _evidence() -> dict[str, Any]:
    events: list[dict[str, Any]] = [
        {"release_date": day, "change_from_prior_statement_pp": 0, "source_stated_release_at": None}
        for day in sorted(history.EXPECTED_DATES)
    ]
    event = next(e for e in events if e["release_date"] == "2024-09-18")
    event.update(
        change_from_prior_statement_pp=-0.5, source_stated_release_at="2024-09-18T18:00:00+00:00"
    )
    return {"status": "SOURCE_RECONSTRUCTION", "failures": [], "events": events}


def _bars() -> dict[str, list[dict[str, Any]]]:
    bars = []
    day = date(2024, 8, 1)
    while day <= date(2024, 10, 1):
        if day.weekday() < 5:
            bars.append(
                {"time": day.isoformat(), "open": 1.2, "high": 1.21, "low": 1.19, "close": 1.2}
            )
        day += timedelta(days=1)
    return {pair: copy.deepcopy(bars) for pair in study.USD_SIGNS}


def test_fixed_orientation_entry_and_matched_horizons() -> None:
    result = study.event_study(_evidence(), _bars())
    assert result["selected_event_count"] == 1
    assert len(result["paths"]) == 14
    assert result["selected_events"][0]["entry_date"] == "2024-09-20"
    assert result["selected_events"][0]["signal_date"] == "2024-09-19"
    for row in result["paths"]:
        assert row["hypothesis"]["direction"] == (
            "SELL" if study.USD_SIGNS[row["pair"]] > 0 else "BUY"
        )
        assert row["hypothesis"]["entry_time"] == row["opposite"]["entry_time"] == "2024-09-20"
        assert row["hypothesis"]["cost_r"] > 0
        assert row["risk_distance"] == pytest.approx(0.03)
    assert result["probability"] is None and result["surprise"] is None
    assert result["zero_event_weeks"] == result["complete_calendar_weeks"] - 1
    assert all(r["event_block_interval95_descriptive_r"] is None for r in result["results"])


def test_future_prices_do_not_change_frozen_risk_or_direction() -> None:
    first = study.event_study(_evidence(), _bars())
    bars = _bars()
    for rows in bars.values():
        for row in rows:
            if row["time"] >= "2024-09-20":
                row.update(high=2, low=0.1)
    second = study.event_study(_evidence(), bars)
    assert first["selected_events"] == second["selected_events"]
    assert [
        (p["pair"], p["horizon"], p["risk_distance"], p["hypothesis"]["direction"])
        for p in first["paths"]
    ] == [
        (p["pair"], p["horizon"], p["risk_distance"], p["hypothesis"]["direction"])
        for p in second["paths"]
    ]
    assert first["paths"][0]["hypothesis"]["net_r"] != second["paths"][0]["hypothesis"]["net_r"]


@pytest.mark.parametrize("damage", ["risk-gap", "hold-gap", "quarantine"])
def test_gap_excludes_same_pair_from_both_directions_and_common_mask(damage: str) -> None:
    bars = _bars()
    if damage == "quarantine":
        next(r for r in bars["USDJPY"] if r["time"] == "2024-09-20")["gap_before"] = True
    else:
        remove = "2024-09-10" if damage == "risk-gap" else "2024-09-20"
        bars["USDJPY"] = [r for r in bars["USDJPY"] if r["time"] != remove]
    result = study.event_study(_evidence(), bars)
    assert len(result["paths"]) == 12
    assert not any(p["pair"] == "USDJPY" for p in result["paths"])
    assert all(r["complete_event_count"] == 0 for r in result["results"])
    assert sum(e.get("pair") == "USDJPY" for e in result["exclusions"]) == 2


def test_date_only_and_broken_sequence_cannot_issue_calls() -> None:
    evidence = _evidence()
    next(e for e in evidence["events"] if e["release_date"] == "2024-09-18")[
        "source_stated_release_at"
    ] = None
    result = study.event_study(evidence, _bars())
    assert result["selected_event_count"] == 0 and not result["paths"]
    assert any(e["reason"] == "EXACT_CLOCK_UNAVAILABLE" for e in result["exclusions"])
    evidence["status"] = "PARTIAL"
    with pytest.raises(ValueError):
        study.event_study(evidence, _bars())


def test_event_block_interval_deterministic_and_small_sample_missing() -> None:
    assert study._interval([1] * 7) is None
    assert study._interval([1] * 8) == [1, 1]
    assert study._interval(list(range(12))) == study._interval(list(range(12)))


def test_tampered_source_is_not_attached(tmp_path: Path) -> None:
    root = tmp_path / "fomc-history"
    root.mkdir()
    (root / "evidence.json").write_text("{}")
    report: dict[str, Any] = {"pair_reports": []}
    study.attach_fomc_evidence(report, tmp_path)
    assert report["fomc_history"]["status"] == report["fomc_study"]["status"] == "UNAVAILABLE"


def test_deleted_history_clears_embedded_stale_study(tmp_path: Path) -> None:
    report: dict[str, Any] = {"fomc_history": {"status": "OLD"}, "fomc_study": {"status": "OLD"}}
    study.attach_fomc_evidence(report, tmp_path)
    assert report["fomc_study"]["status"] == report["fomc_history"]["status"] == "UNAVAILABLE"


def test_missing_pointer_clears_embedded_stale_study(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fomc-history"
    root.mkdir()
    (root / "evidence.json").write_text("{}")
    monkeypatch.setattr(study, "load_history", lambda root: {"status": "SOURCE_RECONSTRUCTION"})
    report: dict[str, Any] = {"fomc_study": {"status": "OLD", "marker": "must not survive"}}
    study.attach_fomc_evidence(report, tmp_path)
    assert report["fomc_history"]["status"] == "SOURCE_RECONSTRUCTION"
    assert report["fomc_study"]["status"] == "UNAVAILABLE"
    assert "marker" not in report["fomc_study"]


def test_workspace_digest_resolves_git_names_from_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pipeline").mkdir()
    (tmp_path / "docs").mkdir()
    filename = "docs/frozen rules.txt"
    untracked = tmp_path / filename
    untracked.write_bytes(b"original rules")
    monkeypatch.chdir(tmp_path / "pipeline")
    patch = b"staged and unstaged changes"

    def git_output(args: list[str], **kwargs: Any) -> bytes:
        assert kwargs["cwd"] == tmp_path
        if args == ["git", "diff", "HEAD", "--binary"]:
            return patch
        assert args == ["git", "ls-files", "--others", "--exclude-standard", "-z"]
        return filename.encode() + b"\0"

    monkeypatch.setattr(subprocess, "check_output", git_output)
    expected = hashlib.sha256(
        patch
        + json.dumps(
            {filename: hashlib.sha256(b"original rules").hexdigest()}, sort_keys=True
        ).encode()
    ).hexdigest()
    assert study._workspace_digest(tmp_path) == expected
    untracked.write_bytes(b"changed rules")
    assert study._workspace_digest(tmp_path) != expected
    second = study._workspace_digest(tmp_path)
    patch = b"changed HEAD/index/worktree patch"
    assert study._workspace_digest(tmp_path) != second


def _registered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    evidence = {**_evidence(), "indexes": [], "captures": []}
    monkeypatch.setattr(study, "load_history", lambda root: evidence)
    monkeypatch.setattr(history, "audit_history", lambda root, indexes, captures: evidence)
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda args, **kwargs: "test-head\n" if kwargs.get("text") else b"",
    )
    pairs = []
    for pair, bars in _bars().items():
        path = tmp_path / (pair + ".json")
        raw = json.dumps({"pair": pair, "interval": "1d", "bars": bars}).encode()
        path.write_bytes(raw)
        pairs.append(
            {
                "pair": pair,
                "source_metadata": {
                    "capture_path": str(path),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                },
            }
        )
    report = {"pair_reports": pairs}
    return study.register_study(tmp_path, report), report


@pytest.mark.parametrize("damage", ["code", "source", "price", "rules", "price-manifest"])
def test_frozen_study_rejects_changed_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    path, report = _registered(tmp_path, monkeypatch)
    manifest = json.loads(path.read_bytes())
    if damage == "code":
        first = next(iter(manifest["code_bindings"]))
        manifest["code_bindings"][first] = "0" * 64
        path.write_text(json.dumps(manifest))
    elif damage == "source":
        Path(manifest["source_capture_path"]).write_text("{}")
    elif damage == "price":
        Path(report["pair_reports"][0]["source_metadata"]["capture_path"]).write_text("{}")
    else:
        if damage == "rules":
            manifest["target_event_and_horizon"]["entry_weekday_delay"] = 1
        else:
            manifest["price_captures"]["EURUSD"]["sha256"] = "0" * 64
        path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        study.run_study(tmp_path, path)


def test_saved_result_and_manifest_hashes_are_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _registered(tmp_path, monkeypatch)
    result = study.run_study(tmp_path, path)
    output = path.with_suffix(".result.json")
    raw = json.dumps(result).encode()
    output.write_bytes(raw)
    pointer = tmp_path / "fomc-history/studies/latest.json"
    pointer.write_text(
        json.dumps({"capture_path": str(output), "sha256": hashlib.sha256(raw).hexdigest()})
    )
    assert study.load_study(tmp_path) == result
    output.write_text("{}")
    with pytest.raises(ValueError, match="artifact changed"):
        study.load_study(tmp_path)
    output.write_bytes(raw)
    path.write_text("{}")
    with pytest.raises(ValueError, match="does not reproduce"):
        study.load_study(tmp_path)


def test_publication_uses_shared_journal_preserves_parent_and_prior_ai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.private_desk import report as publisher
    from tests.test_private_desk_journal import make_report

    path = make_report(tmp_path)
    report = json.loads(path.read_bytes())
    report["ai_summary"] = {"status": "GENERATED_UNVALIDATED", "original": "preserve"}
    report["current_review"] = {"status": "GENERATED_UNVALIDATED", "original": "preserve"}
    publisher.atomic_json(path, report)
    parent = path.read_bytes()
    root = tmp_path / "fomc-history"
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text("{}")
    monkeypatch.setattr(study, "register_study", lambda state, report: manifest)
    monkeypatch.setattr(
        study,
        "run_study",
        lambda state, manifest: {"experiment_id": "test", "status": "DEVELOPMENT_SENSITIVITY"},
    )

    def attach(report: dict[str, Any], state: Path) -> None:
        report["fomc_study"] = {"status": "DEVELOPMENT_SENSITIVITY"}

    monkeypatch.setattr(study, "attach_fomc_evidence", attach)
    result = study.publish_fomc(tmp_path)
    archive = Path(result["fomc_publication"]["parent_path"])
    assert archive.read_bytes() == parent
    assert result["prior_ai_summary"] == report["ai_summary"]
    assert result["prior_current_review"] == report["current_review"]
    assert result["pair_reports"][0]["candidate"] == report["pair_reports"][0]["candidate"]
    from src.private_desk.journal import journal_view

    view = journal_view(tmp_path)
    assert view["decision_count"] == 8 and view["unpublished_report_count"] == 0
    assert result["current_review"]["status"] == "DETACHED"


def test_context_refresh_replays_frozen_study_before_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.private_desk import data, report
    from tests.test_private_desk_journal import make_report

    path = make_report(tmp_path)
    order = []
    monkeypatch.setattr(data, "fetch_fundamentals", lambda root: {"status": "TEST"})
    monkeypatch.setattr(data, "fetch_news", lambda: [])
    monkeypatch.setattr(study, "attach_fomc_evidence", lambda value, root: order.append("replay"))
    monkeypatch.setattr(
        report, "apply_current_review", lambda *args, **kwargs: order.append("review")
    )
    report.refresh_current_report(tmp_path, use_ai=False)
    assert path.exists() and order == ["replay", "review"]
