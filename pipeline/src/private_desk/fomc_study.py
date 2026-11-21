"""Frozen announcement-change development study; no forecast or portfolio claim."""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.private_desk.bidask import bounded_path
from src.private_desk.engine import Costs, _atr, simulate_trade, validate_bars
from src.private_desk.fomc_history import EXPECTED_DATES, load_history
from src.private_desk.report import atomic_json

METHOD = "private-fomc-change-development-v1"
USD_SIGNS = {
    "EURUSD": -1,
    "GBPUSD": -1,
    "AUDUSD": -1,
    "NZDUSD": -1,
    "USDCAD": 1,
    "USDCHF": 1,
    "USDJPY": 1,
}
RULE: dict[str, Any] = {
    "horizons": [3, 5],
    "entry_weekday_delay": 2,
    "stop_atr": 1.5,
    "atr_period": 14,
    "costs": asdict(Costs()),
    "bootstrap_block": 4,
    "bootstrap_replicates": 2000,
    "bootstrap_seed": 20261002,
}
LIMITS = [
    "Already examined 2015-2024 development data, not an untouched validation cohort.",
    "Target change is not a surprise; expected policy and communication news are missing.",
    "Archive vintage, historical receipt and vendor candle boundaries remain unverified.",
    "Separate pair alternatives, not admitted portfolio trades or account returns.",
    "Event-average block intervals are descriptive; no selected winner or significance claim.",
    "Observed net-positive fractions are not calibrated live probabilities.",
    "No current recommendation, eligibility change, model call or automatic learning.",
]


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _weekday(day: date, steps: int) -> date:
    direction = 1 if steps > 0 else -1
    for _ in range(abs(steps)):
        day += timedelta(days=direction)
        while day.weekday() > 4:
            day += timedelta(days=direction)
    return day


def _price_inputs(state_dir: Path, references: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if set(references) != set(USD_SIGNS):
        raise ValueError("Exactly seven pinned USD-major captures are required")
    histories = {}
    for pair, meta in references.items():
        raw = bounded_path(state_dir, meta["capture_path"]).read_bytes()
        if _hash(raw) != meta["sha256"]:
            raise ValueError("Frozen price capture changed")
        value = json.loads(raw)
        if value["pair"] != pair or value["interval"] != "1d":
            raise ValueError("Frozen price identity changed")
        if any(
            type(b[key]) not in (int, float)
            for b in value["bars"]
            for key in ("open", "high", "low", "close")
        ):
            raise ValueError("Non-numeric frozen price")
        histories[pair] = validate_bars(value["bars"])
    return histories


def _interval(values: list[float]) -> list[float] | None:
    if len(values) < 8:
        return None
    generator = random.Random(RULE["bootstrap_seed"])
    n, width = len(values), RULE["bootstrap_block"]
    draws = []
    for _ in range(RULE["bootstrap_replicates"]):
        sample: list[float] = []
        while len(sample) < n:
            start = generator.randrange(n - width + 1)
            sample.extend(values[start : start + width])
        draws.append(sum(sample[:n]) / n)
    draws.sort()
    return [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))]]


