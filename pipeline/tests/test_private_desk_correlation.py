"""Risk admission cannot use future returns, realised winners or forced weekly entries."""

import math
from copy import deepcopy
from datetime import date, timedelta
from typing import Any

import pytest

from src.private_desk.correlation import (
    currency_legs,
    lagged_correlation,
    replay_correlated_portfolio,
    return_series,
)
from src.private_desk.engine import METHOD_VERSION
from src.private_desk.portfolio import _business_day
from src.private_desk.universe import PAIRS


def histories(*, identical: bool = False) -> dict[str, list[dict[str, Any]]]:
    output = {}
    for index, pair in enumerate(PAIRS):
        bars = []
        day, close = date(2022, 8, 1), 150.0 if pair == "USDJPY" else 1.2
        for i in range(160):
            delta = math.sin(2 * math.pi * i * (1 if identical else index + 1) / 60) * 0.005
            close *= math.exp(delta)
            bars.append({"time": day.isoformat(), "close": close})
            day = _business_day(day, 1)
        output[pair] = bars
    return output


def call(
    pair: str,
    *,
    entry: str = "2023-01-02",
    direction: str = "BUY",
    probability: float | None = None,
) -> dict[str, Any]:
    day = date.fromisoformat(entry)
    signal = day - timedelta(days=1)
    while signal.weekday() >= 5:
        signal -= timedelta(days=1)
    end = _business_day(signal, 3).isoformat()
    return {
        "pair": pair,
        "signal_time": signal.isoformat(),
        "entry_time": entry,
        "exit_time": end,
        "horizon_end_time": end,
        "holding_days": 3,
        "direction": direction,
        "policy": "test-only",
        "predicted_probability": probability,
        "probability_conditioning": "POLICY_DIRECTION_STRENGTH_BUCKET",
        "gross_r": 0.5,
        "cost_r": 0.1,
        "net_r": 0.4,
    }


def reports(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pair": p,
            "backtest": {
                "method_version": METHOD_VERSION,
                "trades": [r for r in rows if r["pair"] == p],
            },
        }
        for p in PAIRS
    ]


def replay(rows: list[dict[str, Any]], *, identical: bool = False) -> dict[str, Any]:
    return replay_correlated_portfolio(
        reports(rows),
        histories(identical=identical),
        evaluation_start="2023-01-02",
        evaluation_end="2023-01-20",
    )


def test_signed_correlation_blocks_third_same_risk_but_allows_offset() -> None:
    rows = [call(p) for p in PAIRS[:3]]
    result = replay(rows, identical=True)
    assert result["accepted_call_count"] == 2
    assert result["skip_reasons"] == {"CORRELATED_GROUP_FULL": 1}
    rows[-1]["direction"] = "SELL"
    offset = replay(rows, identical=True)
    assert offset["accepted_call_count"] == 3
    assert offset["hedge_qualification"] == "UNQUALIFIED"


def test_five_open_cap_and_outcome_independent_ranking() -> None:
    rows = [call(p, probability=0.8 - i * 0.01) for i, p in enumerate(PAIRS[:6])]
    original = replay(rows)
    assert original["accepted_call_count"] == 5
    assert original["skip_reasons"] == {"CAPACITY_FULL": 1}
    changed = deepcopy(rows)
    for i, row in enumerate(changed):
        row["net_r"] = float(i * 10 - 10)
        row["gross_r"] = row["net_r"] + row["cost_r"]
    again = replay(changed)
    assert [r["pair"] for r in original["accepted"]] == [r["pair"] for r in again["accepted"]]
    assert original["exposure_events"] == again["exposure_events"]
    assert original["skipped"] == again["skipped"]


def test_weekly_cap_applies_after_earlier_positions_mature() -> None:
    rows = [call(p) for p in PAIRS[:5]] + [call("USDJPY", entry="2023-01-05")]
    result = replay(rows)
    assert result["accepted_call_count"] == 5
    assert result["skip_reasons"] == {"WEEKLY_CAP": 1}
    assert result["weekly"][0]["admitted_research_calls"] == 5


