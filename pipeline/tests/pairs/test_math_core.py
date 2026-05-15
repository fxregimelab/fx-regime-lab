"""Tests for src.pairs.math_core."""

from __future__ import annotations

import numpy as np
import pytest

from src.pairs.math_core import (
    REGIME_MULTIPLIERS,
    apply_regime_adjustment,
    clip_composite,
    compute_expected_value,
    compute_interaction_terms,
    correlation_adjusted_size,
    kelly_fraction,
    normalize_weights,
    pair_specific_thresholds,
)

# ---------------------------------------------------------------------------
# compute_interaction_terms
# ---------------------------------------------------------------------------


class TestComputeInteractionTerms:
    def test_all_none_returns_zeros(self) -> None:
        result = compute_interaction_terms(None, None, None, None, None)
        assert result == {"rate_cot": 0.0, "vol_oi": 0.0, "special_rate": 0.0}

    def test_partial_none(self) -> None:
        result = compute_interaction_terms(1.0, None, 2.0, None, 3.0)
        assert result["rate_cot"] == 0.0
        assert result["vol_oi"] == 0.0
        assert result["special_rate"] == pytest.approx(0.3)

    def test_full_inputs(self) -> None:
        result = compute_interaction_terms(1.0, 2.0, 3.0, 4.0, 5.0)
        assert result["rate_cot"] == pytest.approx(0.3)
        assert result["vol_oi"] == pytest.approx(1.2)
        assert result["special_rate"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# apply_regime_adjustment
# ---------------------------------------------------------------------------


class TestApplyRegimeAdjustment:
    @pytest.mark.parametrize("regime", list(REGIME_MULTIPLIERS.keys()))
    def test_each_regime_renormalizes(self, regime: str) -> None:
        base = {"rate": 0.5, "cot": 0.3, "vol": 0.2}
        adjusted = apply_regime_adjustment(base, regime, "NEUTRAL")
        total = sum(adjusted.values())
        assert total == pytest.approx(1.0)

    def test_high_vol_dominates(self) -> None:
        base = {"rate": 0.5, "vol": 0.5}
        adjusted = apply_regime_adjustment(base, "HIGH_VOL", "TRENDING")
        # HIGH_VOL has priority over TRENDING
        assert adjusted["vol"] > adjusted["rate"]

    def test_zero_sum_returns_base(self) -> None:
        base = {"rate": 0.0, "cot": 0.0}
        adjusted = apply_regime_adjustment(base, "TRENDING", "NEUTRAL")
        assert adjusted == base

    def test_unknown_regime_fallback(self) -> None:
        base = {"rate": 0.5, "cot": 0.5}
        adjusted = apply_regime_adjustment(base, "UNKNOWN", "ALSO_UNKNOWN")
        total = sum(adjusted.values())
        assert total == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# kelly_fraction
# ---------------------------------------------------------------------------


class TestKellyFraction:
    def test_typical(self) -> None:
        result = kelly_fraction(0.6, 30.0, 20.0)
        # Kelly is capped at max_risk=0.01
        b = 30.0 / 20.0
        q = 0.4
        raw = (0.6 * b - q) / b * 0.25
        expected = min(raw, 0.01)
        assert result == pytest.approx(expected)

    def test_zero_loss_returns_zero(self) -> None:
        assert kelly_fraction(0.6, 30.0, 0.0) == 0.0

    def test_zero_win(self) -> None:
        result = kelly_fraction(0.6, 0.0, 20.0)
        assert result == 0.0

    def test_negative_kelly_capped_at_zero(self) -> None:
        result = kelly_fraction(0.3, 10.0, 20.0)
        assert result == 0.0

    def test_max_risk_cap(self) -> None:
        result = kelly_fraction(0.9, 100.0, 1.0, max_risk=0.005)
        assert result <= 0.005

    def test_win_rate_zero(self) -> None:
        assert kelly_fraction(0.0, 30.0, 20.0) == 0.0


# ---------------------------------------------------------------------------
# pair_specific_thresholds
# ---------------------------------------------------------------------------


class TestPairSpecificThresholds:
    @pytest.mark.parametrize(
        "pair,expected_conviction",
        [
            ("EURUSD", 3),
            ("USDJPY", 3),
            ("USDINR", 4),
        ],
    )
    def test_known_pairs(self, pair: str, expected_conviction: int) -> None:
        thresholds = pair_specific_thresholds(pair)
        assert thresholds["conviction_enter_min"] == expected_conviction

    def test_unknown_pair_fallback(self) -> None:
        thresholds = pair_specific_thresholds("GBPUSD")
        # Falls back to EURUSD defaults
        assert thresholds["conviction_enter_min"] == 3

    def test_slash_normalized(self) -> None:
        assert pair_specific_thresholds("EUR/USD") == pair_specific_thresholds("EURUSD")


# ---------------------------------------------------------------------------
# correlation_adjusted_size
# ---------------------------------------------------------------------------


class TestCorrelationAdjustedSize:
    def test_no_correlation_unchanged(self) -> None:
        result = correlation_adjusted_size(1.0, "EURUSD", {}, {})
        assert result == pytest.approx(1.0)

    def test_moderate_corr_reduces_to_85(self) -> None:
        portfolio = {"USDJPY": 0.5}
        corr = {"EURUSD": {"USDJPY": 0.8}}
        result = correlation_adjusted_size(1.0, "EURUSD", portfolio, corr)
        # exposure = 0.8 * 0.5 = 0.4  →  unchanged (<=0.3 threshold check: 0.4 > 0.3, so *0.85)
        assert result == pytest.approx(0.85)

    def test_high_corr_reduces_to_70(self) -> None:
        portfolio = {"USDJPY": 1.0}
        corr = {"EURUSD": {"USDJPY": 0.8}}
        result = correlation_adjusted_size(1.0, "EURUSD", portfolio, corr)
        # exposure = 0.8 * 1.0 = 0.8 > 0.5
        assert result == pytest.approx(0.70)

    def test_no_portfolio_unchanged(self) -> None:
        corr = {"EURUSD": {"USDJPY": 0.99}}
        result = correlation_adjusted_size(1.0, "EURUSD", {}, corr)
        assert result == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_expected_value
# ---------------------------------------------------------------------------


class TestComputeExpectedValue:
    @pytest.mark.parametrize(
        "conviction,mult",
        [
            (1, 0.5),
            (2, 0.7),
            (3, 1.0),
            (4, 1.2),
            (5, 1.4),
            (99, 1.0),  # unknown conviction
        ],
    )
    def test_conviction_levels(self, conviction: int, mult: float) -> None:
        ev = compute_expected_value(0.5, 20.0, 10.0, conviction, "NEUTRAL")
        gross = 0.5 * 20.0 - 0.5 * 10.0
        assert ev == pytest.approx(gross * mult)

    def test_negative_ev(self) -> None:
        ev = compute_expected_value(0.2, 10.0, 20.0, 3, "NEUTRAL")
        assert ev < 0

    def test_regime_param_unused(self) -> None:
        ev1 = compute_expected_value(0.5, 20.0, 10.0, 3, "NEUTRAL")
        ev2 = compute_expected_value(0.5, 20.0, 10.0, 3, "TRENDING")
        assert ev1 == ev2


# ---------------------------------------------------------------------------
# clip_composite
# ---------------------------------------------------------------------------


class TestClipComposite:
    def test_in_bounds_scalar(self) -> None:
        assert clip_composite(1.5) == pytest.approx(1.5)
        assert clip_composite(-1.5) == pytest.approx(-1.5)

    def test_out_of_bounds_scalar(self) -> None:
        assert clip_composite(3.0) == pytest.approx(2.0)
        assert clip_composite(-3.0) == pytest.approx(-2.0)

    def test_array(self) -> None:
        arr = np.array([-5.0, -1.0, 0.0, 1.5, 5.0])
        clipped = clip_composite(arr)
        expected = np.array([-2.0, -1.0, 0.0, 1.5, 2.0])
        np.testing.assert_array_almost_equal(clipped, expected)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# normalize_weights
# ---------------------------------------------------------------------------


class TestNormalizeWeights:
    def test_normal(self) -> None:
        weights = {"a": 1.0, "b": 1.0, "c": 2.0}
        norm = normalize_weights(weights)
        assert sum(norm.values()) == pytest.approx(1.0)
        assert norm["c"] == pytest.approx(0.5)

    def test_zero_sum(self) -> None:
        weights = {"a": 0.0, "b": 0.0}
        norm = normalize_weights(weights)
        assert norm == weights

    def test_empty(self) -> None:
        weights: dict[str, float] = {}
        norm = normalize_weights(weights)
        assert norm == {}

    def test_negative_values(self) -> None:
        weights = {"a": -1.0, "b": 2.0}
        norm = normalize_weights(weights)
        assert sum(norm.values()) == pytest.approx(1.0)
