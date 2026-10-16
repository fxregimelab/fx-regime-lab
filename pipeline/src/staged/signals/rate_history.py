"""RateHistoryProvider port and implementations for spread / carry history."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.staged.contracts import IngestionSnapshot

_SINGLE_POINT_REPEAT = 5


@runtime_checkable
class RateHistoryProvider(Protocol):
    """Provide spread and carry histories for rate normalization and Layer 1."""

    def spread_history(self, pair: str, spread: float) -> list[float]:
        """Oldest-first tactical spread history for MAD normalization."""

    def structural_history(self, spread_structural: float | None) -> list[float] | None:
        """Oldest-first structural spread history, or None when unavailable."""

    def carry_series(
        self,
        risk_adjusted_carry: float | None,
        *,
        min_length: int,
    ) -> tuple[float, ...]:
        """Chronological carry series for Layer 1 classifier."""

    def bei_series(
        self,
        breakeven_inflation: float | None,
        *,
        min_length: int,
    ) -> tuple[float, ...] | None:
        """Chronological breakeven-inflation series for Layer 1, or None."""


class SinglePointFallbackProvider:
    """Explicit single-point fallback: repeat current value for MAD floor.

    When no historical spread series is available, repeats the current spread
    ``_SINGLE_POINT_REPEAT`` times so MAD hits the noise floor and Z=0.
    """

    def spread_history(self, pair: str, spread: float) -> list[float]:
        del pair
        return [spread] * _SINGLE_POINT_REPEAT

    def structural_history(self, spread_structural: float | None) -> list[float] | None:
        if spread_structural is None:
            return None
        return [spread_structural] * _SINGLE_POINT_REPEAT

    def carry_series(
        self,
        risk_adjusted_carry: float | None,
        *,
        min_length: int,
    ) -> tuple[float, ...]:
        if risk_adjusted_carry is None:
            return ()
        return tuple(float(risk_adjusted_carry) for _ in range(min_length))

    def bei_series(
        self,
        breakeven_inflation: float | None,
        *,
        min_length: int,
    ) -> tuple[float, ...] | None:
        if breakeven_inflation is None:
            return None
        return tuple(float(breakeven_inflation) for _ in range(min_length))


class SnapshotRateHistoryProvider:
    """Rate history derived from an ingestion snapshot when possible.

    Falls back to ``SinglePointFallbackProvider`` when the snapshot lacks
    enough history for robust MAD estimation.
    """

    def __init__(self, snapshot: IngestionSnapshot) -> None:
        self._snapshot = snapshot
        self._fallback = SinglePointFallbackProvider()

    def spread_history(self, pair: str, spread: float) -> list[float]:
        # Snapshot currently carries only the as-of point; use explicit fallback.
        return self._fallback.spread_history(pair, spread)

    def structural_history(self, spread_structural: float | None) -> list[float] | None:
        return self._fallback.structural_history(spread_structural)

    def _spot_history_length(self) -> int:
        if not self._snapshot.spots:
            return 0
        return max(len(bars) for bars in self._snapshot.spots.values())

    def carry_series(
        self,
        risk_adjusted_carry: float | None,
        *,
        min_length: int,
    ) -> tuple[float, ...]:
        length = max(self._spot_history_length(), min_length)
        return self._fallback.carry_series(risk_adjusted_carry, min_length=length)

    def bei_series(
        self,
        breakeven_inflation: float | None,
        *,
        min_length: int,
    ) -> tuple[float, ...] | None:
        length = max(self._spot_history_length(), min_length)
        return self._fallback.bei_series(breakeven_inflation, min_length=length)