def test_zero_weeks_are_counted_and_no_trade_quota_is_filled() -> None:
    result = replay([call("EURUSD")])
    assert len(result["weekly"]) == result["complete_week_count"] == 3
    assert result["zero_entry_week_count"] == 2
    assert result["weeks_meeting_target"] == 0
    assert result["weekly"][0]["shortfall_to_three"] == 2
    assert result["accepted_call_count"] == 1


def test_every_future_and_same_signal_date_price_is_excluded() -> None:
    source = histories(identical=True)
    rows = reports([call(p) for p in PAIRS[:3]])
    before = replay_correlated_portfolio(
        rows, source, evaluation_start="2023-01-02", evaluation_end="2023-01-20"
    )
    changed = deepcopy(source)
    for bars in changed.values():
        for i, row in enumerate(bars):
            if row["time"] >= "2022-12-30":
                row["close"] = 1000 + i * 300
    after = replay_correlated_portfolio(
        rows, changed, evaluation_start="2023-01-02", evaluation_end="2023-01-20"
    )
    for key in ("accepted", "skipped", "exposure_events", "weekly"):
        assert before[key] == after[key]


def test_later_correlation_drift_is_reported_without_hindsight_exit() -> None:
    source = histories()
    for pair in PAIRS[:3]:
        for row in source[pair]:
            if row["time"] == "2023-01-02":
                row["close"] *= math.exp(1.0)
    result = replay_correlated_portfolio(
        reports([call(p) for p in PAIRS[:3]]),
        source,
        evaluation_start="2023-01-02",
        evaluation_end="2023-01-20",
    )
    assert result["accepted_call_count"] == 3
    assert result["dynamic_group_audit"]["breach_day_count"] > 0
    assert result["dynamic_group_audit"]["continuous_group_control"] == "UNQUALIFIED"
    assert all(r["exit_time"] == "2023-01-04" for r in result["accepted"])


def test_sparse_constant_and_stale_correlation_cannot_assume_independence() -> None:
    source = histories()
    first = return_series(source["EURUSD"])
    assert lagged_correlation(first, first, date(2023, 1, 2))["correlation"] == pytest.approx(1)
    assert (
        lagged_correlation({d: 0.0 for d in first}, first, date(2023, 1, 2))["correlation"] is None
    )
    assert (
        lagged_correlation(dict(list(first.items())[:20]), first, date(2023, 1, 2))["correlation"]
        is None
    )
    assert lagged_correlation(first, first, date(2024, 1, 2))["correlation"] is None
    source["GBPUSD"] = source["GBPUSD"][-10:]
    result = replay_correlated_portfolio(
        reports([call("EURUSD"), call("GBPUSD")]),
        source,
        evaluation_start="2023-01-02",
        evaluation_end="2023-01-20",
    )
    assert result["skip_reasons"] == {"CORRELATION_UNAVAILABLE": 1}


def test_missing_weekday_and_quarantine_returns_are_excluded() -> None:
    bars = [
        {"time": "2023-01-02", "close": 1.0},
        {"time": "2023-01-04", "close": 2.0},
        {"time": "2023-01-05", "close": 3.0, "gap_before": True},
        {"time": "2023-01-06", "close": 4.0},
    ]
    assert return_series(bars) == {date(2023, 1, 6): math.log(4 / 3)}


def test_currency_direction_counts_do_not_claim_equal_notional_hedge() -> None:
    legs = currency_legs([call("EURUSD"), call("USDJPY")])
    assert legs["USD"] == {"long": 1, "short": 1, "net": 0}
    assert legs["JPY"]["net"] == -1


def test_wrong_universe_or_duplicate_call_refuses_partial_results() -> None:
    row = call("EURUSD")
    assert replay([row, deepcopy(row)])["status"] == "UNAVAILABLE"
    source = histories()
    source.pop("USDJPY")
    result = replay_correlated_portfolio(
        reports([row]), source, evaluation_start="2023-01-02", evaluation_end="2023-01-20"
    )
    assert result["status"] == "UNAVAILABLE" and result["accepted"] == []