def event_study(
    evidence: dict[str, Any], histories: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    if evidence["status"] != "SOURCE_RECONSTRUCTION" or evidence["failures"]:
        raise ValueError("Complete target-decision source sequence is required")
    events = evidence["events"]
    if {e["release_date"] for e in events} != EXPECTED_DATES or len(events) != len(EXPECTED_DATES):
        raise ValueError("Study source event cohort changed")
    if set(histories) != set(USD_SIGNS):
        raise ValueError("Study requires all seven USD majors")
    bars = {pair: validate_bars(rows) for pair, rows in histories.items()}
    indices = {pair: {row["time"]: i for i, row in enumerate(rows)} for pair, rows in bars.items()}
    paths, excluded, selected_events = [], [], []
    for event in events:
        change = event["change_from_prior_statement_pp"]
        if change in (None, 0):
            excluded.append({"release_date": event["release_date"], "reason": "NO_TARGET_CHANGE"})
            continue
        if not event["source_stated_release_at"]:
            excluded.append(
                {"release_date": event["release_date"], "reason": "EXACT_CLOCK_UNAVAILABLE"}
            )
            continue
        released = datetime.fromisoformat(event["source_stated_release_at"])
        if released.utcoffset() is None:
            raise ValueError("Source clock requires an offset")
        entry = _weekday(released.astimezone(UTC).date(), RULE["entry_weekday_delay"])
        signal = _weekday(entry, -1)
        selected_events.append(
            {
                "release_date": event["release_date"],
                "source_stated_release_at": event["source_stated_release_at"],
                "change_pp": change,
                "entry_date": entry.isoformat(),
                "signal_date": signal.isoformat(),
            }
        )
        for pair, usd_sign in USD_SIGNS.items():
            source = bars[pair]
            index = indices[pair].get(signal.isoformat())
            for horizon in RULE["horizons"]:
                try:
                    if index is None or index < 14:
                        raise ValueError("MISSING_RISK_WINDOW")
                    expected = [
                        _weekday(signal, step).isoformat() for step in range(-14, horizon + 1)
                    ]
                    window = source[index - 14 : index + horizon + 1]
                    if [row["time"] for row in window] != expected or any(
                        row.get("gap_before") for row in window[1:]
                    ):
                        raise ValueError("MISSING_OR_QUARANTINED_WINDOW")
                    risk = _atr(source, index) * RULE["stop_atr"]
                    if not math.isfinite(risk) or risk <= 0:
                        raise ValueError("INVALID_FROZEN_RISK")
                    direction = usd_sign * (1 if change > 0 else -1)
                    hypothesis = simulate_trade(
                        pair, source, index, direction, risk, horizon, costs=Costs(**RULE["costs"])
                    )
                    opposite = simulate_trade(
                        pair, source, index, -direction, risk, horizon, costs=Costs(**RULE["costs"])
                    )
                except ValueError as exc:
                    excluded.append(
                        {
                            "release_date": event["release_date"],
                            "pair": pair,
                            "horizon": horizon,
                            "reason": str(exc),
                        }
                    )
                    continue
                paths.append(
                    {
                        "release_date": event["release_date"],
                        "pair": pair,
                        "horizon": horizon,
                        "risk_distance": risk,
                        "signal_date": signal.isoformat(),
                        "entry_date": entry.isoformat(),
                        "hypothesis": hypothesis,
                        "opposite": opposite,
                        "paired_net_r_difference": hypothesis["net_r"] - opposite["net_r"],
                    }
                )
    results = []
    for horizon in RULE["horizons"]:
        relevant = [p for p in paths if p["horizon"] == horizon]
        counts = Counter(p["release_date"] for p in relevant)
        complete = sorted(day for day, count in counts.items() if count == len(USD_SIGNS))
        mask = set(complete)
        paired = [p for p in relevant if p["release_date"] in mask]
        event_differences = [
            sum(p["paired_net_r_difference"] for p in paired if p["release_date"] == day)
            / len(USD_SIGNS)
            for day in complete
        ]
        cells = []
        for pair in USD_SIGNS:
            cell = [p for p in paired if p["pair"] == pair]
            cells.append(
                {
                    "pair": pair,
                    "count": len(cell),
                    "hypothesis_mean_net_r": sum(p["hypothesis"]["net_r"] for p in cell) / len(cell)
                    if cell
                    else None,
                    "opposite_mean_net_r": sum(p["opposite"]["net_r"] for p in cell) / len(cell)
                    if cell
                    else None,
                    "hypothesis_net_positive_fraction": sum(
                        p["hypothesis"]["net_r"] > 0 for p in cell
                    )
                    / len(cell)
                    if cell
                    else None,
                    "paired_mean_difference_r": sum(p["paired_net_r_difference"] for p in cell)
                    / len(cell)
                    if cell
                    else None,
                }
            )
        periods = []
        for label, start, end in (
            ("2015-2018", "2015-01-01", "2018-12-31"),
            ("2019-2020", "2019-01-01", "2020-12-31"),
            ("2021-2024", "2021-01-01", "2024-12-31"),
        ):
            cohort = [p for p in paired if start <= p["release_date"] <= end]
            periods.append(
                {
                    "period": label,
                    "event_count": len({p["release_date"] for p in cohort}),
                    "mean_hypothesis_net_r": sum(p["hypothesis"]["net_r"] for p in cohort)
                    / len(cohort)
                    if cohort
                    else None,
                    "mean_opposite_net_r": sum(p["opposite"]["net_r"] for p in cohort) / len(cohort)
                    if cohort
                    else None,
                }
            )
        results.append(
            {
                "horizon": horizon,
                "complete_event_count": len(complete),
                "complete_event_dates": complete,
                "valid_pair_alternatives": len(relevant),
                "all_pair_mask_alternatives": len(paired),
                "event_average_paired_difference_r": sum(event_differences) / len(event_differences)
                if event_differences
                else None,
                "event_block_interval95_descriptive_r": _interval(event_differences),
                "pair_results": cells,
                "development_periods": periods,
            }
        )
    counts = Counter(
        (
            date.fromisoformat(e["entry_date"])
            - timedelta(days=date.fromisoformat(e["entry_date"]).weekday())
        ).isoformat()
        for e in selected_events
    )
    weeks: list[dict[str, Any]] = []
    monday = date(2015, 1, 5)
    while monday + timedelta(days=4) <= date(2024, 12, 31):
        weeks.append(
            {"week_start": monday.isoformat(), "distinct_change_events": counts[monday.isoformat()]}
        )
        monday += timedelta(days=7)
    return {
        "method_version": METHOD,
        "status": "DEVELOPMENT_SENSITIVITY",
        "rules": RULE,
        "selected_event_count": len(selected_events),
        "selected_events": selected_events,
        "results": results,
        "paths": paths,
        "exclusions": excluded,
        "weekly": weeks,
        "complete_calendar_weeks": len(weeks),
        "zero_event_weeks": sum(w["distinct_change_events"] == 0 for w in weeks),
        "mean_policy_events_per_week": sum(w["distinct_change_events"] for w in weeks) / len(weeks),
        "maximum_events_in_one_week": max(w["distinct_change_events"] for w in weeks),
        "frequency_basis": (
            "Distinct change events; pair alternatives are not separate "
            "opportunities or admitted trades."
        ),
        "EURGBP": "NOT_APPLICABLE_NO_DIRECT_USD_LEG",
        "forecast_qualification": "UNQUALIFIED",
        "probability": None,
        "surprise": None,
        "limitations": LIMITS,
    }


def _workspace_digest(repo: Path) -> str:
    changes = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=repo)
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=repo
        )
        .decode("utf-8")
        .split("\0")
    )
    untracked = {
        name: _hash(bounded_path(repo, str(repo / name)).read_bytes()) for name in names if name
    }
    return _hash(changes + json.dumps(untracked, sort_keys=True).encode())


