"""NVIDIA NIM provider adapter."""

from __future__ import annotations

import os

from openai import AsyncOpenAI, OpenAI

NIM_PRIMARY_MODEL = "meta/llama-3.3-70b-instruct"
NIM_FALLBACK_MODELS = [
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
]


def nim_api_key() -> str | None:
    key = os.environ.get("NVIDIA_NIM_API_KEY")
    return str(key).strip() if key and str(key).strip() else None


def nim_available() -> bool:
    return nim_api_key() is not None


def nim_client() -> OpenAI:
    key = nim_api_key()
    if not key:
        raise RuntimeError("NVIDIA_NIM_API_KEY is not set")
    return OpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1")


def async_nim_client() -> AsyncOpenAI:
    key = nim_api_key()
    if not key:
        raise RuntimeError("NVIDIA_NIM_API_KEY is not set")
    return AsyncOpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1")
