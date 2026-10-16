"""Groq provider adapter."""

from __future__ import annotations

import os

from openai import AsyncOpenAI, OpenAI

GROQ_PRIMARY_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODELS = [
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "llama4-scout-17b-16e-instruct",
]


def groq_api_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    return str(key).strip() if key and str(key).strip() else None


def groq_available() -> bool:
    return groq_api_key() is not None


def groq_client() -> OpenAI:
    key = groq_api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


def async_groq_client() -> AsyncOpenAI:
    key = groq_api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    return AsyncOpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
