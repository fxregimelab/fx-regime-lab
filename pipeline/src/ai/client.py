"""OpenRouter AI client — Free model selection. Zero cost."""

from __future__ import annotations

import logging
import os
from typing import Any, cast

from openai import OpenAI

from src.types import SignalRow

logger = logging.getLogger(__name__)

# Updated free models list using verified endpoints from OpenRouter API
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/free",
]
MINIMAX_M1_MODEL = "minimax/minimax-m1:free"

DAILY_REQUEST_LIMIT = 180


def _openrouter_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://fxregimelab.com",
            "X-Title": "FX Regime Lab",
        },
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


def _call_preferred_model(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    date_str: str,
    purpose: str,
) -> str:
    """Call a preferred model once, then fall back to free-model rotation."""
    from src.db import writer

    _check_limit(date_str)
    try:
        logger.info("Attempting AI call with preferred model: %s", model)
        resp = _openrouter_client().chat.completions.create(
            model=model,
            messages=cast(Any, messages),
            max_tokens=max_tokens,
            temperature=0.3,
        )
        writer.write_ai_request(date_str, purpose, model)
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("Preferred model %s failed: %s; falling back", model, exc)
    return _call(messages, max_tokens=max_tokens, date_str=date_str, purpose=purpose)


def generate_brief(
    pair: str,
    regime: str,
    confidence: float,
    composite: float,
    signal_row: SignalRow,
    date_str: str,
    primary_driver: str | None = None,
    polymarket_context: str = "",
) -> str:
    """Generate pair brief. Cache-check must be done by caller (orchestrator)."""
    chg = signal_row.day_change_pct
    chg_s = f"{chg:+.2f}%" if chg is not None else "NA"
    prompt = (
        "TASK: FX analyst brief. 3 short paragraphs. Under 200 words total.\n"
        f"PAIR:{pair} DATE:{date_str}\n"
        f"REGIME:{regime} CONF:{confidence:.0%} COMPOSITE:{composite:+.2f}\n"
        f"PRIMARY_DRIVER:{primary_driver or 'unknown'} "
        f"RATE_DIFF_2Y:{signal_row.rate_diff_2y} RATE_DIFF_10Y:{signal_row.rate_diff_10y} "
        f"CROSS_ASSET_OIL:{signal_row.cross_asset_oil} COT_PCT:{signal_row.cot_percentile} "
        f"RVOL20:{signal_row.realized_vol_20d} RVOL5:{signal_row.realized_vol_5d} "
        f"SPOT:{signal_row.spot} CHG:{chg_s}\n"
        f"{polymarket_context}\n"
        "STRUCTURE: Block1 signals Block2 call and key level Block3 primary risk.\n"
        "Use 10Y and Oil context to distinguish narrow rates-driven moves "
        "from broader macro moves.\n"
        "Explicitly mention if the Primary Driver is shifting from 2Y rates "
        "to broader macro (Oil/10Y).\n"
        "If Polymarket odds are provided, treat them as cutting-edge market sentiment and use "
        "them in Primary Risk or Macro Context.\n"
        "OUTPUT: plain text only. No headers. No markdown."
    )
    messages = [{"role": "user", "content": prompt}]
    return _call(messages, max_tokens=280, date_str=date_str, purpose=f"brief{pair}")


def generate_event_brief(
    event: str,
    impact: str,
    pairs: list[str],
    date_str: str,
    polymarket_context: str = "",
) -> str:
    """Generate AI context for a macro calendar event. Under 100 words."""
    prompt = (
        "TASK: macro event FX brief. Under 100 words.\n"
        f"EVENT:{event} DATE:{date_str} IMPACT:{impact} PAIRS:{','.join(pairs)}\n"
        f"{polymarket_context}\n"
        "STRUCTURE: Block1 what it measures Block2 FX impact beat/inline/miss "
        "Block3 pair-specific note.\n"
        "If Polymarket odds are provided, use them as live sentiment in the macro context.\n"
        "OUTPUT: plain text only. No markdown. No headers."
    )
    messages = [{"role": "user", "content": prompt}]
    safe_purpose = f"event{event[:30]}"
    return _call(messages, max_tokens=150, date_str=date_str, purpose=safe_purpose)


def generate_global_macro_summary(
    *,
    date_str: str,
    pair_contexts: list[str],
    macro_context: str,
) -> str:
    """Generate a unified global macro brief for `brief_log`."""
    prompt = (
        "TASK: Create a global FX macro summary in ~150 words.\n"
        f"DATE:{date_str}\n"
        f"PAIR_CONTEXTS:{' | '.join(pair_contexts)}\n"
        f"MACRO_CONTEXT:{macro_context}\n"
        "INCLUDE: dominant cross-asset driver, where rates vs oil/10Y are shifting, "
        "and one key risk to monitor.\n"
        "OUTPUT: plain text only. No markdown. No headers."
    )
    messages = [{"role": "user", "content": prompt}]
    return _call_preferred_model(
        model=MINIMAX_M1_MODEL,
        messages=messages,
        max_tokens=220,
        date_str=date_str,
        purpose="global_macro_summary",
    )
