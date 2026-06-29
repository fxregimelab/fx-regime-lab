"""Pure invalidation breach and persistence logic for desk open cards."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.desk.invalidation_types import BreachInput, InvalidationDecision, StreakState

INVALIDATION_VOL_MULTIPLIER = 1.5
INVALIDATION_PERSISTENCE_TICKS = 3
OFFLINE_FAILURE_THRESHOLD = 3


class InvalidationEvaluator:
    """Stateless evaluator for overnight invalidation flags."""

    def __init__(
        self,
        *,
        vol_multiplier: float = INVALIDATION_VOL_MULTIPLIER,
        persistence_ticks: int = INVALIDATION_PERSISTENCE_TICKS,
    ) -> None:
        self._vol_multiplier = vol_multiplier
        self._persistence_ticks = persistence_ticks

    @staticmethod
    def compute_vix_trigger(
        live_vix: float | None,
        baseline_vix: float | None,
        vol_ref: float,
        *,
        vol_multiplier: float = INVALIDATION_VOL_MULTIPLIER,
    ) -> bool:
        if (
            live_vix is None
            or baseline_vix is None
            or baseline_vix == 0.0
            or vol_ref <= 0.0
        ):
            return False
        vix_change_pct = ((live_vix / baseline_vix) - 1.0) * 100.0
        return abs(vix_change_pct) > vol_ref * vol_multiplier

    @staticmethod
    def resolve_vix_trigger_from_signals(
        live_vix: float | None,
        signal_rows: Iterable[Mapping[str, Any]],
        *,
        vol_multiplier: float = INVALIDATION_VOL_MULTIPLIER,
    ) -> bool:
        baseline_vix = None
        vol_ref = 0.0
        for signal_row in signal_rows:
            if baseline_vix is None and signal_row.get("cross_asset_vix") is not None:
                baseline_vix = float(signal_row["cross_asset_vix"])
            rv20 = signal_row.get("realized_vol_20d")
            if isinstance(rv20, (int, float)):
                vol_ref = max(vol_ref, float(rv20))
        return InvalidationEvaluator.compute_vix_trigger(
            live_vix,
            baseline_vix,
            vol_ref,
            vol_multiplier=vol_multiplier,
        )

    def evaluate(
        self,
        breach_input: BreachInput,
        streak_state: StreakState,
    ) -> InvalidationDecision:
        if breach_input.ny_close == 0.0:
            raise ValueError("ny_close must be non-zero to compute day_change_pct")
        day_change_pct = ((breach_input.live_spot / breach_input.ny_close) - 1.0) * 100.0
        vol_threshold = breach_input.realized_vol_20d * self._vol_multiplier
        pair_trigger = abs(day_change_pct) > vol_threshold
        breach = pair_trigger or breach_input.vix_trigger

        if breach:
            new_streak = streak_state.streak_count + 1
        else:
            new_streak = 0

        invalidation = (
            breach_input.prev_invalidation_triggered
            or new_streak >= self._persistence_ticks
        )
        pending_invalidation = (
            breach
            and not invalidation
            and 0 < new_streak < self._persistence_ticks
        )

        return InvalidationDecision(
            breach=breach,
            pair_trigger=pair_trigger,
            day_change_pct=day_change_pct,
            vol_threshold=vol_threshold,
            new_streak_count=new_streak,
            invalidation_triggered=invalidation,
            pending_invalidation=pending_invalidation,
        )
