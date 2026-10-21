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
    DetectionResult,
    PairCandidate,
    ReplayEvent,
    ReplayOutcome,
    ReplayState,
    Trade,
    context_at,
    d1_context_series,
    detect_candidates,
    evaluate_h1_bar,
    order_candidates,
    replay_candidates,
    run_backtest,
    simulate_trade,
)
from src.paper.backtest.portfolio import (
    JointConfig,
    JointResult,
    PairBars,
    TieBreak,
    replay_joint,
    run_joint_backtest,
    usd_sign,
)
from src.paper.backtest.report import (
    RESERVED_STEM,
    build_report,
    funnel,
    joint_to_results,
    per_setup_stats,
    render_markdown,
    semantics_block,
    trade_stats,
    weekly_summary,
    weekly_table,
    write_report,
)

__all__ = [
    # --- original exports (unchanged) ---
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
    # --- PD-00C1: the detection / event-time replay split ---
    "DetectionResult",
    "PairCandidate",
    "ReplayEvent",
    "ReplayOutcome",
    "ReplayState",
    "detect_candidates",
    "order_candidates",
    "replay_candidates",
    # --- PD-00C1: the joint (cross-pair) portfolio ---
    "JointConfig",
    "JointResult",
    "PairBars",
    "TieBreak",
    "replay_joint",
    "run_joint_backtest",
    "usd_sign",
    # --- PD-00C2: the settled-only report layer ---
    "RESERVED_STEM",
    "build_report",
    "funnel",
    "joint_to_results",
    "per_setup_stats",
    "render_markdown",
    "semantics_block",
    "trade_stats",
    "weekly_summary",
    "weekly_table",
    "write_report",
]
