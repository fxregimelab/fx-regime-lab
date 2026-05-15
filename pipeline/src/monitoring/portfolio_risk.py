"""Portfolio-level risk monitoring and position correlation management."""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


class PortfolioRiskManager:
    def __init__(self, max_portfolio_heat: float = 0.03):
        self.max_portfolio_heat = max_portfolio_heat  # 3% max portfolio risk
        self.positions: dict[str, float] = {}  # pair -> risk amount

    def can_add_position(self, pair: str, risk_amount: float) -> bool:
        """Check if adding position would exceed portfolio heat."""
        total_risk = sum(self.positions.values()) + risk_amount
        return total_risk <= self.max_portfolio_heat

    def add_position(self, pair: str, risk_amount: float) -> None:
        """Record an accepted position risk amount."""
        self.positions[pair] = risk_amount

    def adjust_for_correlation(
        self,
        pair: str,
        base_size: float,
        corr_matrix: dict[str, dict[str, float]],
    ) -> float:
        """Reduce size if highly correlated with existing positions."""
        if not self.positions or not corr_matrix:
            return base_size

        max_corr = 0.0
        for existing_pair in self.positions:
            corr = corr_matrix.get(pair, {}).get(existing_pair)
            if corr is None:
                corr = corr_matrix.get(existing_pair, {}).get(pair)
            if corr is not None:
                max_corr = max(max_corr, abs(corr))

        # Reduce size linearly for correlations > 0.70
        if max_corr >= 0.90:
            return base_size * 0.5
        if max_corr >= 0.70:
            return base_size * 0.75
        return base_size

    def compute_portfolio_var(self, confidence: float = 0.95) -> float | None:
        """Compute portfolio Value-at-Risk using variance-covariance method.

        Simplified VaR assuming positions are independent when correlation
        data is unavailable. Returns None if no positions are held.
        """
        if not self.positions:
            return None

        # Simplified: assume each position has ~10% daily volatility
        daily_vol = 0.10
        z_score = 1.645 if confidence <= 0.95 else 2.33

        total_var = 0.0
        for risk in self.positions.values():
            # risk_amount is roughly the notional at risk; VaR = notional * vol * z
            total_var += (risk * daily_vol * z_score) ** 2

        return math.sqrt(total_var)

    def check_drawdown_circuit_breaker(
        self,
        current_equity: float,
        peak_equity: float,
        threshold: float = 0.05,
    ) -> bool:
        """Return True if drawdown exceeds threshold (5%)."""
        if peak_equity <= 0:
            return False
        drawdown = (peak_equity - current_equity) / peak_equity
        return drawdown > threshold
