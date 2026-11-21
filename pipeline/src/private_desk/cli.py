"""Local research and launch commands; no hidden production or broker actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.private_desk.api import create_app, initialize_access
from src.private_desk.report import (
    PAIRS,
    ROOT,
    STATE_DIR,
    _publish_report,
    atomic_json,
    attach_bidask_evidence,
    attach_historical_evidence,
    attach_policy_history,
    attach_release_evidence,
    build_report,
    detach_current_review,
    recalculate_report,
    refresh_current_report,
)
from src.private_desk.universe import LEGACY_PAIRS, UNIVERSE_VERSION


def verify_report(path: Path) -> dict[str, Any]:
    report: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "private-fx-v1"
    names = [r["pair"] for r in report["pair_reports"]]
    expected = PAIRS if report.get("universe_version") == UNIVERSE_VERSION else LEGACY_PAIRS
    assert len(names) == len(expected) and set(names) == set(expected)
    assert report["universe"] == list(expected)
    assert report["policy"]["full_target_gross_r"] == 2.0
    for item in report["pair_reports"]:
        probability = item["candidate"].get("probability")
        assert probability is None or 0 <= probability <= 1
        assert item["candidate"].get("execution_status") in (None, "RESEARCH_ONLY")
        for trade in item.get("backtest", {}).get("trades", []):
            assert trade["signal_time"] < trade["entry_time"] <= trade["exit_time"]
            assert trade["net_r"] <= trade["gross_r"]
        meta = item.get("source_metadata", {})
        capture = meta.get("capture_path")
        if capture:
            assert Path(capture).exists()
    captures: dict[str, str] = {}

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("capture_path") and value.get("sha256"):
                captures[str(value["capture_path"])] = str(value["sha256"])
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(report)
    for capture_path, expected_digest in captures.items():
        assert hashlib.sha256(Path(capture_path).read_bytes()).hexdigest() == expected_digest
    encoded = json.dumps(report).lower()
    assert "api_key" not in encoded
    assert re.search(r"\bsk-[a-z0-9_-]{20,}", encoded) is None
    return report


def replay_report(path: Path) -> None:
    """Recompute pinned price cohorts without network access or a model call."""
    from src.private_desk.bidask import audit_pair
    from src.private_desk.engine import METHOD_VERSION, analyze_pair, analyze_reference_pair
    from src.private_desk.portfolio import replay_portfolio
    from src.private_desk.sessions import session_study

    report = verify_report(path)
    if report.get("current_review"):
        from src.private_desk.current_review import verify_current_review

        verify_current_review(report, STATE_DIR / "current-review")
        print(
            "CURRENT_REVIEW_DETACHED"
            if report["current_review"]["status"] == "DETACHED"
            else "CURRENT_REVIEW_REPLAY_OK"
        )
    if any(
        pair["backtest"].get("method_version") != METHOD_VERSION for pair in report["pair_reports"]
    ):
        raise ValueError(
            "Saved price method differs; use recalculate to create a new offline report."
        )
    started = time.perf_counter()
    for pair in report["pair_reports"]:
        capture_path = pair.get("source_metadata", {}).get("capture_path")
        assert capture_path, f"No pinned daily capture for {pair['pair']}"
        capture = json.loads(Path(capture_path).read_text(encoding="utf-8"))
        recomputed = analyze_pair(pair["pair"], capture["bars"])
        assert recomputed["backtest"] == pair["backtest"], pair["pair"] + " daily replay mismatch"
        reference_meta = pair.get("long_history", {}).get("source_metadata", {})
        if reference_meta.get("capture_path"):
            reference = json.loads(Path(reference_meta["capture_path"]).read_text(encoding="utf-8"))
            observations = []
            for date, rates in sorted(reference["raw_json"]["rates"].items()):
                base = 1.0 if pair["pair"][:3] == "EUR" else float(rates[pair["pair"][:3]])
                quote = float(rates[pair["pair"][3:]])
                observations.append({"time": date, "close": quote / base})
            study = analyze_reference_pair(pair["pair"], observations)
            assert study["backtest"] == pair["long_history"]["backtest"], (
                "Reference replay mismatch"
            )
        session_meta = pair.get("session", {}).get("source_metadata", {})
        if session_meta.get("capture_path"):
            hourly = json.loads(Path(session_meta["capture_path"]).read_text(encoding="utf-8"))
            study = session_study(pair["pair"], hourly["bars"])
            assert study.get("comparisons") == pair["session"].get("comparisons"), (
                "Session mismatch"
            )
        evidence = pair.get("bidask_evidence", {})
        if evidence.get("archives"):
            assert audit_pair(pair["pair"], evidence["archives"], STATE_DIR / "bidask") == evidence
        print(pair["pair"], "pinned daily/reference/session/bidask replay passed")
    vintage = report.get("historical_fundamentals", {})
    if vintage.get("captures"):
        from src.private_desk.vintage import audit_records

        assert audit_records(STATE_DIR / "vintages", vintage["captures"]) == vintage
        print("HISTORICAL_VINTAGE_REPLAY_OK")
    releases = report.get("historical_releases", {})
    if releases.get("captures"):
        from src.private_desk.releases import audit_records as audit_releases

        assert audit_releases(STATE_DIR / "releases", releases["captures"]) == releases
        print("HISTORICAL_RELEASE_REPLAY_OK")
    assert replay_portfolio(report["pair_reports"]) == report["portfolio_audit"], (
        "Portfolio mismatch"
    )
    print("PRIVATE_PORTFOLIO_REPLAY_OK")
    if report.get("correlation_audit"):
        from src.private_desk.report import attach_correlation_evidence

        old = report["correlation_audit"]
        attach_correlation_evidence(report)
        assert report["correlation_audit"] == old, "Correlation replay mismatch"
        print("PRIVATE_CORRELATION_REPLAY_OK")
    if report.get("daily_risk_audit"):
        from src.private_desk.risk_control import attach_daily_risk_evidence

        old_daily = report["daily_risk_audit"]
        attach_daily_risk_evidence(report)
        assert report["daily_risk_audit"] == old_daily, "Daily holding-risk replay mismatch"
        print("PRIVATE_DAILY_RISK_REPLAY_OK")
    policy = report.get("historical_policy", {})
    if policy.get("captures"):
        from src.private_desk.policy_history import audit_records as audit_policy
        from src.private_desk.policy_history import pair_policy_features

        assert (
            audit_policy(
                STATE_DIR / "policy-history",
                policy["captures"],
                method_version=policy["method_version"],
            )
            == policy
        )
        for pair in report["pair_reports"]:
            assert pair_policy_features(policy, pair["pair"]) == pair["historical_policy_features"]
        print("HISTORICAL_POLICY_REPLAY_OK")
    if report.get("fomc_history", {}).get("status") == "SOURCE_RECONSTRUCTION":
        from src.private_desk.fomc_history import audit_history
        from src.private_desk.fomc_study import run_study

        history = report["fomc_history"]
        assert (
            audit_history(STATE_DIR / "fomc-history", history["indexes"], history["captures"])
            == history
        )
        study = report["fomc_study"]
        assert run_study(STATE_DIR, Path(study["manifest_reference"]["capture_path"])) == study
        print("PRIVATE_FOMC_HISTORY_REPLAY_OK")
    print("PRIVATE_DESK_REPLAY_OK", f"{time.perf_counter() - started:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "init",
            "research",
            "recalculate",
            "serve",
            "verify",
            "replay",
            "checks",
            "bidask",
            "vintage",
            "release",
            "policy-history",
            "review",
            "journal",
            "daily-risk",
            "fomc-history",
        ),
    )
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--week", action="append", default=[])
    parser.add_argument("--pair", choices=PAIRS, action="append")
    parser.add_argument("--series", choices=("CPIAUCSL", "DGS2"), action="append")
    parser.add_argument("--vintage", action="append")
    parser.add_argument("--observation-start")
    parser.add_argument("--observation-end")
    parser.add_argument("--release-source", choices=("FOMC", "CPI"))
    parser.add_argument("--release-date", action="append")
    parser.add_argument(
        "--currency",
        choices=("USD", "EUR", "GBP", "AUD", "NZD", "CAD", "CHF", "JPY"),
        action="append",
    )
    parser.add_argument("--policy-start")
    parser.add_argument("--policy-end")
    args = parser.parse_args()
    if args.command == "init":
        initialize_access(STATE_DIR)
        print("Private login file: " + str(STATE_DIR / "access.txt"))
    elif args.command == "research":
        build_report(refresh=args.refresh, use_ai=not args.no_ai, progress=print)
        print("PRIVATE_DESK_RESEARCH_READY")
    elif args.command == "journal":
        from src.private_desk.journal import sync_journal

        value = sync_journal(STATE_DIR, STATE_DIR / "report.json")
        print("JOURNAL_COUNTS", value["decision_count"], value["outcome_status_counts"])
        print("PRIVATE_OUTCOME_JOURNAL_OK")
    elif args.command == "daily-risk":
        from src.private_desk.risk_control import publish_daily_risk

        verify_report(STATE_DIR / "report.json")
        risk_report = publish_daily_risk(STATE_DIR)
        print("DAILY_RISK", risk_report["daily_risk_audit"]["status"])
        print("PRIVATE_DAILY_RISK_READY")
    elif args.command == "fomc-history":
        from src.private_desk.fomc_study import publish_fomc

        verify_report(STATE_DIR / "report.json")
        fomc_report = publish_fomc(STATE_DIR, acquire=True)
        print("FOMC_HISTORY", fomc_report["fomc_history"]["status"])
        print("FOMC_STUDY", fomc_report["fomc_study"]["selected_event_count"])
        print("PRIVATE_FOMC_HISTORY_READY")
    elif args.command == "recalculate":
        verify_report(STATE_DIR / "report.json")
        report = recalculate_report()
        print(
            report["portfolio_audit"]["status"],
            report["portfolio_audit"].get("accepted_call_count"),
        )
        print("PRIVATE_QUANTITATIVE_RECALCULATION_OK")
    elif args.command == "review":
        verify_report(STATE_DIR / "report.json")
        report = refresh_current_report(use_ai=not args.no_ai)
        ai = report["ai_summary"]
        print("CURRENT_AI", ai["status"], ai.get("model"), ai.get("usage"))
        admission = report["current_review"]["input_admission"]
        print(
            "NEWS_ADMISSION",
            {
                name: admission[name]
                for name in (
                    "supplied_news",
                    "accepted_before_cap",
                    "selected_news",
                    "missing_news_currencies",
                )
            },
            "rejected",
            len(admission["rejected_news"]),
        )
        print("PRIVATE_CURRENT_REVIEW_READY")
    elif args.command == "verify":
        report = verify_report(STATE_DIR / "report.json")
        for item in report["pair_reports"]:
            coverage = item.get("data_coverage", {})
            print(
                item["pair"],
                coverage.get("bar_count"),
                item["backtest"].get("trade_count"),
                item["candidate"].get("status"),
            )
        print("PRIVATE_DESK_REPORT_OK")
    elif args.command == "checks":
        for command in (
            [sys.executable, "-m", "pytest", "-q"],
            [sys.executable, "-m", "ruff", "check", "."],
            [sys.executable, "-m", "mypy", "."],
        ):
            result = subprocess.run(command, cwd=ROOT / "pipeline", check=False)
            if result.returncode:
                raise SystemExit(result.returncode)
        print("PRIVATE_DESK_CHECKS_OK")
    elif args.command == "replay":
        replay_report(STATE_DIR / "report.json")
    elif args.command == "bidask":
        from src.private_desk.bidask import capture_cohort

        cohort = capture_cohort(
            STATE_DIR / "bidask", args.week, args.pair or list(PAIRS), refresh=args.refresh
        )
        for item in cohort["pair_audits"]:
            print(
                item["pair"],
                item["status"],
                item.get("observed_minutes"),
                item.get("proxy_missing_minutes"),
                item["failures"],
            )
        path = STATE_DIR / "report.json"
        if path.exists():
            report = verify_report(path)
            attach_bidask_evidence(report, STATE_DIR)
            report["bidask_updated_at"] = datetime.now(UTC).isoformat()
            detach_current_review(
                report, reason="Saved price evidence changed; prior AI review archived."
            )
            artifact = (
                STATE_DIR
                / "reports"
                / (f"{datetime.now(UTC):%Y%m%dT%H%M%S}-bidask-{uuid4().hex}.json")
            )
            atomic_json(artifact, report)
            _publish_report(STATE_DIR, artifact, report)
        print("PRIVATE_BIDASK_CAPTURE_OK")
    elif args.command == "vintage":
        from src.private_desk.vintage import capture_cohort as capture_vintage_cohort

        if not all((args.series, args.vintage, args.observation_start, args.observation_end)):
            parser.error("vintage requires named series, vintage dates and observation window")
        specs = [
            {
                "series": series,
                "vintage": vintage,
                "start": args.observation_start,
                "end": args.observation_end,
            }
            for series in args.series
            for vintage in args.vintage
        ]
        cohort = capture_vintage_cohort(STATE_DIR / "vintages", specs, refresh=args.refresh)
        for item in cohort["series_audits"]:
            print(item["series"], item["status"], len(item["snapshot_summaries"]), item["failures"])
        path = STATE_DIR / "report.json"
        if path.exists():
            report = verify_report(path)
            attach_historical_evidence(report, STATE_DIR)
            report["vintage_updated_at"] = datetime.now(UTC).isoformat()
            detach_current_review(
                report, reason="Saved vintage evidence changed; prior AI review archived."
            )
            artifact = (
                STATE_DIR
                / "reports"
                / (f"{datetime.now(UTC):%Y%m%dT%H%M%S}-vintage-{uuid4().hex}.json")
            )
            atomic_json(artifact, report)
            _publish_report(STATE_DIR, artifact, report)
        print("PRIVATE_VINTAGE_CAPTURE_OK")
    elif args.command == "release":
        from src.private_desk.releases import capture_cohort as capture_release_cohort

        if not args.release_source or not args.release_date:
            parser.error("release requires a named source and release dates")
        cohort = capture_release_cohort(
            STATE_DIR / "releases",
            [{"source": args.release_source, "date": day} for day in args.release_date],
            refresh=args.refresh,
        )
        print(cohort["status"], len(cohort["events"]), "source-stated releases", cohort["failures"])
        path = STATE_DIR / "report.json"
        if path.exists():
            report = verify_report(path)
            attach_release_evidence(report, STATE_DIR)
            report["release_updated_at"] = datetime.now(UTC).isoformat()
            detach_current_review(
                report, reason="Saved release evidence changed; prior AI review archived."
            )
            artifact = (
                STATE_DIR
                / "reports"
                / (f"{datetime.now(UTC):%Y%m%dT%H%M%S}-release-{uuid4().hex}.json")
            )
            atomic_json(artifact, report)
            _publish_report(STATE_DIR, artifact, report)
        print("PRIVATE_RELEASE_CAPTURE_OK")
    elif args.command == "policy-history":
        from src.private_desk.policy_history import AREAS
        from src.private_desk.policy_history import capture_cohort as capture_policy_cohort

        if not args.policy_start or not args.policy_end:
            parser.error("policy-history requires an explicit start and end date")
        cohort = capture_policy_cohort(
            STATE_DIR / "policy-history",
            [
                {"currency": currency, "start": args.policy_start, "end": args.policy_end}
                for currency in args.currency or AREAS
            ],
            refresh=args.refresh,
        )
        for item in cohort["series_audits"]:
            print(
                item["currency"], item["numeric_count"], item["first_numeric"], item["last_numeric"]
            )
        print("Failures", cohort["failures"])
        path = STATE_DIR / "report.json"
        if path.exists():
            report = verify_report(path)
            attach_policy_history(report, STATE_DIR)
            report["policy_history_updated_at"] = datetime.now(UTC).isoformat()
            detach_current_review(
                report, reason="Saved policy evidence changed; prior AI review archived."
            )
            artifact = (
                STATE_DIR
                / "reports"
                / (f"{datetime.now(UTC):%Y%m%dT%H%M%S}-policy-{uuid4().hex}.json")
            )
            atomic_json(artifact, report)
            _publish_report(STATE_DIR, artifact, report)
        print("PRIVATE_POLICY_HISTORY_CAPTURE_OK")
    elif args.command == "serve":
        import uvicorn

        uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
