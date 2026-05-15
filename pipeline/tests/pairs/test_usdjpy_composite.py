"""Tests for USDJPY pair-specific composite scorer."""

from __future__ import annotations

import pytest

from src.pairs.usdjpy.composite import USDJPYComposite, _compute_usdjpy_special


class TestUSDJPYComposite:
    def test_all_none_returns_none(self) -> None:
        comp = USDJPYComposite()
        assert comp.score(None, None, None, None) is None

    def test_score_with_all_signals(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0)
        # Base = 1.0*0.30 + 0.5*0.20 = 0.40
        assert result is not None
        assert result == pytest.approx(0.40)

    def test_score_with_missing_signals(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(None, 1.0, None, None)
        assert result is not None
        assert result == pytest.approx(0.20)

    def test_regime_conditional_weight_changes(self) -> None:
        neutral = USDJPYComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        high_vol = USDJPYComposite(vol_regime="HIGH_VOL", rate_regime="NEUTRAL")
        assert high_vol.weights["vol"] > neutral.weights["vol"]
        assert high_vol.weights["rate"] < neutral.weights["rate"]

    def test_interaction_terms_effect(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, None, None, None, boj_intervention_proximity=0.5)
        # special = 0.5
        # interaction: special_rate = 0.5*1.0*0.10 = 0.05
        # base = 1.0*0.30 + 0.5*0.15 = 0.375
        # interaction_boost = 0.05
        # composite = 0.375 + 0.05 * 0.45 = 0.3975
        assert result is not None
        assert result == pytest.approx(0.3975, abs=0.001)

    def test_intervention_proximity_in_special_signal(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, None, None, None, boj_intervention_proximity=0.8)
        # intervention proximity 0.8 should contribute to special signal
        assert result is not None
        assert result > 0.30  # base rate only would be 0.30

    def test_special_signal_computation(self) -> None:
        assert _compute_usdjpy_special(1.0, 3.0, None) == pytest.approx(2.0)
        assert _compute_usdjpy_special(None, None, None) is None

    def test_output_clipping(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(5.0, 5.0, 5.0, 5.0, vix=5.0)
        assert result is not None
        assert result <= 2.0
