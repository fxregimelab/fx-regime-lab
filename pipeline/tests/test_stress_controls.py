"""Comprehensive tests for stress_controls module."""

from __future__ import annotations

from src.monitoring.stress_controls import _is_correlation_cluster, assess_stress_mode

# ---------------------------------------------------------------------------
# assess_stress_mode
# ---------------------------------------------------------------------------


class TestAssessStressMode:
    def test_no_stress(self) -> None:
        result = assess_stress_mode(vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0)
        assert result["is_stress"] is False
        assert result["active_modes"] == []
        assert result["max_position_size"] == 0.01
        assert result["conviction_cap"] == 5
        assert result["skip_ai_briefs"] is False

    def test_vix_gt_30(self) -> None:
        result = assess_stress_mode(vix=35.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0)
        assert result["is_stress"] is True
        assert "VIX_GT_30" in result["active_modes"]
        assert result["max_position_size"] == 0.005
        assert result["conviction_cap"] == 3
        assert result["skip_ai_briefs"] is True

    def test_vix_gt_25(self) -> None:
        result = assess_stress_mode(vix=28.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0)
        assert result["is_stress"] is True
        assert "VIX_GT_25" in result["active_modes"]
        assert "VIX_GT_30" not in result["active_modes"]
        assert result["max_position_size"] == 0.0075
        assert result["conviction_cap"] == 4
        assert result["skip_ai_briefs"] is False

    def test_dxy_move_gt_1pct(self) -> None:
        result = assess_stress_mode(vix=15.0, dxy_overnight_pct=1.5, max_pair_overnight_pct=1.0)
        assert result["is_stress"] is True
        assert "DXY_MOVE_GT_1PCT" in result["active_modes"]
        assert result["max_position_size"] == 0.005
        assert result["conviction_cap"] == 3

    def test_dxy_move_negative(self) -> None:
        result = assess_stress_mode(vix=15.0, dxy_overnight_pct=-1.5, max_pair_overnight_pct=1.0)
        assert result["is_stress"] is True
        assert "DXY_MOVE_GT_1PCT" in result["active_modes"]

    def test_pair_gap_gt_2pct(self) -> None:
        result = assess_stress_mode(vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=2.5)
        assert result["is_stress"] is True
        assert "PAIR_GAP_GT_2PCT" in result["active_modes"]
        assert result["max_position_size"] == 0.0
        assert result["conviction_cap"] == 1
        assert result["skip_ai_briefs"] is True
        assert result["reduce_existing"] == 0.5

    def test_correlation_cluster(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95, "GBPUSD": 0.92},
            "USDJPY": {"EURUSD": 0.95, "GBPUSD": 0.91},
            "GBPUSD": {"EURUSD": 0.92, "USDJPY": 0.91},
        }
        result = assess_stress_mode(
            vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0, correlation_matrix=corr
        )
        assert result["is_stress"] is True
        assert "CORRELATION_CLUSTER" in result["active_modes"]
        assert result["max_position_size"] == 0.005
        assert result["reduce_existing"] == 0.25

    def test_correlation_cluster_not_enough_pairs(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95},
            "USDJPY": {"EURUSD": 0.95},
        }
        result = assess_stress_mode(
            vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0, correlation_matrix=corr
        )
        assert result["is_stress"] is False
        assert "CORRELATION_CLUSTER" not in result["active_modes"]

    def test_correlation_cluster_not_high_enough(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.85, "GBPUSD": 0.80},
            "USDJPY": {"EURUSD": 0.85, "GBPUSD": 0.80},
            "GBPUSD": {"EURUSD": 0.80, "USDJPY": 0.80},
        }
        result = assess_stress_mode(
            vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0, correlation_matrix=corr
        )
        assert result["is_stress"] is False
        assert "CORRELATION_CLUSTER" not in result["active_modes"]

    def test_multiple_simultaneous_stress_modes(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95, "GBPUSD": 0.92},
            "USDJPY": {"EURUSD": 0.95, "GBPUSD": 0.91},
            "GBPUSD": {"EURUSD": 0.92, "USDJPY": 0.91},
        }
        result = assess_stress_mode(
            vix=35.0, dxy_overnight_pct=1.5, max_pair_overnight_pct=2.5, correlation_matrix=corr
        )
        assert result["is_stress"] is True
        assert "VIX_GT_30" in result["active_modes"]
        assert "DXY_MOVE_GT_1PCT" in result["active_modes"]
        assert "PAIR_GAP_GT_2PCT" in result["active_modes"]
        assert "CORRELATION_CLUSTER" in result["active_modes"]
        # Most restrictive settings should apply
        assert result["max_position_size"] == 0.0  # PAIR_GAP_GT_2PCT
        assert result["conviction_cap"] == 1  # PAIR_GAP_GT_2PCT
        assert result["skip_ai_briefs"] is True  # VIX_GT_30 or PAIR_GAP_GT_2PCT
        assert result["reduce_existing"] == 0.5  # PAIR_GAP_GT_2PCT

    def test_none_inputs(self) -> None:
        result = assess_stress_mode(vix=None, dxy_overnight_pct=None, max_pair_overnight_pct=None)
        assert result["is_stress"] is False
        assert result["active_modes"] == []

    def test_vix_none(self) -> None:
        result = assess_stress_mode(vix=None, dxy_overnight_pct=1.5, max_pair_overnight_pct=1.0)
        assert result["is_stress"] is True
        assert "DXY_MOVE_GT_1PCT" in result["active_modes"]

    def test_empty_correlation_matrix(self) -> None:
        result = assess_stress_mode(
            vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0, correlation_matrix={}
        )
        assert result["is_stress"] is False

    def test_none_correlation_matrix(self) -> None:
        result = assess_stress_mode(
            vix=15.0, dxy_overnight_pct=0.5, max_pair_overnight_pct=1.0, correlation_matrix=None
        )
        assert result["is_stress"] is False


# ---------------------------------------------------------------------------
# _is_correlation_cluster
# ---------------------------------------------------------------------------


class TestIsCorrelationCluster:
    def test_three_pairs_highly_correlated(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.95, "GBPUSD": 0.92},
            "USDJPY": {"EURUSD": 0.95, "GBPUSD": 0.91},
            "GBPUSD": {"EURUSD": 0.92, "USDJPY": 0.91},
        }
        assert _is_correlation_cluster(corr) is True

    def test_three_pairs_not_correlated(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.50, "GBPUSD": 0.40},
            "USDJPY": {"EURUSD": 0.50, "GBPUSD": 0.30},
            "GBPUSD": {"EURUSD": 0.40, "USDJPY": 0.30},
        }
        assert _is_correlation_cluster(corr) is False

    def test_two_pairs_only(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.99},
            "USDJPY": {"EURUSD": 0.99},
        }
        assert _is_correlation_cluster(corr) is False

    def test_empty_matrix(self) -> None:
        assert _is_correlation_cluster({}) is False

    def test_exactly_90_threshold(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.90, "GBPUSD": 0.90},
            "USDJPY": {"EURUSD": 0.90, "GBPUSD": 0.90},
            "GBPUSD": {"EURUSD": 0.90, "USDJPY": 0.90},
        }
        assert _is_correlation_cluster(corr) is True

    def test_just_below_90(self) -> None:
        corr = {
            "EURUSD": {"USDJPY": 0.89, "GBPUSD": 0.89},
            "USDJPY": {"EURUSD": 0.89, "GBPUSD": 0.89},
            "GBPUSD": {"EURUSD": 0.89, "USDJPY": 0.89},
        }
        assert _is_correlation_cluster(corr) is False
