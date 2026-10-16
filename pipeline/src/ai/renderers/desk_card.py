"""Desk open card brief renderer."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from src.ai.providers.groq import GROQ_PRIMARY_MODEL
from src.db import writer

logger = logging.getLogger(__name__)

REQUIRED_KEYS: tuple[str, ...] = ("bias_summary", "catalyst_driver", "squeeze_risk")


@dataclass(frozen=True, slots=True)
class DeskCardInput:
    pair: str
    regime: str
    date_str: str
    primary_driver: str | None
    pain_index: float | None
    rvol: float | None = None
    todays_event_matrix: dict[str, Any] | None = None
    dollar_dominance_score: float | None = None
    dollar_bias: str | None = None


def deterministic_desk_card_brief(
    regime: str,
    primary_driver: str | None,
    pain_index: float | None,
    rvol: float | None = None,
    todays_event_matrix: dict[str, Any] | None = None,
    dollar_dominance_score: float | None = None,
    dollar_bias: str | None = None,
) -> str:
    dom_ok = (
        dollar_dominance_score is not None
        and float(dollar_dominance_score) > 0.7
        and dollar_bias in ("Strength", "Weakness")
    )
    bias_suffix = f" (DOLLAR {str(dollar_bias).upper()})" if dom_ok else ""
    bias_summary = f"{regime}{bias_suffix}".upper()
    driver_u = (primary_driver or "UNKNOWN").strip().upper()
    catalyst_driver = driver_u if driver_u else "UNKNOWN"

    squeeze_bits: list[str] = []
    if pain_index is None:
        squeeze_bits.append("PAIN INDEX NULL")
    else:
        tag = "ELEVATED" if float(pain_index) >= 80 else "CONTROLLED"
        squeeze_bits.append(f"{tag} (PAIN {float(pain_index):.1f})")

    if rvol is not None:
        squeeze_bits.append(f"RVOL {float(rvol):.2f}X")

    if todays_event_matrix is not None:
        evn = str(todays_event_matrix.get("event_name") or "MACRO EVENT")
        ar = todays_event_matrix.get("asymmetry_ratio")
        ar_txt = f"{float(ar):.2f}" if ar is not None else "N/A"
        squeeze_bits.append(f"EVENT: {evn} \u00b7 ASYM {ar_txt}")
    squeeze_risk = " \u00b7 ".join(squeeze_bits) if squeeze_bits else "UNAVAILABLE"

    payload: dict[str, str] = {
        "bias_summary": bias_summary[:180],
        "catalyst_driver": catalyst_driver[:180],
        "squeeze_risk": squeeze_risk[:220],
    }
    return json.dumps(payload)


def parse_desk_card_json(
    payload_text: str, *, required_keys: tuple[str, ...] = REQUIRED_KEYS
) -> dict[str, str]:
    parsed = json.loads(payload_text)
    if not isinstance(parsed, dict):
        raise ValueError("Desk card response is not a JSON object")

    out: dict[str, str] = {}
    for key in required_keys:
        value = parsed.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing/invalid key: {key}")
        out[key] = value.strip()
    return out


def desk_card_brief_fallback(
    *,
    regime: str,
    primary_driver: str | None,
    pain_index: float | None,
    rvol: float | None = None,
    todays_event_matrix: dict[str, Any] | None = None,
    dollar_dominance_score: float | None = None,
    dollar_bias: str | None = None,
) -> str:
    """Deterministic JSON when LLM fails (orchestrator batch path)."""
    return deterministic_desk_card_brief(
        regime,
        primary_driver,
        pain_index,
        rvol=rvol,
        todays_event_matrix=todays_event_matrix,
        dollar_dominance_score=dollar_dominance_score,
        dollar_bias=dollar_bias,
    )


class DeskCardRenderer:
    """Prompt + parser for desk-card JSON briefs."""

    purpose_prefix = "desk_card"
    max_tokens = 220
    primary_model = GROQ_PRIMARY_MODEL
    response_format: dict[str, str] = {"type": "json_object"}
    timeout_seconds = 5.0
    retry_attempts = 2

    def human_grounding_active(self, input_data: DeskCardInput) -> bool:
        return bool(writer.get_latest_research_memo_thesis_bullets())

    def build_messages(self, input_data: DeskCardInput) -> list[dict[str, str]]:
        thesis_bullets = writer.get_latest_research_memo_thesis_bullets()
        sig_row = writer.get_signal_for_pair_date(input_data.pair, input_data.date_str)
        z_t = sig_row.get("rate_z_tactical") if sig_row else None
        z_s = sig_row.get("rate_z_structural") if sig_row else None
        z_b = sig_row.get("z_blended") if sig_row else None
        z_line = (
            f"RATE_Z_TACTICAL_MAD:{z_t if z_t is not None else 'null'} "
            f"RATE_Z_STRUCTURAL_MAD:{z_s if z_s is not None else 'null'} "
            f"RATE_Z_BLENDED_MAD:{z_b if z_b is not None else 'null'}\n"
        )
        founder_instructions = ""
        stale_signal_gating = ""
        if thesis_bullets:
            thesis_block = "\n".join(f"- {b}" for b in thesis_bullets)
            founder_instructions = (
                "You are the Lead Researcher's Adversary. Cross-reference today's MAD Z-Scores "
                "(RATE_Z_TACTICAL_MAD and RATE_Z_STRUCTURAL_MAD) and PAIN_INDEX against the "
                f"following Structural Thesis:\n{thesis_block}\n"
                "Your primary directive is to find mathematical evidence that "
                "CONTRADICTS the thesis. "
                "If the math disputes the thesis, encode the contradiction in "
                "catalyst_driver or squeeze_risk (terse labels only); put the "
                "directional read in bias_summary. "
                "If the math confirms the thesis, align bias_summary accordingly\u2014"
                "still no prose paragraphs.\n\n"
            )
        else:
            stale_signal_gating = (
                "No weekly Structural Thesis is available for this run. Do NOT invent, "
                "assume, or reference a 'Project Founder' view, 'macro memo', or any "
                "off-book narrative. Ground bias_summary, catalyst_driver, and "
                "squeeze_risk ONLY in the explicit numeric and categorical fields above "
                "(REGIME, PRIMARY_DRIVER, PAIN_INDEX, RATE_Z_*_MAD, DOLLAR_*). If a field "
                "is null or telemetry is stale, say so plainly\u2014do not fill gaps with "
                "speculative macro story.\n\n"
            )

        keys_literal = '{"bias_summary":"","catalyst_driver":"","squeeze_risk":""}'
        event_context = ""
        if input_data.todays_event_matrix is not None:
            evn = str(input_data.todays_event_matrix.get("event_name") or "unknown")
            ar_raw = input_data.todays_event_matrix.get("asymmetry_ratio")
            ar_txt = f"{float(ar_raw):.4f}" if ar_raw is not None else "N/A"
            event_context = (
                f"There is a high-impact event today: {evn}. "
                f"The historical Asymmetry Ratio is {ar_txt}. "
                "squeeze_risk MUST reference this event together with PAIN_INDEX "
                "(use NULL/UNAVAILABLE wording if PAIN_INDEX is null).\n"
            )
        squeeze_rules = (
            "- squeeze_risk: ONE terse institutional line (no multi-sentence prose). "
            "MUST encode pain / squeeze / vol risk from PAIN_INDEX (e.g. "
            "'ELEVATED (PAIN 82)' or 'CONTROLLED (PAIN 41)' or "
            "'NULL (PAIN INDEX UNAVAILABLE)'). "
            f"{event_context}"
        )
        dscore_txt = (
            "null"
            if input_data.dollar_dominance_score is None
            else f"{float(input_data.dollar_dominance_score):.4f}"
        )
        dbias_txt = input_data.dollar_bias or "null"
        dollar_rule = ""
        dom_ok = (
            input_data.dollar_dominance_score is not None
            and float(input_data.dollar_dominance_score) > 0.7
            and input_data.dollar_bias in ("Strength", "Weakness")
        )
        if dom_ok:
            dollar_rule = (
                "- bias_summary MUST be a short uppercase label that includes the "
                "regime AND '(DOLLAR "
                f"{str(input_data.dollar_bias).upper()})' when DOLLAR_DOMINANCE_SCORE > 0.70.\n"
                "  Example shape: 'MODERATE USD STRENGTH (DOLLAR STRENGTH)'.\n"
            )
        pain_index_text = (
            "null" if input_data.pain_index is None else f"{input_data.pain_index:.2f}"
        )
        rvol_text = "null" if input_data.rvol is None else f"{input_data.rvol:.2f}x"
        prompt = (
            "You are a deterministic FX desk-card encoder. Output machine-readable "
            "labels only\u2014NO paragraphs, NO narrative sentences, NO filler words "
            "like 'Regime remains'.\n"
            "Return ONLY a strict JSON object with exactly these keys:\n"
            f"{keys_literal}\n"
            f"PAIR:{input_data.pair} DATE:{input_data.date_str} REGIME:{input_data.regime}\n"
            f"PRIMARY_DRIVER:{input_data.primary_driver or 'unknown'}\n"
            f"PAIN_INDEX:{pain_index_text}\n"
            f"RVOL:{rvol_text}\n"
            f"DOLLAR_DOMINANCE_SCORE:{dscore_txt} DOLLAR_BIAS:{dbias_txt}\n"
            f"{z_line}"
            f"{stale_signal_gating}"
            f"{founder_instructions}"
            "Constraints:\n"
            "- bias_summary: ONE line, mostly UPPERCASE, bias + regime read "
            "(e.g. 'BULLISH (DOLLAR STRENGTH)' or 'NEUTRAL / RANGE'). Max ~120 chars.\n"
            "- catalyst_driver: ONE line, UPPERCASE shorthand for the structural catalyst; "
            "MUST reference PRIMARY_DRIVER (e.g. '8-WEEK VWAP BREACH', '2Y SPREAD COMPRESSION'). "
            "Max ~120 chars.\n"
            f"{squeeze_rules}"
            f"{dollar_rule}"
            "- Do not add markdown, prose wrappers, or extra keys.\n"
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> dict[str, str]:
        return parse_desk_card_json(payload_text, required_keys=REQUIRED_KEYS)

    def purpose(self, input_data: DeskCardInput) -> str:
        return f"{self.purpose_prefix}_{input_data.pair}"

    def fallback(self, input_data: DeskCardInput) -> str:
        return deterministic_desk_card_brief(
            input_data.regime,
            input_data.primary_driver,
            input_data.pain_index,
            rvol=input_data.rvol,
            todays_event_matrix=input_data.todays_event_matrix,
            dollar_dominance_score=input_data.dollar_dominance_score,
            dollar_bias=input_data.dollar_bias,
        )
