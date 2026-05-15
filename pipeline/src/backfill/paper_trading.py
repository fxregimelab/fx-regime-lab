"""Paper trading simulation that runs alongside production.

Tracks hypothetical P&L using new models without real capital at risk.
All state is persisted to file-based JSONL — no production DB writes.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from src.fx_types import Layer2DirectionalBias
from src.monitoring.stress_controls import assess_stress_mode
from src.pairs.math_core import correlation_adjusted_size, kelly_fraction

logger = logging.getLogger(__name__)

_DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "paper_trading_logs"
_MAX_HOLD_DAYS = 20
_RR_RATIO = 2.0


@dataclass
class PaperPortfolio:
    capital: float = 1_000_000.0
    positions: dict[str, dict[str, Any]] = field(default_factory=dict)
    equity_curve: list[tuple[date, float]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    peak_capital: float = 1_000_000.0
    max_drawdown: float = 0.0

    def update_drawdown(self) -> None:
        """Recalculate drawdown from current capital."""
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
        if self.peak_capital > 0:
            dd = (self.peak_capital - self.capital) / self.peak_capital
            if dd > self.max_drawdown:
                self.max_drawdown = dd


def _direction_from_regime(regime: str | None) -> Layer2DirectionalBias:
    """Map regime string to directional bias."""
    if regime is None:
        return "NEUTRAL"
    r = regime.upper()
    if any(k in r for k in ("DEPRECIATION", "STRENGTH", "INR_DEPR", "BULLISH")):
        return "LONG"
    if any(k in r for k in ("APPRECIATION", "WEAKNESS", "INR_APPR", "BEARISH")):
        return "SHORT"
    return "NEUTRAL"


class PaperTradingSimulator:
    """Simulate trades using pair-specific models on production data."""

    def __init__(
        self,
        pairs: list[str],
        *,
        initial_capital: float = 1_000_000.0,
        log_dir: Path | str | None = None,
        transaction_cost_bps: float = 2.0,
        slippage_bps: float = 1.0,
    ) -> None:
        self.pairs = [p.upper().replace("/", "") for p in pairs]
        self.portfolios: dict[str, PaperPortfolio] = {
            p: PaperPortfolio(capital=initial_capital) for p in self.pairs
        }
        self._log_dir = Path(log_dir) if log_dir else _DEFAULT_LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._transaction_cost_bps = transaction_cost_bps
        self._slippage_bps = slippage_bps
        self._running_stats: dict[str, dict[str, Any]] = {
            p: {"wins": 0, "losses": 0, "win_bps": [], "loss_bps": []} for p in self.pairs
        }

    def on_regime_call(
        self,
        pair: str,
        date_str: str,
        regime_call: dict[str, Any],
        signal_row: dict[str, Any],
    ) -> None:
        """Process a new regime call and simulate trade.

        Parameters
        ----------
        pair:
            FX pair key.
        date_str:
            ISO date string (YYYY-MM-DD).
        regime_call:
            Dict with keys ``regime``, ``composite``, ``confidence``, ``conviction``.
        signal_row:
            Dict with market data (``spot``, ``cross_asset_vix``, etc.).
        """
        pair_key = pair.upper().replace("/", "")
        if pair_key not in self.pairs:
            logger.warning("Pair %s not tracked by paper simulator", pair)
            return

        portfolio = self.portfolios[pair_key]
        d = date.fromisoformat(date_str[:10])

        # Close any existing position first (one-position-per-pair model)
        if pair_key in portfolio.positions:
            spot = float(signal_row.get("spot", 0.0) or 0.0)
            if spot > 0:
                self.close_positions(pair_key, date_str, spot, reason="REVERSAL")

        direction = _direction_from_regime(regime_call.get("regime"))
        if direction == "NEUTRAL":
            portfolio.equity_curve.append((d, portfolio.capital))
            return

        spot = float(signal_row.get("spot", 0.0) or 0.0)
        if spot <= 0:
            portfolio.equity_curve.append((d, portfolio.capital))
            return

        # Position sizing
        position_size = self._compute_position_size(
            pair=pair_key,
            signal=signal_row,
            regime=regime_call,
            direction=direction,
        )
        if position_size <= 0.0:
            portfolio.equity_curve.append((d, portfolio.capital))
            return

        # Stop / take-profit
        rv20 = signal_row.get("realized_vol_20d")
        atr_proxy = float(rv20) / math.sqrt(252.0) * spot if rv20 is not None else None
        adr_proxy = float(rv20) / math.sqrt(252.0) * spot * 1.5 if rv20 is not None else None
        parts: list[float] = []
        if adr_proxy is not None and adr_proxy > 0.0:
            parts.append(adr_proxy)
        if atr_proxy is not None and atr_proxy > 0.0:
            parts.append(atr_proxy)
        if not parts:
            parts.append(spot * 0.005)
        buf = max(parts)

        stop_level = spot - buf if direction == "LONG" else spot + buf
        take_profit = spot + buf * _RR_RATIO if direction == "LONG" else spot - buf * _RR_RATIO

        portfolio.positions[pair_key] = {
            "entry_date": date_str,
            "direction": direction,
            "entry_spot": spot,
            "position_size": position_size,
            "stop_level": stop_level,
            "take_profit": take_profit,
        }
        portfolio.equity_curve.append((d, portfolio.capital))

        self._log_event(
            pair_key,
            {
                "event": "OPEN",
                "date": date_str,
                "direction": direction,
                "spot": spot,
                "position_size": position_size,
                "stop_level": stop_level,
                "take_profit": take_profit,
            },
        )

    def close_positions(
        self,
        pair: str,
        date_str: str,
        spot: float,
        reason: str = "T+20",
    ) -> None:
        """Close open positions and record P&L.

        Parameters
        ----------
        pair:
            FX pair key.
        date_str:
            ISO date string.
        spot:
            Current spot price.
        reason:
            Exit reason (STOP, TP, TIME, REVERSAL).
        """
        pair_key = pair.upper().replace("/", "")
        if pair_key not in self.pairs:
            return

        portfolio = self.portfolios[pair_key]
        pos = portfolio.positions.pop(pair_key, None)
        if pos is None:
            return

        entry_spot = float(pos["entry_spot"])
        direction = str(pos["direction"])
        position_size = float(pos["position_size"])
        dir_mult = 1.0 if direction == "LONG" else -1.0

        tc_decimal = (self._transaction_cost_bps + self._slippage_bps) / 10_000.0
        gross_return = (spot / entry_spot - 1.0) * dir_mult if entry_spot > 0 else 0.0
        net_return = gross_return - tc_decimal * 2.0
        pnl_bps = net_return * 10_000.0

        # Update capital
        portfolio.capital = portfolio.capital * (1.0 + net_return)
        portfolio.update_drawdown()

        trade_record: dict[str, Any] = {
            "date": date_str,
            "pair": pair_key,
            "direction": direction,
            "entry_price": entry_spot,
            "exit_price": spot,
            "position_size": position_size,
            "pnl_bps": float(pnl_bps),
            "exit_reason": reason,
        }
        portfolio.trades.append(trade_record)
        portfolio.equity_curve.append((date.fromisoformat(date_str[:10]), portfolio.capital))

        # Update running stats
        stats = self._running_stats[pair_key]
        if pnl_bps > 0:
            stats["wins"] += 1
            stats["win_bps"].append(float(pnl_bps))
        else:
            stats["losses"] += 1
            stats["loss_bps"].append(abs(float(pnl_bps)))

        self._log_event(pair_key, {"event": "CLOSE", **trade_record})

    def get_performance_summary(self) -> dict[str, Any]:
        """Return performance metrics for all pairs."""
        summary: dict[str, Any] = {}
        for pair_key, portfolio in self.portfolios.items():
            trades = portfolio.trades
            wins = [t for t in trades if t.get("pnl_bps", 0.0) > 0]
            losses = [t for t in trades if t.get("pnl_bps", 0.0) <= 0]
            total = len(trades)

            win_rate = (len(wins) / total * 100.0) if total > 0 else 0.0
            avg_win = float(np.mean([t["pnl_bps"] for t in wins])) if wins else 0.0
            avg_loss = float(np.mean([t["pnl_bps"] for t in losses])) if losses else 0.0

            # Sharpe from equity curve
            equity_values = [e for _, e in portfolio.equity_curve]
            sharpe = 0.0
            if len(equity_values) > 1:
                daily_returns = np.diff(equity_values) / np.array(equity_values[:-1])
                daily_returns = daily_returns[np.isfinite(daily_returns)]
                if len(daily_returns) > 1:
                    mean_ret = float(np.mean(daily_returns))
                    std_ret = float(np.std(daily_returns, ddof=1))
                    if std_ret > 0:
                        sharpe = (mean_ret / std_ret) * math.sqrt(252.0)

            summary[pair_key] = {
                "capital": portfolio.capital,
                "peak_capital": portfolio.peak_capital,
                "max_drawdown_pct": portfolio.max_drawdown * 100.0,
                "total_trades": total,
                "win_rate": win_rate,
                "avg_win_bps": avg_win,
                "avg_loss_bps": avg_loss,
                "sharpe_ratio": sharpe,
                "open_position": portfolio.positions.get(pair_key) is not None,
            }
        return summary

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _compute_position_size(
        self,
        pair: str,
        signal: dict[str, Any],
        regime: dict[str, Any],
        direction: Layer2DirectionalBias,
    ) -> float:
        """Return position size as fraction of capital."""
        composite = float(regime.get("composite", 0.0) or 0.0)
        conviction = int(regime.get("conviction", 0) or 0)
        base_size = min(abs(composite), 1.0)
        if conviction >= 4:
            base_size = max(base_size, 0.75)
        elif conviction >= 3:
            base_size = max(base_size, 0.50)
        else:
            base_size = max(base_size, 0.25)

        # Kelly
        stats = self._running_stats[pair]
        total = stats["wins"] + stats["losses"]
        if total > 0:
            win_rate = stats["wins"] / total
            avg_win = float(np.mean(stats["win_bps"])) if stats["win_bps"] else 15.0
            avg_loss = float(np.mean(stats["loss_bps"])) if stats["loss_bps"] else 10.0
        else:
            win_rate, avg_win, avg_loss = 0.50, 15.0, 10.0

        kelly = kelly_fraction(
            win_rate=win_rate,
            avg_win_bps=avg_win,
            avg_loss_bps=avg_loss,
            safety_factor=0.25,
            max_risk=0.01,
        )
        base_size *= kelly * 100.0

        # Stress
        vix = signal.get("cross_asset_vix")
        dxy_chg = signal.get("day_change_pct")
        pair_chg = abs(float(signal.get("day_change_pct", 0.0) or 0.0))
        stress = assess_stress_mode(
            vix=float(vix) if vix is not None else None,
            dxy_overnight_pct=float(dxy_chg) if dxy_chg is not None else None,
            max_pair_overnight_pct=pair_chg,
        )
        if stress["is_stress"]:
            base_size = min(base_size, stress["max_position_size"])

        # Correlation adjustment (simplified: no cross-pair correlation in paper mode)
        portfolio = {p: 0.0 for p in self.pairs}
        for p, port in self.portfolios.items():
            pos = port.positions.get(p)
            if pos is not None:
                portfolio[p] = (
                    float(pos["position_size"])
                    if pos["direction"] == "LONG"
                    else -float(pos["position_size"])
                )
        corr_matrix: dict[str, dict[str, float]] = {}
        base_size = correlation_adjusted_size(base_size, pair, portfolio, corr_matrix)

        return float(np.clip(base_size, 0.0, 0.02))

    def _log_event(self, pair: str, event: dict[str, Any]) -> None:
        """Append event to pair-specific JSONL log."""
        log_path = self._log_dir / f"{pair}_paper_trades.jsonl"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str) + "\n")
