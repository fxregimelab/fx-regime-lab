"""Typed outcomes returned by scheduler entry points."""

from __future__ import annotations

from dataclasses import dataclass

from src.staged.contracts import StageHealth


@dataclass(frozen=True)
class DailyRunOutput:
    """Observable result of one legacy daily pipeline invocation."""

    date: str
    published_pairs: tuple[str, ...]
    dqs_score: float | None
    health: StageHealth
    stage_health: tuple[StageHealth, ...]
