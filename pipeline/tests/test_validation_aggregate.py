"""Tests for aggregate validation cohort and metric contracts."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest

from src.validation.aggregate import (
    HorizonStats,
    _calibration_buckets,
    _compute_horizon,
    _mean,
    _std,
)


def _t5(rows: list[dict[str, Any]], as_of: date = date(2026, 5, 15)) -> HorizonStats:
    return _compute_horizon(
        rows,
        "T+5",
        "brier_score_t5",
        "correct_t5",
        "log_return_t5_bps",
        as_of,
    )


def test_mean_and_population_std() -> None:
    assert _mean([]) is None
    assert _mean([1.0, 2.0, 3.0]) == 2.0
    assert _std([]) is None
    assert _std([5.0]) is None
    assert _std([0.0, 4.0]) == 2.0


def test_calibration_filters_probability_and_outcome_as_pairs() -> None:
    calibration = _calibration_buckets(
        [0.1, float("nan"), 1.1, 0.9, 0.5],
        [False, True, False, True, None],  # type: ignore[list-item]
        n_buckets=2,
    )

    buckets = calibration["buckets"]
    assert sum(bucket["n"] for bucket in buckets) == 2
    assert [bucket["avg_confidence"] for bucket in buckets] == [0.1, 0.9]
    assert [bucket["observed_accuracy"] for bucket in buckets] == [0.0, 1.0]


def test_mixed_rows_use_only_mature_scored_directional_calls() -> None:
    rows: list[dict[str, object]] = [
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "confidence": 0.8,
            "log_return_t5_bps": 12.0,
            "correct_t5": True,
            "brier_score_t5": 0.04,
        },
        {
            "date": "2026-05-02",
            "predicted_direction": "BEARISH",
            "confidence": 0.7,
            "log_return_t5_bps": 8.0,
            "correct_t5": False,
            "brier_score_t5": 0.49,
        },
        {  # pending because the T+5 trading-day date is after as_of
            "date": "2026-05-12",
            "predicted_direction": "BULLISH",
            "confidence": 0.9,
            "log_return_t5_bps": 20.0,
            "correct_t5": True,
            "brier_score_t5": 0.01,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "NEUTRAL",
            "log_return_t5_bps": 1.0,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "",
            "log_return_t5_bps": 1.0,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "UP",
            "log_return_t5_bps": 1.0,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": None,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 3.0,
            "correct_t5": None,
        },
    ]

    stats = _t5(rows)

    assert stats.total_calls == 8
    assert stats.directional_calls == 2
    assert stats.wins == 1
    assert stats.win_rate == 0.5
    assert stats.mean_brier == pytest.approx(0.265)


def test_net_win_rate_uses_only_rows_with_boolean_net_outcomes() -> None:
    rows = [
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 8.0,
            "correct_t5": True,
            "correct_net_t5": True,
            "log_return_net_bps_t5": 7.5,
            "cost_bps_t5": 0.5,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BEARISH",
            "log_return_t5_bps": -6.0,
            "correct_t5": True,
            "correct_net_t5": False,
            "log_return_net_bps_t5": -7.5,
            "cost_bps_t5": 1.5,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 4.0,
            "correct_t5": True,
            "correct_net_t5": True,
            "log_return_net_bps_t5": None,
            "cost_bps_t5": 0.5,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 4.0,
            "correct_t5": True,
            "correct_net_t5": True,
            "log_return_net_bps_t5": 3.5,
            "cost_bps_t5": None,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 4.0,
            "correct_t5": True,
            "correct_net_t5": True,
            "log_return_net_bps_t5": 3.5,
            "cost_bps_t5": -0.5,
        },
    ]

    stats = _t5(rows)

    assert stats.win_rate == 1.0
    assert stats.net_directional_calls == 2
    assert stats.net_win_rate == 0.5
    assert stats.cost_bps == 1.0
    assert stats.net_win_rate_ci_lower is not None
    assert stats.net_win_rate_ci_upper is not None


def test_as_of_excludes_future_calls_and_bounds_rolling_window() -> None:
    rows = [
        {
            "date": "2026-02-15",  # exact 90-day inclusive cutoff
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 4.0,
            "correct_t5": True,
        },
        {
            "date": "2026-02-14",
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": -4.0,
            "correct_t5": False,
        },
        {
            "date": "2026-05-16",  # after as_of, even though populated
            "predicted_direction": "BULLISH",
            "log_return_t5_bps": 30.0,
            "correct_t5": True,
        },
    ]

    stats = _t5(rows)

    assert stats.total_calls == 2
    assert stats.directional_calls == 2
    assert stats.win_rate == 0.5
    assert stats.rolling_90d_accuracy == 1.0


def test_known_call_date_must_reach_requested_horizon() -> None:
    row = {
        "date": "2026-04-30",
        "predicted_direction": "BULLISH",
        "log_return_t20_bps": 10.0,
        "correct_t20": True,
    }

    stats = _compute_horizon(
        [row],
        "T+20",
        "brier_score_t20",
        "correct_t20",
        "log_return_t20_bps",
        date(2026, 5, 15),
    )

    assert stats.total_calls == 1
    assert stats.directional_calls == 0
    assert stats.win_rate is None


def test_short_calls_report_positive_signed_payoff_when_correct() -> None:
    rows = [
        {
            "date": "2026-05-01",
            "predicted_direction": "BEARISH",
            "log_return_t5_bps": -15.0,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BEARISH",
            "log_return_t5_bps": -5.0,
            "correct_t5": True,
        },
    ]

    stats = _t5(rows)

    assert stats.mean_log_return_bps == 10.0
    assert stats.return_std_bps == 5.0
    assert stats.sharpe_like is None
    assert stats.max_drawdown_bps is None


def test_calibration_excludes_missing_and_invalid_probabilities() -> None:
    rows: list[dict[str, Any]] = [
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "confidence": 0.8,
            "log_return_t5_bps": 10.0,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BEARISH",
            "confidence": None,
            "log_return_t5_bps": -10.0,
            "correct_t5": True,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "confidence": float("inf"),
            "log_return_t5_bps": -10.0,
            "correct_t5": False,
        },
        {
            "date": "2026-05-01",
            "predicted_direction": "BULLISH",
            "confidence": -0.1,
            "log_return_t5_bps": -10.0,
            "correct_t5": False,
        },
    ]

    stats = _t5(rows)
    calibration = json.loads(stats.calibration_json)

    assert stats.directional_calls == 4
    assert sum(bucket["n"] for bucket in calibration["buckets"]) == 1
    assert calibration["buckets"][0]["avg_confidence"] == 0.8
    assert calibration["buckets"][0]["observed_accuracy"] == 1.0


def test_missing_or_malformed_dates_cannot_enter_scored_cohort() -> None:
    stats = _t5(
        [
            {
                "predicted_direction": "BULLISH",
                "log_return_t5_bps": 5.0,
                "correct_t5": True,
            },
            {
                "date": "not-a-date",
                "predicted_direction": "BEARISH",
                "log_return_t5_bps": -5.0,
                "correct_t5": True,
            },
        ]
    )

    assert stats.total_calls == 2
    assert stats.directional_calls == 0
    assert stats.win_rate is None
    assert stats.rolling_90d_accuracy is None


def test_datetime_call_date_is_normalized_before_as_of_comparison() -> None:
    stats = _t5(
        [
            {
                "date": datetime(2026, 5, 1, 16, 30),
                "predicted_direction": "BULLISH",
                "log_return_t5_bps": 5.0,
                "correct_t5": True,
            }
        ]
    )

    assert stats.directional_calls == 1
    assert stats.rolling_90d_accuracy == 1.0


def test_compute_horizon_no_rows() -> None:
    stats = _t5([])
    assert stats.total_calls == 0
    assert stats.directional_calls == 0
    assert stats.win_rate is None
    assert stats.mean_brier is None


def test_horizon_reports_distinct_metric_denominators() -> None:
    stats = _t5(
        [
            {
                "date": "2026-05-01",
                "predicted_direction": "BULLISH",
                "confidence": 0.8,
                "log_return_t5_bps": 5.0,
                "correct_t5": True,
                "correct_net_t5": False,
                "log_return_net_bps_t5": 4.5,
                "cost_bps_t5": 0.5,
                "brier_score_t5": 0.04,
            },
            {
                "date": "2026-05-01",
                "predicted_direction": "UP",
                "log_return_t5_bps": 2.0,
                "correct_t5": True,
            },
            {
                "date": "2026-05-01",
                "predicted_direction": "BEARISH",
                "log_return_t5_bps": None,
                "correct_t5": None,
            },
            {
                "date": "2026-05-01",
                "predicted_direction": "NEUTRAL",
                "log_return_t5_bps": 1.0,
                "correct_t5": None,
            },
            {
                "date": "2026-05-01",
                "predicted_direction": "BEARISH",
                "log_return_t5_bps": -3.0,
                "correct_t5": True,
            },
            {
                "date": "2026-05-12",
                "predicted_direction": "BULLISH",
                "confidence": 0.9,
                "log_return_t5_bps": 9.0,
                "correct_t5": True,
                "brier_score_t5": 0.01,
            },
        ]
    )

    assert stats.total_calls == 6
    assert stats.mature_calls == 5
    assert stats.pending_calls == 1
    assert stats.abstention_calls == 1
    assert stats.unknown_direction_calls == 1
    assert stats.missing_outcome_calls == 1
    assert stats.directional_calls == 2
    assert stats.net_directional_calls == 1
    assert stats.probability_score_calls == 1
    assert stats.calibration_calls == 1
