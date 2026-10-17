"""Tests for the LLM reader eval harness (pure, no DB, no network)."""

from __future__ import annotations

from typing import Any

from src.ai.renderers.analyst_note import AnalystNoteInput, deterministic_analyst_note
from src.eval.llm_reader_eval import (
    brier_on_conviction,
    evaluate_notes,
    number_accuracy,
    score_faithfulness,
)


def _frozen(pair: str = "EURUSD") -> dict[str, Any]:
    return {
        "pair": pair,
        "date_str": "2026-10-17",
        "regime": "RANGE",
        "confidence": 0.62,
        "signal_composite": 0.18,
        "composite": 0.18,
        "primary_driver": "2Y SPREAD",
        "model_version": "fx-live-personal-v1",
    }


def test_faithfulness_rewards_citations_and_penalizes_advice() -> None:
    frozen = _frozen()
    note = deterministic_analyst_note(
        AnalystNoteInput(
            pair="EURUSD",
            date_str="2026-10-17",
            regime="RANGE",
            confidence=0.62,
            composite=0.18,
            primary_driver="2Y SPREAD",
            brief_text="x",
        )
    )
    assert score_faithfulness(note, frozen) >= 0.75
    assert score_faithfulness("BUY NOW SELL NOW x", frozen) < 0.5


def test_number_accuracy_matches_within_tolerance() -> None:
    frozen = _frozen()
    note = deterministic_analyst_note(
        AnalystNoteInput(
            pair="EURUSD",
            date_str="2026-10-17",
            regime="RANGE",
            confidence=0.62,
            composite=0.18,
            primary_driver="2Y SPREAD",
            brief_text="x",
        )
    )
    assert number_accuracy(note, frozen) is True
    assert number_accuracy("no numbers here", frozen) is False


def test_brier_skips_null_outcomes() -> None:
    rows: list[dict[str, Any]] = [
        {"confidence": 0.8, "outcome": 1},
        {"confidence": 0.6, "outcome": 0},
        {"confidence": 0.5, "outcome": None},
    ]
    out = brier_on_conviction(rows)
    assert out["n"] == 2 and out["skipped"] == 1
    assert abs(out["mean_brier"] - (((0.2**2) + (0.6**2)) / 2)) < 1e-9


def test_evaluate_notes_versioned_per_pair() -> None:
    rows = []
    for pair in ("EURUSD", "USDJPY", "USDINR"):
        frozen = _frozen(pair)
        note = deterministic_analyst_note(
            AnalystNoteInput(
                pair=pair,
                date_str="2026-10-17",
                regime="RANGE",
                confidence=0.62,
                composite=0.18,
                primary_driver="2Y SPREAD",
                brief_text="x",
            )
        )
        rows.append({**frozen, "note": note, "outcome": 1})
    result = evaluate_notes(rows)
    assert result["n"] == 3
    assert set(result["per_pair"]) == {"EURUSD", "USDJPY", "USDINR"}
    assert "fx-live-personal-v1" in result["versions"]
