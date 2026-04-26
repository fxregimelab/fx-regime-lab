"""OpenRouter AI client — MiniMax M1 primary, Llama 3.1 8B fallback. Zero cost."""

from __future__ import annotations

import logging
import os
from typing import Any, cast

from openai import APIError, OpenAI

from src.types import SignalRow

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "minimax/minimax-m1:free"
FALLBACK_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
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
    """Try PRIMARY_MODEL, fall back to FALLBACK_MODEL on error."""
    from src.db import writer

    _check_limit(date_str)
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            resp = _openrouter_client().chat.completions.create(
                model=model,
                messages=cast(Any, messages),
                max_tokens=max_tokens,
                temperature=0.3,
            )
            writer.write_ai_request(date_str, purpose, model)
            return resp.choices[0].message.content or ""
        except APIError as exc:
            logger.warning("OpenRouter model %s failed (%s), trying next", model, exc)
    raise RuntimeError("All OpenRouter models failed")


def generate_brief(
    pair: str,
    regime: str,
    confidence: float,
    composite: float,
    signal_row: SignalRow,
    date_str: str,
) -> str:
    """Generate pair brief. Cache-check must be done by caller (orchestrator)."""
    chg = signal_row.day_change_pct
    chg_s = f"{chg:+.2f}%" if chg is not None else "NA"
    prompt = (
        "TASK: FX analyst brief. 3 short paragraphs. Under 200 words total.\n"
        f"PAIR:{pair} DATE:{date_str}\n"
        f"REGIME:{regime} CONF:{confidence:.0%} COMPOSITE:{composite:+.2f}\n"
        f"RATE_DIFF_2Y:{signal_row.rate_diff_2y} COT_PCT:{signal_row.cot_percentile} "
        f"RVOL20:{signal_row.realized_vol_20d} RVOL5:{signal_row.realized_vol_5d} "
        f"SPOT:{signal_row.spot} CHG:{chg_s}\n"
        "STRUCTURE: Block1 signals Block2 call and key level Block3 primary risk.\n"
        "OUTPUT: plain text only. No headers. No markdown."
    )
    messages = [{"role": "user", "content": prompt}]
    return _call(messages, max_tokens=280, date_str=date_str, purpose=f"brief{pair}")


def generate_event_brief(
    event: str,
    impact: str,
    pairs: list[str],
    date_str: str,
) -> str:
    """Generate AI context for a macro calendar event. Under 100 words."""
    prompt = (
        "TASK: macro event FX brief. Under 100 words.\n"
        f"EVENT:{event} DATE:{date_str} IMPACT:{impact} PAIRS:{','.join(pairs)}\n"
        "STRUCTURE: Block1 what it measures Block2 FX impact beat/inline/miss "
        "Block3 pair-specific note.\n"
        "OUTPUT: plain text only. No markdown. No headers."
    )
    messages = [{"role": "user", "content": prompt}]
    safe_purpose = f"event{event[:30]}"
    return _call(messages, max_tokens=150, date_str=date_str, purpose=safe_purpose)
