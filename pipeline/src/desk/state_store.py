"""Persistence port for overnight telemetry state."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol


def _coerce_streak_dict(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = int(v)
        except (TypeError, ValueError):
            continue
    return out


@dataclass(frozen=True, slots=True)
class OvernightState:
    consecutive_failures: int = 0
    invalidation_streak: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.invalidation_streak is None:
            object.__setattr__(self, "invalidation_streak", {})

    def with_failures(self, consecutive_failures: int) -> OvernightState:
        return replace(self, consecutive_failures=max(0, consecutive_failures))

    def with_streaks(self, invalidation_streak: dict[str, int]) -> OvernightState:
        return replace(
            self,
            invalidation_streak={k: int(v) for k, v in invalidation_streak.items()},
        )


class StateStore(Protocol):
    def load(self) -> OvernightState: ...

    def save(self, state: OvernightState) -> None: ...


class FileStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (
            Path(tempfile.gettempdir()) / "fx_regime_lab_overnight_state.json"
        )

    def load(self) -> OvernightState:
        if not self._path.exists():
            return OvernightState()
        try:
            parsed = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return OvernightState()
        cf_raw = parsed.get("consecutive_failures", 0)
        streaks = _coerce_streak_dict(parsed.get("invalidation_streak", {}))
        consecutive_failures = int(cf_raw) if isinstance(cf_raw, int) else 0
        return OvernightState(
            consecutive_failures=consecutive_failures,
            invalidation_streak=streaks,
        )

    def save(self, state: OvernightState) -> None:
        streaks = state.invalidation_streak or {}
        payload: dict[str, Any] = {
            "consecutive_failures": max(0, state.consecutive_failures),
            "invalidation_streak": {k: int(v) for k, v in streaks.items()},
        }
        self._path.write_text(json.dumps(payload), encoding="utf-8")


class InMemoryStateStore:
    def __init__(self, initial: OvernightState | None = None) -> None:
        self._state = initial or OvernightState()

    def load(self) -> OvernightState:
        streaks = self._state.invalidation_streak or {}
        return OvernightState(
            consecutive_failures=self._state.consecutive_failures,
            invalidation_streak=dict(streaks),
        )

    def save(self, state: OvernightState) -> None:
        streaks = state.invalidation_streak or {}
        self._state = OvernightState(
            consecutive_failures=state.consecutive_failures,
            invalidation_streak=dict(streaks),
        )
