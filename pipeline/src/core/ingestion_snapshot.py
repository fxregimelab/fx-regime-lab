"""Typed snapshot of all fetched market and macro inputs for a single pipeline date."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.types import CotRow, SpotBar


@dataclass(frozen=True)
class IngestionSnapshot:
    """All fetched market and macro inputs for a single pipeline date.

    This object isolates fetcher outputs from signal logic and downstream
    regime-call assembly. It is intentionally flat and immutable so that
    signal builders can depend on a stable contract.
    """

    date: date
    spots: dict[str, Sequence[SpotBar]]
    yields: dict[str, float | None]
    cot_rows: list[CotRow]
    cross_asset: dict[str, float | None]
    macro: dict[str, Any] | None = None
    dqs_score: float | None = None
    stress_level: str | None = None

    def spot_bars_for(self, pair: str) -> Sequence[SpotBar]:
        """Return the spot bar sequence for ``pair`` (empty if missing)."""

        return self.spots.get(pair, ())

    def today_bar_for(self, pair: str) -> SpotBar | None:
        """Return the bar matching ``snapshot.date`` for ``pair``, or the latest bar."""

        bars = self.spot_bars_for(pair)
        if not bars:
            return None
        for bar in bars:
            if bar.date == self.date:
                return bar
        return bars[-1]

    def yesterday_bar_for(self, pair: str) -> SpotBar | None:
        """Return the bar immediately preceding ``today_bar_for(pair)``."""

        bars = self.spot_bars_for(pair)
        today = self.today_bar_for(pair)
        if today is None:
            return None
        for idx, bar in enumerate(bars):
            if bar is today or bar.date == today.date:
                return bars[idx - 1] if idx >= 1 else today
        return None

    def macro_value(self, key: str) -> Any | None:
        """Safely read a macro value from the optional macro payload."""

        if self.macro is None:
            return None
        return self.macro.get(key)
