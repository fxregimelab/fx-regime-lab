"""Daily boundary controls and explicitly modelled exits, never executable fills."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.private_desk.correlation import (
    MIN_MATCHED,
    THRESHOLD,
    WINDOW,
    _risk_groups,
    _weekly,
    currency_legs,
    return_series,
)
from src.private_desk.engine import METHOD_VERSION, Costs, simulate_trade, validate_bars
from src.private_desk.portfolio import _business_day, _date, _validate_call
from src.private_desk.universe import PAIRS

METHOD = "private-daily-risk-v1"
LIMITS = [
    "Daily-OHLC development counterfactual under fixed generic costs; no executable fills.",
    "Limits apply only immediately after a simulated daily review, never intraday.",
    "Examined price cohorts and risk settings remain unqualified development evidence.",
    "The admission cutoff is the entry day, unlike the earlier signal-date v1 replay.",
    "Capacity stays reserved through the original horizon even after an early exit.",
    "Equal per-call R and currency direction counts are not account equity or notionals.",
    "The closed-path curve excludes unrealised losses and financing is an assumption.",
    "Executable forced-exit and hedge returns remain unavailable; no hedge is simulated.",
]


def _rank(row: dict[str, Any]) -> tuple[str, float, int]:
    probability = row["predicted_probability"]
    return (
        row["entry_time"],
        -probability if probability is not None else 1.0,
        PAIRS.index(row["pair"]),
    )


def _inputs(
    pair_reports: list[dict[str, Any]],
    histories: dict[str, list[dict[str, Any]]],
    start: date,
    end: date,
) -> tuple[list[dict[str, Any]], dict[str, Costs]]:
    names = [item["pair"] for item in pair_reports]
    if len(names) != len(PAIRS) or set(names) != set(PAIRS) or set(histories) != set(PAIRS):
        raise ValueError("Incomplete universe")
    if start > end or (end - start).days > 365 * 100:
        raise ValueError("Invalid evaluation span")
    calls, costs, identities = [], {}, set()
    for item in pair_reports:
        pair, backtest = item["pair"], item["backtest"]
        if backtest["method_version"] != METHOD_VERSION:
            raise ValueError("Unsupported source trade method")
        assumptions = backtest["assumptions"]["costs"]
        if set(assumptions) != {
            "spread_pips",
            "slippage_pips_per_side",
            "holding_pips_per_calendar_day",
        }:
            raise ValueError("Incomplete cost assumptions")
        if any(
            isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0
            for v in assumptions.values()
        ):
            raise ValueError("Invalid cost assumptions")
        costs[pair] = Costs(**assumptions)
        bars = validate_bars(histories[pair])
        if any(_date(b["time"]).isoformat() != b["time"] for b in bars):
            raise ValueError("Daily sources require canonical validated weekdays")
        for original in backtest["trades"]:
            _validate_call(pair, original)
            identity = pair, original["entry_time"]
            if identity in identities or not start <= _date(original["entry_time"]) <= end:
                raise ValueError("Duplicate or out-of-range candidate")
            identities.add(identity)
            signal = original["signal_index"]
            if type(signal) is not int or type(original["end_index"]) is not int:
                raise ValueError("Invalid signal index")
            replay = simulate_trade(
                pair,
                bars,
                signal,
                1 if original["direction"] == "BUY" else -1,
                abs(original["entry"] - original["stop"]),
                original["holding_days"],
                costs=costs[pair],
            )
            for key, value in replay.items():
                saved = original[key]
                if isinstance(value, float):
                    if isinstance(saved, bool) or not math.isclose(
                        value, saved, rel_tol=1e-10, abs_tol=1e-10
                    ):
                        raise ValueError("Source trade path does not reproduce")
                elif saved != value:
                    raise ValueError("Source trade path does not reproduce")
            calls.append(dict(original))
    return sorted(calls, key=_rank), costs


def _path(
    row: dict[str, Any],
    bars: list[dict[str, Any]],
    costs: Costs,
    through: date,
    *,
    forced: bool = False,
    extra: float = 1.0,
) -> dict[str, Any]:
    signal = row["signal_index"]
    index = next(
        i for i in range(signal + 1, row["end_index"] + 1) if _date(bars[i]["time"]) == through
    )
    return simulate_trade(
        row["pair"],
        bars,
        signal,
        1 if row["direction"] == "BUY" else -1,
        abs(row["entry"] - row["stop"]),
        row["holding_days"] if forced else index - signal,
        costs=costs,
        exit_at_open_index=index if forced else None,
        extra_exit_slippage_pips=extra if forced else 0,
    )


def _close(row: dict[str, Any], path: dict[str, Any]) -> None:
    original_end, original_horizon = row["end_index"], row["holding_days"]
    row.update(path)
    row["end_index"], row["holding_days"] = original_end, original_horizon


def replay_daily_risk(
    pair_reports: list[dict[str, Any]],
    histories: dict[str, list[dict[str, Any]]],
    *,
    evaluation_start: str,
    evaluation_end: str,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "method_version": METHOD,
        "status": "UNAVAILABLE",
        "strategy_qualification": "UNQUALIFIED",
        "continuous_control": "UNQUALIFIED",
        "execution_qualification": "UNQUALIFIED",
        "hedge_qualification": "UNQUALIFIED",
        "executable_forced_exit_return": None,
        "hedge_return": None,
        "return_basis": "MODELLED_DAILY_OHLC_AFTER_ASSUMED_COSTS",
        "maximum_open_positions": 5,
        "maximum_weekly_entries": 5,
        "maximum_correlated_group": 2,
        "weekly_target": [3, 5],
        "correlation_window": WINDOW,
        "minimum_matched_returns": MIN_MATCHED,
        "signed_correlation_threshold": THRESHOLD,
        "cutoff": "Strictly before each review/entry day",
        "priority": (
            "Earlier entry, then original probability descending/null last, then fixed universe"
        ),
        "risk_exit_extra_slippage_pips": [0.0, 1.0, 3.0],
        "displayed_extra_slippage_pips": 1.0,
        "capacity_release": "Strictly after original planned horizon",
        "limitations": LIMITS,
        "accepted": [],
        "skipped": [],
        "daily_reviews": [],
        "exit_requests": [],
        "weekly": [],
    }
    try:
        start, end = _date(evaluation_start), _date(evaluation_end)
        if any(
            isinstance(bar[key], bool)
            for bars in histories.values()
            for bar in bars
            for key in ("open", "high", "low", "close")
        ):
            raise ValueError("Boolean source price")
        histories = {pair: validate_bars(bars) for pair, bars in histories.items()}
        calls, costs = _inputs(pair_reports, histories, start, end)
        series = {pair: return_series(histories[pair]) for pair in PAIRS}
        entries: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for row in calls:
            entries[_date(row["entry_time"])].append(row)
        accepted: list[dict[str, Any]] = []
        active: list[dict[str, Any]] = []
        reserved: list[dict[str, Any]] = []
        skipped, reviews, requests = [], [], []
        counts: Counter[tuple[int, int]] = Counter()
        cache: dict[tuple[str, str, date], dict[str, Any]] = {}
        day = min(entries) if entries else start
        last = max((_date(r["horizon_end_time"]) for r in calls), default=end)
        while day <= last:
            reserved = [r for r in reserved if _date(r["horizon_end_time"]) >= day]
            if not active and not entries.get(day):
                day = _business_day(day, 1)
                continue
            before, before_evidence, unknown = _risk_groups(active, series, day, cache)
            retained: list[dict[str, Any]] = []
            for row in sorted(active, key=_rank):
                groups, evidence, unavailable = _risk_groups(retained + [row], series, day, cache)
                if unavailable or any(len(g) > 2 for g in groups):
                    reason: str | None = (
                        "CORRELATION_UNAVAILABLE" if unavailable else "CORRELATED_GROUP_FULL"
                    )
                    paths = [
                        _path(
                            row,
                            histories[row["pair"]],
                            costs[row["pair"]],
                            day,
                            forced=True,
                            extra=extra,
                        )
                        for extra in (0.0, 1.0, 3.0)
                    ]
                    _close(row, paths[1])
                    row["risk_exit_request_date"], row["risk_exit_reason"] = day.isoformat(), reason
                    row["risk_exit_sensitivity"] = [
                        {
                            "extra_slippage_pips": extra,
                            "gross_r": p["gross_r"],
                            "cost_r": p["cost_r"],
                            "net_r": p["net_r"],
                        }
                        for extra, p in zip((0.0, 1.0, 3.0), paths, strict=True)
                    ]
                    requests.append(
                        {
                            "date": day.isoformat(),
                            "pair": row["pair"],
                            "entry_time": row["entry_time"],
                            "reason": reason,
                            "groups": groups,
                            "correlations": evidence,
                            "modelled_outcome": row["outcome"],
                            "sensitivity": row["risk_exit_sensitivity"],
                        }
                    )
                else:
                    retained.append(row)
            active = retained
            rejected_today = []
            for row in entries.get(day, []):
                groups, evidence, unavailable = _risk_groups(active + [row], series, day, cache)
                week = day.isocalendar()[:2]
                reason = (
                    "PAIR_RESERVED"
                    if any(p["pair"] == row["pair"] for p in reserved)
                    else "CAPACITY_FULL"
                    if len(reserved) >= 5
                    else "WEEKLY_CAP"
                    if counts[week] >= 5
                    else "CORRELATION_UNAVAILABLE"
                    if unavailable
                    else "CORRELATED_GROUP_FULL"
                    if any(len(g) > 2 for g in groups)
                    else None
                )
                if reason:
                    record = {
                        "pair": row["pair"],
                        "entry_time": row["entry_time"],
                        "reason": reason,
                        "groups": groups,
                        "correlations": evidence,
                    }
                    skipped.append(record)
                    rejected_today.append(record)
                else:
                    selected = dict(row)
                    accepted.append(selected)
                    active.append(selected)
                    reserved.append(selected)
                    counts[week] += 1
            after, after_evidence, after_unknown = _risk_groups(active, series, day, cache)
            if after_unknown or any(len(g) > 2 for g in after) or len(active) > 5:
                raise ValueError("Daily post-decision limits failed")
            reviews.append(
                {
                    "date": day.isoformat(),
                    "cutoff_exclusive": day.isoformat(),
                    "state": "MODELLED_DAILY_BOUNDARY_WITHIN_LIMIT",
                    "before_groups": before,
                    "before_correlations": before_evidence,
                    "before_unknown": unknown,
                    "before_breach": any(len(g) > 2 for g in before),
                    "after_groups": after,
                    "after_correlations": after_evidence,
                    "active_pairs_after_decision": [r["pair"] for r in active],
                    "reserved_pairs": [r["pair"] for r in reserved],
                    "currency_direction_counts": currency_legs(active),
                    "rejected_admissions": rejected_today,
                }
            )
            survivors = []
            for row in active:
                path = _path(row, histories[row["pair"]], costs[row["pair"]], day)
                if path["outcome"] != "TIME_EXIT" or day == _date(row["horizon_end_time"]):
                    _close(row, path)
                else:
                    survivors.append(row)
            active = survivors
            day = _business_day(day, 1)
        if active:
            raise ValueError("Incomplete holding paths")
        weekly = _weekly(calls, accepted, start, end)
        complete = [w for w in weekly if w["complete_week"]]
        closing: dict[str, float] = defaultdict(float)
        for row in accepted:
            closing[row["exit_time"]] += row["net_r"]
        total = peak = drawdown = 0.0
        curve = []
        for stamp, amount in sorted(closing.items()):
            total += amount
            peak = max(peak, total)
            drawdown = max(drawdown, peak - total)
            curve.append({"time": stamp, "modelled_net_r": amount, "cumulative_r": total})
        stress = []
        for extra in (0.0, 1.0, 3.0):
            value = sum(
                next(
                    s["net_r"]
                    for s in r["risk_exit_sensitivity"]
                    if s["extra_slippage_pips"] == extra
                )
                if r.get("risk_exit_sensitivity")
                else r["net_r"]
                for r in accepted
            )
            stress.append(
                {
                    "extra_exit_slippage_pips": extra,
                    "modelled_net_r": value,
                    "mean_modelled_net_r": value / len(accepted) if accepted else None,
                }
            )
        return {
            **base,
            "status": "DEVELOPMENT_DAILY_RISK_COUNTERFACTUAL",
            "evaluation_start": start.isoformat(),
            "evaluation_end": end.isoformat(),
            "accepted": accepted,
            "skipped": skipped,
            "daily_reviews": reviews,
            "exit_requests": requests,
            "weekly": weekly,
            "modelled_closed_path_curve": curve,
            "input_call_count": len(calls),
            "accepted_call_count": len(accepted),
            "skipped_call_count": len(skipped),
            "skip_reasons": dict(Counter(r["reason"] for r in skipped)),
            "checked_daily_boundaries": len(reviews),
            "modelled_exit_request_count": len(requests),
            "pre_review_breach_days": sum(r["before_breach"] for r in reviews),
            "unknown_pre_review_days": sum(r["before_unknown"] for r in reviews),
            "post_decision_breach_days": 0,
            "post_decision_unknown_days": 0,
            "complete_week_count": len(complete),
            "weeks_meeting_target": sum(w["target_met"] for w in complete),
            "zero_entry_week_count": sum(w["admitted_research_calls"] == 0 for w in complete),
            "mean_weekly_entries": sum(w["admitted_research_calls"] for w in complete)
            / len(complete)
            if complete
            else None,
            "modelled_net_r": total,
            "mean_modelled_net_r": total / len(accepted) if accepted else None,
            "modelled_closed_path_drawdown_r": drawdown,
            "cost_sensitivity": stress,
        }
    except (KeyError, ValueError, TypeError, OSError, OverflowError, IndexError, StopIteration):
        return {
            **base,
            "reason": "Invalid or incomplete original source paths/costs; no partial study.",
        }


def attach_daily_risk_evidence(report: dict[str, Any]) -> None:
    """Attach a separate exact replay without changing original pair or v1 evidence."""
    try:
        histories = {}
        for item in report["pair_reports"]:
            meta = item["source_metadata"]
            raw = Path(meta["capture_path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                raise ValueError("Pinned source changed")
            histories[item["pair"]] = json.loads(raw)["bars"]
        original = report["correlation_audit"]
        audit = replay_daily_risk(
            report["pair_reports"],
            histories,
            evaluation_start=original["evaluation_start"],
            evaluation_end=original["evaluation_end"],
        )
        audit["source_hashes"] = {
            item["pair"]: item["source_metadata"]["sha256"] for item in report["pair_reports"]
        }
        coverage = {w["week_start"]: w["all_pair_test_coverage"] for w in original["weekly"]}
        for week in audit["weekly"]:
            week["all_pair_test_coverage"] = coverage[week["week_start"]]
        common = [w for w in audit["weekly"] if w["all_pair_test_coverage"]]
        audit["common_coverage_frequency"] = {
            "complete_week_count": len(common),
            "mean_weekly_entries": sum(w["admitted_research_calls"] for w in common) / len(common)
            if common
            else None,
            "weeks_meeting_target": sum(w["target_met"] for w in common),
            "zero_entry_week_count": sum(w["admitted_research_calls"] == 0 for w in common),
            "basis": "Same complete all-pair test weeks as the preserved v1 audit",
        }
        report["daily_risk_audit"] = audit
    except (KeyError, ValueError, TypeError, OSError, OverflowError):
        report["daily_risk_audit"] = {
            "method_version": METHOD,
            "status": "UNAVAILABLE",
            "strategy_qualification": "UNQUALIFIED",
            "limitations": LIMITS,
            "reason": "Incomplete or changed pinned sources/coverage; no partial study.",
        }


def publish_daily_risk(state_dir: Path) -> dict[str, Any]:
    """Publish an offline overlay through the journal and preserve the exact parent."""
    from src.private_desk.report import _publish_report, atomic_json, detach_current_review

    target = state_dir / "report.json"
    parent = target.read_bytes()
    report: dict[str, Any] = json.loads(parent)
    attach_daily_risk_evidence(report)
    if report["daily_risk_audit"]["status"] == "UNAVAILABLE":
        raise ValueError("Original source paths did not qualify for the bounded study")
    if target.read_bytes() != parent:
        raise ValueError("Report changed during the offline daily-risk study")
    digest = hashlib.sha256(parent).hexdigest()
    archive = state_dir / "daily-risk" / f"parent-{digest}.json"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists() and archive.read_bytes() != parent:
        raise ValueError("Immutable parent archive changed")
    if not archive.exists():
        with archive.open("xb") as stream:
            stream.write(parent)
    detach_current_review(
        report, reason="Daily holding-risk inputs changed; prior AI binding preserved."
    )
    report["daily_risk_publication"] = {
        "at": datetime.now(UTC).isoformat(),
        "parent_sha256": digest,
        "parent_path": str(archive),
        "method_version": METHOD,
        "inputs": (
            "Original pinned sources; no network, model call, broker order or production write"
        ),
    }
    artifact = (
        state_dir / "reports" / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-daily-risk-{uuid4().hex}.json"
    )
    atomic_json(artifact, report)
    _publish_report(state_dir, artifact, report)
    return report
