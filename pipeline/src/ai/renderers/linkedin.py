"""LinkedIn alpha hook renderer."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.ai.providers.groq import GROQ_PRIMARY_MODEL


@dataclass(frozen=True, slots=True)
class LinkedInInput:
    card_data: dict[str, Any]
    date_str: str | None = None


class LinkedInRenderer:
    """Prompt builder for institutional LinkedIn posts."""

    max_tokens = 520
    primary_model = GROQ_PRIMARY_MODEL
    purpose_name = "linkedin_alpha_hook"

    def resolve_date_str(self, input_data: LinkedInInput) -> str:
        if input_data.date_str is not None:
            return input_data.date_str
        return str(input_data.card_data.get("date") or date.today().isoformat())

    def build_messages(self, input_data: LinkedInInput) -> list[dict[str, str]]:
        payload = json.dumps(input_data.card_data, ensure_ascii=False, default=str)
        base_url = os.environ.get("SITE_PUBLIC_URL", "https://fxregimelab.com").rstrip("/")
        prompt = (
            "You are an Institutional FX Strategist. Write a 1,200 character LinkedIn post "
            "based on the provided Apex Target data.\n"
            "STRICT CONSTRAINTS:\n"
            "- STRICTLY NO MARKETING FLUFF.\n"
            "- No emojis.\n"
            "- No hashtags.\n"
            "- Style: institutional shorthand only (e.g., \"1.5x MAD breach,\" \"COT extremes,\" "
            "\"Asymmetric Downside\").\n"
            "- Structure exactly four blocks separated by line breaks:\n"
            "  [REGIME ALERT] then [THE NUMBERS] then [THE SQUEEZE RISK] then [LINK]\n"
            "- In [LINK], give one plain URL: use pair slug from data (lowercase, e.g. eurusd) as "
            f"{base_url}/terminal/fx-regime/<slug>\n"
            f"APEX_TARGET_JSON:\n{payload}\n"
            "Output: plain text only. Max ~1200 characters. No markdown."
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> str:
        return payload_text

    def purpose(self, input_data: LinkedInInput) -> str:
        _ = input_data
        return self.purpose_name
