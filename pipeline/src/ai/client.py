"""
@agent_context: Multi-provider AI client for generating research briefs and event
risk summaries. Hierarchy: Groq primary -> Gemini secondary -> NIM tertiary ->
OpenRouter fallback.
@allowed_imports: [asyncio, json, logging, os, dataclasses, typing, openai,
src.analysis, src.db, src.types]
@forbidden_imports: [src.fetchers]
@obsidian_link: [[AI Intelligence#Multi-Provider Integration]]
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from openai import APITimeoutError

from src.ai.providers.chain import FallbackProviderChain
from src.ai.providers.groq import GROQ_PRIMARY_MODEL
from src.ai.renderers.desk_card import (
    DeskCardInput,
    DeskCardRenderer,
    desk_card_brief_fallback,
)
from src.ai.renderers.event_brief import EventBriefInput, EventBriefRenderer
from src.ai.renderers.linkedin import LinkedInInput, LinkedInRenderer
from src.ai.renderers.macro_summary import MacroSummaryInput, MacroSummaryRenderer
from src.ai.renderers.memo import MemoInput, MemoRenderer
from src.ai.renderers.pair_brief import PairBriefInput, PairBriefRenderer
from src.ai.renderers.protocol import ArtifactRenderer
from src.analysis.event_risk import EventRiskResult
from src.types import SignalRow

logger = logging.getLogger(__name__)

__all__ = [
    "AIClient",
    "GROQ_PRIMARY_MODEL",
    "desk_card_brief_fallback",
    "generate_brief",
    "generate_desk_card_brief_async",
    "generate_event_brief",
    "generate_global_macro_summary",
    "generate_linkedin_alpha_hook",
    "generate_linkedin_alpha_hook_async",
    "summarize_weekly_memo_async",
]


TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


def _is_timeout_error(exc: Exception) -> bool:
    return isinstance(exc, APITimeoutError) or "timeout" in str(exc).lower()


class AIClient:
    """Thin facade over provider chain and artifact renderers."""

    def __init__(self, chain: FallbackProviderChain | None = None) -> None:
        self._chain = chain or FallbackProviderChain()

    async def render_async(
        self,
        renderer: ArtifactRenderer[TInput, TOutput],
        input_data: TInput,
        *,
        date_str: str,
    ) -> TOutput:
        messages = renderer.build_messages(input_data)
        purpose = renderer.purpose(input_data)
        raw = await self._chain.call_preferred_model_async(
            model=renderer.primary_model,
            messages=messages,
            max_tokens=renderer.max_tokens,
            date_str=date_str,
            purpose=purpose,
            response_format=getattr(renderer, "response_format", None),
            timeout_seconds=getattr(renderer, "timeout_seconds", None),
        )
        return renderer.parse(raw)

    def render(
        self,
        renderer: ArtifactRenderer[TInput, TOutput],
        input_data: TInput,
        *,
        date_str: str,
    ) -> TOutput:
        messages = renderer.build_messages(input_data)
        purpose = renderer.purpose(input_data)
        raw = self._chain.call_preferred_model(
            model=renderer.primary_model,
            messages=messages,
            max_tokens=renderer.max_tokens,
            date_str=date_str,
            purpose=purpose,
            response_format=getattr(renderer, "response_format", None),
            timeout_seconds=getattr(renderer, "timeout_seconds", None),
        )
        return renderer.parse(raw)

    async def summarize_weekly_memo_async(self, raw_text: str, *, date_str: str) -> list[str]:
        renderer = MemoRenderer()
        return await self.render_async(
            renderer, MemoInput(raw_text=raw_text, date_str=date_str), date_str=date_str
        )

    async def generate_desk_card_brief_async(
        self,
        *,
        pair: str,
        regime: str,
        date_str: str,
        primary_driver: str | None,
        pain_index: float | None,
        rvol: float | None = None,
        todays_event_matrix: dict[str, Any] | None = None,
        dollar_dominance_score: float | None = None,
        dollar_bias: str | None = None,
    ) -> tuple[str, bool]:
        renderer = DeskCardRenderer()
        input_data = DeskCardInput(
            pair=pair,
            regime=regime,
            date_str=date_str,
            primary_driver=primary_driver,
            pain_index=pain_index,
            rvol=rvol,
            todays_event_matrix=todays_event_matrix,
            dollar_dominance_score=dollar_dominance_score,
            dollar_bias=dollar_bias,
        )
        human_grounding_active = renderer.human_grounding_active(input_data)
        messages = renderer.build_messages(input_data)
        for attempt in range(renderer.retry_attempts):
            try:
                raw = await self._chain.call_preferred_model_async(
                    model=renderer.primary_model,
                    messages=messages,
                    max_tokens=renderer.max_tokens,
                    date_str=date_str,
                    purpose=renderer.purpose(input_data),
                    response_format=renderer.response_format,
                    timeout_seconds=renderer.timeout_seconds,
                )
                parsed = renderer.parse(raw)
                return json.dumps(parsed), human_grounding_active
            except Exception as exc:  # noqa: BLE001
                if _is_timeout_error(exc):
                    logger.warning("Desk card timeout for %s attempt %s", pair, attempt + 1)
                else:
                    logger.warning("Desk card JSON parse/call failure for %s: %s", pair, exc)
        logger.warning("Falling back to deterministic desk card brief for %s", pair)
        return renderer.fallback(input_data), human_grounding_active

    def generate_brief(
        self,
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
        renderer = PairBriefRenderer()
        input_data = PairBriefInput(
            pair=pair,
            regime=regime,
            confidence=confidence,
            composite=composite,
            signal_row=signal_row,
            date_str=date_str,
            primary_driver=primary_driver,
            polymarket_context=polymarket_context,
            dollar_dominance_pct=dollar_dominance_pct,
            polymarket_odds_json=polymarket_odds_json,
        )
        return self.render(renderer, input_data, date_str=date_str)

    def generate_event_brief(
        self,
        risk_matrix: EventRiskResult | dict[str, Any],
        date_str: str,
        polymarket_context: str = "",
    ) -> str:
        renderer = EventBriefRenderer()
        input_data = EventBriefInput(
            risk_matrix=risk_matrix,
            date_str=date_str,
            polymarket_context=polymarket_context,
        )
        pair, event_name = renderer.log_context(input_data)
        messages = renderer.build_messages(input_data)
        for attempt in range(renderer.retry_attempts):
            try:
                raw = self._chain.call_preferred_model(
                    model=renderer.primary_model,
                    messages=messages,
                    max_tokens=renderer.max_tokens,
                    date_str=date_str,
                    purpose=renderer.purpose(input_data),
                    response_format=renderer.response_format,
                    timeout_seconds=renderer.timeout_seconds,
                )
                return renderer.parse(raw)
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
        return renderer.fallback(input_data)

    async def generate_linkedin_alpha_hook_async(
        self,
        card_data: dict[str, Any],
        *,
        date_str: str,
    ) -> str:
        renderer = LinkedInRenderer()
        input_data = LinkedInInput(card_data=card_data, date_str=date_str)
        return await self.render_async(renderer, input_data, date_str=date_str)

    def generate_linkedin_alpha_hook(self, card_data: dict[str, Any]) -> str:
        renderer = LinkedInRenderer()
        input_data = LinkedInInput(card_data=card_data)
        date_str = renderer.resolve_date_str(input_data)
        return self.render(renderer, input_data, date_str=date_str)

    async def generate_global_macro_summary(
        self,
        *,
        date_str: str,
        pair_contexts: list[str],
        macro_context: str,
        dollar_dominance_pct: float | None = None,
        polymarket_odds_json: str = "[]",
    ) -> str:
        renderer = MacroSummaryRenderer()
        input_data = MacroSummaryInput(
            date_str=date_str,
            pair_contexts=pair_contexts,
            macro_context=macro_context,
            dollar_dominance_pct=dollar_dominance_pct,
            polymarket_odds_json=polymarket_odds_json,
        )
        return await self.render_async(renderer, input_data, date_str=date_str)


_default_client = AIClient()


async def summarize_weekly_memo_async(raw_text: str, *, date_str: str) -> list[str]:
    return await _default_client.summarize_weekly_memo_async(raw_text, date_str=date_str)


async def generate_desk_card_brief_async(
    *,
    pair: str,
    regime: str,
    date_str: str,
    primary_driver: str | None,
    pain_index: float | None,
    rvol: float | None = None,
    todays_event_matrix: dict[str, Any] | None = None,
    dollar_dominance_score: float | None = None,
    dollar_bias: str | None = None,
) -> tuple[str, bool]:
    return await _default_client.generate_desk_card_brief_async(
        pair=pair,
        regime=regime,
        date_str=date_str,
        primary_driver=primary_driver,
        pain_index=pain_index,
        rvol=rvol,
        todays_event_matrix=todays_event_matrix,
        dollar_dominance_score=dollar_dominance_score,
        dollar_bias=dollar_bias,
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
    return _default_client.generate_brief(
        pair,
        regime,
        confidence,
        composite,
        signal_row,
        date_str,
        primary_driver=primary_driver,
        polymarket_context=polymarket_context,
        dollar_dominance_pct=dollar_dominance_pct,
        polymarket_odds_json=polymarket_odds_json,
    )


def generate_event_brief(
    risk_matrix: EventRiskResult | dict[str, Any],
    date_str: str,
    polymarket_context: str = "",
) -> str:
    return _default_client.generate_event_brief(
        risk_matrix, date_str, polymarket_context=polymarket_context
    )


async def generate_linkedin_alpha_hook_async(
    card_data: dict[str, Any],
    *,
    date_str: str,
) -> str:
    return await _default_client.generate_linkedin_alpha_hook_async(
        card_data, date_str=date_str
    )


def generate_linkedin_alpha_hook(card_data: dict[str, Any]) -> str:
    return _default_client.generate_linkedin_alpha_hook(card_data)


async def generate_global_macro_summary(
    *,
    date_str: str,
    pair_contexts: list[str],
    macro_context: str,
    dollar_dominance_pct: float | None = None,
    polymarket_odds_json: str = "[]",
) -> str:
    return await _default_client.generate_global_macro_summary(
        date_str=date_str,
        pair_contexts=pair_contexts,
        macro_context=macro_context,
        dollar_dominance_pct=dollar_dominance_pct,
        polymarket_odds_json=polymarket_odds_json,
    )
