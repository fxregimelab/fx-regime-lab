"""Unit tests for overnight StateStore implementations."""

from __future__ import annotations

import json
from pathlib import Path

from src.desk.state_store import FileStateStore, InMemoryStateStore, OvernightState


def test_in_memory_round_trip() -> None:
    store = InMemoryStateStore(
        OvernightState(consecutive_failures=1, invalidation_streak={"EURUSD": 2})
    )
    loaded = store.load()
    assert loaded.consecutive_failures == 1
    assert loaded.invalidation_streak == {"EURUSD": 2}

    store.save(OvernightState(consecutive_failures=0, invalidation_streak={"USDJPY": 1}))
    reloaded = store.load()
    assert reloaded.consecutive_failures == 0
    assert reloaded.invalidation_streak == {"USDJPY": 1}


def test_in_memory_load_returns_copy() -> None:
    store = InMemoryStateStore(OvernightState(invalidation_streak={"EURUSD": 1}))
    loaded = store.load()
    assert loaded.invalidation_streak is not None
    loaded.invalidation_streak["EURUSD"] = 99
    assert store.load().invalidation_streak == {"EURUSD": 1}


def test_file_state_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "overnight_state.json"
    store = FileStateStore(path)
    store.save(
        OvernightState(
            consecutive_failures=2,
            invalidation_streak={"EURUSD": 1, "USDJPY": 3},
        )
    )

    loaded = store.load()
    assert loaded.consecutive_failures == 2
    assert loaded.invalidation_streak == {"EURUSD": 1, "USDJPY": 3}

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw == {
        "consecutive_failures": 2,
        "invalidation_streak": {"EURUSD": 1, "USDJPY": 3},
    }


def test_file_state_store_missing_file_returns_defaults(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "missing.json")
    loaded = store.load()
    assert loaded.consecutive_failures == 0
    assert loaded.invalidation_streak == {}


def test_file_state_store_invalid_json_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not-json", encoding="utf-8")
    store = FileStateStore(path)
    loaded = store.load()
    assert loaded.consecutive_failures == 0
    assert loaded.invalidation_streak == {}


def test_overnight_state_with_failures_clamps_negative() -> None:
    state = OvernightState(consecutive_failures=1)
    assert state.with_failures(-5).consecutive_failures == 0


def test_file_state_store_coerces_streak_values(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "consecutive_failures": "3",
                "invalidation_streak": {"EURUSD": "2", "BAD": "x"},
            }
        ),
        encoding="utf-8",
    )
    store = FileStateStore(path)
    loaded = store.load()
    assert loaded.consecutive_failures == 0
    assert loaded.invalidation_streak == {"EURUSD": 2}
