"""Tests for pair-specific regime detection modules."""

from __future__ import annotations

import pytest

from src.pairs.eurusd.regime import (
    detect_ecb_policy_regime,
    ecb_regime_adjustment_factor,
    eurusd_hysteresis_tier,
    get_eurusd_thresholds,
)
from src.pairs.usdinr.regime import (
    detect_fpi_flow_regime,
    detect_rbi_management_regime,
    get_usdinr_thresholds,
    usdinr_hysteresis_tier,
)
from src.pairs.usdjpy.regime import (
    detect_boj_intervention_regime,
    get_usdjpy_thresholds,
    usdjpy_hysteresis_tier,
)

# ---------------------------------------------------------------------------
# Pair-specific thresholds
# ---------------------------------------------------------------------------


class TestPairSpecificThresholds:
    def test_eurusd_thresholds(self) -> None:
        t = get_eurusd_thresholds()
        assert t["hysteresis_tier4"] == 1.0
        assert t["hysteresis_tier3"] == 0.45
        assert t["conviction_enter_min"] == 3
        assert t["adr_multiplier"] == 1.3

    def test_usdjpy_thresholds(self) -> None:
        t = get_usdjpy_thresholds()
        assert t["hysteresis_tier4"] == 1.0
        assert t["hysteresis_tier3"] == 0.40
        assert t["conviction_enter_min"] == 3
        assert t["adr_multiplier"] == 1.5
        assert t["intervention_proximity_discount"] is True

    def test_usdinr_thresholds(self) -> None:
        t = get_usdinr_thresholds()
        assert t["hysteresis_tier4"] == 1.0
        assert t["hysteresis_tier3"] == 0.50
        assert t["conviction_enter_min"] == 4
        assert t["adr_multiplier"] == 1.2
        assert t["rbi_management_discount"] is True

    def test_usdjpy_intervention_active_adjustments(self) -> None:
        t = get_usdjpy_thresholds("ACTIVE")
        assert t["conviction_enter_min"] == 4
        assert t["vol_rank_enter_max"] == pytest.approx(0.90 * 0.85)
        assert t["mie_multiplier"] == pytest.approx(1.2 * 1.3)

    def test_usdjpy_intervention_proximal_adjustments(self) -> None:
        t = get_usdjpy_thresholds("PROXIMAL")
        assert t["conviction_enter_min"] == 3
        assert t["vol_rank_enter_max"] == pytest.approx(0.90 * 0.92)
        assert t["mie_multiplier"] == pytest.approx(1.2 * 1.15)

    def test_usdinr_rbi_active_defence(self) -> None:
        t = get_usdinr_thresholds("ACTIVE_DEFENCE")
        assert t["conviction_enter_min"] == 5
        assert t["vol_rank_enter_max"] == pytest.approx(0.82 * 0.80)
        assert t["adr_multiplier"] == pytest.approx(1.2 * 0.90)

    def test_usdinr_rbi_accumulation(self) -> None:
        t = get_usdinr_thresholds("ACCUMULATION")
        # ACCUMULATION keeps conviction at default (4) via max(4, 3)
        assert t["conviction_enter_min"] == 4


# ---------------------------------------------------------------------------
# EURUSD hysteresis
# ---------------------------------------------------------------------------


class TestEURUSDHysteresis:
    @pytest.mark.parametrize(
        "composite,expected",
        [
            (-2.0, 0),
            (-1.0, 1),
            (-0.35, 2),
            (0.0, 2),
            (0.46, 3),
            (1.5, 4),
        ],
    )
    def test_snap_no_prior(self, composite: float, expected: int) -> None:
        assert eurusd_hysteresis_tier(composite, None) == expected

    def test_hysteresis_stays_at_four(self) -> None:
        assert eurusd_hysteresis_tier(0.90, 4) == 4
        assert eurusd_hysteresis_tier(0.80, 4) == 3

    def test_hysteresis_stays_at_zero(self) -> None:
        assert eurusd_hysteresis_tier(-0.90, 0) == 0
        assert eurusd_hysteresis_tier(-0.80, 0) == 1


# ---------------------------------------------------------------------------
# ECB policy regime detection
# ---------------------------------------------------------------------------


