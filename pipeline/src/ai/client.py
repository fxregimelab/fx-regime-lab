"""OpenRouter AI client — Free model selection. Zero cost."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict
from typing import Any, cast

from openai import APITimeoutError, AsyncOpenAI, OpenAI

from src.analysis.event_risk import EventRiskResult
from src.db import writer
from src.types import SignalRow

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "google/gemma-3-27b-it:free"

# Free-model fallbacks (primary tried first via _call / _call_preferred_model)
FREE_MODELS = [
    PRIMARY_MODEL,
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/free",
]

DAILY_REQUEST_LIMIT = 180


def _openrouter_headers() -> dict[str, str]:
    return {
        "HTTP-Referer": "https://fxregimelab.com",
        "X-Title": "FX Regime Lab",
    }


def _openrouter_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
        default_headers=_openrouter_headers(),
    )


async_client = AsyncOpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    default_headers=_openrouter_headers(),
)


def _check_limit(date_str: str) -> None:
    from src.db import writer

    count = writer.get_ai_request_count_today(date_str)
    if count >= DAILY_REQUEST_LIMIT:
        msg = f"Daily OpenRouter request limit reached ({count}/{DAILY_REQUEST_LIMIT})"
        raise RuntimeError(msg)


def _call(messages: list[dict[str, str]], max_tokens: int, date_str: str, purpose: str) -> str:
    """Try available free models in order."""
    from src.db import writer

    _check_limit(date_str)
    for model in FREE_MODELS:
        try:
            logger.info("Attempting AI call with model: %s", model)
            resp = _openrouter_client().chat.completions.create(
                model=model,
                messages=cast(Any, messages),
                max_tokens=max_tokens,
                temperature=0.3,
            )
            writer.write_ai_request(date_str, purpose, model)
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenRouter model %s failed: %s", model, exc)
    raise RuntimeError("All OpenRouter free models failed")


async def _call_async(
    messages: list[dict[str, str]],
    max_tokens: int,
    date_str: str,
    purpose: str,
) -> str:
    """Try available free models in order (async)."""
    from src.db import writer

    for model in FREE_MODELS:
        try:
            _check_limit(date_str)
            logger.info("Attempting async AI call with model: %s", model)
            resp = await async_client.chat.completions.create(
                model=model,
                messages=cast(Any, messages),
                max_tokens=max_tokens,
                temperature=0.3,
            )
            writer.write_ai_request(date_str, purpose, model)
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenRouter model %s failed: %s", model, exc)
    raise RuntimeError("All OpenRouter free models failed")


async def _call_preferred_model_async(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    date_str: str,
    purpose: str,
    response_format: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> str:
    """Call a preferred model once, then fall back to free-model rotation (async)."""
    from src.db import writer

    _check_limit(date_str)
    try:
        logger.info("Attempting async AI call with preferred model: %s", model)
        resp = await async_client.chat.completions.create(
            model=model,
            messages=cast(Any, messages),
            max_tokens=max_tokens,
            temperature=0.3,
            response_format=cast(Any, response_format),
            timeout=timeout_seconds,
        )
        writer.write_ai_request(date_str, purpose, model)
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("Preferred model %s failed: %s; falling back", model, exc)
    return await _call_async(
        messages, max_tokens=max_tokens, date_str=date_str, purpose=purpose
    )


def _call_preferred_model(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    date_str: str,
    purpose: str,
    response_format: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> str:
    """Sync wrapper: preferred model + fallback (used by non-async call sites)."""

    return asyncio.run(
        _call_preferred_model_async(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            date_str=date_str,
            purpose=purpose,
            response_format=response_format,
            timeout_seconds=timeout_seconds,
        )
    )


def _is_timeout_error(exc: Exception) -> bool:
    return isinstance(exc, APITimeoutError) or "timeout" in str(exc).lower()


def _deterministic_desk_card_brief(
    regime: str,
    primary_driver: str | None,
    pain_index: float | None,
    *,
    todays_event_matrix: dict[str, Any] | None = None,
    dollar_dominance_score: float | None = None,
    dollar_bias: str | None = None,
) -> str:
    pain_text = (
        "unknown due to stale/failed positioning input"
        if pain_index is None
        else f"{pain_index:.1f}"
    )
    regime_state = f"Regime remains {regime}."
    if (
        dollar_dominance_score is not None
        and dollar_dominance_score > 0.7
        and dollar_bias in ("Strength", "Weakness")
    ):
        regime_state += (
            f" This setup is driven by broad-based Dollar {dollar_bias}."
        )
    payload: dict[str, str] = {
        "regime_state": regime_state,
        "key_divergence": f"Primary driver: {primary_driver or 'unknown'}.",
    }
    if pain_index is not None or todays_event_matrix is not None:
        ev_part = ""
        if todays_event_matrix is not None:
            evn = str(todays_event_matrix.get("event_name") or "macro event")
            ar = todays_event_matrix.get("asymmetry_ratio")
            ar_txt = f"{float(ar):.4f}" if ar is not None else "N/A"
            ev_part = f" High-impact event today ({evn}); historical asymmetry ratio {ar_txt}."
        payload["swing_factor"] = (
            f"Pain index is {pain_text}.{ev_part} Size for event risk vs positioning."
        )
    return json.dumps(payload)


def _parse_desk_card_json(
    payload_text: str, *, required_keys: tuple[str, ...]
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


def _deterministic_event_brief(mie: float | None) -> str:
    mie_text = "N/A" if mie is None else f"{mie:.2f}x"
    payload: dict[str, str] = {
        "volatility_profile": f"Expected MIE multiplier: {mie_text}",
        "asymmetric_setup": "Data unavailable/timeout",
        "execution_note": "Proceed with caution.",
    }
    return json.dumps(payload)


def _parse_event_brief_json(payload_text: str) -> str:
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


def desk_card_brief_fallback(
    *,
    regime: str,
    primary_driver: str | None,
    pain_index: float | None,
    todays_event_matrix: dict[str, Any] | None = None,
    dollar_dominance_score: float | None = None,
    dollar_bias: str | None = None,
) -> str:
    """Deterministic JSON when LLM fails (orchestrator batch path)."""

    return _deterministic_desk_card_brief(
        regime,
        primary_driver,
        pain_index,
        todays_event_matrix=todays_event_matrix,
        dollar_dominance_score=dollar_dominance_score,
        dollar_bias=dollar_bias,
    )


def _parse_weekly_memo_thesis(payload_text: str) -> list[str]:
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


async def summarize_weekly_memo_async(raw_text: str, *, date_str: str) -> list[str]:
    """Summarize ingested Substack memo into five structural thesis bullets (JSON)."""

    cap = 120_000
    body = raw_text if len(raw_text) <= cap else raw_text[:cap]
    prompt = (
        "You are a Quant Fund Researcher. Summarize the following Macro Memo into exactly 5 "
        "'Structural Thesis' bullets. Focus on: 1. Primary Bias (Bull/Bear), 2. Key Level, "
        "3. Narrative Driver.\n"
        "Return ONLY a strict JSON object with exactly one key \"theses\" whose value is a "
        "JSON array of exactly 5 strings (each string is one bullet).\n"
        f"MEMO_TEXT:\n{body}\n"
    )
    messages = [{"role": "user", "content": prompt}]
    raw = await _call_preferred_model_async(
        model=PRIMARY_MODEL,
        messages=messages,
        max_tokens=600,
        date_str=date_str,
        purpose="weekly_memo_thesis",
        response_format={"type": "json_object"},
        timeout_seconds=90.0,
    )
    return _parse_weekly_memo_thesis(raw)


async def generate_desk_card_brief_async(
    *,
    pair: str,
    regime: str,
    date_str: str,
    primary_driver: str | None,
    pain_index: float | None,
    todays_event_matrix: dict[str, Any] | None = None,
    dollar_dominance_score: float | None = None,
    dollar_bias: str | None = None,
) -> tuple[str, bool]:
    """Return desk-card JSON brief and whether founder thesis grounding was active."""

    thesis_bullets = writer.get_latest_research_memo_thesis_bullets()
    human_grounding_active = bool(thesis_bullets)
    sig_row = writer.get_signal_for_pair_date(pair, date_str)
    z_t = sig_row.get("rate_z_tactical") if sig_row else None
    z_s = sig_row.get("rate_z_structural") if sig_row else None
    z_line = (
        f"RATE_Z_TACTICAL_MAD:{z_t if z_t is not None else 'null'} "
        f"RATE_Z_STRUCTURAL_MAD:{z_s if z_s is not None else 'null'}\n"
    )
    founder_instructions = ""
    stale_signal_gating = ""
    if thesis_bullets:
        founder_instructions = (
            "Cross-reference today's MAD Z-Scores (RATE_Z_TACTICAL_MAD and "
            "RATE_Z_STRUCTURAL_MAD) and PAIN_INDEX against the following Structural Thesis "
            "from the Project Founder:\n"
            + "\n".join(f"- {b}" for b in thesis_bullets)
            + "\nIf the math contradicts the human thesis, headline the divergence as a primary "
            "risk in key_divergence or swing_factor as appropriate. Do not attempt to hide the "
            "conflict.\n\n"
        )
    else:
        stale_signal_gating = (
            "No weekly Structural Thesis is available for this run. Do NOT invent, assume, or "
            "reference a 'Project Founder' view, 'macro memo', or any off-book narrative. "
            "Ground regime_state, key_divergence, and swing_factor ONLY in the explicit numeric "
            "and categorical fields above (REGIME, PRIMARY_DRIVER, PAIN_INDEX, RATE_Z_*_MAD, "
            "DOLLAR_*). If a field is null or telemetry is stale, say so plainly—do not fill "
            "gaps with speculative macro story.\n\n"
        )

    require_swing = pain_index is not None or todays_event_matrix is not None
    keys_literal = (
        '{"regime_state":"","key_divergence":"","swing_factor":""}'
        if require_swing
        else '{"regime_state":"","key_divergence":""}'
    )
    event_context = ""
    if todays_event_matrix is not None:
        evn = str(todays_event_matrix.get("event_name") or "unknown")
        ar_raw = todays_event_matrix.get("asymmetry_ratio")
        ar_txt = f"{float(ar_raw):.4f}" if ar_raw is not None else "N/A"
        event_context = (
            f"There is a high-impact event today: {evn}. "
            f"The historical Asymmetry Ratio is {ar_txt}. "
            "In swing_factor, you MUST synthesize how today's event interacts with the current "
            "PAIN_INDEX.\n"
        )
    swing_rules = (
        (
            "- swing_factor: one concise sentence that MUST reference PAIN_INDEX "
            "(use null/unavailable wording if PAIN_INDEX is null) and its risk implication.\n"
            f"{event_context}"
        )
        if require_swing
        else (
            "- Do NOT include swing_factor or any key other than regime_state "
            "and key_divergence (PAIN_INDEX is unavailable).\n"
        )
    )
    dscore_txt = (
        "null" if dollar_dominance_score is None else f"{float(dollar_dominance_score):.4f}"
    )
    dbias_txt = dollar_bias or "null"
    dollar_rule = ""
    dom_ok = (
        dollar_dominance_score is not None
        and float(dollar_dominance_score) > 0.7
        and dollar_bias in ("Strength", "Weakness")
    )
    if dom_ok:
        dollar_rule = (
            "- If DOLLAR_DOMINANCE_SCORE is greater than 0.70, you MUST include this exact "
            f'sentence as its own sentence in regime_state or key_divergence: '
            f'"This setup is driven by broad-based Dollar {dollar_bias}."\n'
        )
    prompt = (
        "You are a deterministic FX research writer.\n"
        "Return ONLY a strict JSON object with exactly these keys:\n"
        f"{keys_literal}\n"
        f"PAIR:{pair} DATE:{date_str} REGIME:{regime}\n"
        f"PRIMARY_DRIVER:{primary_driver or 'unknown'}\n"
        f"PAIN_INDEX:{'null' if pain_index is None else f'{pain_index:.2f}'}\n"
        f"DOLLAR_DOMINANCE_SCORE:{dscore_txt} DOLLAR_BIAS:{dbias_txt}\n"
        f"{z_line}"
        f"{stale_signal_gating}"
        f"{founder_instructions}"
        "Constraints:\n"
        "- regime_state: one concise sentence describing the current regime.\n"
        "- key_divergence: one concise sentence that MUST reference PRIMARY_DRIVER.\n"
        f"{dollar_rule}"
        f"{swing_rules}"
        "- Do not add markdown, prose wrappers, or extra keys.\n"
    )
    required_keys: tuple[str, ...] = (
        ("regime_state", "key_divergence", "swing_factor")
        if require_swing
        else ("regime_state", "key_divergence")
    )
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(2):
        try:
            raw = await _call_preferred_model_async(
                model=PRIMARY_MODEL,
                messages=messages,
                max_tokens=180,
                date_str=date_str,
                purpose=f"desk_card_{pair}",
                response_format={"type": "json_object"},
                timeout_seconds=5.0,
            )
            parsed = _parse_desk_card_json(raw, required_keys=required_keys)
            return json.dumps(parsed), human_grounding_active
        except Exception as exc:  # noqa: BLE001
            if _is_timeout_error(exc):
                logger.warning("Desk card timeout for %s attempt %s", pair, attempt + 1)
            else:
                logger.warning("Desk card JSON parse/call failure for %s: %s", pair, exc)
    logger.warning("Falling back to deterministic desk card brief for %s", pair)
    return (
        _deterministic_desk_card_brief(
            regime,
            primary_driver,
            pain_index,
            todays_event_matrix=todays_event_matrix,
            dollar_dominance_score=dollar_dominance_score,
            dollar_bias=dollar_bias,
        ),
        human_grounding_active,
    )


def generate_brief(
    pair: str,
    regime: str,
    confidence: float,
    composite: float,
    signal_row: SignalRow,
    date_str: str,
    primary_driver: str | None = None,
    polymarket_context: str = "",
    dollar_dominance_pct: float | None = None,
    polymarket_odds_json: str = "[]",
) -> str:
    """Generate pair brief. Cache-check must be done by caller (orchestrator)."""
    chg = signal_row.day_change_pct
    chg_s = f"{chg:+.2f}%" if chg is not None else "NA"
    dom_txt = (
        "null"
        if dollar_dominance_pct is None
        else f"{float(dollar_dominance_pct):.2f}"
    )
    prompt = (
        "TASK: FX analyst brief. 3 short paragraphs. Under 200 words total.\n"
        f"PAIR:{pair} DATE:{date_str}\n"
        f"REGIME:{regime} CONF:{confidence:.0%} COMPOSITE:{composite:+.2f}\n"
        f"PRIMARY_DRIVER:{primary_driver or 'unknown'} "
        f"RATE_DIFF_2Y:{signal_row.rate_diff_2y} RATE_DIFF_10Y:{signal_row.rate_diff_10y} "
        f"CROSS_ASSET_OIL:{signal_row.cross_asset_oil} COT_PCT:{signal_row.cot_percentile} "
        f"RVOL20:{signal_row.realized_vol_20d} RVOL5:{signal_row.realized_vol_5d} "
        f"SPOT:{signal_row.spot} CHG:{chg_s}\n"
        f"DOLLAR_DOMINANCE_PCT:{dom_txt}\n"
        f"POLYMARKET_ODDS_JSON:{polymarket_odds_json}\n"
        f"{polymarket_context}\n"
        "STRUCTURE: Block1 signals Block2 call and key level Block3 primary risk.\n"
        "Use 10Y and Oil context to distinguish narrow rates-driven moves "
        "from broader macro moves.\n"
        "Explicitly mention if the Primary Driver is shifting from 2Y rates "
        "to broader macro (Oil/10Y).\n"
        "You MUST synthesize DOLLAR_DOMINANCE_PCT with POLYMARKET_ODDS_JSON to explain "
        "today's move: reconcile book-wide USD thematic alignment with prediction-market "
        "macro odds (Fed path, recession, etc.).\n"
        "If Polymarket odds are provided, treat them as cutting-edge market sentiment and use "
        "them in Primary Risk or Macro Context.\n"
        "OUTPUT: plain text only. No headers. No markdown."
    )
    messages = [{"role": "user", "content": prompt}]
    return _call(messages, max_tokens=280, date_str=date_str, purpose=f"brief{pair}")


def generate_event_brief(
    risk_matrix: EventRiskResult | dict[str, Any],
    date_str: str,
    polymarket_context: str = "",
) -> str:
    """Generate deterministic structured event brief JSON from risk matrix context."""
    risk = asdict(risk_matrix) if isinstance(risk_matrix, EventRiskResult) else dict(risk_matrix)
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
        str(risk["asymmetry_direction"]) if risk.get("asymmetry_direction") is not None else None
    )
    mie_text = "null" if mie is None else f"{mie:.4f}"
    asymmetry_ratio_text = "null" if asymmetry_ratio is None else f"{asymmetry_ratio:.4f}"
    prompt = (
        "You are a deterministic FX event-risk analyst.\n"
        "Return ONLY a strict JSON object with exactly these keys:\n"
        '{"volatility_profile":"","asymmetric_setup":"","execution_note":""}\n'
        f"EVENT:{event_name} DATE:{date_str} PAIR:{pair} ACTIVE_REGIME:{active_regime}\n"
        f"SAMPLE_SIZE:{sample_size} MEDIAN_MIE_MULTIPLIER:{mie_text}\n"
        f"ASYMMETRY_RATIO:{asymmetry_ratio_text} "
        f"ASYMMETRY_DIRECTION:{asymmetry_direction or 'null'}\n"
        f"{polymarket_context}\n"
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
    messages = [{"role": "user", "content": prompt}]
    safe_purpose = f"event_risk_brief_{event_name[:24]}"
    for attempt in range(2):
        try:
            raw = _call_preferred_model(
                model=PRIMARY_MODEL,
                messages=messages,
                max_tokens=170,
                date_str=date_str,
                purpose=safe_purpose,
                response_format={"type": "json_object"},
                timeout_seconds=5.0,
            )
            return _parse_event_brief_json(raw)
        except Exception as exc:  # noqa: BLE001
            if _is_timeout_error(exc):
                logger.warning(
                    "Event brief timeout for %s/%s attempt %s",
                    pair,
                    event_name,
                    attempt + 1,
                )
            else:
                logger.warning(
                    "Event brief JSON parse/call failure for %s/%s: %s",
                    pair,
                    event_name,
                    exc,
                )
    return _deterministic_event_brief(mie)


async def generate_linkedin_alpha_hook_async(
    card_data: dict[str, Any],
    *,
    date_str: str,
) -> str:
    """Institutional LinkedIn post (~1,200 chars) from Apex Target JSON. Uses AsyncOpenAI client."""
    payload = json.dumps(card_data, ensure_ascii=False, default=str)
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
    messages = [{"role": "user", "content": prompt}]
    return await _call_preferred_model_async(
        model=PRIMARY_MODEL,
        messages=messages,
        max_tokens=520,
        date_str=date_str,
        purpose="linkedin_alpha_hook",
    )


def generate_linkedin_alpha_hook(card_data: dict[str, Any]) -> str:
    """Sync wrapper for Apex LinkedIn hook (orchestrators / scripts)."""
    from datetime import date

    ds = str(card_data.get("date") or date.today().isoformat())
    return asyncio.run(generate_linkedin_alpha_hook_async(card_data, date_str=ds))


def generate_global_macro_summary(
    *,
    date_str: str,
    pair_contexts: list[str],
    macro_context: str,
    dollar_dominance_pct: float | None = None,
    polymarket_odds_json: str = "[]",
) -> str:
    """Generate a unified global macro brief for `brief_log`."""
    dom_txt = (
        "null"
        if dollar_dominance_pct is None
        else f"{float(dollar_dominance_pct):.2f}"
    )
    prompt = (
        "TASK: Create a global FX macro summary in ~150 words.\n"
        f"DATE:{date_str}\n"
        f"PAIR_CONTEXTS:{' | '.join(pair_contexts)}\n"
        f"MACRO_CONTEXT:{macro_context}\n"
        f"DOLLAR_DOMINANCE_PCT:{dom_txt} "
        "(0–100 book-wide USD thematic alignment from regime classifier metadata)\n"
        f"POLYMARKET_ODDS_JSON:{polymarket_odds_json}\n"
        "You MUST synthesize DOLLAR_DOMINANCE_PCT with POLYMARKET_ODDS_JSON: explain how "
        "prediction-market odds on Fed / recession / macro outcomes reconcile with or diverge "
        "from the dollar-factor read, and tie that to the day's FX impulse.\n"
        "INCLUDE: dominant cross-asset driver, where rates vs oil/10Y are shifting, "
        "and one key risk to monitor.\n"
        "OUTPUT: plain text only. No markdown. No headers."
    )
    messages = [{"role": "user", "content": prompt}]
    return _call_preferred_model(
        model=PRIMARY_MODEL,
        messages=messages,
        max_tokens=220,
        date_str=date_str,
        purpose="global_macro_summary",
    )
