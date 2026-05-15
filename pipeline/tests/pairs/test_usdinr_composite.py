"""Tests for USDINR pair-specific composite scorer."""

from __future__ import annotations

import pytest

from src.pairs.usdinr.composite import USDINRComposite, _compute_usdinr_special


class TestUSDINRComposite:
    def test_all_none_returns_none(self) -> None:
        comp = USDINRComposite()
        assert comp.score(None, None, None, None) is None

    def test_score_with_all_signals(self) -> None:
        comp = USDINRComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0)
        # Base = 1.0*0.25 + 0.5*0.05 = 0.275
        assert result is not None
        assert result == pytest.approx(0.275)

    def test_score_with_missing_signals(self) -> None:
        comp = USDINRComposite()
        result = comp.score(None, None, 1.0, None)
        assert result is not None
        assert result == pytest.approx(0.15)

    def test_regime_conditional_weight_changes(self) -> None:
        neutral = USDINRComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        carry = USDINRComposite(vol_regime="NEUTRAL", rate_regime="CARRY")
        assert carry.weights["rate"] > neutral.weights["rate"]
        assert carry.weights["vol"] < neutral.weights["vol"]

    def test_interaction_terms_effect(self) -> None:
        comp = USDINRComposite()
        result = comp.score(1.0, None, None, None, rbi_reserves=0.5, fpi_flow=0.5)
        # special = mean([0.5, 0.5]) = 0.5
        # interaction: special_rate = 0.5*1.0*0.10 = 0.05
        # base = 1.0*0.25 + 0.5*0.45 = 0.475
        # interaction_boost = 0.05
        # composite = 0.475 + 0.05 * 0.70 = 0.51
        assert result is not None
        assert result == pytest.approx(0.51, abs=0.001)

    def test_rbi_reserves_and_fpi_flow_in_special_signal(self) -> None:
        comp = USDINRComposite()
        result = comp.score(1.0, None, None, None, rbi_reserves=0.5, fpi_flow=0.5, oil=0.5, dxy=0.5)
        # special = mean of all four = 0.5
        assert result is not None
        assert result > 0.25  # base rate only would be 0.25

    def test_special_signal_computation(self) -> None:
        assert _compute_usdinr_special(1.0, 2.0, None, None, None, None) == pytest.approx(1.5)
        assert _compute_usdinr_special(None, None, None, None, None, None) is None

    def test_output_clipping(self) -> None:
        comp = USDINRComposite()
        result = comp.score(5.0, 5.0, 5.0, 5.0, dxy=5.0, oil=5.0)
        assert result is not None
        assert result <= 2.0
