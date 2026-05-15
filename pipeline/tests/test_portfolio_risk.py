"""Comprehensive tests for portfolio_risk module."""

from __future__ import annotations

import pytest

from src.monitoring.portfolio_risk import PortfolioRiskManager

# ---------------------------------------------------------------------------
# PortfolioRiskManager.can_add_position
# ---------------------------------------------------------------------------


class TestCanAddPosition:
    def test_empty_portfolio(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        assert mgr.can_add_position("EURUSD", 0.01) is True

    def test_within_heat_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        mgr.add_position("EURUSD", 0.01)
        assert mgr.can_add_position("USDJPY", 0.01) is True

    def test_at_heat_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        mgr.add_position("EURUSD", 0.03)
        assert mgr.can_add_position("USDJPY", 0.0) is True

    def test_exceeds_heat_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        mgr.add_position("EURUSD", 0.02)
        assert mgr.can_add_position("USDJPY", 0.02) is False

    def test_exactly_at_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        mgr.add_position("EURUSD", 0.015)
        mgr.add_position("USDJPY", 0.015)
        assert mgr.can_add_position("USDINR", 0.001) is False

    def test_zero_heat(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        assert mgr.can_add_position("EURUSD", 0.0) is True

    def test_negative_risk_amount(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        assert mgr.can_add_position("EURUSD", -0.01) is True


# ---------------------------------------------------------------------------
# PortfolioRiskManager.adjust_for_correlation
# ---------------------------------------------------------------------------


class TestAdjustForCorrelation:
    def test_no_positions(self) -> None:
        mgr = PortfolioRiskManager()
        result = mgr.adjust_for_correlation("EURUSD", 1.0, {})
        assert result == pytest.approx(1.0)

    def test_no_correlation_data(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        result = mgr.adjust_for_correlation("EURUSD", 1.0, {})
        assert result == pytest.approx(1.0)

    def test_low_correlation(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.50}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(1.0)

    def test_moderate_correlation(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.80}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(0.75)

    def test_high_correlation(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.95}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(0.5)

    def test_multiple_positions_uses_max(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        mgr.add_position("GBPUSD", 0.01)
        corr = {
            "EURUSD": {"USDJPY": 0.95, "GBPUSD": 0.50},
        }
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        # max corr is 0.95 (> 0.90) → 0.5
        assert result == pytest.approx(0.5)

    def test_reverse_lookup(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        # Reverse key lookup
        corr = {
            "USDJPY": {"EURUSD": 0.95},
        }
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(0.5)

    def test_exactly_70_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.70}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        # > 0.70 uses 0.75; exactly 0.70 should use 0.75
        assert result == pytest.approx(0.75)

    def test_exactly_90_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.90}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        # > 0.90 uses 0.5; exactly 0.90 should use 0.5
        assert result == pytest.approx(0.5)

    def test_just_below_70(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.69}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# PortfolioRiskManager.compute_portfolio_var
# ---------------------------------------------------------------------------


class TestComputePortfolioVar:
    def test_no_positions(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.compute_portfolio_var() is None

    def test_single_position(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        var = mgr.compute_portfolio_var()
        assert var is not None
        assert var > 0

    def test_multiple_positions(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        mgr.add_position("USDJPY", 0.01)
        var = mgr.compute_portfolio_var()
        assert var is not None
        # VaR should increase with more positions
        mgr2 = PortfolioRiskManager()
        mgr2.add_position("EURUSD", 0.01)
        assert var > (mgr2.compute_portfolio_var() or 0.0)

    def test_high_confidence(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        var_95 = mgr.compute_portfolio_var(confidence=0.95)
        var_99 = mgr.compute_portfolio_var(confidence=0.99)
        assert var_99 is not None
        assert var_95 is not None
        assert var_99 > var_95


# ---------------------------------------------------------------------------
# PortfolioRiskManager.check_drawdown_circuit_breaker
# ---------------------------------------------------------------------------


class TestCheckDrawdownCircuitBreaker:
    def test_no_drawdown(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(100.0, 100.0) is False

    def test_small_drawdown(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(97.0, 100.0) is False

    def test_at_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(95.0, 100.0) is False

    def test_above_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(94.0, 100.0) is True

    def test_large_drawdown(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(50.0, 100.0) is True

    def test_equity_above_peak(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(105.0, 100.0) is False

    def test_zero_peak(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(100.0, 0.0) is False

    def test_negative_peak(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(100.0, -100.0) is False

    def test_custom_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(92.0, 100.0, threshold=0.10) is False
        assert mgr.check_drawdown_circuit_breaker(89.0, 100.0, threshold=0.10) is True

    def test_edge_case_exactly_5_percent(self) -> None:
        mgr = PortfolioRiskManager()
        # 5% drawdown from 100 = 95, so 94.999 should trigger
        assert mgr.check_drawdown_circuit_breaker(94.999, 100.0) is True
