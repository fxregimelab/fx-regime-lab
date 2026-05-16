"""Tests for Round 3 Phase 2 — Aggregate validation statistics."""

from __future__ import annotations

from datetime import date

import pytest

from src.validation.aggregate import (
    _calibration_buckets,
    _compute_horizon,
    _max_drawdown_bps,
    _mean,
    _sharpe_like,
    _std,
)


def test_mean_empty() -> None:
    assert _mean([]) is None


def test_mean_basic() -> None:
    assert _mean([1.0, 2.0, 3.0]) == 2.0


def test_std_empty() -> None:
    assert _std([]) is None
    assert _std([5.0]) is None


def test_std_basic() -> None:
    xs = [0.0, 4.0]
    s = _std(xs)
    assert s is not None
    assert s == 2.0


def test_sharpe_like_none_on_zero_std() -> None:
    assert _sharpe_like([1.0, 1.0, 1.0]) is None


def test_sharpe_like_basic() -> None:
    # mean=0, std=1 -> sharpe=0
    assert _sharpe_like([-1.0, 1.0]) == 0.0


def test_max_drawdown_flat() -> None:
    assert _max_drawdown_bps([0.0, 0.0]) == 0.0


def test_max_drawdown_simple() -> None:
    # +10, -15 -> peak 10, trough -5, dd=15
    assert _max_drawdown_bps([10.0, -15.0]) == 15.0


def test_calibration_buckets_basic() -> None:
    calib = _calibration_buckets([0.1, 0.9], [False, True], n_buckets=2)
    assert "buckets" in calib
    assert len(calib["buckets"]) == 2


def test_compute_horizon_all_hits() -> None:
    rows = [
        {
            "predicted_direction": "BULLISH",
            "confidence": 0.8,
            "actual_direction_t5": "UP",
            "log_return_t5_bps": 12.0,
            "correct_t5": True,
            "brier_score_t5": 0.04,
        },
        {
            "predicted_direction": "BULLISH",
            "confidence": 0.7,
            "actual_direction_t5": "UP",
            "log_return_t5_bps": 8.0,
            "correct_t5": True,
            "brier_score_t5": 0.09,
        },
    ]
    h = _compute_horizon(
        rows, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps", date(2026, 5, 15)
    )
    assert h.total_calls == 2
    assert h.directional_calls == 2
    assert h.wins == 2
    assert h.win_rate == 1.0
    assert h.mean_brier == pytest.approx(0.065, abs=0.001)
    assert h.brier_skill == pytest.approx((0.25 - 0.065) / 0.25, abs=0.001)
    assert h.mean_log_return_bps == 10.0
    assert h.sharpe_like is not None


def test_compute_horizon_with_neutral() -> None:
    rows = [
        {
            "predicted_direction": "NEUTRAL",
            "confidence": 0.5,
            "actual_direction_t5": "NEUTRAL",
            "log_return_t5_bps": 2.0,
            "correct_t5": True,
            "brier_score_t5": None,
        },
        {
            "predicted_direction": "BEARISH",
            "confidence": 0.6,
            "actual_direction_t5": "DOWN",
            "log_return_t5_bps": -15.0,
            "correct_t5": True,
            "brier_score_t5": 0.16,
        },
    ]
    h = _compute_horizon(
        rows, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps", date(2026, 5, 15)
    )
    assert h.total_calls == 2
    assert h.directional_calls == 1
    assert h.wins == 1
    assert h.win_rate == 1.0


def test_compute_horizon_no_rows() -> None:
    h = _compute_horizon(
        [], "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps", date(2026, 5, 15)
    )
    assert h.total_calls == 0
    assert h.directional_calls == 0
    assert h.win_rate is None
    assert h.mean_brier is None

