"""Event risk brief renderer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from src.ai.providers.groq import GROQ_PRIMARY_MODEL
from src.analysis.event_risk import EventRiskResult


@dataclass(frozen=True, slots=True)
class EventBriefInput:
    risk_matrix: EventRiskResult | dict[str, Any]
    date_str: str
    polymarket_context: str = ""


def deterministic_event_brief(mie: float | None) -> str:
    mie_text = "N/A" if mie is None else f"{mie:.2f}x"
    payload: dict[str, str] = {
        "volatility_profile": f"Expected MIE multiplier: {mie_text}",
        "asymmetric_setup": "Data unavailable/timeout",
        "execution_note": "Proceed with caution.",
    }
    return json.dumps(payload)


def parse_event_brief_json(payload_text: str) -> str:
    parsed = json.loads(payload_text)
    if not isinstance(parsed, dict):
        raise ValueError("Event brief response is not a JSON object")
    required_keys = ("volatility_profile", "asymmetric_setup", "execution_note")
    out: dict[str, str] = {}
    for key in required_keys:
        value = parsed.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing/invalid key: {key}")
        out[key] = value.strip()
    return json.dumps(out)


class EventBriefRenderer:
    """Prompt + parser for structured event brief JSON."""

    max_tokens = 170
    primary_model = GROQ_PRIMARY_MODEL
    response_format: dict[str, str] = {"type": "json_object"}
    timeout_seconds = 5.0
    retry_attempts = 2

    def _risk_dict(self, input_data: EventBriefInput) -> dict[str, Any]:
        risk = input_data.risk_matrix
        if isinstance(risk, EventRiskResult):
            return asdict(risk)
        return dict(risk)

    def build_messages(self, input_data: EventBriefInput) -> list[dict[str, str]]:
        risk = self._risk_dict(input_data)
        event_name = str(risk.get("event_name") or "Unknown Event")
        pair = str(risk.get("pair") or "UNKNOWN")
        active_regime = str(risk.get("active_regime") or "UNKNOWN")
        sample_size = int(risk.get("sample_size") or 0)
        mie = (
            float(risk["median_mie_multiplier"])
            if risk.get("median_mie_multiplier") is not None
            else None
        )
        asymmetry_ratio = (
            float(risk["asymmetry_ratio"]) if risk.get("asymmetry_ratio") is not None else None
        )
        asymmetry_direction = (
            str(risk["asymmetry_direction"])
            if risk.get("asymmetry_direction") is not None
            else None
        )
        mie_text = "null" if mie is None else f"{mie:.4f}"
        asymmetry_ratio_text = "null" if asymmetry_ratio is None else f"{asymmetry_ratio:.4f}"
        prompt = (
            "You are a deterministic FX event-risk analyst.\n"
            "Return ONLY a strict JSON object with exactly these keys:\n"
            '{"volatility_profile":"","asymmetric_setup":"","execution_note":""}\n'
            f"EVENT:{event_name} DATE:{input_data.date_str} PAIR:{pair} "
            f"ACTIVE_REGIME:{active_regime}\n"
            f"SAMPLE_SIZE:{sample_size} MEDIAN_MIE_MULTIPLIER:{mie_text}\n"
            f"ASYMMETRY_RATIO:{asymmetry_ratio_text} "
            f"ASYMMETRY_DIRECTION:{asymmetry_direction or 'null'}\n"
            f"{input_data.polymarket_context}\n"
            "Constraints:\n"
            "- volatility_profile: one concise sentence with expected volatility behavior "
            "from MEDIAN_MIE_MULTIPLIER.\n"
            "- asymmetric_setup: one concise sentence based on ASYMMETRY_RATIO "
            "and ASYMMETRY_DIRECTION.\n"
            "- execution_note: one concise sentence with practical trading risk guidance.\n"
            "- If SAMPLE_SIZE < 5, asymmetric_setup MUST be exactly: "
            "'Insufficient historical data for directional bias.' "
            "Do not invent or guess directional setup.\n"
            "- Do not add markdown, prose wrappers, or extra keys.\n"
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> str:
        return parse_event_brief_json(payload_text)

    def purpose(self, input_data: EventBriefInput) -> str:
        risk = self._risk_dict(input_data)
        event_name = str(risk.get("event_name") or "Unknown Event")
        return f"event_risk_brief_{event_name[:24]}"

    def fallback(self, input_data: EventBriefInput) -> str:
        risk = self._risk_dict(input_data)
        mie = (
            float(risk["median_mie_multiplier"])
            if risk.get("median_mie_multiplier") is not None
            else None
        )
        return deterministic_event_brief(mie)

    @property
    def pair(self) -> str:
        return ""

    def log_context(self, input_data: EventBriefInput) -> tuple[str, str]:
        risk = self._risk_dict(input_data)
        return str(risk.get("pair") or "UNKNOWN"), str(risk.get("event_name") or "Unknown Event")