def register_study(state_dir: Path, report: dict[str, Any]) -> Path:
    root = state_dir / "fomc-history"
    evidence = load_history(root)
    references = {
        p["pair"]: p["source_metadata"] for p in report["pair_reports"] if p["pair"] in USD_SIGNS
    }
    _price_inputs(state_dir, references)  # Identity and integrity only; no outcomes.
    repo = Path(__file__).resolve().parents[3]
    files = [
        "pipeline/src/private_desk/fomc_history.py",
        "pipeline/src/private_desk/fomc_study.py",
        "pipeline/src/private_desk/engine.py",
        "pipeline/src/private_desk/universe.py",
        "pipeline/src/private_desk/releases.py",
        "pipeline/src/private_desk/bidask.py",
        "docs/PRIVATE_FOMC_HISTORY_CONTRACT.md",
    ]
    code = {filename: _hash((repo / filename).read_bytes()) for filename in files}
    source_path = root / "studies" / (uuid4().hex + ".sources.json")
    atomic_json(source_path, evidence)
    experiment = (
        "fomc-development-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex
    )
    manifest = {
        "experiment_id": experiment,
        "registered_at_utc": datetime.now(UTC).isoformat(),
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
        "dirty_patch_sha256": _workspace_digest(repo),
        "dirty_workspace_basis": (
            "Tracked HEAD/index/worktree diff plus every non-ignored untracked path and byte hash."
        ),
        "code_bindings": code,
        "source_cohort": "EXPLORATORY_SOURCE_RECONSTRUCTION",
        "source_capture_path": str(source_path.resolve()),
        "source_sha256": _hash(source_path.read_bytes()),
        "price_captures": references,
        "data_manifest_sha256": _hash(json.dumps(references, sort_keys=True).encode()),
        "feature_contract_version": "PRIVATE_FOMC_HISTORY_CONTRACT-r1",
        "validation_contract_version": METHOD,
        "pair": list(USD_SIGNS),
        "hypothesis_and_rejection": (
            "Higher target midpoint -> USD strength; reject promotion "
            "regardless of descriptive result until untouched validation."
        ),
        "target_event_and_horizon": RULE,
        "cutoff_entry_exit_calendars": (
            "UTC release date, second subsequent weekday open; fixed 3/5 "
            "weekday path; vendor clock unknown."
        ),
        "required_sources_missingness_freshness": (
            "Exact source clock, complete adjacent targets, exact weekday "
            "risk/holding observations; missing outcomes unavailable."
        ),
        "train_calibration_test_boundaries": (
            "No fitting; descriptive periods 2015-2018, 2019-2020, 2021-2024; "
            "all previously inspected development data."
        ),
        "label_interval_purge_and_embargo": (
            "No train/test fit; delayed entry and 14 prior ATR steps; "
            "overlapping event returns not independent."
        ),
        "normalization_and_refit_schedule": "Fixed USD orientation and 1.5 ATR risk; no refits.",
        "candidate_models_and_total_trial_budget": (
            "One hypothesis and one opposite comparator, each 3/5-day horizon; "
            "all 14 pair/horizon cells reported; no selection."
        ),
        "baselines_and_eligibility_masks": (
            "Same event/pair/horizon windows for both directions; aggregates "
            "use all-seven complete events per horizon."
        ),
        "primary_metric_and_minimum_effect": (
            "Descriptive paired mean net R difference; no confirmatory minimum effect or promotion."
        ),
        "coverage_floor_and_allowed_change": (
            "Complete official source sequence; all exclusions recorded; "
            "unchanged source cohort, no outcome-based removals."
        ),
        "uncertainty_method_block_lengths_seeds": (
            "Event-average contiguous moving blocks 4, replicates 2000, seed "
            "20261002; fewer than 8 events => unavailable."
        ),
        "multiple_comparison_policy": (
            "Report every cell; no selected best, p-values or family-level significance claim."
        ),
        "holdout_access_log_and_hash": (
            "No untouched historical holdout: prior price research inspected "
            "this interval; this manifest precedes only the present fixed "
            "candidate calculation."
        ),
        "decision_rule_and_stop_rule": (
            "Publish truthfully even if negative; no tuning, new "
            "probabilities, current trade promotion or causal interpretation."
        ),
    }
    path = root / "studies" / (experiment + ".manifest.json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
    return path


def run_study(state_dir: Path, manifest_path: Path) -> dict[str, Any]:
    manifest_raw = bounded_path(state_dir, str(manifest_path)).read_bytes()
    manifest = json.loads(manifest_raw)
    if (
        manifest["validation_contract_version"] != METHOD
        or manifest["target_event_and_horizon"] != RULE
    ):
        raise ValueError("Frozen study rules changed")
    if (
        _hash(json.dumps(manifest["price_captures"], sort_keys=True).encode())
        != manifest["data_manifest_sha256"]
    ):
        raise ValueError("Frozen price manifest changed")
    repo = Path(__file__).resolve().parents[3]
    for filename, digest in manifest["code_bindings"].items():
        if _hash((repo / filename).read_bytes()) != digest:
            raise ValueError("Frozen implementation changed")
    raw = bounded_path(state_dir, manifest["source_capture_path"]).read_bytes()
    if _hash(raw) != manifest["source_sha256"]:
        raise ValueError("Frozen event source changed")
    from src.private_desk.fomc_history import audit_history

    evidence = json.loads(raw)
    if (
        audit_history(state_dir / "fomc-history", evidence["indexes"], evidence["captures"])
        != evidence
    ):
        raise ValueError("Frozen history does not replay")
    result = event_study(evidence, _price_inputs(state_dir, manifest["price_captures"]))
    result["manifest_reference"] = {
        "capture_path": str(manifest_path.resolve()),
        "sha256": _hash(manifest_raw),
    }
    result["experiment_id"] = manifest["experiment_id"]
    return result


def load_study(state_dir: Path) -> dict[str, Any]:
    pointer = json.loads((state_dir / "fomc-history/studies/latest.json").read_bytes())
    raw = bounded_path(state_dir, pointer["capture_path"]).read_bytes()
    if _hash(raw) != pointer["sha256"]:
        raise ValueError("Study artifact changed")
    result: dict[str, Any] = json.loads(raw)
    reference = result["manifest_reference"]
    manifest_path = bounded_path(state_dir, reference["capture_path"])
    if (
        _hash(manifest_path.read_bytes()) != reference["sha256"]
        or run_study(state_dir, manifest_path) != result
    ):
        raise ValueError("Study does not reproduce")
    return result


def attach_fomc_evidence(report: dict[str, Any], state_dir: Path) -> None:
    root = state_dir / "fomc-history"
    if not (root / "evidence.json").exists() and not any(
        key in report for key in ("fomc_history", "fomc_study")
    ):
        return
    report["fomc_study"] = {
        "status": "UNAVAILABLE",
        "reason": "No replayable frozen FOMC study is saved",
        "probability": None,
        "forecast_qualification": "UNQUALIFIED",
    }
    try:
        report["fomc_history"] = load_history(root)
        if (root / "studies/latest.json").exists():
            report["fomc_study"] = load_study(state_dir)
    except (OSError, ValueError, KeyError, TypeError):
        report["fomc_history"] = {
            "status": "UNAVAILABLE",
            "reason": "Pinned FOMC evidence did not replay",
            "forecast_qualification": "UNQUALIFIED",
        }
        report["fomc_study"] = {
            "status": "UNAVAILABLE",
            "probability": None,
            "forecast_qualification": "UNQUALIFIED",
        }


def publish_fomc(state_dir: Path, *, acquire: bool = False) -> dict[str, Any]:
    from src.private_desk.fomc_history import capture_history
    from src.private_desk.report import _publish_report, detach_current_review

    target = state_dir / "report.json"
    parent = target.read_bytes()
    report: dict[str, Any] = json.loads(parent)
    root = state_dir / "fomc-history"
    if acquire:
        capture_history(root)
    manifest = register_study(state_dir, report)
    result = run_study(state_dir, manifest)
    path = root / "studies" / (result["experiment_id"] + ".result.json")
    atomic_json(path, result)
    atomic_json(
        root / "studies/latest.json",
        {"capture_path": str(path.resolve()), "sha256": _hash(path.read_bytes())},
    )
    attach_fomc_evidence(report, state_dir)
    if report["fomc_study"]["status"] != "DEVELOPMENT_SENSITIVITY" or target.read_bytes() != parent:
        raise ValueError("Study did not qualify or current report changed")
    archive = root / ("parent-" + _hash(parent) + ".json")
    if archive.exists() and archive.read_bytes() != parent:
        raise ValueError("Parent archive changed")
    if not archive.exists():
        with archive.open("xb") as stream:
            stream.write(parent)
    detach_current_review(report, reason="FOMC development evidence added; prior AI retained.")
    report["fomc_publication"] = {
        "at": datetime.now(UTC).isoformat(),
        "parent_path": str(archive.resolve()),
        "parent_sha256": _hash(parent),
        "experiment_id": result["experiment_id"],
    }
    artifact = state_dir / "reports" / (uuid4().hex + "-fomc.json")
    atomic_json(artifact, report)
    _publish_report(state_dir, artifact, report)
    return report
