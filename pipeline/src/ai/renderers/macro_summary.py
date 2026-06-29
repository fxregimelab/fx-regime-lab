"""Global macro summary brief renderer."""

from __future__ import annotations

from dataclasses import dataclass

from src.ai.providers.groq import GROQ_PRIMARY_MODEL


@dataclass(frozen=True, slots=True)
class MacroSummaryInput:
    date_str: str
    pair_contexts: list[str]
    macro_context: str
    dollar_dominance_pct: float | None = None
    polymarket_odds_json: str = "[]"


class MacroSummaryRenderer:
    """Prompt builder for unified global macro briefs."""

    max_tokens = 220
    primary_model = GROQ_PRIMARY_MODEL
    purpose_name = "global_macro_summary"

    def build_messages(self, input_data: MacroSummaryInput) -> list[dict[str, str]]:
        dom_txt = (
            "null"
            if input_data.dollar_dominance_pct is None
            else f"{float(input_data.dollar_dominance_pct):.2f}"
        )
        prompt = (
            "TASK: Create a global FX macro summary in ~150 words.\n"
            f"DATE:{input_data.date_str}\n"
            f"PAIR_CONTEXTS:{' | '.join(input_data.pair_contexts)}\n"
            f"MACRO_CONTEXT:{input_data.macro_context}\n"
            f"DOLLAR_DOMINANCE_PCT:{dom_txt} "
            "(0\u2013100 book-wide USD thematic alignment from regime classifier metadata)\n"
            f"POLYMARKET_ODDS_JSON:{input_data.polymarket_odds_json}\n"
            "You MUST synthesize DOLLAR_DOMINANCE_PCT with POLYMARKET_ODDS_JSON: explain how "
            "prediction-market odds on Fed / recession / macro outcomes reconcile with or diverge "
            "from the dollar-factor read, and tie that to the day's FX impulse.\n"
            "INCLUDE: dominant cross-asset driver, where rates vs oil/10Y are shifting, "
            "and one key risk to monitor.\n"
            "OUTPUT: plain text only. No markdown. No headers."
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> str:
        return payload_text

    def purpose(self, input_data: MacroSummaryInput) -> str:
        _ = input_data
        return self.purpose_name
