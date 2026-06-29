"""OpenRouter provider adapter."""

from __future__ import annotations

import os

from openai import AsyncOpenAI, OpenAI

OPENROUTER_PRIMARY_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_FALLBACK_MODELS = [
    OPENROUTER_PRIMARY_MODEL,
    "google/gemma-3-27b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/free",
]


def openrouter_headers() -> dict[str, str]:
    return {
        "HTTP-Referer": "https://fxregimelab.com",
        "X-Title": "FX Regime Lab",
    }


def openrouter_api_key() -> str | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    return str(key).strip() if key and str(key).strip() else None


def openrouter_available() -> bool:
    return openrouter_api_key() is not None


def openrouter_client() -> OpenAI:
    key = openrouter_api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=openrouter_headers(),
    )


def async_openrouter_client() -> AsyncOpenAI:
    key = openrouter_api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return AsyncOpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=openrouter_headers(),
    )
