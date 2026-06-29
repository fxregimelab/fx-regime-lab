"""Provider port for multi-tier AI fallback chain."""

from __future__ import annotations

from typing import Protocol


class ProviderPort(Protocol):
    """Async chat completion against a single provider tier."""

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        date_str: str,
        purpose: str,
        response_format: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> str: ...
