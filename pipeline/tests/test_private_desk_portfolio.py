"""Outcome leakage, full-horizon occupancy and realised-risk controls."""

from copy import deepcopy
from typing import Any

import pytest

from src.private_desk.engine import METHOD_VERSION, UNIVERSE
from src.private_desk.portfolio import replay_portfolio


def call(
    pair: str,
    *,
    signal: str = "2023-01-04",
    entry: str = "2023-01-05",
    end: str = "2023-01-09",
    exit_day: str | None = None,
    probability: float | None = None,
    net: float = -1.1,
) -> dict[str, Any]:
    return {
        "pair": pair,
        "signal_time": signal,
        "entry_time": entry,
        "exit_time": exit_day or end,
        "horizon_end_time": end,
        "holding_days": 3,
        "direction": "BUY",
        "policy": "trend5_125_h3",
        "predicted_probability": probability,
        "probability_conditioning": "POLICY_DIRECTION_STRENGTH_BUCKET",
        "net_r": net,
        "gross_r": net + 0.1,
        "cost_r": 0.1,
    }


def reports(*rows: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pair": pair,
            "backtest": {
                "method_version": METHOD_VERSION,
                "trades": [row for row in rows if row["pair"] == pair],
            },
        }
        for pair in UNIVERSE
    ]


def test_currency_collision_and_null_priority_use_no_realised_outcomes() -> None:
    rows = reports(
        call("EURUSD", probability=0.7),
        call("GBPUSD", probability=0.8),
        call("EURGBP", probability=None),
    )
    result = replay_portfolio(rows)
    assert [row["pair"] for row in result["accepted"]] == ["GBPUSD"]
    assert result["skip_reasons"] == {"CURRENCY_OCCUPIED": 2}
    changed = deepcopy(rows)
    for item in changed:
        for row in item["backtest"]["trades"]:
            row["net_r"], row["gross_r"] = 1.9, 2.0
    again = replay_portfolio(changed)
    assert [row["pair"] for row in again["accepted"]] == ["GBPUSD"]
    assert again["skipped"] == result["skipped"]
    assert again["exposure_events"] == result["exposure_events"]


def test_ties_and_missing_probabilities_use_fixed_universe_order() -> None:
    result = replay_portfolio(list(reversed(reports(call("GBPUSD"), call("EURUSD")))))
    assert [row["pair"] for row in result["accepted"]] == ["EURUSD"]
    assert result["unavailable_probability_call_count"] == 1
    assert result["strategy_qualification"] == "UNQUALIFIED"


def test_opposite_currency_directions_are_not_assumed_to_hedge() -> None:
    second = call("USDCHF", probability=0.6)
    second["direction"] = "SELL"
    result = replay_portfolio(reports(call("EURUSD", probability=0.8), second))
    assert result["accepted_call_count"] == 1
    assert result["skipped"][0]["reason"] == "CURRENCY_OCCUPIED"


def test_two_disjoint_pairs_and_same_date_closes_are_net_settled() -> None:
    result = replay_portfolio(
        reports(
            call("EURGBP", probability=0.7, net=-1.1),
            call("AUDUSD", probability=0.6, net=1.1),
            call("USDCHF", probability=0.5),
        )
    )
    assert result["accepted_call_count"] == 2
    assert result["realised_curve"] == [
        {"time": "2023-01-09", "realised_net_r": 0.0, "cumulative_r": 0.0}
    ]
    assert result["realised_close_drawdown_r"] == 0
    assert result["worst_observed_call_r"] == -1.1
    assert result["worst_five_percent_call_mean_r"] == -1.1
    assert result["tail_call_count"] == 1
    assert result["account_drawdown"] is None
    assert result["exposure_events"][-1]["reserved_positions"] == 2


def test_early_exit_cannot_release_capacity_before_full_horizon_or_same_date() -> None:
    initial = call("EURUSD", exit_day="2023-01-05")
    boundary = call("GBPUSD", signal="2023-01-06", entry="2023-01-09", end="2023-01-11")
    later = call("GBPUSD", signal="2023-01-09", entry="2023-01-10", end="2023-01-12")
    result = replay_portfolio(reports(initial, boundary, later))
    assert [(row["pair"], row["entry_time"]) for row in result["accepted"]] == [
        ("EURUSD", "2023-01-05"),
        ("GBPUSD", "2023-01-10"),
    ]
    assert result["skipped"][0]["entry_time"] == "2023-01-09"
    # Change the stop date without changing the planned release date: selection is identical.
    initial["exit_time"] = "2023-01-09"
    again = replay_portfolio(reports(initial, boundary, later))
    assert again["skipped"] == result["skipped"]
    assert again["exposure_events"] == result["exposure_events"]


def test_chronological_prefix_decisions_do_not_change_when_later_calls_added() -> None:
    rows = [call("EURUSD"), call("EURGBP", probability=0.6)]
    before = replay_portfolio(reports(*rows))
    rows.append(
        call(
            "AUDUSD",
            signal="2023-01-10",
            entry="2023-01-11",
            end="2023-01-13",
            probability=0.99,
            net=1.9,
        )
    )
    after = replay_portfolio(reports(*rows))
    assert after["accepted"][: len(before["accepted"])] == before["accepted"]
    assert after["skipped"] == before["skipped"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("entry_time", "2023-01-07"),
        ("entry_time", "2023-01-06"),
        ("entry_time", "2023-01-05T00:00:00Z"),
        ("horizon_end_time", None),
        ("horizon_end_time", "2023-01-10"),
        ("exit_time", "2023-01-10"),
        ("exit_time", "2023-01-04"),
        ("holding_days", True),
        ("holding_days", 20),
        ("pair", "USDJPY"),
        ("direction", "HOLD"),
        ("predicted_probability", 1.1),
        ("predicted_probability", "0.7"),
        ("predicted_probability", True),
        ("predicted_probability", float("nan")),
        ("net_r", float("inf")),
        ("cost_r", -0.1),
        ("gross_r", 2.0),
        ("policy", None),
        ("probability_conditioning", "POOLED"),
    ],
)
def test_malformed_call_rejects_whole_replay(key: str, value: Any) -> None:
    row = call("EURUSD")
    packet = reports(row, call("EURGBP"))
    row[key] = value
    result = replay_portfolio(packet)
    assert result["status"] == "UNAVAILABLE"
    assert result["accepted"] == []
    assert result["realised_curve"] == []


def test_old_method_duplicate_call_and_missing_pair_fail_closed() -> None:
    packet = reports(call("EURUSD"))
    packet[0]["backtest"]["method_version"] = "POOLED_OLD"
    assert replay_portfolio(packet)["status"] == "UNAVAILABLE"
    row = call("EURUSD")
    assert replay_portfolio(reports(row, deepcopy(row)))["status"] == "UNAVAILABLE"
    assert replay_portfolio(reports(row)[:-1])["status"] == "UNAVAILABLE"


def test_empty_pair_evidence_is_visible_without_invented_success() -> None:
    result = replay_portfolio(reports())
    assert result["status"] == "PROVISIONAL_INCOMPLETE"
    assert result["missing_pair_calls"] == list(UNIVERSE)
    assert result["accepted_call_count"] == 0
    assert result["net_profitable_call_rate"] is None
