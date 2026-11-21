"""Lagged directional-risk and weekly-throughput research, without trade approval."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from src.private_desk.engine import METHOD_VERSION
from src.private_desk.portfolio import _business_day, _date, _validate_call
from src.private_desk.universe import PAIRS

METHOD = "private-correlation-v1"
WINDOW = 60
MIN_MATCHED = 40
THRESHOLD = 0.70
LIMITS = [
    "Historical price calls include unqualified forecasts; admission is not trade approval.",
    "Lagged daily returns lack verified historical receipt and common executable close clocks.",
    "Correlation can change in stress; measured grouping does not bound future losses.",
    "Currency legs count directions, not equal currency notionals or account exposures.",
    "Realised-close R excludes unrealised losses; it is not account drawdown.",
    "No hedge is qualified; two-leg executable costs and independent evaluation remain required.",
    "Examined historical folds remain development evidence after this method change.",
]


def return_series(bars: list[dict[str, Any]]) -> dict[date, float]:
    """Never fill prices or calculate a return across a missing weekday."""
    result: dict[date, float] = {}
    previous: date | None = None
    last_close = 0.0
    for row in bars:
        day = _date(row["time"])
        value = row["close"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Invalid return price")
        close = float(value)
        if not math.isfinite(close) or close <= 0 or (previous is not None and day <= previous):
            raise ValueError("Invalid return series")
        if "gap_before" in row and type(row["gap_before"]) is not bool:
            raise ValueError("Invalid return gap marker")
        if previous is not None and day == _business_day(previous, 1) and not row.get("gap_before"):
            result[day] = math.log(close / last_close)
        previous, last_close = day, close
    return result


def lagged_correlation(
    first: dict[date, float], second: dict[date, float], cutoff: date, *, window: int = WINDOW
) -> dict[str, Any]:
    common = sorted(day for day in first.keys() & second.keys() if day < cutoff)
    # Bound elapsed history as well as observation count; sparse old points are not recent evidence.
    common = [day for day in common if (cutoff - day).days <= window * 2][-window:]
    base: dict[str, Any] = {
        "observations": len(common),
        "window": window,
        "cutoff_exclusive": cutoff.isoformat(),
        "last_observation": common[-1].isoformat() if common else None,
        "correlation": None,
        "status": "UNAVAILABLE",
    }
    floor = (
        MIN_MATCHED if window == WINDOW else 15 if window == 20 else max(MIN_MATCHED, window // 2)
    )
    if len(common) < floor or (cutoff - common[-1]).days > 7:
        return {**base, "reason": "Insufficient recent matched returns"}
    x, y = [first[d] for d in common], [second[d] for d in common]
    if not all(math.isfinite(v) for v in x + y):
        return {**base, "reason": "Invalid matched returns"}
    mx, my = sum(x) / len(x), sum(y) / len(y)
    xx = sum((v - mx) ** 2 for v in x)
    yy = sum((v - my) ** 2 for v in y)
    if xx <= 1e-24 or yy <= 1e-24:
        return {**base, "reason": "Constant or numerically degenerate returns"}
    rho = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / math.sqrt(xx * yy)
    return {**base, "status": "DESCRIPTIVE", "correlation": max(-1.0, min(1.0, rho))}


def _sign(row: dict[str, Any]) -> int:
    return 1 if row["direction"] == "BUY" else -1


def currency_legs(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for row in rows:
        for currency, sign in ((row["pair"][:3], _sign(row)), (row["pair"][3:], -_sign(row))):
            legs = result.setdefault(currency, {"long": 0, "short": 0, "net": 0})
            legs["long" if sign > 0 else "short"] += 1
            legs["net"] += sign
    return result


def _risk_groups(
    rows: list[dict[str, Any]],
    series: dict[str, dict[date, float]],
    cutoff: date,
    cache: dict[tuple[str, str, date], dict[str, Any]],
) -> tuple[list[list[str]], list[dict[str, Any]], bool]:
    links: dict[str, set[str]] = {row["pair"]: set() for row in rows}
    observations: list[dict[str, Any]] = []
    unknown = False
    for i, first in enumerate(rows):
        for second in rows[i + 1 :]:
            a, b = sorted((first["pair"], second["pair"]))
            key = (a, b, cutoff)
            if key not in cache:
                cache[key] = lagged_correlation(series[a], series[b], cutoff)
            evidence = cache[key]
            rho = evidence["correlation"]
            signed = None if rho is None else rho * _sign(first) * _sign(second)
            observations.append(
                {"pairs": [first["pair"], second["pair"]], **evidence, "signed_correlation": signed}
            )
            if signed is None:
                unknown = True
            elif signed >= THRESHOLD:
                links[first["pair"]].add(second["pair"])
                links[second["pair"]].add(first["pair"])
    groups: list[list[str]] = []
    remaining = set(links)
    while remaining:
        seed = min(remaining)
        component, stack = {seed}, [seed]
        while stack:
            for other in links[stack.pop()] - component:
                component.add(other)
                stack.append(other)
        remaining -= component
        groups.append(sorted(component))
    return groups, observations, unknown


def _weekly(
    calls: list[dict[str, Any]], accepted: list[dict[str, Any]], start: date, end: date
) -> list[dict[str, Any]]:
    offered = Counter(_date(row["entry_time"]).isocalendar()[:2] for row in calls)
    admitted = Counter(_date(row["entry_time"]).isocalendar()[:2] for row in accepted)
    monday = start - timedelta(days=start.weekday())
    weeks = []
    while monday <= end:
        key = monday.isocalendar()[:2]
        count = admitted[key]
        full = start <= monday and monday + timedelta(days=4) <= end
        weeks.append(
            {
                "week": f"{key[0]}-W{key[1]:02d}",
                "week_start": monday.isoformat(),
                "complete_week": full,
                "offered_research_calls": offered[key],
                "admitted_research_calls": count,
                "shortfall_to_three": max(0, 3 - count),
                "target_met": 3 <= count <= 5,
            }
        )
        monday += timedelta(days=7)
    return weeks


def _daily_group_audit(
    accepted: list[dict[str, Any]],
    series: dict[str, dict[date, float]],
    cache: dict[tuple[str, str, date], dict[str, Any]],
) -> dict[str, Any]:
    """Measure later group drift; do not invent a hindsight exit or hedge."""
    active: list[dict[str, Any]] = []
    entries: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        entries[_date(row["entry_time"])].append(row)
    breaches, unknown_days = [], []
    checked = 0
    for day in sorted({d for row in accepted for d in _holding_dates(row)}):
        active = [r for r in active if _date(r["horizon_end_time"]) >= day]
        active.extend(entries[day])
        groups, evidence, unknown = _risk_groups(active, series, day, cache)
        checked += 1
        if unknown:
            unknown_days.append(day.isoformat())
        if any(len(group) > 2 for group in groups):
            breaches.append({"date": day.isoformat(), "groups": groups, "correlations": evidence})
    return {
        "checked_open_weekdays": checked,
        "breach_day_count": len(breaches),
        "unknown_day_count": len(unknown_days),
        "breaches": breaches,
        "unknown_dates": unknown_days,
        "continuous_group_control": "UNQUALIFIED",
        "action": "Diagnostic only; no rebalancing or retrospective replacement exit is assumed.",
    }


def _holding_dates(row: dict[str, Any]) -> list[date]:
    day, end = _date(row["entry_time"]), _date(row["horizon_end_time"])
    days = []
    while day <= end:
        days.append(day)
        day = _business_day(day, 1)
    return days


def replay_correlated_portfolio(
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
        "maximum_open_positions": 5,
        "maximum_weekly_entries": 5,
        "weekly_target": [3, 5],
        "maximum_correlated_group": 2,
        "correlation_window": WINDOW,
        "minimum_matched_returns": MIN_MATCHED,
        "signed_correlation_threshold": THRESHOLD,
        "hedge_qualification": "UNQUALIFIED",
        "priority": "Signal-date probability descending, null last, then fixed universe order.",
        "capacity_release": "Strictly after the full planned horizon date.",
        "drawdown_basis": "REALISED_CLOSE_DATE_R_ONLY",
        "limitations": LIMITS,
        "accepted": [],
        "skipped": [],
        "weekly": [],
        "realised_curve": [],
    }
    try:
        start, end = _date(evaluation_start), _date(evaluation_end)
        if start > end or (end - start).days > 365 * 100:
            raise ValueError("Invalid evaluation span")
        names = [row["pair"] for row in pair_reports]
        if len(names) != len(PAIRS) or set(names) != set(PAIRS) or set(histories) != set(PAIRS):
            raise ValueError("Incomplete universe")
        series = {pair: return_series(histories[pair]) for pair in PAIRS}
        calls: list[dict[str, Any]] = []
        identities: set[tuple[str, str]] = set()
        for item in pair_reports:
            backtest = item["backtest"]
            if backtest.get("method_version") != METHOD_VERSION:
                raise ValueError("Unsupported price method")
            for row in backtest["trades"]:
                _validate_call(item["pair"], row)
                identity = row["pair"], row["entry_time"]
                if identity in identities or not start <= _date(row["entry_time"]) <= end:
                    raise ValueError("Duplicate or out-of-range call")
                identities.add(identity)
                calls.append(row)
    except (ValueError, KeyError, TypeError, OverflowError):
        return {**base, "reason": "Invalid or incomplete research inputs; no partial replay."}

    def priority(row: dict[str, Any]) -> tuple[str, float, int]:
        p = row["predicted_probability"]
        return row["entry_time"], -p if p is not None else 1.0, PAIRS.index(row["pair"])

    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    reserved: list[dict[str, Any]] = []
    events = []
    counts: Counter[tuple[int, int]] = Counter()
    cache: dict[tuple[str, str, date], dict[str, Any]] = {}
    for row in sorted(calls, key=priority):
        entry, signal = _date(row["entry_time"]), _date(row["signal_time"])
        reserved = [p for p in reserved if p["horizon_end_time"] >= row["entry_time"]]
        week = entry.isocalendar()[:2]
        groups, observations, unknown = _risk_groups(reserved + [row], series, signal, cache)
        reason = (
            "PAIR_ALREADY_OPEN"
            if any(p["pair"] == row["pair"] for p in reserved)
            else "CAPACITY_FULL"
            if len(reserved) >= 5
            else "WEEKLY_CAP"
            if counts[week] >= 5
            else "CORRELATION_UNAVAILABLE"
            if unknown
            else "CORRELATED_GROUP_FULL"
            if any(len(g) > 2 for g in groups)
            else None
        )
        if reason:
            skipped.append(
                {
                    "pair": row["pair"],
                    "entry_time": row["entry_time"],
                    "reason": reason,
                    "groups": groups,
                    "correlations": observations,
                }
            )
            continue
        accepted.append(dict(row))
        reserved.append(row)
        counts[week] += 1
        events.append(
            {
                "entry_time": row["entry_time"],
                "cutoff_exclusive": signal.isoformat(),
                "reserved_positions": len(reserved),
                "reserved_pairs": [p["pair"] for p in reserved],
                "groups": groups,
                "correlations": observations,
                "currency_legs": currency_legs(reserved),
            }
        )
    weekly = _weekly(calls, accepted, start, end)
    full = [w for w in weekly if w["complete_week"]]
    closing: dict[str, float] = defaultdict(float)
    for row in accepted:
        closing[row["exit_time"]] += row["net_r"]
    curve = []
    total = peak = drawdown = 0.0
    for day, amount in sorted(closing.items()):
        total += amount
        peak = max(peak, total)
        drawdown = max(drawdown, peak - total)
        curve.append({"time": day, "realised_net_r": amount, "cumulative_r": total})
    dynamic = _daily_group_audit(accepted, series, cache)
    return {
        **base,
        "status": "DESCRIPTIVE_CORRELATION_REPLAY",
        "accepted": accepted,
        "skipped": skipped,
        "exposure_events": events,
        "weekly": weekly,
        "dynamic_group_audit": dynamic,
        "realised_curve": curve,
        "evaluation_start": start.isoformat(),
        "evaluation_end": end.isoformat(),
        "input_call_count": len(calls),
        "accepted_call_count": len(accepted),
        "skipped_call_count": len(skipped),
        "skip_reasons": dict(Counter(r["reason"] for r in skipped)),
        "complete_week_count": len(full),
        "zero_entry_week_count": sum(w["admitted_research_calls"] == 0 for w in full),
        "weeks_meeting_target": sum(w["target_met"] for w in full),
        "mean_weekly_entries": sum(w["admitted_research_calls"] for w in full) / len(full)
        if full
        else None,
        "realised_net_r": total,
        "realised_close_drawdown_r": drawdown,
        "mean_net_r": total / len(accepted) if accepted else None,
        "net_positive_rate": sum(r["net_r"] > 0 for r in accepted) / len(accepted)
        if accepted
        else None,
        "unavailable_probability_call_count": sum(
            r["predicted_probability"] is None for r in accepted
        ),
    }


def correlation_snapshot(
    histories: dict[str, list[dict[str, Any]]], cutoff: str
) -> list[dict[str, Any]]:
    series = {p: return_series(histories[p]) for p in PAIRS}
    return [
        {
            "pairs": [a, b],
            **lagged_correlation(series[a], series[b], _date(cutoff)),
            "short_window": lagged_correlation(series[a], series[b], _date(cutoff), window=20),
            "long_window": lagged_correlation(series[a], series[b], _date(cutoff), window=250),
        }
        for i, a in enumerate(PAIRS)
        for b in PAIRS[i + 1 :]
    ]
