"""Ingestion quorum and buffer validation (no network)."""

from __future__ import annotations

import datetime

from src.fetchers.buffer_keys import KEY_FX_SPOT
from src.types import SpotBar
from src.validation.ingestion_buffer import validate_ingestion_buffer


def _universe_stub(*, n: int) -> dict[str, object]:
    return {f"P{i}": {"class": "FX"} for i in range(n)}


def _bar(close: float = 1.0) -> SpotBar:
    d = datetime.date(2026, 1, 15)
    return SpotBar(date=d, pair="PX", open=close, high=close, low=close, close=close)


def test_quorum_offline_when_gt_20pct_missing() -> None:
    u = _universe_stub(n=7)
    spots = {f"P{i}": [_bar()] for i in range(5)}
    spots["P5"] = []
    spots["P6"] = []
    buf = {KEY_FX_SPOT: spots}
    gate = validate_ingestion_buffer(buf, universe=u)
    assert gate.telemetry_status == "OFFLINE"


def test_quorum_online_drops_poisoned_pair() -> None:
    u = _universe_stub(n=7)
    spots: dict[str, list[SpotBar]] = {f"P{i}": [_bar()] for i in range(7)}
    spots["P6"] = []
    buf = {KEY_FX_SPOT: spots}
    gate = validate_ingestion_buffer(buf, universe=u)
    assert gate.telemetry_status == "ONLINE"
    fx = gate.buffer[KEY_FX_SPOT]
    assert isinstance(fx, dict)
    assert "P6" not in fx
    assert isinstance(fx["P0"], tuple)


def test_quorum_online_when_failures_at_20pct_boundary() -> None:
    """1/5 = 20% is not *greater than* 20%, so we stay ONLINE and drop the bad row."""
    u = _universe_stub(n=5)
    spots = {f"P{i}": [_bar()] for i in range(4)}
    spots["P4"] = []
    buf = {KEY_FX_SPOT: spots}
    gate = validate_ingestion_buffer(buf, universe=u)
    assert gate.telemetry_status == "ONLINE"
    assert "P4" not in gate.buffer[KEY_FX_SPOT]
