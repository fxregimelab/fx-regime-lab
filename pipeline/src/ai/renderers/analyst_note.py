"""Frozen 5-line analyst note renderer (FX live personal slice).

Input is a frozen regime call plus brief text. Output is a 5-line analyst
note with cited inputs. No new signals. No new pairs. 3-pair lock enforced.

All AI calls go through ``pipeline/src/ai/client.py`` (AIClient.render).
This module never touches providers, DB, or secrets directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ai.providers.groq import GROQ_PRIMARY_MODEL

ALLOWED_PAIRS = ("EURUSD", "USDJPY", "USDINR")

__all__ = [
    "ALLOWED_PAIRS",
    "AnalystNoteInput",
    "AnalystNoteRenderer",
    "deterministic_analyst_note",
    "parse_analyst_note",
]


def _normalize_pair(pair: str) -> str:
    return pair.replace("/", "").replace("_", "").upper()


@dataclass(frozen=True, slots=True)
class AnalystNoteInput:
    pair: str
    date_str: str
    regime: str
    confidence: float
    composite: float
    primary_driver: str | None = None
    brief_text: str = ""
    model_version: str = "fx-live-personal-v1"


class AnalystNoteRenderer:
    """Prompt builder for the single LLM reader slice."""

    max_tokens = 220
    primary_model = GROQ_PRIMARY_MODEL

    def build_messages(self, input_data: AnalystNoteInput) -> list[dict[str, str]]:
        pair = _normalize_pair(input_data.pair)
        if pair not in ALLOWED_PAIRS:
            raise ValueError(f"3-pair lock: unsupported pair {input_data.pair!r}")
        brief = (input_data.brief_text or "")[:1200]
        prompt = (
            "TASK: FX analyst note. Exactly 5 lines. Under 120 words total.\n"
            f"PAIR:{pair} DATE:{input_data.date_str}\n"
            f"REGIME:{input_data.regime} CONF:{input_data.confidence:.0%} "
            f"COMPOSITE:{input_data.composite:+.2f}\n"
            f"PRIMARY_DRIVER:{input_data.primary_driver or 'unknown'} "
            f"MODEL:{input_data.model_version}\n"
            f"BRIEF:{brief}\n"
            "STRUCTURE: L1 regime+conviction L2 primary driver L3 key level/risk "
            "L4 what would invalidate L5 cited inputs.\n"
            "RULES: Cite at least 2 inputs as [REGIME] [CONF] [COMPOSITE] "
            "[DRIVER] [BRIEF]. No new signals. No new pairs. "
            "No investment advice. No buy/sell language.\n"
            "OUTPUT: exactly 5 plain-text lines. No headers. No markdown."
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> str:
        return parse_analyst_note(payload_text)

    def purpose(self, input_data: AnalystNoteInput) -> str:
        return f"analyst-note-{_normalize_pair(input_data.pair).lower()}"


def parse_analyst_note(payload_text: str) -> str:
    """Validate exactly 5 non-empty lines; raise ValueError otherwise."""
    lines = [ln.strip() for ln in payload_text.strip().splitlines() if ln.strip()]
    if len(lines) != 5:
        raise ValueError(f"Expected exactly 5 lines, got {len(lines)}")
    return "\n".join(lines)


def deterministic_analyst_note(input_data: AnalystNoteInput) -> str:
    """Offline fallback: 5 lines, cites frozen inputs, no LLM call."""
    pair = _normalize_pair(input_data.pair)
    driver = input_data.primary_driver or "unknown"
    brief_flag = "brief-cited" if input_data.brief_text.strip() else "no-brief"
    return "\n".join(
        [
            f"1. {pair} {input_data.date_str}: {input_data.regime} "
            f"[REGIME] conviction {input_data.confidence:.0%} [CONF].",
            f"2. Primary driver {driver} [DRIVER]; "
            f"composite {input_data.composite:+.2f} [COMPOSITE].",
            "3. Key risk: crowded positioning or vol expansion; size HALF, WAIT "
            "on timing (research only, no advice).",
            "4. Invalidated if driver reverses and composite flips sign on "
            "next frozen call.",
            f"5. Sources: frozen call {input_data.model_version} + {brief_flag} "
            "[BRIEF].",
        ]
    )
