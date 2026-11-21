"""Daily controls preserve frozen calls and never borrow tomorrow's candle."""

import math
from copy import deepcopy
from dataclasses import asdict
from datetime import date
from typing import Any

import pytest

from src.private_desk.correlation import replay_correlated_portfolio
from src.private_desk.engine import METHOD_VERSION, Costs, simulate_trade, validate_bars
from src.private_desk.portfolio import _business_day
from src.private_desk.risk_control import replay_daily_risk
from src.private_desk.universe import PAIRS


def history(*, identical: bool = False, drift: bool = False) -> dict[str, list[dict[str, Any]]]:
    output = {}
    for k, pair in enumerate(PAIRS):
        bars = []
        day, close = date(2022, 8, 1), 150.0 if pair == "USDJPY" else 1.2
        for i in range(160):
            opened = close
            delta = math.sin(2 * math.pi * i * (1 if identical else k + 1) / 60) * 0.005
            if drift and day == date(2023, 1, 2) and k < 3:
                delta = 0.10
            close *= math.exp(delta)
            bars.append(
                {
                    "time": day.isoformat(),
                    "open": opened,
                    "high": max(opened, close) * 1.00001,
                    "low": min(opened, close) * 0.99999,
                    "close": close,
                }
            )
            day = _business_day(day, 1)
        output[pair] = validate_bars(bars)
    return output


def rows(
    prices: dict[str, list[dict[str, Any]]],
    pairs: tuple[str, ...] = PAIRS[:3],
    *,
    entry: str = "2023-01-02",
    horizon: int = 3,
) -> list[dict[str, Any]]:
    result = []
    for pair in pairs:
        bars = prices[pair]
        signal = next(i for i, bar in enumerate(bars) if bar["time"] == entry) - 1
        trade = simulate_trade(pair, bars, signal, 1, bars[signal + 1]["open"] * 0.8, horizon)
        trade.update(
            {
                "horizon_end_time": bars[signal + horizon]["time"],
                "policy": "test-only",
                "predicted_probability": None,
                "probability_conditioning": "POLICY_DIRECTION_STRENGTH_BUCKET",
            }
        )
        result.append(trade)
    return result


def reports(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pair": pair,
            "backtest": {
                "method_version": METHOD_VERSION,
                "assumptions": {"costs": asdict(Costs())},
                "trades": [r for r in calls if r["pair"] == pair],
            },
        }
        for pair in PAIRS
    ]


