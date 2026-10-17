"""Single LLM reader facade (FX live personal slice).

One LLM reader only. Input is a frozen regime call plus brief text.
Output is a 5-line analyst note with cited inputs. No new signals.
No new pairs. All AI calls go through ``src.ai.client.AIClient``.
Respects the daily rate limiter indirectly via the provider chain.
Never logs secrets. Never writes to production tables.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ai.client import AIClient
from src.ai.renderers.analyst_note import (
    AnalystNoteInput,
    AnalystNoteRenderer,
    _normalize_pair,
    deterministic_analyst_note,
)

logger = logging.getLogger(__name__)

__all__ = [
    "AnalystNoteInput",
    "generate_analyst_note",
    "generate_analyst_note_async",
]


def _fallback(input_data: AnalystNoteInput, reason: str) -> str:
    logger.warning("Analyst reader fallback for %s: %s", input_data.pair, reason)
    return deterministic_analyst_note(input_data)


def generate_analyst_note(
    *,
    pair: str,
    date_str: str,
    regime: str,
    confidence: float,
    composite: float,
    primary_driver: str | None = None,
    brief_text: str = "",
    model_version: str = "fx-live-personal-v1",
    client: AIClient | None = None,
) -> str:
    """Sync reader. Uses ``AIClient.render``; falls back deterministically."""
    input_data = AnalystNoteInput(
        pair=pair,
        date_str=date_str,
        regime=regime,
        confidence=confidence,
        composite=composite,
        primary_driver=primary_driver,
        brief_text=brief_text,
        model_version=model_version,
    )
    if _normalize_pair(pair) not in ("EURUSD", "USDJPY", "USDINR"):
        raise ValueError(f"3-pair lock: unsupported pair {pair!r}")
    renderer = AnalystNoteRenderer()
    ai = client or AIClient()
    try:
        return ai.render(renderer, input_data, date_str=date_str)
    except Exception as exc:  # noqa: BLE001 - offline-safe fallback, no secret logging
        return _fallback(input_data, type(exc).__name__)


async def generate_analyst_note_async(
    *,
    pair: str,
    date_str: str,
    regime: str,
    confidence: float,
    composite: float,
    primary_driver: str | None = None,
    brief_text: str = "",
    model_version: str = "fx-live-personal-v1",
    client: AIClient | None = None,
) -> str:
    """Async reader. Uses ``AIClient.render_async``; falls back deterministically."""
    input_data = AnalystNoteInput(
        pair=pair,
        date_str=date_str,
        regime=regime,
        confidence=confidence,
        composite=composite,
        primary_driver=primary_driver,
        brief_text=brief_text,
        model_version=model_version,
    )
    if _normalize_pair(pair) not in ("EURUSD", "USDJPY", "USDINR"):
        raise ValueError(f"3-pair lock: unsupported pair {pair!r}")
    renderer = AnalystNoteRenderer()
    ai = client or AIClient()
    try:
        return await ai.render_async(renderer, input_data, date_str=date_str)
    except Exception as exc:  # noqa: BLE001 - offline-safe fallback, no secret logging
        return _fallback(input_data, type(exc).__name__)


def analyst_note_from_frozen_call(
    frozen_call: dict[str, Any],
    brief_text: str = "",
    *,
    client: AIClient | None = None,
) -> str:
    """Convenience: build reader input from a frozen regime_calls row dict."""
    return generate_analyst_note(
        pair=str(frozen_call.get("pair", "")),
        date_str=str(frozen_call.get("date", ""))[:10],
        regime=str(frozen_call.get("regime", "")),
        confidence=float(frozen_call.get("confidence", 0.0)),
        composite=float(frozen_call.get("signal_composite", 0.0)),
        primary_driver=frozen_call.get("primary_driver"),
        brief_text=brief_text,
        model_version=str(frozen_call.get("model_version") or "fx-live-personal-v1"),
        client=client,
    )
