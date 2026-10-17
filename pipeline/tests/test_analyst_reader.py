"""Tests for the single LLM reader slice (mocked, no DB, no network)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.ai.analyst_reader import generate_analyst_note, generate_analyst_note_async
from src.ai.renderers.analyst_note import (
    AnalystNoteInput,
    AnalystNoteRenderer,
    deterministic_analyst_note,
    parse_analyst_note,
)
from src.types import SignalRow


def _input() -> AnalystNoteInput:
    return AnalystNoteInput(
        pair="EURUSD",
        date_str="2026-10-17",
        regime="RANGE",
        confidence=0.62,
        composite=0.18,
        primary_driver="2Y SPREAD",
        brief_text="Rates steady, positioning crowded.",
    )


def test_renderer_prompt_cites_pair_and_inputs() -> None:
    prompt = AnalystNoteRenderer().build_messages(_input())[0]["content"]
    assert "PAIR:EURUSD" in prompt
    assert "REGIME:RANGE" in prompt
    assert "No investment advice" in prompt


def test_renderer_rejects_fourth_pair() -> None:
    bad = AnalystNoteInput(
        pair="GBPUSD",
        date_str="2026-10-17",
        regime="RANGE",
        confidence=0.5,
        composite=0.0,
    )
    with pytest.raises(ValueError, match="3-pair lock"):
        AnalystNoteRenderer().build_messages(bad)


def test_parse_requires_exactly_five_lines() -> None:
    with pytest.raises(ValueError, match="Expected exactly 5"):
        parse_analyst_note("only\ntwo lines")
    good = "a\nb\nc\nd\ne"
    assert parse_analyst_note(good) == good


def test_deterministic_fallback_has_five_lines_and_citations() -> None:
    note = deterministic_analyst_note(_input())
    assert len(note.splitlines()) == 5
    assert "[REGIME]" in note and "[CONF]" in note


def test_reader_uses_client_and_returns_five_lines() -> None:
    class FakeClient:
        def render(self, renderer: Any, input_data: Any, *, date_str: str) -> str:
            assert date_str == "2026-10-17"
            return "l1\nl2\nl3\nl4\nl5"

    out = generate_analyst_note(
        pair="EURUSD",
        date_str="2026-10-17",
        regime="RANGE",
        confidence=0.62,
        composite=0.18,
        client=FakeClient(),  # type: ignore[arg-type]
    )
    assert out.splitlines() == ["l1", "l2", "l3", "l4", "l5"]


def test_reader_falls_back_offline_without_secrets() -> None:
    class BoomClient:
        def render(self, renderer: Any, input_data: Any, *, date_str: str) -> str:
            raise RuntimeError("no keys in test env")

    out = generate_analyst_note(
        pair="USDJPY",
        date_str="2026-10-17",
        regime="CARRY INTACT",
        confidence=0.55,
        composite=0.10,
        client=BoomClient(),  # type: ignore[arg-type]
    )
    assert len(out.splitlines()) == 5


def test_async_reader_falls_back() -> None:
    import asyncio

    class BoomAsync:
        async def render_async(self, renderer: Any, input_data: Any, *, date_str: str) -> str:
            raise RuntimeError("offline")

    out = asyncio.run(
        generate_analyst_note_async(
            pair="USDINR",
            date_str="2026-10-17",
            regime="MANAGED RANGE",
            confidence=0.5,
            composite=-0.05,
            client=BoomAsync(),  # type: ignore[arg-type]
        )
    )
    assert len(out.splitlines()) == 5


def test_pair_brief_signal_row_still_importable() -> None:
    row = SignalRow(
        pair="EURUSD",
        date=date(2026, 10, 17),
        rate_diff_2y=0.5,
        rate_diff_10y=0.3,
        cot_percentile=60.0,
        realized_vol_20d=8.0,
        realized_vol_5d=7.0,
        implied_vol_30d=None,
        spot=1.08,
        day_change=0.001,
        day_change_pct=0.1,
        cross_asset_vix=None,
        cross_asset_dxy=None,
        cross_asset_oil=75.0,
        cross_asset_us10y=None,
        cross_asset_gold=None,
        cross_asset_copper=None,
        cross_asset_stoxx=None,
        oi_delta=None,
    )
    assert row.pair == "EURUSD"
