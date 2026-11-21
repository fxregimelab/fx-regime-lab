"""Fixed overlapping-call audit in research risk units, without account returns."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from src.private_desk.engine import METHOD_VERSION, UNIVERSE
from src.private_desk.universe import LEGACY_PAIRS

PORTFOLIO_VERSION = "private-overlap-v1"
LIMITS = [
    "Counterfactual of held-out price calls, including unqualified forecasts; not approved trades.",
    "One fixed research risk unit per call; no account capital, leverage or percentage return.",
    "Currency occupancy is conservative exclusion, not a measured correlation or hedge.",
    "Capacity stays reserved through the full horizon and is released only on a later date.",
    "Realised close-date drawdown excludes unrealised losses and is not account drawdown.",
    "Provider candles and assumed costs do not establish executable fills, spreads or swaps.",
    "Observed folds are not an untouched validation set after research changes.",
]


def _date(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("Daily date must be a canonical string")
    parsed = date.fromisoformat(value)
    if value != parsed.isoformat() or parsed.weekday() >= 5:
        raise ValueError("Expected a canonical FX weekday")
    return parsed


def _business_day(start: date, steps: int) -> date:
    for _ in range(steps):
        start += timedelta(days=1)
        while start.weekday() >= 5:
            start += timedelta(days=1)
    return start


def _finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Outcome or forecast is not a finite numeric value")
    return float(value)


def _validate_call(pair: str, row: dict[str, Any]) -> None:
    if row.get("pair") != pair or row.get("direction") not in ("BUY", "SELL"):
        raise ValueError("Pair or direction mismatch")
    signal, entry, exit_day, horizon_end = (
        _date(row.get(key))
        for key in ("signal_time", "entry_time", "exit_time", "horizon_end_time")
    )
    horizon = row.get("holding_days")
    if type(horizon) is not int or horizon not in (3, 5):
        raise ValueError("Unknown holding horizon")
    if entry != _business_day(signal, 1) or horizon_end != _business_day(signal, horizon):
        raise ValueError("Contradictory next-open or full-horizon boundary")
    if not entry <= exit_day <= horizon_end:
        raise ValueError("Exit outside holding horizon")
    if row.get("probability_conditioning") != "POLICY_DIRECTION_STRENGTH_BUCKET":
        raise ValueError("Forecast uses an unknown conditioning method")
    probability = row.get("predicted_probability")
    if probability is not None and not 0 <= _finite(probability) <= 1:
        raise ValueError("Probability outside unit interval")
    net, gross, costs = (_finite(row.get(key)) for key in ("net_r", "gross_r", "cost_r"))
    if costs < 0 or not math.isclose(net, gross - costs, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("Inconsistent cost-adjusted outcome")
    if not isinstance(row.get("policy"), str) or not row["policy"]:
        raise ValueError("Missing fold-time policy")


def replay_portfolio(pair_reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Select using only fold-time forecasts; book outcomes only after selection."""
    base: dict[str, Any] = {
        "method_version": PORTFOLIO_VERSION,
        "source_method": METHOD_VERSION,
        "strategy_qualification": "UNQUALIFIED",
        "maximum_open_positions": 2,
        "risk_units_per_position": 1,
        "currency_rule": "No repeated currency in open reserved positions, in either direction.",
        "priority": "Fold-time probability descending, null last, then fixed universe order.",
        "capacity_release": "Strictly after the full planned horizon date.",
        "drawdown_basis": "REALISED_CLOSE_DATE_R_ONLY",
        "account_drawdown": None,
        "limitations": LIMITS,
    }
    try:
        names = [item["pair"] for item in pair_reports]
        if len(names) != len(set(names)) or set(names) not in (set(UNIVERSE), set(LEGACY_PAIRS)):
            raise ValueError("Expected each private pair exactly once")
        calls: list[dict[str, Any]] = []
        identities: set[tuple[str, str]] = set()
        missing = []
        for item in pair_reports:
            backtest = item.get("backtest", {})
            rows = backtest.get("trades", [])
            if not isinstance(rows, list):
                raise ValueError("Malformed held-out calls")
            if not rows:
                missing.append(item["pair"])
            elif backtest.get("method_version") != METHOD_VERSION:
                raise ValueError("Recalculate the old price method before portfolio replay")
            for row in rows:
                _validate_call(item["pair"], row)
                identity = (item["pair"], row["entry_time"])
                if identity in identities:
                    raise ValueError("Duplicate pair entry identity")
                identities.add(identity)
                calls.append(row)
    except (ValueError, TypeError, KeyError, OverflowError):
        return {
            **base,
            "status": "UNAVAILABLE",
            "reason": "Invalid or incompatible held-out inputs; no partial replay accepted.",
            "accepted": [],
            "skipped": [],
            "realised_curve": [],
        }

    def priority(row: dict[str, Any]) -> tuple[str, float, int]:
        forecast = row["predicted_probability"]
        return (
            row["entry_time"],
            -float(forecast) if forecast is not None else 1.0,
            UNIVERSE.index(row["pair"]),
        )

    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    reserved: list[dict[str, Any]] = []
    exposures = []
    for row in sorted(calls, key=priority):
        reserved = [
            position for position in reserved if position["horizon_end_time"] >= row["entry_time"]
        ]
        currencies = {row["pair"][:3], row["pair"][3:]}
        occupied = {
            currency
            for position in reserved
            for currency in (position["pair"][:3], position["pair"][3:])
        }
        reason = (
            "CURRENCY_OCCUPIED"
            if currencies & occupied
            else "CAPACITY_FULL"
            if len(reserved) >= 2
            else None
        )
        if reason:
            skipped.append(
                {
                    "pair": row["pair"],
                    "entry_time": row["entry_time"],
                    "policy": row["policy"],
                    "reason": reason,
                    "blocked_by_pairs": [position["pair"] for position in reserved],
                }
            )
            continue
        accepted.append(dict(row))
        reserved.append(row)
        exposures.append(
            {
                "entry_time": row["entry_time"],
                "reserved_positions": len(reserved),
                "reserved_pairs": [position["pair"] for position in reserved],
                "currencies": sorted(occupied | currencies),
                "initial_risk_units_reserved": len(reserved),
            }
        )

    closing: dict[str, float] = defaultdict(float)
    for row in accepted:
        closing[row["exit_time"]] += row["net_r"]
    cumulative, peak, drawdown = 0.0, 0.0, 0.0
    curve = []
    for day, value in sorted(closing.items()):
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = max(drawdown, peak - cumulative)
        curve.append({"time": day, "realised_net_r": value, "cumulative_r": cumulative})
    worst = sorted(float(row["net_r"]) for row in accepted)
    tail_count = max(1, math.ceil(len(worst) * 0.05))
    return {
        **base,
        "status": "PROVISIONAL_INCOMPLETE" if missing else "PROVISIONAL_OVERLAP_AUDIT",
        "missing_pair_calls": missing,
        "input_call_count": len(calls),
        "accepted_call_count": len(accepted),
        "skipped_call_count": len(skipped),
        "skip_reasons": dict(Counter(row["reason"] for row in skipped)),
        "unavailable_probability_call_count": sum(
            row["predicted_probability"] is None for row in accepted
        ),
        "realised_net_r": cumulative,
        "realised_close_drawdown_r": drawdown,
        "worst_observed_call_r": worst[0] if worst else None,
        "worst_five_percent_call_mean_r": sum(worst[:tail_count]) / tail_count if worst else None,
        "tail_call_count": min(len(worst), tail_count),
        "net_profitable_call_rate": sum(row["net_r"] > 0 for row in accepted) / len(accepted)
        if accepted
        else None,
        "accepted": accepted,
        "skipped": skipped,
        "exposure_events": exposures,
        "realised_curve": curve,
    }
