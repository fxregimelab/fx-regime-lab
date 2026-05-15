"""Tests for EURUSD pair-specific composite scorer."""

from __future__ import annotations

import pytest

from src.pairs.eurusd.composite import EURUSDComposite, _compute_eurusd_special


class TestEURUSDComposite:
    def test_all_none_returns_none(self) -> None:
        comp = EURUSDComposite()
        assert comp.score(None, None, None, None) is None

    def test_score_with_all_signals(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0)
        # Base = 1.0*0.45 + 0.5*0.20 + 0.0*0.15 + 0.0*0.10 = 0.55
        # interaction rate_cot = 1.0*0.5*0.15 = 0.075
        # wsum = 0.45+0.20+0.15+0.10 = 0.90
        # composite = 0.55 + 0.075 * 0.90 = 0.6175
        assert result is not None
        assert result == pytest.approx(0.6175, abs=0.0001)

    def test_score_with_missing_signals(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, None, None, None)
        assert result is not None
        assert result == pytest.approx(0.45)

    def test_regime_conditional_weight_changes(self) -> None:
        neutral = EURUSDComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        trending = EURUSDComposite(vol_regime="TRENDING", rate_regime="NEUTRAL")
        assert trending.weights["rate"] > neutral.weights["rate"]
        assert trending.weights["vol"] < neutral.weights["vol"]

    def test_interaction_terms_effect(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0, ecb_bs_trajectory=0.5, bund_btp_spread=0.5)
        # special = mean([0.5, 0.5]) = 0.5
        # interactions: rate_cot = 1.0*0.5*0.15 = 0.075, special_rate = 0.5*1.0*0.10 = 0.05
        # base = 1.0*0.45 + 0.5*0.20 + 0.0*0.15 + 0.0*0.10 + 0.5*0.10 = 0.60
        # interaction_boost = 0.075 + 0.05 = 0.125
        # composite = 0.60 + 0.125 * 1.0 = 0.725
        assert result is not None
        assert result == pytest.approx(0.725, abs=0.001)

    def test_special_signal_computation(self) -> None:
        assert _compute_eurusd_special(None, None, None) is None
        assert _compute_eurusd_special(1.0, 2.0, None) == pytest.approx(1.5)

    def test_output_clipping(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(5.0, 5.0, 5.0, 5.0, ecb_bs_trajectory=5.0)
        assert result is not None
        assert result <= 2.0
