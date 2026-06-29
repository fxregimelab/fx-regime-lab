"""Weekly memo thesis summarizer renderer."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.ai.providers.groq import GROQ_PRIMARY_MODEL


@dataclass(frozen=True, slots=True)
class MemoInput:
    raw_text: str
    date_str: str


def parse_weekly_memo_thesis(payload_text: str) -> list[str]:
    parsed = json.loads(payload_text)
    if isinstance(parsed, list):
        if len(parsed) != 5:
            raise ValueError("Expected exactly 5 thesis strings")
        out: list[str] = []
        for i, item in enumerate(parsed):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Invalid thesis bullet at index {i}")
            out.append(item.strip())
        return out
    if not isinstance(parsed, dict):
        raise ValueError("Weekly memo thesis response must be a JSON object or array")
    theses = parsed.get("theses")
    if theses is None:
        theses = parsed.get("structural_theses")
    if theses is None:
        theses = parsed.get("bullets")
    if not isinstance(theses, list) or len(theses) != 5:
        raise ValueError("Expected exactly 5 thesis strings under theses/bullets")
    out2: list[str] = []
    for i, item in enumerate(theses):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Invalid thesis bullet at index {i}")
        out2.append(item.strip())
    return out2


class MemoRenderer:
    """Prompt + parser for weekly memo structural thesis bullets."""

    max_tokens = 600
    primary_model = GROQ_PRIMARY_MODEL
    response_format: dict[str, str] = {"type": "json_object"}
    timeout_seconds = 90.0
    purpose_name = "weekly_memo_thesis"

    def build_messages(self, input_data: MemoInput) -> list[dict[str, str]]:
        cap = 120_000
        body = (
            input_data.raw_text
            if len(input_data.raw_text) <= cap
            else input_data.raw_text[:cap]
        )
        prompt = (
            "You are a Quant Fund Researcher. Summarize the following Macro Memo into exactly 5 "
            "'Structural Thesis' bullets. Focus on: 1. Primary Bias (Bull/Bear), 2. Key Level, "
            "3. Narrative Driver.\n"
            "Return ONLY a strict JSON object with exactly one key \"theses\" whose value is a "
            "JSON array of exactly 5 strings (each string is one bullet).\n"
            f"MEMO_TEXT:\n{body}\n"
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> list[str]:
        return parse_weekly_memo_thesis(payload_text)

    def purpose(self, input_data: MemoInput) -> str:
        _ = input_data
        return self.purpose_name
