"""Pair-specific backtest engine for walk-forward validation.

Simulates trading using historical signals and regime calls,
computing P&L, Sharpe, drawdown, and win rates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np

from src.fx_types import Layer2DirectionalBias
from src.monitoring.stress_controls import assess_stress_mode
from src.pairs.math_core import (
    correlation_adjusted_size,
    kelly_fraction,
    pair_specific_thresholds,
)

# Default Kelly prior for first trades (replaced by running stats)
_DEFAULT_WIN_RATE = 0.50
_DEFAULT_AVG_WIN_BPS = 15.0
_DEFAULT_AVG_LOSS_BPS = 10.0
_MAX_HOLD_DAYS = 20
_RR_RATIO = 2.0  # Take-profit = 2 × stop distance


@dataclass
class TradeRecord:
    date: date
    pair: str
    direction: str  # LONG / SHORT / NEUTRAL
    entry_price: float | None
    exit_price: float | None
    position_size: float  # fraction of capital
    stop_level: float | None
    take_profit: float | None
    pnl_bps: float | None
    exit_reason: str  # STOP / TP / TIME / REVERSAL


@dataclass
class BacktestResult:
    pair: str
    start_date: date
    end_date: date
    total_trades: int
    win_rate: float
    avg_win_bps: float
    avg_loss_bps: float
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    equity_curve: list[tuple[date, float]]
    trades: list[TradeRecord]
    brier_score: float | None
    calibration_error: float | None


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


def _extract_price_map(
    historical_signals: list[dict[str, Any]],
    historical_prices: list[dict[str, Any]] | None,
) -> dict[date, dict[str, float]]:
    """Build date → {open, high, low, close} map.

    Prefers explicit historical_prices; falls back to ``spot`` from signals.
    """
    price_map: dict[date, dict[str, float]] = {}
    if historical_prices:
        for p in historical_prices:
            d = p.get("date")
            if d is None:
                continue
            if isinstance(d, str):
                d = date.fromisoformat(d[:10])
            price_map[d] = {
                "open": float(p.get("open", p.get("close", 0.0)) or 0.0),
                "high": float(p.get("high", p.get("close", 0.0)) or 0.0),
                "low": float(p.get("low", p.get("close", 0.0)) or 0.0),
                "close": float(p.get("close", 0.0) or 0.0),
            }
    else:
        for s in historical_signals:
            d = s.get("date")
            if d is None:
                continue
            if isinstance(d, str):
                d = date.fromisoformat(d[:10])
            spot = float(s.get("spot", 0.0) or 0.0)
            if spot > 0:
                price_map[d] = {
                    "open": spot,
                    "high": spot,
                    "low": spot,
                    "close": spot,
                }
    return price_map


def _build_spot_bars(
    price_map: dict[date, dict[str, float]],
) -> list[Any]:
    """Build minimal SpotBar-like objects for ADR/MIE/ATR computation."""
    from src.fx_types import SpotBar

    bars: list[SpotBar] = []
    for d in sorted(price_map):
        px = price_map[d]
        bars.append(
            SpotBar(
                date=d,
                pair="",
                open=px["open"],
                high=px["high"],
                low=px["low"],
                close=px["close"],
            )
        )
    return bars  # type: ignore[return-value]


class PairBacktestEngine:
    """Backtest a pair-specific strategy on historical data."""

    def __init__(
        self,
        pair: str,
        initial_capital: float = 1_000_000.0,
        transaction_cost_bps: float = 2.0,  # spread + commission
        slippage_bps: float = 1.0,
    ) -> None:
        self.pair = pair.upper().replace("/", "")
        self.initial_capital = initial_capital
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        self._trade_history: list[TradeRecord] = []
        self._equity_curve: list[tuple[date, float]] = []
        self._running_wins = 0
        self._running_losses = 0
        self._running_win_bps: list[float] = []
        self._running_loss_bps: list[float] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(
        self,
        historical_signals: list[dict[str, Any]],
        historical_regimes: list[dict[str, Any]],
        *,
        use_kelly: bool = True,
        use_stress_controls: bool = True,
        use_correlation_adjustment: bool = False,
        historical_prices: list[dict[str, Any]] | None = None,
    ) -> BacktestResult:
        """Run backtest on historical data.

        Parameters
        ----------
        historical_signals:
            Chronological signal rows (oldest → newest). Must contain at
            least ``date`` and ``spot``.
        historical_regimes:
            Chronological regime-call rows aligned to signal dates.
        use_kelly:
            Apply Kelly-optimal position sizing.
        use_stress_controls:
            Apply stress-mode position caps.
        use_correlation_adjustment:
            Reduce size when correlated with existing positions.
        historical_prices:
            Optional OHLC rows for realistic stop simulation.
        """
        if not historical_signals or not historical_regimes:
            return self._empty_result()

        # Build lookups
        price_map = _extract_price_map(historical_signals, historical_prices)
        regime_by_date: dict[date, dict[str, Any]] = {}
        for r in historical_regimes:
            d = r.get("date")
            if d is None:
                continue
            if isinstance(d, str):
                d = date.fromisoformat(d[:10])
            regime_by_date[d] = r

        capital = self.initial_capital
        first_date = date.fromisoformat(str(historical_signals[0]["date"])[:10])
        self._equity_curve = [(first_date, capital)]
        self._trade_history = []
        self._running_wins = 0
        self._running_losses = 0
        self._running_win_bps = []
        self._running_loss_bps = []

        # Running portfolio for correlation adjustment
        portfolio: dict[str, float] = {}
        corr_matrix: dict[str, dict[str, float]] = {}

        brier_scores: list[float] = []
        calibration_errors: list[float] = []

        for idx, signal in enumerate(historical_signals):
            d_raw = signal.get("date")
            if d_raw is None:
                continue
            if isinstance(d_raw, str):
                d = date.fromisoformat(d_raw[:10])
            else:
                d = d_raw

            regime = regime_by_date.get(d)
            if regime is None:
                # Still record equity point
                self._equity_curve.append((d, capital))
                continue

            direction = _direction_from_regime(regime.get("regime"))
            if direction == "NEUTRAL":
                self._equity_curve.append((d, capital))
                continue

            spot = float(signal.get("spot", 0.0) or 0.0)
            if spot <= 0:
                self._equity_curve.append((d, capital))
                continue

            # Position sizing
            position_size = self._compute_position_size(
                signal=signal,
                regime=regime,
                direction=direction,
                portfolio=portfolio,
                corr_matrix=corr_matrix,
                use_kelly=use_kelly,
                use_stress_controls=use_stress_controls,
                use_correlation_adjustment=use_correlation_adjustment,
            )

            if position_size <= 0.0:
                self._equity_curve.append((d, capital))
                continue

            # Stop / take-profit levels
            stop_level = self._compute_stop_level(
                spot=spot,
                direction=direction,
                signal=signal,
                regime=regime,
            )

            take_profit: float | None = None
            if stop_level is not None:
                stop_dist = abs(stop_level - spot)
                if direction == "LONG":
                    take_profit = spot + stop_dist * _RR_RATIO
                else:
                    take_profit = spot - stop_dist * _RR_RATIO

            # Simulate trade
            actual_future: list[dict[str, Any]] = []
            for i in range(1, _MAX_HOLD_DAYS + 1):
                pd = d + timedelta(days=i)
                if pd in price_map:
                    actual_future.append({"date": pd, **price_map[pd]})
                else:
                    # Skip non-trading days; if we run out of data, pad with last known
                    if actual_future:
                        last = actual_future[-1].copy()
                        last["date"] = pd
                        actual_future.append(last)
                    else:
                        actual_future.append(
                            {"date": pd, "open": spot, "high": spot, "low": spot, "close": spot}
                        )

            trade = self._simulate_trade(
                entry_date=d,
                direction=direction,
                position_size=position_size,
                stop_level=stop_level,
                historical_prices=actual_future,
                entry_spot=spot,
                take_profit=take_profit,
            )

            # Update capital
            if trade.pnl_bps is not None:
                pnl_decimal = trade.pnl_bps / 10_000.0
                capital = capital * (1.0 + pnl_decimal)

            self._trade_history.append(trade)
            self._equity_curve.append((d, capital))

            # Update running stats for next Kelly iteration
            if trade.pnl_bps is not None:
                if trade.pnl_bps > 0:
                    self._running_wins += 1
                    self._running_win_bps.append(trade.pnl_bps)
                else:
                    self._running_losses += 1
                    self._running_loss_bps.append(abs(trade.pnl_bps))

            # Update portfolio for correlation tracking
            portfolio[self.pair] = position_size if direction == "LONG" else -position_size

            # Brier / calibration from regime confidence
            confidence = float(regime.get("confidence", 0.0) or 0.0)
            if trade.pnl_bps is not None:
                correct = trade.pnl_bps > 0
                p = float(np.clip(confidence, 0.0, 1.0))
                brier_scores.append((p - (1.0 if correct else 0.0)) ** 2)
                calibration_errors.append(abs(p - (1.0 if correct else 0.0)))

        return self._build_result(
            start_date=date.fromisoformat(str(historical_signals[0]["date"])[:10]),
            end_date=date.fromisoformat(str(historical_signals[-1]["date"])[:10]),
            brier_scores=brier_scores,
            calibration_errors=calibration_errors,
        )

    def _simulate_trade(
        self,
        entry_date: date,
        direction: str,
        position_size: float,
        stop_level: float | None,
        historical_prices: list[dict[str, Any]],
        entry_spot: float,
        take_profit: float | None,
    ) -> TradeRecord:
        """Simulate a single trade through T+20 or until stop/take-profit."""
        if not historical_prices:
            return TradeRecord(
                date=entry_date,
                pair=self.pair,
                direction=direction,
                entry_price=entry_spot,
                exit_price=entry_spot,
                position_size=position_size,
                stop_level=stop_level,
                take_profit=take_profit,
                pnl_bps=0.0,
                exit_reason="TIME",
            )

        dir_mult = 1.0 if direction == "LONG" else -1.0
        exit_reason = "TIME"
        exit_price = historical_prices[-1].get("close", entry_spot)

        for bar in historical_prices:
            hi = float(bar.get("high", 0.0) or 0.0)
            lo = float(bar.get("low", 0.0) or 0.0)
            if hi <= 0 or lo <= 0:
                continue

            # Stop hit
            if stop_level is not None:
                if direction == "LONG" and lo <= stop_level:
                    exit_price = stop_level * (1.0 - self.slippage_bps / 10_000.0)
                    exit_reason = "STOP"
                    break
                if direction == "SHORT" and hi >= stop_level:
                    exit_price = stop_level * (1.0 + self.slippage_bps / 10_000.0)
                    exit_reason = "STOP"
                    break

            # Take-profit hit
            if take_profit is not None:
                if direction == "LONG" and hi >= take_profit:
                    exit_price = take_profit * (1.0 - self.slippage_bps / 10_000.0)
                    exit_reason = "TP"
                    break
                if direction == "SHORT" and lo <= take_profit:
                    exit_price = take_profit * (1.0 + self.slippage_bps / 10_000.0)
                    exit_reason = "TP"
                    break

        # Transaction cost on round-trip (entry + exit)
        tc_decimal = (self.transaction_cost_bps + self.slippage_bps) / 10_000.0
        gross_return = (exit_price / entry_spot - 1.0) * dir_mult if entry_spot > 0 else 0.0
        net_return = gross_return - tc_decimal * 2.0
        pnl_bps = net_return * 10_000.0

        return TradeRecord(
            date=entry_date,
            pair=self.pair,
            direction=direction,
            entry_price=entry_spot,
            exit_price=exit_price,
            position_size=position_size,
            stop_level=stop_level,
            take_profit=take_profit,
            pnl_bps=float(pnl_bps),
            exit_reason=exit_reason,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _compute_position_size(
        self,
        signal: dict[str, Any],
        regime: dict[str, Any],
        direction: Layer2DirectionalBias,
        portfolio: dict[str, float],
        corr_matrix: dict[str, dict[str, float]],
        *,
        use_kelly: bool,
        use_stress_controls: bool,
        use_correlation_adjustment: bool,
    ) -> float:
        """Return position size as fraction of capital."""
        # Base size from conviction (fallback to composite magnitude)
        conviction = int(regime.get("conviction", 0) or 0)
        composite = float(regime.get("composite", 0.0) or 0.0)
        base_size = min(abs(composite), 1.0)
        if conviction >= 4:
            base_size = max(base_size, 0.75)
        elif conviction >= 3:
            base_size = max(base_size, 0.50)
        else:
            base_size = max(base_size, 0.25)

        if use_kelly:
            win_rate, avg_win, avg_loss = self._running_stats()
            kelly = kelly_fraction(
                win_rate=win_rate,
                avg_win_bps=avg_win,
                avg_loss_bps=avg_loss,
                safety_factor=0.25,
                max_risk=0.01,
            )
            base_size *= kelly * 100.0  # Scale to fraction of capital

        # Stress controls
        if use_stress_controls:
            vix = signal.get("cross_asset_vix")
            dxy_chg = signal.get("day_change_pct")  # proxy overnight
            pair_chg = abs(float(signal.get("day_change_pct", 0.0) or 0.0))
            stress = assess_stress_mode(
                vix=float(vix) if vix is not None else None,
                dxy_overnight_pct=float(dxy_chg) if dxy_chg is not None else None,
                max_pair_overnight_pct=pair_chg,
                correlation_matrix=corr_matrix if use_correlation_adjustment else None,
            )
            if stress["is_stress"]:
                base_size = min(base_size, stress["max_position_size"])

        # Correlation adjustment
        if use_correlation_adjustment:
            base_size = correlation_adjusted_size(base_size, self.pair, portfolio, corr_matrix)

        # Hard cap
        return float(np.clip(base_size, 0.0, 0.02))

    def _compute_stop_level(
        self,
        spot: float,
        direction: Layer2DirectionalBias,
        signal: dict[str, Any],
        regime: dict[str, Any],
    ) -> float | None:
        """Compute stop price using pair-specific execution logic."""
        if direction == "NEUTRAL" or spot <= 0:
            return None

        # Build minimal spot bars from recent signal history (not available here),
        # so fall back to ATR proxy from realized vol.
        rv20 = signal.get("realized_vol_20d")
        atr_proxy = float(rv20) / math.sqrt(252.0) * spot if rv20 is not None else None

        thresholds = pair_specific_thresholds(self.pair)
        adr_mult = float(thresholds.get("adr_multiplier", 1.0))

        # ADR proxy: 1.5 × daily vol × spot
        adr_proxy = float(rv20) / math.sqrt(252.0) * spot * 1.5 if rv20 is not None else None

        parts: list[float] = []
        if adr_proxy is not None and adr_proxy > 0.0:
            parts.append(adr_mult * adr_proxy)
        if atr_proxy is not None and atr_proxy > 0.0:
            parts.append(atr_proxy)

        if not parts:
            # Fallback: 0.5 % stop
            parts.append(spot * 0.005)

        buf = max(parts)
        if direction == "LONG":
            return spot - buf
        return spot + buf

    def _running_stats(self) -> tuple[float, float, float]:
        """Return (win_rate, avg_win_bps, avg_loss_bps) from closed trades."""
        total = self._running_wins + self._running_losses
        if total == 0:
            return _DEFAULT_WIN_RATE, _DEFAULT_AVG_WIN_BPS, _DEFAULT_AVG_LOSS_BPS
        win_rate = self._running_wins / total
        avg_win = (
            float(np.mean(self._running_win_bps)) if self._running_win_bps else _DEFAULT_AVG_WIN_BPS
        )
        avg_loss = (
            float(np.mean(self._running_loss_bps))
            if self._running_loss_bps
            else _DEFAULT_AVG_LOSS_BPS
        )
        return win_rate, avg_win, avg_loss

    def _build_result(
        self,
        start_date: date,
        end_date: date,
        brier_scores: list[float],
        calibration_errors: list[float],
    ) -> BacktestResult:
        trades = [t for t in self._trade_history if t.pnl_bps is not None]
        total_trades = len(trades)
        wins = [t for t in trades if t.pnl_bps > 0]
        losses = [t for t in trades if t.pnl_bps <= 0]

        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
        avg_win_bps = float(np.mean([t.pnl_bps for t in wins])) if wins else 0.0
        avg_loss_bps = float(np.mean([t.pnl_bps for t in losses])) if losses else 0.0

        # Sharpe from daily equity changes
        equity_values = [e for _, e in self._equity_curve]
        daily_returns = np.diff(equity_values) / np.array(equity_values[:-1])
        daily_returns = daily_returns[np.isfinite(daily_returns)]
        sharpe = 0.0
        if len(daily_returns) > 1:
            mean_ret = float(np.mean(daily_returns))
            std_ret = float(np.std(daily_returns, ddof=1))
            if std_ret > 0:
                sharpe = (mean_ret / std_ret) * math.sqrt(252.0)

        # Max drawdown
        peak = equity_values[0]
        max_dd = 0.0
        for val in equity_values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Profit factor
        gross_profit = sum(t.pnl_bps for t in wins) if wins else 0.0
        gross_loss = abs(sum(t.pnl_bps for t in losses)) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        brier = float(np.mean(brier_scores)) if brier_scores else None
        cal_err = float(np.mean(calibration_errors)) if calibration_errors else None

        return BacktestResult(
            pair=self.pair,
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            win_rate=win_rate,
            avg_win_bps=avg_win_bps,
            avg_loss_bps=avg_loss_bps,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd * 100.0,
            profit_factor=profit_factor,
            equity_curve=self._equity_curve,
            trades=self._trade_history,
            brier_score=brier,
            calibration_error=cal_err,
        )

    def _empty_result(self) -> BacktestResult:
        return BacktestResult(
            pair=self.pair,
            start_date=date.min,
            end_date=date.min,
            total_trades=0,
            win_rate=0.0,
            avg_win_bps=0.0,
            avg_loss_bps=0.0,
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            profit_factor=0.0,
            equity_curve=[],
            trades=[],
            brier_score=None,
            calibration_error=None,
        )
