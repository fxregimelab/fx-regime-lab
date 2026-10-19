"""Backtest package (research/measurement only; never imported by execution paths)."""

from __future__ import annotations

from src.paper.backtest.data import (
    DEFAULT_DATA_DIR,
    BarSeries,
    coverage_summary,
    load_bundle,
    load_pair,
    load_series,
)
from src.paper.backtest.engine import (
    BacktestConfig,
    BacktestResult,
    Trade,
    context_at,
    d1_context_series,
    evaluate_h1_bar,
    run_backtest,
    simulate_trade,
)

__all__ = [
    "DEFAULT_DATA_DIR",
    "BacktestConfig",
    "BacktestResult",
    "BarSeries",
    "Trade",
    "context_at",
    "coverage_summary",
    "d1_context_series",
    "evaluate_h1_bar",
    "load_bundle",
    "load_pair",
    "load_series",
    "run_backtest",
    "simulate_trade",
]
