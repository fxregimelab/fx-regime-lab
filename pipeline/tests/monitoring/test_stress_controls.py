"""Tests for src.monitoring.stress_controls."""

from __future__ import annotations

import pytest

from src.monitoring.stress_controls import assess_stress_mode


class TestAssessStressMode:
    def test_no_stress(self) -> None:
        result = assess_stress_mode(20.0, 0.5, 1.0)
        assert result["is_stress"] is False
        assert result["active_modes"] == []
        assert result["max_position_size"] == pytest.approx(0.01)
        assert result["conviction_cap"] == 5
        assert result["skip_ai_briefs"] is False
        assert result["reduce_existing"] == 0.0

    def test_vix_high(self) -> None:
        result = assess_stress_mode(32.0, 0.5, 1.0)
        assert result["is_stress"] is True
        assert "VIX_GT_30" in result["active_modes"]
        assert result["max_position_size"] == pytest.approx(0.005)
        assert result["conviction_cap"] == 3
        assert result["skip_ai_briefs"] is True

    def test_vix_elevated(self) -> None:
        result = assess_stress_mode(26.0, 0.5, 1.0)
        assert result["is_stress"] is True
        assert "VIX_GT_25" in result["active_modes"]
        assert "VIX_GT_30" not in result["active_modes"]
        assert result["max_position_size"] == pytest.approx(0.0075)
        assert result["conviction_cap"] == 4

    def test_dxy_gap(self) -> None:
        result = assess_stress_mode(20.0, 1.5, 1.0)
        assert result["is_stress"] is True
        assert "DXY_MOVE_GT_1PCT" in result["active_modes"]
        assert result["max_position_size"] == pytest.approx(0.005)

    def test_dxy_gap_negative(self) -> None:
        result = assess_stress_mode(20.0, -1.5, 1.0)
        assert result["is_stress"] is True
        assert "DXY_MOVE_GT_1PCT" in result["active_modes"]

    def test_pair_gap(self) -> None:
        result = assess_stress_mode(20.0, 0.5, 2.5)
        assert result["is_stress"] is True
        assert "PAIR_GAP_GT_2PCT" in result["active_modes"]
        assert result["max_position_size"] == 0.0
        assert result["conviction_cap"] == 1
        assert result["skip_ai_briefs"] is True
        assert result["reduce_existing"] == 0.5

    def test_pair_gap_exactly_2_not_triggered(self) -> None:
        result = assess_stress_mode(20.0, 0.5, 2.0)
        assert "PAIR_GAP_GT_2PCT" not in result["active_modes"]

    def test_correlation_cluster(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95, "USDINR": 0.92},
            "USDJPY": {"EURUSD": 0.95, "USDINR": 0.91},
            "USDINR": {"EURUSD": 0.92, "USDJPY": 0.91},
        }
        result = assess_stress_mode(20.0, 0.5, 1.0, corr)
        assert result["is_stress"] is True
        assert "CORRELATION_CLUSTER" in result["active_modes"]
        assert result["max_position_size"] == pytest.approx(0.005)
        assert result["reduce_existing"] == 0.25

    def test_correlation_cluster_not_enough_pairs(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95},
            "USDJPY": {"EURUSD": 0.95},
        }
        result = assess_stress_mode(20.0, 0.5, 1.0, corr)
        assert "CORRELATION_CLUSTER" not in result["active_modes"]

    def test_correlation_cluster_weak_corr(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.80, "USDINR": 0.92},
            "USDJPY": {"EURUSD": 0.80, "USDINR": 0.91},
            "USDINR": {"EURUSD": 0.92, "USDJPY": 0.91},
        }
        result = assess_stress_mode(20.0, 0.5, 1.0, corr)
        assert "CORRELATION_CLUSTER" not in result["active_modes"]

    def test_combined_stress_most_restrictive(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95, "USDINR": 0.92},
            "USDJPY": {"EURUSD": 0.95, "USDINR": 0.91},
            "USDINR": {"EURUSD": 0.92, "USDJPY": 0.91},
        }
        result = assess_stress_mode(32.0, 1.5, 2.5, corr)
        assert result["is_stress"] is True
        assert set(result["active_modes"]) == {
            "VIX_GT_30",
            "DXY_MOVE_GT_1PCT",
            "PAIR_GAP_GT_2PCT",
            "CORRELATION_CLUSTER",
        }
        # Most restrictive settings
        assert result["max_position_size"] == 0.0  # PAIR_GAP
        assert result["conviction_cap"] == 1  # PAIR_GAP
        assert result["skip_ai_briefs"] is True  # VIX_GT_30 or PAIR_GAP
        assert result["reduce_existing"] == 0.5  # PAIR_GAP

    def test_none_inputs(self) -> None:
        result = assess_stress_mode(None, None, None)
        assert result["is_stress"] is False
        assert result["active_modes"] == []
