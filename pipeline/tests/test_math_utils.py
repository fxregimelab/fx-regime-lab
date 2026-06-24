"""Tests for src/logic/math_utils.py helpers."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.logic.math_utils import (
    hysteresis_tier_composite,
    log_return_series,
    momentum_last,
    rolling_zscore_last,
    rolling_zscore_series,
)


class TestRollingZscoreSeries:
    def test_window_less_than_two_raises(self) -> None:
        with pytest.raises(ValueError, match="window must be >= 2"):
            rolling_zscore_series([1.0, 2.0, 3.0], 1)

    def test_empty_array_returns_empty(self) -> None:
        result = rolling_zscore_series([], 5)
        assert result.size == 0

    def test_first_window_points_are_nan(self) -> None:
        series = rolling_zscore_series([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        assert np.isnan(series[:3]).all()

    def test_constant_series_returns_nan(self) -> None:
        series = rolling_zscore_series([5.0, 5.0, 5.0, 5.0, 5.0], 3)
        assert np.isnan(series).all()

    def test_linear_series_zscore(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        series = rolling_zscore_series(values, 3)
        last = series[-1]
        assert not np.isnan(last)

    def test_nan_input_propagates(self) -> None:
        values = [1.0, 2.0, np.nan, 4.0, 5.0]
        series = rolling_zscore_series(values, 2)
        assert np.isnan(series[2])

    def test_min_periods_reduces_requirement(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        series = rolling_zscore_series(values, 5, min_periods=2)
        # Index 6 has a causal window of 5 points (indices 1-5).
        assert not np.isnan(series[6])


class TestRollingZscoreLast:
    def test_empty_returns_none(self) -> None:
        assert rolling_zscore_last([], 5) is None

    def test_undefined_returns_none(self) -> None:
        assert rolling_zscore_last([1.0, 1.0, 1.0], 3) is None

    def test_defined_returns_float(self) -> None:
        result = rolling_zscore_last([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        assert isinstance(result, float)
        assert not math.isnan(result)


class TestMomentumLast:
    def test_lag_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="lag must be >= 1"):
            momentum_last([1.0, 2.0, 3.0], 0)

    def test_insufficient_data_returns_none(self) -> None:
        assert momentum_last([1.0, 2.0], 3) is None

    def test_nan_at_end_returns_none(self) -> None:
        assert momentum_last([1.0, 2.0, np.nan, 4.0], 1) is None

    def test_simple_momentum(self) -> None:
        result = momentum_last([1.0, 2.0, 3.0, 4.0], 2)
        assert result == pytest.approx(2.0)

    def test_negative_momentum(self) -> None:
        result = momentum_last([5.0, 4.0, 3.0, 2.0], 1)
        assert result == pytest.approx(-1.0)


class TestLogReturnSeries:
    def test_insufficient_data_returns_empty(self) -> None:
        result = log_return_series([100.0])
        assert result.size == 0

    def test_simple_log_return(self) -> None:
        result = log_return_series([100.0, 110.0])
        assert result[0] == pytest.approx(math.log(1.1))

    def test_non_positive_price_returns_nan(self) -> None:
        result = log_return_series([100.0, 0.0, 110.0])
        assert np.isnan(result[0])
        assert np.isnan(result[1])

    def test_nan_price_returns_nan(self) -> None:
        result = log_return_series([100.0, np.nan, 110.0])
        assert np.isnan(result[0])
        assert np.isnan(result[1])


class TestHysteresisTierComposite:
    def test_no_prior_tier_snaps_directly(self) -> None:
        assert hysteresis_tier_composite(1.5, None) == 4
        assert hysteresis_tier_composite(0.7, None) == 3
        assert hysteresis_tier_composite(0.0, None) == 2
        assert hysteresis_tier_composite(-0.7, None) == 1
        assert hysteresis_tier_composite(-1.5, None) == 0

    def test_large_jump_overrides_hysteresis(self) -> None:
        assert hysteresis_tier_composite(1.5, 0) == 4
        assert hysteresis_tier_composite(-1.5, 4) == 0

    def test_strong_bull_holds_at_0dot85(self) -> None:
        assert hysteresis_tier_composite(0.85, 4) == 4

    def test_strong_bull_releases_below_0dot85(self) -> None:
        assert hysteresis_tier_composite(0.84, 4) == 3

    def test_strong_bear_holds_at_minus_0dot85(self) -> None:
        assert hysteresis_tier_composite(-0.85, 0) == 0

    def test_strong_bear_releases_above_minus_0dot85(self) -> None:
        assert hysteresis_tier_composite(-0.84, 0) == 1

    def test_tier_3_to_4_threshold(self) -> None:
        assert hysteresis_tier_composite(1.01, 3) == 4

    def test_tier_3_to_neutral_below_0dot28(self) -> None:
        assert hysteresis_tier_composite(0.27, 3) == 2

    def test_tier_1_to_0_threshold(self) -> None:
        assert hysteresis_tier_composite(-1.01, 1) == 0

    def test_tier_1_to_neutral_above_minus_0dot28(self) -> None:
        assert hysteresis_tier_composite(-0.27, 1) == 2

    def test_tier_2_deadband(self) -> None:
        assert hysteresis_tier_composite(0.1, 2) == 2
        assert hysteresis_tier_composite(-0.1, 2) == 2

    def test_invalid_prior_tier_treated_as_none(self) -> None:
        assert hysteresis_tier_composite(0.7, -1) == 3
        assert hysteresis_tier_composite(0.7, 99) == 3
