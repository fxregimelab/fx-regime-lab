"""Artifact renderer protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

TInput = TypeVar("TInput", contravariant=True)
TOutput = TypeVar("TOutput", covariant=True)


class ArtifactRenderer(Protocol[TInput, TOutput]):
    """Build prompts and parse LLM responses for a single artifact type."""

    primary_model: str
    max_tokens: int

    def build_messages(self, input_data: TInput) -> list[dict[str, str]]: ...

    def parse(self, payload_text: str) -> TOutput: ...

    def purpose(self, input_data: TInput) -> str: ...
