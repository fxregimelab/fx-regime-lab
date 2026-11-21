"""Orchestrate private research into versioned local artifacts, without DB writes."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.private_desk.universe import PAIRS as PAIRS
from src.private_desk.universe import UNIVERSE_VERSION

ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / ".private-fx"


def attach_correlation_evidence(report: dict[str, Any]) -> None:
    """Reproduce a separate risk/frequency audit from hash-bound daily captures."""
    import hashlib

    from src.private_desk.correlation import correlation_snapshot, replay_correlated_portfolio

    try:
        histories = {}
        intervals: list[tuple[str, str]] = []
        for item in report["pair_reports"]:
            meta = item["source_metadata"]
            raw = Path(meta["capture_path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                raise ValueError("Pinned price capture changed")
            histories[item["pair"]] = json.loads(raw)["bars"]
            intervals.extend(
                (fold["test_start"], fold["test_end"]) for fold in item["backtest"]["folds"]
            )
        if not intervals:
            raise ValueError("No chronological test interval")
        start, end = min(i[0] for i in intervals), max(i[1] for i in intervals)
        audit = replay_correlated_portfolio(
            report["pair_reports"], histories, evaluation_start=start, evaluation_end=end
        )
        cutoff = min(str(item["candidate"]["as_of"]) for item in report["pair_reports"])
        audit["current_pair_correlations"] = correlation_snapshot(histories, cutoff)
        audit["current_correlation_cutoff_exclusive"] = cutoff
        audit["pair_evaluation_intervals"] = {
            item["pair"]: [
                {"start": f["test_start"], "end": f["test_end"]} for f in item["backtest"]["folds"]
            ]
            for item in report["pair_reports"]
        }
        from datetime import date, timedelta

        for week in audit.get("weekly", []):
            monday = date.fromisoformat(week["week_start"])
            friday = (monday + timedelta(days=4)).isoformat()
            week["all_pair_test_coverage"] = bool(week["complete_week"]) and all(
                any(f["start"] <= week["week_start"] and f["end"] >= friday for f in intervals)
                for intervals in audit["pair_evaluation_intervals"].values()
            )
        common_weeks = [w for w in audit.get("weekly", []) if w["all_pair_test_coverage"]]
        audit["common_coverage_frequency"] = {
            "complete_week_count": len(common_weeks),
            "mean_weekly_offered_calls": sum(w["offered_research_calls"] for w in common_weeks)
            / len(common_weeks)
            if common_weeks
            else None,
            "mean_weekly_entries": sum(w["admitted_research_calls"] for w in common_weeks)
            / len(common_weeks)
            if common_weeks
            else None,
            "weeks_meeting_target": sum(w["target_met"] for w in common_weeks),
            "zero_entry_week_count": sum(w["admitted_research_calls"] == 0 for w in common_weeks),
            "basis": "Complete weeks inside all eight test ranges; source gaps remain excluded.",
        }
        audit["weekly_cohort_basis"] = (
            "Calendar span from earliest to latest pair test date, including zero weeks; "
            "pair-specific source/fold coverage varies and is recorded separately."
        )
        report["correlation_audit"] = audit
    except (KeyError, ValueError, TypeError, OSError, OverflowError):
        report["correlation_audit"] = {
            "status": "UNAVAILABLE",
            "strategy_qualification": "UNQUALIFIED",
            "reason": "Incomplete or invalid pinned daily/fold evidence; no partial audit.",
        }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def _publish_report(state_dir: Path, artifact: Path, report: dict[str, Any]) -> None:
    from src.private_desk.journal import commit_publication, evaluate_pending, record_report

    tracked = report.get("universe_version") == UNIVERSE_VERSION
    if tracked:
        record_report(state_dir, artifact)
    atomic_json(state_dir / "report.json", report)
    if tracked:
        commit_publication(state_dir, artifact)
        evaluate_pending(state_dir, artifact)


def detach_current_review(report: dict[str, Any], *, reason: str) -> None:
    """Preserve an old review while refusing to bind it to revised research inputs."""
    if report.get("current_review", {}).get("status") not in (None, "DETACHED"):
        report["prior_current_review"] = report["current_review"]
        report["current_review"] = {
            "status": "DETACHED",
            "reason": reason,
            "forecast_qualification": "UNQUALIFIED",
        }
    if report.get("ai_summary", {}).get("status") not in (None, "UNAVAILABLE"):
        report["prior_ai_summary"] = report["ai_summary"]
    report["ai_summary"] = {"status": "UNAVAILABLE", "reason": reason}
    for item in report["pair_reports"]:
        if item.get("ai_analysis", {}).get("status") not in (None, "UNAVAILABLE"):
            item["prior_ai_analysis"] = item["ai_analysis"]
        item["ai_analysis"] = {"status": "UNAVAILABLE", "reason": reason}


def attach_bidask_evidence(report: dict[str, Any], state_dir: Path) -> None:
    """Read saved original archives only; failure cannot erase other research."""
    from src.private_desk.bidask import LIMITS, load_evidence

    try:
        audits = load_evidence(state_dir / "bidask")
        reason = "No named-week capture saved for this pair"
    except Exception as exc:
        audits = {}
        reason = "Saved bid/ask evidence rejected: " + type(exc).__name__
    for item in report["pair_reports"]:
        item["bidask_evidence"] = audits.get(
            item["pair"],
            {
                "pair": item["pair"],
                "status": "UNAVAILABLE",
                "reason": reason,
                "execution_qualification": "UNQUALIFIED",
                "timestamp_role": "UNKNOWN",
                "limitations": LIMITS,
            },
        )


def attach_historical_evidence(report: dict[str, Any], state_dir: Path) -> None:
    """Attach original vintage audit evidence without changing any pair calculation."""
    from src.private_desk.vintage import LIMITS, load_evidence

    try:
        evidence = load_evidence(state_dir / "vintages")
        reason = "No historical vintage snapshots saved"
    except Exception as exc:
        evidence = None
        reason = "Saved historical evidence rejected: " + type(exc).__name__
    report["historical_fundamentals"] = evidence or {
        "status": "UNAVAILABLE",
        "reason": reason,
        "covered_currencies": [],
        "release_timing": "UNKNOWN",
        "historical_model_qualification": "UNQUALIFIED",
        "metadata_qualification": "UNQUALIFIED",
        "limitations": LIMITS,
    }


def apply_current_review(
    report: dict[str, Any],
    state_dir: Path,
    *,
    use_ai: bool,
    parent_bytes: bytes | None = None,
) -> None:
    from src.ai.client import PRIVATE_REVIEW_METHOD, generate_private_fundamental_brief
    from src.private_desk.current_review import (
        AI_FIELDS,
        capture_review_input,
        capture_review_output,
        verify_current_review,
    )

    as_of = datetime.now(UTC).isoformat()
    root = state_dir / "current-review"
    receipt = capture_review_input(report, root, as_of=as_of, parent_bytes=parent_bytes)
    config_path = state_dir / "provider.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if use_ai:
        ai = generate_private_fundamental_brief(
            report["pair_reports"],
            report["news"],
            report["pair_reports"][0]["fundamentals"],
            as_of=as_of,
            env_file=os.environ.get("PRIVATE_FX_AI_ENV_FILE") or config.get("env_file"),
        )
    else:
        ai = {
            "status": "UNAVAILABLE",
            "reason": "Current AI review not requested",
            "pairs": [],
            "generated_at": as_of,
            "payload_sha256": receipt["input_packet"]["sha256"],
            "method_version": PRIVATE_REVIEW_METHOD,
        }
    by_pair = {item["pair"]: item for item in ai.get("pairs", [])}
    for item in report["pair_reports"]:
        item["ai_analysis"] = {name: ai.get(name) for name in AI_FIELDS}
        item["ai_analysis"].update(by_pair.get(item["pair"], {}))
    report["ai_summary"] = ai
    receipt["status"] = ai["status"]
    receipt["output_packet"] = capture_review_output(ai, root)
    report["current_review"] = receipt
    report["current_context_updated_at"] = as_of
    verify_current_review(report, root)


def build_report(
    state_dir: Path = STATE_DIR,
    *,
    refresh: bool = False,
    use_ai: bool = True,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    from src.private_desk.data import (
        fetch_fundamentals,
        fetch_news,
        load_history,
        load_reference_history,
    )
    from src.private_desk.engine import analyze_pair, analyze_reference_pair
    from src.private_desk.portfolio import replay_portfolio

    update = progress or (lambda _message: None)
    now = datetime.now(UTC).isoformat()
    reports: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    update("Fetching current fundamental evidence and dated headlines")
    fundamentals = fetch_fundamentals(state_dir / "captures")
    news = fetch_news()
    atomic_json(state_dir / "news" / f"{uuid4().hex}.json", news)
    for i, pair in enumerate(PAIRS):
        update(f"{i + 1}/{len(PAIRS)}: {pair} daily history and chronological research")
        try:
            reference, reference_meta = load_reference_history(
                pair,
                cache_dir=state_dir / "sources",
                refresh=refresh and i == 0,
            )
            long_history = analyze_reference_pair(pair, reference)
            long_history["source_metadata"] = reference_meta
            bars, meta = load_history(
                pair,
                cache_dir=state_dir / "sources",
                refresh=refresh,
            )
            analysis = analyze_pair(pair, bars)
            analysis["long_history"] = long_history
            analysis["source_metadata"] = meta
            analysis["fundamentals"] = fundamentals
            sources.append({"pair": pair, **meta})
            update(f"{pair}: recent hourly session evidence")
            try:
                hourly, hourly_meta = load_history(
                    pair,
                    interval="1h",
                    cache_dir=state_dir / "sources",
                    refresh=refresh,
                )
                from src.private_desk.sessions import session_study

                analysis["session"] = session_study(pair, hourly)
                analysis["session"]["source_metadata"] = hourly_meta
            except Exception as exc:
                analysis["session"] = {
                    "status": "UNAVAILABLE",
                    "reason": f"Hourly study failed: {type(exc).__name__}",
                }
            analysis["candidate"]["fundamental_qualification"] = "UNQUALIFIED"
            analysis["candidate"]["execution_status"] = "RESEARCH_ONLY"
            reports.append(analysis)
        except Exception as exc:  # Keep provider/SDK messages and credentials out of artifacts.
            reports.append(
                {
                    "pair": pair,
                    "data_coverage": {"status": "UNAVAILABLE"},
                    "backtest": {"status": "UNAVAILABLE", "trade_count": 0, "trades": []},
                    "candidate": {
                        "status": "ABSTAIN",
                        "direction": "UNAVAILABLE",
                        "probability": None,
                        "expected_r": None,
                        "reasons": [f"Research failed: {type(exc).__name__}"],
                    },
                    "chart": {"ohlc": [], "equity": []},
                    "session": {"status": "UNAVAILABLE"},
                    "fundamentals": fundamentals,
                }
            )
    report = {
        "schema_version": "private-fx-v1",
        "generated_at": now,
        "universe": list(PAIRS),
        "universe_version": UNIVERSE_VERSION,
        "policy": {
            "horizons": [3, 5],
            "entry": "Next completed daily bar open (daily baseline)",
            "partial_exit": "50% at +1R; remainder stop to entry and target +3R",
            "full_target_gross_r": 2.0,
            "costs": "Explicit model assumptions; see each backtest",
            "order": "Adverse-first when daily bars cannot resolve intrabar order",
            "execution": "Manual; independent technical review required",
        },
        "pair_reports": reports,
        "news": news,
        "sources": sources,
        "data_status": "PROVISIONAL_PROVIDER_RECONSTRUCTION",
        "research_status": "UNVALIDATED_PRICE_BASELINE_WITH_CURRENT_FUNDAMENTAL_REVIEW",
        "warnings": [
            "Seven USD majors including USDJPY, plus the EURGBP research cross.",
            "Current fundamental/news review is not backtested historical evidence.",
            "Bars lack executable broker bid/ask and historical receipt evidence.",
            "No guaranteed +1R or 60–70% win rate. Stop-to-entry can still lose after costs.",
            "Per-call R is not account equity; the separate overlap audit uses "
            "fixed research risk units.",
            "Model and session selection are research trials requiring forward validation.",
        ],
    }
    attach_bidask_evidence(report, state_dir)
    attach_historical_evidence(report, state_dir)
    attach_release_evidence(report, state_dir)
    attach_policy_history(report, state_dir)
    report["portfolio_audit"] = replay_portfolio(reports)
    attach_correlation_evidence(report)
    from src.private_desk.risk_control import attach_daily_risk_evidence

    attach_daily_risk_evidence(report)
    from src.private_desk.fomc_study import attach_fomc_evidence

    attach_fomc_evidence(report, state_dir)
    update("Capturing current research inputs and bounded AI review")
    apply_current_review(report, state_dir, use_ai=use_ai)
    artifact = state_dir / "reports" / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex}.json"
    atomic_json(artifact, report)
    _publish_report(state_dir, artifact, report)
    update("Research report ready")
    return report


def recalculate_report(state_dir: Path = STATE_DIR) -> dict[str, Any]:
    """Revise quantitative research offline while preserving original source evidence."""
    import hashlib

    from src.private_desk.engine import analyze_pair
    from src.private_desk.portfolio import replay_portfolio

    original_bytes = (state_dir / "report.json").read_bytes()
    report: dict[str, Any] = json.loads(original_bytes)
    if report.get("current_review", {}).get("status") not in (None, "DETACHED"):
        report["prior_current_review"] = report["current_review"]
        report["current_review"] = {
            "status": "DETACHED",
            "reason": "Quantitative inputs changed; previous current-review receipt archived.",
            "forecast_qualification": "UNQUALIFIED",
        }
    for item in report["pair_reports"]:
        meta = item["source_metadata"]
        raw = Path(meta["capture_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError("Pinned daily source hash changed")
        analysis = analyze_pair(item["pair"], json.loads(raw)["bars"])
        for key in ("data_coverage", "backtest", "candidate", "chart"):
            item[key] = analysis[key]
        item["candidate"]["fundamental_qualification"] = "UNQUALIFIED"
        item["candidate"]["execution_status"] = "RESEARCH_ONLY"
        if item.get("ai_analysis", {}).get("status") != "UNAVAILABLE":
            item["prior_ai_analysis"] = item.get("ai_analysis")
        item["ai_analysis"] = {
            "status": "UNAVAILABLE",
            "reason": (
                "Prior AI review used older quantitative inputs; archived separately, "
                "not revalidated."
            ),
        }
    if report.get("ai_summary", {}).get("status") not in (None, "UNAVAILABLE"):
        report["prior_ai_summary"] = report.get("ai_summary")
    report["ai_summary"] = {
        "status": "UNAVAILABLE",
        "reason": (
            "Offline recalculation did not run AI; prior review is not "
            "current quantitative evidence."
        ),
    }
    report["portfolio_audit"] = replay_portfolio(report["pair_reports"])
    if report.get("universe_version") == UNIVERSE_VERSION:
        attach_correlation_evidence(report)
        from src.private_desk.risk_control import attach_daily_risk_evidence

        attach_daily_risk_evidence(report)
    from src.private_desk.fomc_study import attach_fomc_evidence

    attach_fomc_evidence(report, state_dir)
    report["quantitative_recalculation"] = {
        "at": datetime.now(UTC).isoformat(),
        "previous_report_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "original_generated_at": report["generated_at"],
        "inputs": "Original pinned daily sources; no network or AI call.",
    }
    artifact = (
        state_dir / "reports" / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-recalculate-{uuid4().hex}.json"
    )
    atomic_json(artifact, report)
    _publish_report(state_dir, artifact, report)
    return report


def refresh_current_report(state_dir: Path = STATE_DIR, *, use_ai: bool = True) -> dict[str, Any]:
    """Refresh current context while retaining the original quantitative research exactly."""
    from src.private_desk.data import fetch_fundamentals, fetch_news

    target = state_dir / "report.json"
    parent_bytes = target.read_bytes()
    report: dict[str, Any] = json.loads(parent_bytes)
    fundamentals = fetch_fundamentals(state_dir / "captures")
    news = fetch_news()
    report["news"] = news
    if report.get("ai_summary", {}).get("status") not in (None, "UNAVAILABLE"):
        report["prior_ai_summary"] = report.get("ai_summary")
    if report.get("current_review", {}).get("status") not in (None, "DETACHED"):
        report["prior_current_review"] = report["current_review"]
    for item in report["pair_reports"]:
        if item.get("ai_analysis", {}).get("status") not in (None, "UNAVAILABLE"):
            item["prior_ai_analysis"] = item.get("ai_analysis")
        item["fundamentals"] = fundamentals
    from src.private_desk.fomc_study import attach_fomc_evidence

    attach_fomc_evidence(report, state_dir)
    apply_current_review(report, state_dir, use_ai=use_ai, parent_bytes=parent_bytes)
    if target.read_bytes() != parent_bytes:
        raise ValueError("Report changed while current context was being reviewed")
    artifact = (
        state_dir / "reports" / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-review-{uuid4().hex}.json"
    )
    atomic_json(artifact, report)
    _publish_report(state_dir, artifact, report)
    return report


def attach_release_evidence(report: dict[str, Any], state_dir: Path) -> None:
    """Saved source clocks remain separate from forecasts and actual availability."""
    from src.private_desk.releases import LIMITS, load_evidence

    try:
        evidence = load_evidence(state_dir / "releases")
        reason = "No historical release archives saved"
    except Exception as exc:
        evidence = None
        reason = "Saved release evidence rejected: " + type(exc).__name__
    report["historical_releases"] = evidence or {
        "status": "UNAVAILABLE",
        "reason": reason,
        "covered_currencies": [],
        "historical_model_qualification": "UNQUALIFIED",
        "provider_availability": "UNKNOWN",
        "limitations": LIMITS,
    }


def attach_policy_history(report: dict[str, Any], state_dir: Path) -> None:
    """Retrospective policy features cannot change price or AI research qualification."""
    from src.private_desk.policy_history import LIMITS, load_evidence, pair_policy_features

    try:
        evidence = load_evidence(state_dir / "policy-history")
        reason = "No historical policy snapshots saved"
        features = (
            {
                item["pair"]: pair_policy_features(evidence, item["pair"])
                for item in report["pair_reports"]
            }
            if evidence
            else {}
        )
    except Exception as exc:
        evidence = None
        features = {}
        reason = "Saved policy histories rejected: " + type(exc).__name__
    report["historical_policy"] = evidence or {
        "status": "UNAVAILABLE",
        "reason": reason,
        "covered_currencies": [],
        "historical_availability": "UNKNOWN",
        "historical_vintage": "UNKNOWN",
        "forecast_qualification": "UNQUALIFIED",
        "limitations": LIMITS,
    }
    for item in report["pair_reports"]:
        item["historical_policy_features"] = features.get(
            item["pair"],
            {
                "pair": item["pair"],
                "status": "UNAVAILABLE",
                "reason": reason,
                "rows": [],
                "forecast_qualification": "UNQUALIFIED",
                "limitations": LIMITS,
            },
        )