def replay(calls: list[dict[str, Any]], prices: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return replay_daily_risk(
        reports(calls), prices, evaluation_start="2023-01-02", evaluation_end="2023-01-20"
    )


def test_old_drift_is_red_and_daily_counterfactual_requests_one_exit() -> None:
    prices = history(drift=True)
    calls = rows(prices)
    old = replay_correlated_portfolio(
        reports(calls), prices, evaluation_start="2023-01-02", evaluation_end="2023-01-20"
    )
    assert old["accepted_call_count"] == 3
    assert old["dynamic_group_audit"]["breach_day_count"] > 0
    original = deepcopy(calls)
    new = replay(calls, prices)
    assert new["status"] == "DEVELOPMENT_DAILY_RISK_COUNTERFACTUAL"
    assert new["accepted_call_count"] == 3
    assert new["modelled_exit_request_count"] == 1
    assert new["exit_requests"][0]["pair"] == "AUDUSD"
    assert new["exit_requests"][0]["date"] == "2023-01-03"
    assert new["post_decision_breach_days"] == new["post_decision_unknown_days"] == 0
    assert calls == original
    assert new["continuous_control"] == new["execution_qualification"] == "UNQUALIFIED"
    assert new["executable_forced_exit_return"] is None and new["hedge_return"] is None
    assert (
        new["cost_sensitivity"][0]["modelled_net_r"] > new["cost_sensitivity"][1]["modelled_net_r"]
    )
    assert (
        new["cost_sensitivity"][1]["modelled_net_r"] > new["cost_sensitivity"][2]["modelled_net_r"]
    )


def test_same_day_entry_cutoff_rejects_new_third_link() -> None:
    prices = history(drift=True)
    calls = rows(prices, PAIRS[:2]) + rows(prices, PAIRS[2:3], entry="2023-01-03")
    result = replay(calls, prices)
    assert result["accepted_call_count"] == 2
    assert result["skip_reasons"] == {"CORRELATED_GROUP_FULL": 1}
    assert result["modelled_exit_request_count"] == 0


def test_later_path_change_cannot_change_earlier_exit_decision() -> None:
    prices = history(drift=True)
    calls = rows(prices)
    first = replay(calls, prices)
    changed = deepcopy(prices)
    for pair in PAIRS[:3]:
        for bar in changed[pair]:
            if bar["time"] >= "2023-01-03":
                bar["high"] = max(bar["open"], bar["close"]) * 8
    second = replay(rows(changed), changed)
    keys = ("date", "pair", "reason", "groups", "correlations")
    assert [{k: r[k] for k in keys} for r in first["exit_requests"]] == [
        {k: r[k] for k in keys} for r in second["exit_requests"]
    ]
    assert first["exit_requests"][0]["sensitivity"] == second["exit_requests"][0]["sensitivity"]


def test_source_gap_crossing_a_holding_path_fails_closed() -> None:
    prices = history(drift=True)
    calls = rows(prices)
    for pair in PAIRS[:3]:
        for bar in prices[pair]:
            if bar["time"] == "2023-01-02":
                bar["gap_before"] = True
    # A gap crossing a holding path is rejected, not silently treated as a valid exit.
    result = replay(calls, prices)
    assert result["status"] == "UNAVAILABLE" and result["accepted"] == []


def test_unknown_held_edge_reduces_modelled_set_and_preserves_pair_reservation() -> None:
    prices = history()
    index = next(i for i, bar in enumerate(prices["EURUSD"]) if bar["time"] == "2023-01-02")
    for pair in PAIRS[:2]:
        previous = 1.2
        for i, bar in enumerate(prices[pair]):
            close = 1.21 if i >= index - 60 else 1.2
            bar.update(
                open=previous,
                close=close,
                low=min(previous, close) * 0.99999,
                high=max(previous, close) * 1.00001,
            )
            previous = close
    calls = rows(prices, PAIRS[:2]) + rows(prices, PAIRS[1:3], entry="2023-01-03")
    result = replay(calls, prices)
    assert result["status"] == "DEVELOPMENT_DAILY_RISK_COUNTERFACTUAL"
    assert result["accepted_call_count"] == 2
    assert result["modelled_exit_request_count"] == 1
    assert result["exit_requests"][0]["reason"] == "CORRELATION_UNAVAILABLE"
    assert result["exit_requests"][0]["pair"] == "GBPUSD"
    assert result["skip_reasons"] == {"PAIR_RESERVED": 1, "CORRELATION_UNAVAILABLE": 1}
    review = next(r for r in result["daily_reviews"] if r["date"] == "2023-01-03")
    assert review["before_unknown"] is True
    assert review["reserved_pairs"] == ["EURUSD", "GBPUSD"]
    assert review["active_pairs_after_decision"] == ["EURUSD"]


def test_reserved_slots_survive_risk_exit_and_no_replacement_for_weekly_quota() -> None:
    prices = history(drift=True)
    calls = rows(prices, PAIRS[:5]) + rows(prices, PAIRS[5:6], entry="2023-01-03")
    result = replay(calls, prices)
    assert result["accepted_call_count"] == 5
    assert result["skip_reasons"] == {"CAPACITY_FULL": 1}
    third = next(r for r in result["daily_reviews"] if r["date"] == "2023-01-03")
    assert len(third["reserved_pairs"]) == 5
    assert len(third["active_pairs_after_decision"]) < 5
    assert result["zero_entry_week_count"] > 0


@pytest.mark.parametrize("key,value", [("net_r", 99), ("signal_index", True), ("entry", 99)])
def test_corrupted_original_path_fails_closed(key: str, value: Any) -> None:
    prices = history()
    calls = rows(prices)
    calls[0][key] = value
    result = replay(calls, prices)
    assert result["status"] == "UNAVAILABLE" and not result["accepted"]


def test_legacy_default_simulation_is_unchanged_by_optional_exit() -> None:
    prices = history()
    calls = rows(prices)
    result = replay(calls, prices)
    assert result["modelled_exit_request_count"] == 0
    assert result["accepted"] == calls


def bars_for_exit(pair: str = "EURUSD") -> list[dict[str, Any]]:
    scale = 100 if pair == "USDJPY" else 1
    values = [
        (1, 1.02, 0.98, 1),
        (1, 1.15, 1.01, 1.12),
        (1.15, 9, 0.01, 1),
        (1.10, 1.15, 1.09, 1.12),
    ]
    return [
        {
            "time": _business_day(date(2023, 1, 5), i).isoformat(),
            **{
                k: v * scale
                for k, v in zip(("open", "high", "low", "close"), values[i], strict=True)
            },
        }
        for i in range(len(values))
    ]


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY"])
def test_partial_exit_open_ignores_extremes_and_scales_remaining_cost(pair: str) -> None:
    bars = bars_for_exit(pair)
    risk = 10 if pair == "USDJPY" else 0.1
    default = simulate_trade(pair, bars, 0, 1, risk, 3)
    assert default["outcome"] == "BREAKEVEN"  # Daily extreme would otherwise stop the runner.
    result = simulate_trade(
        pair, bars, 0, 1, risk, 3, exit_at_open_index=2, extra_exit_slippage_pips=3
    )
    zero = simulate_trade(pair, bars, 0, 1, risk, 3, exit_at_open_index=2)
    assert result["outcome"] == "RISK_EXIT_AT_OPEN" and result["tp1_hit"]
    assert result["gross_r"] == pytest.approx(1.25)
    assert result["cost_r"] - zero["cost_r"] == pytest.approx(0.0015)
    # Friday entry incurs one day, Monday adds three days at the half position.
    assert zero["cost_r"] == pytest.approx((1.2 + 0.4 + 0.15 * 2.5) * 0.001)


@pytest.mark.parametrize(
    "opened,outcome,gross", [(0.95, "BREAKEVEN_GAP", 0.25), (1.4, "TARGET3", 2.0)]
)
def test_natural_open_gap_keeps_priority(opened: float, outcome: str, gross: float) -> None:
    bars = bars_for_exit()
    bars[2]["open"] = opened
    result = simulate_trade("EURUSD", bars, 0, 1, 0.1, 3, exit_at_open_index=2)
    assert result["outcome"] == outcome and result["gross_r"] == pytest.approx(gross)


def test_initial_stop_gap_can_lose_more_than_one_r() -> None:
    bars = bars_for_exit()
    bars[1].update(high=1.01, low=0.99, close=1.0)
    bars[2]["open"] = 0.7
    result = simulate_trade("EURUSD", bars, 0, 1, 0.1, 3, exit_at_open_index=2)
    assert result["outcome"] == "STOP_GAP" and result["gross_r"] == pytest.approx(-3)


@pytest.mark.parametrize(
    "index,extra", [(1, 0), (4, 0), (True, 0), (2, -1), (2, float("nan")), (None, 1), (2, True)]
)
def test_invalid_risk_exit_requests_are_rejected(index: Any, extra: float) -> None:
    with pytest.raises(ValueError):
        simulate_trade(
            "EURUSD",
            bars_for_exit(),
            0,
            1,
            0.1,
            3,
            exit_at_open_index=index,
            extra_exit_slippage_pips=extra,
        )
