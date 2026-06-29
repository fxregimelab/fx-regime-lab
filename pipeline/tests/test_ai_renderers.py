"""Unit tests for AI artifact renderers (prompt shape + parsers)."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest

from src.ai.renderers.desk_card import (
    DeskCardInput,
    DeskCardRenderer,
    deterministic_desk_card_brief,
    parse_desk_card_json,
)
from src.ai.renderers.event_brief import (
    EventBriefInput,
    EventBriefRenderer,
    deterministic_event_brief,
    parse_event_brief_json,
)
from src.ai.renderers.memo import MemoInput, MemoRenderer, parse_weekly_memo_thesis
from src.ai.renderers.pair_brief import PairBriefInput, PairBriefRenderer
from src.types import SignalRow


def test_parse_desk_card_json_valid() -> None:
    raw = json.dumps(
        {
            "bias_summary": "BULLISH",
            "catalyst_driver": "2Y SPREAD",
            "squeeze_risk": "CONTROLLED (PAIN 41)",
        }
    )
    parsed = parse_desk_card_json(raw)
    assert parsed["bias_summary"] == "BULLISH"
    assert parsed["catalyst_driver"] == "2Y SPREAD"


def test_parse_desk_card_json_rejects_missing_key() -> None:
    raw = json.dumps({"bias_summary": "BULLISH", "catalyst_driver": "X"})
    with pytest.raises(ValueError, match="Missing/invalid key: squeeze_risk"):
        parse_desk_card_json(raw)


def test_deterministic_desk_card_brief_dollar_suffix() -> None:
    raw = deterministic_desk_card_brief(
        "MODERATE USD STRENGTH",
        "2Y SPREAD",
        82.0,
        dollar_dominance_score=0.85,
        dollar_bias="Strength",
    )
    parsed = json.loads(raw)
    assert "DOLLAR STRENGTH" in parsed["bias_summary"]
    assert "ELEVATED" in parsed["squeeze_risk"]


def test_desk_card_renderer_prompt_contains_pair_and_regime() -> None:
    renderer = DeskCardRenderer()
    input_data = DeskCardInput(
        pair="EURUSD",
        regime="MODERATE USD STRENGTH",
        date_str="2026-06-29",
        primary_driver="2Y SPREAD",
        pain_index=55.0,
    )
    with patch(
        "src.ai.renderers.desk_card.writer.get_latest_research_memo_thesis_bullets",
        return_value=[],
    ), patch(
        "src.ai.renderers.desk_card.writer.get_signal_for_pair_date", return_value=None
    ):
        messages = renderer.build_messages(input_data)
    prompt = messages[0]["content"]
    assert "PAIR:EURUSD" in prompt
    assert "REGIME:MODERATE USD STRENGTH" in prompt
    assert "No weekly Structural Thesis is available" in prompt


def test_parse_event_brief_json_valid() -> None:
    raw = json.dumps(
        {
            "volatility_profile": "Elevated vol expected.",
            "asymmetric_setup": "Upside skew.",
            "execution_note": "Reduce size.",
        }
    )
    out = parse_event_brief_json(raw)
    parsed = json.loads(out)
    assert parsed["execution_note"] == "Reduce size."


def test_deterministic_event_brief_uses_mie() -> None:
    raw = deterministic_event_brief(1.42)
    parsed = json.loads(raw)
    assert "1.42x" in parsed["volatility_profile"]


def test_event_brief_renderer_prompt_contains_event_fields() -> None:
    renderer = EventBriefRenderer()
    input_data = EventBriefInput(
        risk_matrix={
            "event_name": "US CPI YoY",
            "pair": "EURUSD",
            "active_regime": "RANGE",
            "sample_size": 12,
            "median_mie_multiplier": 1.5,
            "asymmetry_ratio": 1.2,
            "asymmetry_direction": "UP",
        },
        date_str="2026-06-29",
    )
    messages = renderer.build_messages(input_data)
    prompt = messages[0]["content"]
    assert "EVENT:US CPI YoY" in prompt
    assert "PAIR:EURUSD" in prompt
    assert "MEDIAN_MIE_MULTIPLIER:1.5000" in prompt


def test_parse_weekly_memo_thesis_object_form() -> None:
    raw = json.dumps({"theses": ["a", "b", "c", "d", "e"]})
    assert parse_weekly_memo_thesis(raw) == ["a", "b", "c", "d", "e"]


def test_parse_weekly_memo_thesis_rejects_wrong_count() -> None:
    raw = json.dumps({"theses": ["a", "b"]})
    with pytest.raises(ValueError, match="Expected exactly 5"):
        parse_weekly_memo_thesis(raw)


def test_memo_renderer_prompt_caps_text() -> None:
    renderer = MemoRenderer()
    long_text = "x" * 130_000
    messages = renderer.build_messages(MemoInput(raw_text=long_text, date_str="2026-06-29"))
    prompt = messages[0]["content"]
    assert "MEMO_TEXT:" in prompt
    assert len(prompt) < 125_000


def test_pair_brief_renderer_prompt_includes_polymarket() -> None:
    renderer = PairBriefRenderer()
    signal_row = SignalRow(
        pair="EURUSD",
        date=date(2026, 6, 29),
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
    input_data = PairBriefInput(
        pair="EURUSD",
        regime="RANGE",
        confidence=0.65,
        composite=0.12,
        signal_row=signal_row,
        date_str="2026-06-29",
        polymarket_odds_json='[{"market":"fed"}]',
    )
    prompt = renderer.build_messages(input_data)[0]["content"]
    assert "POLYMARKET_ODDS_JSON" in prompt
    assert "EURUSD" in prompt
