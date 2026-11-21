"""Exit, leakage and abstention checks for the private research baseline."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Any

import pytest

from src.private_desk.engine import (
    EMBARGO,
    POLICIES,
    Costs,
    _bucket,
    _calibrate,
    _calibration_check,
    _cohort,
    _direction_base_rate,
    _positive_ev_for_policy,
    _reference_signal,
    _signal,
    _summary,
    _window_has_gap,
    analyze_pair,
    analyze_reference_pair,
    simulate_trade,
    validate_bars,
    wilson_interval,
)

NO_COST = Costs(0, 0, 0)


def candles(prices: list[tuple[float, float, float, float]]) -> list[dict[str, Any]]:
    return [
        {"time": f"2020-01-{i + 1:02d}", "open": o, "high": h, "low": low, "close": c}
        for i, (o, h, low, c) in enumerate(prices)
    ]


def history(count: int = 1800) -> list[dict[str, Any]]:
    rng = random.Random(1182)
    result: list[dict[str, Any]] = []
    stamp = datetime(2010, 1, 1)
    close = 1.2
    while len(result) < count:
        if stamp.weekday() < 5:
            opening = close + rng.gauss(0, 0.0002)
            close = max(0.5, opening + rng.gauss(0, 0.004))
            result.append(
                {
                    "time": stamp.date().isoformat(),
                    "open": opening,
                    "high": max(opening, close) + rng.uniform(0.0002, 0.003),
                    "low": min(opening, close) - rng.uniform(0.0002, 0.003),
                    "close": close,
                }
            )
        stamp += timedelta(days=1)
    return result


def test_full_winner_is_two_r_not_three_r() -> None:
    bars = candles([(100, 100, 100, 100), (100, 100.9, 99.5, 100.8), (101, 104, 100.5, 103)])
    trade = simulate_trade("EURUSD", bars, 0, 1, 1, 2, costs=NO_COST)
    assert trade["gross_r"] == 2
    assert trade["tp1_hit"]
    assert trade["outcome"] == "TARGET3"


def test_stop_wins_when_first_target_and_stop_share_bar() -> None:
    bars = candles([(100, 100, 100, 100), (100, 104, 98, 102)])
    trade = simulate_trade("EURUSD", bars, 0, 1, 1, 1, costs=NO_COST)
    assert trade["gross_r"] == -1
    assert trade["ambiguous_bars"] == 1
    assert not trade["tp1_hit"]


def test_first_target_then_entry_stop_realizes_half_r() -> None:
    bars = candles([(100, 100, 100, 100), (100, 102, 99.5, 101)])
    trade = simulate_trade("EURUSD", bars, 0, 1, 1, 1, costs=NO_COST)
    assert trade["gross_r"] == 0.5
    assert trade["outcome"] == "BREAKEVEN"
    assert trade["ambiguous_bars"] == 1


def test_known_open_above_tp1_activates_stop_before_extremes() -> None:
    bars = candles(
        [
            (100, 100, 100, 100),
            (100, 100.9, 99.5, 100.8),
            (102, 102.5, 98.5, 99),
        ]
    )
    trade = simulate_trade("EURUSD", bars, 0, 1, 1, 2, costs=NO_COST)
    assert trade["gross_r"] == 0.5
    assert trade["outcome"] == "BREAKEVEN"


def test_short_exit_is_symmetric() -> None:
    bars = candles([(100, 100, 100, 100), (100, 100.5, 98, 99)])
    trade = simulate_trade("EURUSD", bars, 0, -1, 1, 1, costs=NO_COST)
    assert trade["gross_r"] == 0.5
    assert trade["stop"] == 101
    assert trade["tp1"] == 99


def test_gap_can_lose_more_than_initial_risk() -> None:
    bars = candles(
        [
            (100, 100, 100, 100),
            (100, 100.4, 99.5, 100),
            (98, 98.4, 97.8, 98.2),
        ]
    )
    trade = simulate_trade("EURUSD", bars, 0, 1, 1, 2, costs=NO_COST)
    assert trade["gross_r"] == -2
    assert trade["outcome"] == "STOP_GAP"


def test_breakeven_gap_after_partial_can_be_net_loss() -> None:
    bars = candles(
        [
            (100, 100, 100, 100),
            (100, 100.9, 99.5, 100.8),
            (101, 101.2, 100.5, 101),
            (98, 98.4, 97.8, 98.2),
        ]
    )
    trade = simulate_trade("EURUSD", bars, 0, 1, 1, 3, costs=NO_COST)
    assert trade["gross_r"] == -0.5
    assert trade["outcome"] == "BREAKEVEN_GAP"


def test_flat_price_exit_loses_costs_and_weekend_holding_counts() -> None:
    bars = candles([(1.2, 1.2, 1.2, 1.2)] * 3)
    bars[0]["time"], bars[1]["time"], bars[2]["time"] = ("2020-01-02", "2020-01-03", "2020-01-06")
    trade = simulate_trade("EURUSD", bars, 0, 1, 0.001, 2)
    assert trade["gross_r"] == 0
    assert trade["cost_r"] == pytest.approx((1.2 + 0.4 + 0.15 * 4) / 10)
    assert trade["net_r"] < 0


def test_hourly_holding_cost_is_fractional() -> None:
    bars = [
        {"time": f"2020-01-01T{i:02d}:00:00Z", "open": 1.2, "high": 1.2, "low": 1.2, "close": 1.2}
        for i in range(3)
    ]
    trade = simulate_trade("EURUSD", bars, 0, 1, 0.001, 2, costs=Costs(0, 0, 1), bar_interval="1h")
    assert trade["cost_r"] == pytest.approx(2 / 24 / 10)


@pytest.mark.parametrize("kind", ["nan", "bounds", "duplicate", "reverse", "missing"])
def test_invalid_capture_fails_closed(kind: str) -> None:
    bars = history(900)
    if kind == "nan":
        bars[200]["close"] = math.nan
    elif kind == "bounds":
        bars[200]["high"] = 0.1
    elif kind == "duplicate":
        bars[200]["time"] = bars[199]["time"]
    elif kind == "reverse":
        bars.reverse()
    else:
        del bars[200]["low"]
    report = analyze_pair("EURUSD", bars)
    assert report["candidate"]["status"] == "ABSTAIN"
    assert report["candidate"]["probability"] is None
    assert report["backtest"]["trade_count"] == 0


def test_future_changes_do_not_change_signal() -> None:
    bars = history(180)
    old = _signal(bars, 100, POLICIES[0])
    for bar in bars[101:]:
        for field in ("open", "high", "low", "close"):
            bar[field] *= 2
    assert _signal(bars, 100, POLICIES[0]) == old
    assert _signal(bars[:101], 100, POLICIES[0]) == old


def test_actual_entry_is_next_open_not_signal_close() -> None:
    bars = candles([(99, 100, 98, 99), (101, 101.5, 100.5, 101)])
    result = simulate_trade("EURUSD", bars, 0, 1, 1, 1, costs=NO_COST)
    assert result["entry"] == 101
    assert result["entry_time"] != result["signal_time"]
    assert result["gross_r"] == 0


def test_unmatured_labels_are_rejected() -> None:
    with pytest.raises(ValueError, match="complete future"):
        simulate_trade("EURUSD", history(5), 3, 1, 0.01, 3)


def test_fixed_cohort_excludes_overlaps_and_unmatured_labels() -> None:
    rows = [{"signal_index": i, "end_index": i + 5} for i in range(10)]
    assert [r["signal_index"] for r in _cohort(rows, 0, 12)] == [0, 6]
    assert [r["signal_index"] for r in _cohort(rows, 0, 6)] == [0]


def test_calibration_requires_heldout_samples_and_beats_base_rate() -> None:
    rows = [
        {"predicted_probability": 0.6, "profitable": i % 10 < 6, "training_base_rate": 0.5}
        for i in range(100)
    ]
    assert not _calibration_check(rows[:99])["passes"]
    assert _calibration_check(rows)["passes"]
    for row in rows:
        row["predicted_probability"] = 0.95
    assert not _calibration_check(rows)["passes"]


def test_wilson_intervals_preserve_uncertainty() -> None:
    assert wilson_interval(0, 0) is None
    interval = wilson_interval(7, 10)
    assert interval is not None
    assert interval[0] < 0.7 < interval[1]
    assert interval[0] < 0.5


def test_walk_forward_uses_embargo_and_preserves_prefix_results() -> None:
    bars = history(1810)
    report = analyze_pair("EURUSD", bars)
    shorter = analyze_pair("EURUSD", bars[:1560])
    by_time = {bar["time"]: i for i, bar in enumerate(bars)}
    assert report["backtest"]["folds"]
    assert report["backtest"]["folds"][:2] == shorter["backtest"]["folds"][:2]
    for fold in report["backtest"]["folds"]:
        assert by_time[fold["calibration_start"]] - by_time[fold["train_end"]] > EMBARGO
        assert by_time[fold["test_start"]] - by_time[fold["calibration_end"]] > EMBARGO
    for trade in report["backtest"]["trades"]:
        fold = report["backtest"]["folds"][trade["fold"] - 1]
        assert trade["signal_time"] >= fold["test_start"]
        assert trade["exit_time"] <= fold["test_end"]
    assert report["backtest"]["status"] == "PROVISIONAL_PRICE_ONLY"
    assert report["session"]["status"] == "UNAVAILABLE"
    if not report["backtest"]["calibration"]["passes"]:
        assert report["candidate"]["probability"] is None
        assert report["candidate"]["expected_r"] is None
        assert report["candidate"]["status"] == "ABSTAIN"


def test_unknown_pair_insufficient_or_gappy_history_abstains() -> None:
    assert analyze_pair("USDINR", history(1000))["candidate"]["status"] == "ABSTAIN"
    assert analyze_pair("EURUSD", history(100))["candidate"]["probability"] is None
    bars = history(1000)
    del bars[100:110]
    report = analyze_pair("EURUSD", bars)
    assert report["candidate"]["probability"] is None
    assert report["data_coverage"]["marked_gaps"]
    assert any(row["feature_gap_windows"] > 0 for row in report["backtest"]["excluded_windows"])


def test_validation_does_not_mutate_capture() -> None:
    bars = history(10)
    original = [dict(bar) for bar in bars]
    assert validate_bars(bars) == bars
    assert bars == original


def reference_history(count: int = 1810) -> list[dict[str, Any]]:
    return [{"time": bar["time"], "close": bar["close"]} for bar in history(count)]


def test_short_daily_history_is_explicit_and_does_not_relax_probability_gates() -> None:
    report = analyze_pair("EURUSD", history(500))
    backtest = report["backtest"]
    assert backtest["status"] == "PROVISIONAL_SHORT_HISTORY"
    assert backtest["window_bars"] == {
        "minimum_training": 150,
        "calibration": 150,
        "maximum_test": 80,
        "minimum_training_trades": 12,
    }
    assert backtest["folds"]
    assert backtest["trade_count"] > 0
    assert backtest["calibration"]["passes"] is False
    assert report["candidate"]["probability"] is None
    assert report["candidate"]["expected_r"] is None
    assert report["candidate"]["status"] == "ABSTAIN"


def test_reference_research_has_no_manufactured_ohlc_or_r() -> None:
    reference = reference_history()
    report = analyze_reference_pair("EURUSD", reference)
    assert report["status"] == "PROVISIONAL_REFERENCE_DIRECTIONAL"
    assert report["data_coverage"]["observation_count"] == len(reference)
    assert report["backtest"]["trade_count"] > 100
    assert report["backtest"]["summary"]["directional_hit_ci95"]
    assert report["candidate"]["probability"] is None
    assert "expected_r" not in report["candidate"]
    assert "stop" not in report["candidate"]
    assert all(set(row) == {"time", "close"} for row in report["chart"]["reference_closes"])
    by_time = {row["time"]: i for i, row in enumerate(reference)}
    for trade in report["backtest"]["trades"]:
        assert "net_r" not in trade
        assert by_time[trade["entry_time"]] == by_time[trade["signal_time"]] + 1
        assert by_time[trade["exit_time"]] == (by_time[trade["entry_time"]] + trade["holding_days"])
        assert trade["net_return_bp"] == pytest.approx(trade["gross_return_bp"] - 2)


def test_reference_walkforward_is_chronological_and_prefix_stable() -> None:
    series = reference_history()
    report = analyze_reference_pair("EURUSD", series)
    prefix = analyze_reference_pair("EURUSD", series[:1560])
    assert report["backtest"]["folds"][:2] == prefix["backtest"]["folds"][:2]
    by_time = {row["time"]: i for i, row in enumerate(series)}
    for fold in report["backtest"]["folds"]:
        assert by_time[fold["validation_start"]] - by_time[fold["train_end"]] > EMBARGO
        assert by_time[fold["test_start"]] - by_time[fold["validation_end"]] > EMBARGO
    before = _reference_signal(series, 100, 5, False, 0.5)
    for row in series[101:]:
        row["close"] *= 3
    assert _reference_signal(series, 100, 5, False, 0.5) == before
    assert _reference_signal(series[:101], 100, 5, False, 0.5) == before


@pytest.mark.parametrize("kind", ["nan", "zero", "missing", "duplicate", "reverse", "gap"])
def test_invalid_reference_data_fails_closed(kind: str) -> None:
    series = reference_history(500)
    if kind == "nan":
        series[200]["close"] = math.nan
    elif kind == "zero":
        series[200]["close"] = 0
    elif kind == "missing":
        del series[200]["close"]
    elif kind == "duplicate":
        series[200]["time"] = series[199]["time"]
    elif kind == "reverse":
        series.reverse()
    else:
        del series[100:110]
    report = analyze_reference_pair("EURUSD", series)
    assert report["status"] == "UNAVAILABLE"
    assert report["candidate"]["status"] == "ABSTAIN"
    assert report["candidate"]["probability"] is None


def test_flat_reference_history_abstains_without_invented_statistics() -> None:
    series = [{"time": row["time"], "close": 1.2} for row in history(500)]
    report = analyze_reference_pair("EURUSD", series)
    assert report["backtest"]["trade_count"] == 0
    assert report["backtest"]["summary"]["directional_hit_rate"] is None
    assert report["backtest"]["abstentions"] > 0
    assert report["candidate"]["direction"] is None
    assert report["candidate"]["probability"] is None


def test_short_reference_and_unknown_pair_keep_separate_evidence() -> None:
    assert analyze_reference_pair("USDINR", reference_history(500))["status"] == "UNAVAILABLE"
    assert analyze_reference_pair("EURUSD", reference_history(100))["status"] == "UNAVAILABLE"
    report = analyze_reference_pair("EURGBP", reference_history(500))
    assert report["backtest"]["history_mode"] == "SHORT_HISTORY"
    assert report["candidate"]["probability"] is None


def test_source_marked_gap_is_preserved_and_rejects_daily_cohort() -> None:
    bars = history(500)
    # Dense gaps leave no complete ATR/momentum feature windows anywhere.
    for index in range(0, len(bars), 7):
        bars[index]["gap_before"] = True
    bars[200]["gap_before"] = True
    bars[201]["gap_before"] = False
    normalized = validate_bars(bars)
    assert normalized[200]["gap_before"] is True
    assert normalized[201]["gap_before"] is False
    report = analyze_pair("EURUSD", bars)
    assert report["backtest"]["trade_count"] == 0
    assert report["candidate"]["probability"] is None
    assert bars[200]["time"] in report["data_coverage"]["marked_gaps"]


def test_sparse_gap_quarantine_retains_only_contiguous_features_and_labels() -> None:
    bars = history(1810)
    for index in (100, 470, 850, 1090, 1500):
        bars[index]["gap_before"] = True
    report = analyze_pair("EURUSD", bars)
    assert report["backtest"]["trade_count"] > 0
    assert report["data_coverage"]["marked_gap_count"] == 5
    for trade in report["backtest"]["trades"]:
        assert not _window_has_gap(bars, trade["feature_start_index"], trade["signal_index"])
        assert not _window_has_gap(bars, trade["signal_index"], trade["end_index"])
    exclusions = report["backtest"]["excluded_windows"]
    assert all(row["feature_gap_windows"] > 0 for row in exclusions)
    assert sum(row["signal_holding_gap_windows"] for row in exclusions) > 0


def test_missing_weekday_inferred_even_without_source_marker() -> None:
    bars = history(1810)
    missing_date = bars[850]["time"]
    del bars[850]
    clean = validate_bars(bars)
    assert clean[850]["gap_before"]
    report = analyze_pair("EURUSD", bars)
    assert report["backtest"]["trade_count"] > 0
    assert report["data_coverage"]["marked_gap_count"] == 1
    for trade in report["backtest"]["trades"]:
        assert not (trade["feature_start_time"] < missing_date < trade["exit_time"])


def test_future_holding_gap_excluded_even_when_stop_would_exit_before_gap() -> None:
    bars = candles(
        [
            (100, 100, 100, 100),
            (100, 100.5, 98, 99),
            (99, 100, 98.5, 99),
            (99, 100, 98.5, 99),
        ]
    )
    bars[3]["gap_before"] = True
    with pytest.raises(ValueError, match="Holding label crosses"):
        simulate_trade("EURUSD", bars, 0, 1, 1, 3, costs=NO_COST)
    bars[3]["gap_before"] = False
    bars[3]["time"] = "2020-01-07"
    with pytest.raises(ValueError, match="Holding label crosses"):
        simulate_trade("EURUSD", bars, 0, 1, 1, 3, costs=NO_COST)


def test_feature_gap_boundary_and_latest_candidate_abstention() -> None:
    bars = history(1810)
    # The initial feature close has no dependency on the interval preceding it.
    bars[86]["gap_before"] = True
    assert not _window_has_gap(bars, 86, 100)
    bars[87]["gap_before"] = True
    assert _signal(bars, 100, POLICIES[0]) == (0, 0.0, 0.0)
    bars[-10]["gap_before"] = True
    report = analyze_pair("EURUSD", bars)
    assert report["candidate"]["status"] == "ABSTAIN"
    assert report["candidate"]["direction"] is None
    assert report["candidate"]["probability"] is None
    assert any("Latest feature window" in reason for reason in report["candidate"]["reasons"])


def test_invalid_source_gap_type_fails_closed() -> None:
    bars = history(500)
    bars[100]["gap_before"] = "false"
    assert analyze_pair("EURUSD", bars)["backtest"]["status"] == "UNAVAILABLE"


def test_current_policy_cannot_borrow_other_policies_positive_returns() -> None:
    def outcomes(net_r: float, count: int) -> list[dict[str, Any]]:
        return [
            {
                "net_r": net_r,
                "gross_r": net_r,
                "cost_r": 0,
                "tp1_hit": net_r > 0,
                "ambiguous_bars": 0,
                "actual_bars_held": 3,
            }
            for _index in range(count)
        ]

    comparable_calibration = _summary(outcomes(0.5, 40))
    selected_losses = outcomes(-0.2, 120)
    other_policy_wins = outcomes(2.0, 400)
    adaptive_summary = _summary(selected_losses + other_policy_wins)
    assert adaptive_summary["net_ev_ci95_approx"][0] > 0
    # Strong results elsewhere and a positive recent bucket cannot rescue this policy.
    assert not _positive_ev_for_policy(comparable_calibration, _summary(selected_losses), 120)
    selected_wins = _summary(outcomes(0.5, 120))
    assert not _positive_ev_for_policy(comparable_calibration, selected_wins, 99)
    assert _positive_ev_for_policy(comparable_calibration, selected_wins, 100)


def test_selected_policy_summary_matches_its_own_heldout_trades() -> None:
    report = analyze_pair("EURUSD", history(1810))
    backtest = report["backtest"]
    own = backtest["selected_policy_summary"]
    rows = [row for row in backtest["trades"] if row["policy"] == own["policy"]]
    assert own == {"policy": own["policy"], **_summary(rows)}
    candidate = report["candidate"]
    if candidate.get("policy"):
        assert "BUY/SELL direction" in candidate["probability_conditioning"]
        own_direction = candidate["direction_heldout_evidence"]
        same_direction = [row for row in rows if row["direction"] == candidate["direction"]]
        assert own_direction["summary"] == _summary(same_direction)
        own_cell = candidate["probability_heldout_cell"]
        same_cell = [
            row
            for row in same_direction
            if _bucket(row["strength"]) == candidate["probability_strength_bucket"]
        ]
        assert own_cell["summary"] == _summary(same_cell)
        if not own_cell["calibration"]["passes"]:
            assert candidate["probability"] is None
            assert candidate["probability_direction_specific_validated"] is False


def test_opposite_direction_cannot_supply_calibration_probability_or_samples() -> None:
    rows = [
        {"direction": side, "strength": 1.25, "profitable": side == "SELL"}
        for side in ("BUY", "SELL")
        for _ in range(40)
    ]
    assert sum(bool(row["profitable"]) for row in rows) / len(rows) == 0.5
    probability, matching = _calibrate(rows, 1.25, "BUY")
    assert probability == 0.0 and len(matching) == 40
    assert _calibrate(rows, 1.25, "SELL")[0] == 1.0
    assert _calibrate(rows[20:], 1.25, "BUY")[0] is None
    assert _calibrate(rows, 1.25, "NONE") == (None, [])
    assert _direction_base_rate(rows, "BUY") == 0.0
    assert _direction_base_rate(rows, "SELL") == 1.0
    assert _direction_base_rate(rows, "NONE") is None


def test_strength_bucket_still_requires_twenty_in_its_own_direction() -> None:
    rows = [{"direction": "BUY", "strength": 1.25, "profitable": True} for _ in range(19)]
    rows += [{"direction": "BUY", "strength": 2.0, "profitable": False} for _ in range(30)]
    rows += [{"direction": "SELL", "strength": 1.25, "profitable": True} for _ in range(100)]
    probability, matching = _calibrate(rows, 1.25, "BUY")
    assert probability is None and len(matching) == 19


def test_each_heldout_forecast_uses_its_direction_training_benchmark() -> None:
    backtest = analyze_pair("EURUSD", history())["backtest"]
    folds = {fold["fold"]: fold for fold in backtest["folds"]}
    for row in backtest["trades"]:
        assert (
            row["training_base_rate"]
            == folds[row["fold"]]["direction_training_base_rates"][row["direction"]]
        )
        assert row["probability_conditioning"] == "POLICY_DIRECTION_STRENGTH_BUCKET"
        assert row["exit_time"] <= row["horizon_end_time"]


def test_pooled_calibration_can_mask_failure_of_both_directions() -> None:
    rows = [
        {
            "direction": side,
            "predicted_probability": 0.5,
            "profitable": side == "SELL",
            "training_base_rate": 0.5,
        }
        for side in ("BUY", "SELL")
        for _ in range(100)
    ]
    assert _calibration_check(rows)["passes"] is True
    for side in ("BUY", "SELL"):
        assert (
            _calibration_check([row for row in rows if row["direction"] == side])["passes"] is False
        )
