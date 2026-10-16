"""Frozen types for desk-card invalidation evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BreachInput:
    live_spot: float
    ny_close: float
    realized_vol_20d: float
    vix_trigger: bool
    prev_invalidation_triggered: bool = False


@dataclass(frozen=True, slots=True)
class StreakState:
    streak_count: int = 0


@dataclass(frozen=True, slots=True)
class InvalidationDecision:
    breach: bool
    pair_trigger: bool
    day_change_pct: float
    vol_threshold: float
    new_streak_count: int
    invalidation_triggered: bool
    pending_invalidation: bool