class TestECBPolicyRegime:
    def test_qe_from_purchases(self) -> None:
        assert detect_ecb_policy_regime(None, 3.0, 60.0) == "QE"

    def test_qt_from_purchases(self) -> None:
        assert detect_ecb_policy_regime(None, -3.0, -60.0) == "QT"

    def test_qe_fallback(self) -> None:
        assert detect_ecb_policy_regime(-0.5, 1.0, None) == "QE"

    def test_qt_fallback(self) -> None:
        assert detect_ecb_policy_regime(2.5, -2.0, None) == "QT"

    def test_neutral(self) -> None:
        assert detect_ecb_policy_regime(1.0, 0.0, None) == "NEUTRAL"

    def test_all_none(self) -> None:
        assert detect_ecb_policy_regime(None, None, None) == "NEUTRAL"

    def test_ecb_adjustment_qt_negative(self) -> None:
        assert ecb_regime_adjustment_factor("QT", -1.0) == pytest.approx(1.15)
        assert ecb_regime_adjustment_factor("QT", 1.0) == pytest.approx(0.90)

    def test_ecb_adjustment_qe_positive(self) -> None:
        assert ecb_regime_adjustment_factor("QE", 1.0) == pytest.approx(1.15)
        assert ecb_regime_adjustment_factor("QE", -1.0) == pytest.approx(0.90)

    def test_ecb_adjustment_neutral(self) -> None:
        assert ecb_regime_adjustment_factor("NEUTRAL", 1.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# USDJPY hysteresis
# ---------------------------------------------------------------------------


class TestUSDJPYHysteresis:
    @pytest.mark.parametrize(
        "composite,expected",
        [
            (-2.0, 0),
            (-1.0, 1),
            (-0.40, 2),
            (0.0, 2),
            (0.41, 3),
            (1.5, 4),
        ],
    )
    def test_snap_no_prior(self, composite: float, expected: int) -> None:
        assert usdjpy_hysteresis_tier(composite, None) == expected


# ---------------------------------------------------------------------------
# BoJ intervention regime detection
# ---------------------------------------------------------------------------


class TestBoJInterventionRegime:
    def test_dormant_no_data(self) -> None:
        assert detect_boj_intervention_regime(None, None, None, None) == "DORMANT"

    def test_active_near_high(self) -> None:
        assert detect_boj_intervention_regime(150.0, 150.0, None, 10) == "ACTIVE"

    def test_active_near_low(self) -> None:
        assert detect_boj_intervention_regime(140.0, None, 140.0, 10) == "ACTIVE"

    def test_proximal(self) -> None:
        assert detect_boj_intervention_regime(300.0, 150.0, None, 10) == "PROXIMAL"

    def test_dormant_far_away(self) -> None:
        assert detect_boj_intervention_regime(500.0, 150.0, None, 10) == "DORMANT"

    def test_dormant_stale_intervention(self) -> None:
        assert detect_boj_intervention_regime(150.0, 150.0, None, 200) == "DORMANT"

    def test_dormant_no_levels(self) -> None:
        assert detect_boj_intervention_regime(150.0, None, None, 10) == "DORMANT"


# ---------------------------------------------------------------------------
# USDINR hysteresis
# ---------------------------------------------------------------------------


class TestUSDINRHysteresis:
    @pytest.mark.parametrize(
        "composite,expected",
        [
            (-2.0, 0),
            (-1.0, 1),
            (-0.30, 2),
            (0.0, 2),
            (0.51, 3),
            (1.5, 4),
        ],
    )
    def test_snap_no_prior(self, composite: float, expected: int) -> None:
        assert usdinr_hysteresis_tier(composite, None) == expected


# ---------------------------------------------------------------------------
# RBI management regime detection
# ---------------------------------------------------------------------------


class TestRBIManagementRegime:
    def test_active_defence_reserves_drop(self) -> None:
        assert detect_rbi_management_regime(-5.0, None, None) == "ACTIVE_DEFENCE"

    def test_accumulation(self) -> None:
        assert detect_rbi_management_regime(3.0, None, None) == "ACCUMULATION"

    def test_active_defence_fwd_premium(self) -> None:
        assert detect_rbi_management_regime(0.0, 2.5, None) == "ACTIVE_DEFENCE"

    def test_light_touch(self) -> None:
        assert detect_rbi_management_regime(-1.0, 1.0, None) == "LIGHT_TOUCH"

    def test_all_none(self) -> None:
        assert detect_rbi_management_regime(None, None, None) == "LIGHT_TOUCH"


# ---------------------------------------------------------------------------
# FPI flow regime detection
# ---------------------------------------------------------------------------


class TestFPIFlowRegime:
    def test_strong_inflow(self) -> None:
        assert detect_fpi_flow_regime(2.0, 2.0) == "STRONG_INFLOW"

    def test_moderate_inflow(self) -> None:
        assert detect_fpi_flow_regime(1.5, 0.0) == "MODERATE_INFLOW"

    def test_neutral(self) -> None:
        assert detect_fpi_flow_regime(0.5, 0.0) == "NEUTRAL"

    def test_moderate_outflow(self) -> None:
        assert detect_fpi_flow_regime(-1.5, 0.0) == "MODERATE_OUTFLOW"

    def test_strong_outflow(self) -> None:
        assert detect_fpi_flow_regime(-2.0, -2.0) == "STRONG_OUTFLOW"

    def test_none_inputs(self) -> None:
        assert detect_fpi_flow_regime(None, None) == "NEUTRAL"
