"""Append-only ledger strategy for supersede + insert writes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AppendOnlyLedger:
    """Encapsulates the append-only supersede-then-insert invariant."""

    @staticmethod
    def append(
        payload: dict[str, Any],
        existing: dict[str, Any] | None,
        *,
        payload_matches: Callable[[dict[str, Any], dict[str, Any]], bool],
        on_supersede: Callable[[Any], None],
        on_insert: Callable[[dict[str, Any]], None],
        should_skip: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
    ) -> None:
        """Apply append-only versioning: supersede current row, then insert new."""
        versioned = {**payload, "is_superseded": False}

        if existing is None:
            on_insert(versioned)
            return

        if should_skip is not None and should_skip(existing, versioned):
            return

        if payload_matches(versioned, existing):
            return

        existing_id = existing.get("id")
        if existing_id is not None:
            on_supersede(existing_id)

        on_insert(versioned)
