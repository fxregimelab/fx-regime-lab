"""Gemini provider adapter."""

from __future__ import annotations

import os

from openai import AsyncOpenAI, OpenAI

GEMINI_PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")


def gemini_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    return str(key).strip() if key and str(key).strip() else None


def gemini_available() -> bool:
    return gemini_api_key() is not None


def gemini_client() -> OpenAI:
    key = gemini_api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return OpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def async_gemini_client() -> AsyncOpenAI:
    key = gemini_api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return AsyncOpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
