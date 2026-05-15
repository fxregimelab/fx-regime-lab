"""Tests for src.monitoring.portfolio_risk."""

from __future__ import annotations

import pytest

from src.monitoring.portfolio_risk import PortfolioRiskManager


class TestCanAddPosition:
    def test_add_within_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        assert mgr.can_add_position("EURUSD", 0.02) is True

    def test_add_at_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        mgr.add_position("EURUSD", 0.01)
        assert mgr.can_add_position("USDJPY", 0.02) is True

    def test_add_exceeds_limit(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        mgr.add_position("EURUSD", 0.02)
        assert mgr.can_add_position("USDJPY", 0.02) is False

    def test_add_zero(self) -> None:
        mgr = PortfolioRiskManager(max_portfolio_heat=0.03)
        assert mgr.can_add_position("EURUSD", 0.0) is True


class TestAdjustForCorrelation:
    def test_no_positions_unchanged(self) -> None:
        mgr = PortfolioRiskManager()
        result = mgr.adjust_for_correlation("EURUSD", 1.0, {})
        assert result == pytest.approx(1.0)

    def test_no_corr_matrix_unchanged(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        result = mgr.adjust_for_correlation("EURUSD", 1.0, {})
        assert result == pytest.approx(1.0)

    def test_high_corr_reduces_to_50(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.95}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(0.5)

    def test_moderate_corr_reduces_to_75(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.75}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(0.75)

    def test_low_corr_unchanged(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("USDJPY", 0.01)
        corr = {"EURUSD": {"USDJPY": 0.50}}
        result = mgr.adjust_for_correlation("EURUSD", 1.0, corr)
        assert result == pytest.approx(1.0)

    def test_reverse_lookup(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        corr = {"USDJPY": {"EURUSD": 0.95}}
        result = mgr.adjust_for_correlation("USDJPY", 1.0, corr)
        assert result == pytest.approx(0.5)


class TestComputePortfolioVar:
    def test_no_positions_returns_none(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.compute_portfolio_var() is None

    def test_single_position(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        var = mgr.compute_portfolio_var(0.95)
        # 0.01 * 0.10 * 1.645 = 0.001645
        assert var is not None
        assert var == pytest.approx(0.001645, abs=1e-6)

    def test_two_positions(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        mgr.add_position("USDJPY", 0.01)
        var = mgr.compute_portfolio_var(0.95)
        expected = (0.01 * 0.10 * 1.645) * (2 ** 0.5)
        assert var is not None
        assert var == pytest.approx(expected, abs=1e-6)

    def test_higher_confidence(self) -> None:
        mgr = PortfolioRiskManager()
        mgr.add_position("EURUSD", 0.01)
        var_95 = mgr.compute_portfolio_var(0.95)
        var_99 = mgr.compute_portfolio_var(0.99)
        assert var_99 is not None
        assert var_95 is not None
        assert var_99 > var_95


class TestCheckDrawdownCircuitBreaker:
    def test_no_drawdown(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(100.0, 100.0) is False

    def test_below_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(97.0, 100.0, threshold=0.05) is False

    def test_at_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(95.0, 100.0, threshold=0.05) is False

    def test_above_threshold(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(94.0, 100.0, threshold=0.05) is True

    def test_zero_peak(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(50.0, 0.0) is False

    def test_negative_peak(self) -> None:
        mgr = PortfolioRiskManager()
        assert mgr.check_drawdown_circuit_breaker(50.0, -10.0) is False
