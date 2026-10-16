"""Desk open card repository (internal — use ``src.db.writer``)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from supabase import Client

from src.db.repositories.common import date_iso
from src.types import DeskOpenCardRow


class DeskCardRepository:
    def __init__(self, client_factory: Callable[[], Client]) -> None:
        self._client_factory = client_factory

    @staticmethod
    def _desk_open_card_payload(card: DeskOpenCardRow) -> dict[str, Any]:
        from dataclasses import asdict

        payload: dict[str, Any] = asdict(card)
        payload["date"] = date_iso(card.date)
        return payload

    def write_desk_open_card(self, card: DeskOpenCardRow) -> None:
        self._client_factory().table("desk_open_cards").upsert(
            self._desk_open_card_payload(card), on_conflict="pair,date"
        ).execute()

    def write_desk_open_cards_bulk(self, cards: Sequence[DeskOpenCardRow]) -> None:
        if not cards:
            return
        rows = [self._desk_open_card_payload(c) for c in cards]
        self._client_factory().table("desk_open_cards").upsert(
            rows, on_conflict="pair,date"
        ).execute()

    def get_desk_open_cards_for_date(self, date_str: str) -> list[dict[str, Any]]:
        res = (
            self._client_factory()
            .table("desk_open_cards")
            .select("*")
            .eq("date", str(date_str)[:10])
            .execute()
        )
        return cast(list[dict[str, Any]], res.data or [])

    def get_latest_desk_open_card(self, pair: str) -> dict[str, Any] | None:
        res = (
            self._client_factory()
            .table("desk_open_cards")
            .select("*")
            .eq("pair", pair)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], res.data or [])
        return rows[0] if rows else None

    def update_desk_open_card_flags(
        self,
        pair: str,
        date_str: str,
        *,
        invalidation_triggered: bool | None = None,
        telemetry_status: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {}
        if invalidation_triggered is not None:
            payload["invalidation_triggered"] = invalidation_triggered
        if telemetry_status is not None:
            payload["telemetry_status"] = telemetry_status
        if not payload:
            return
        (
            self._client_factory()
            .table("desk_open_cards")
            .update(payload)
            .eq("pair", pair)
            .eq("date", date_str)
            .execute()
        )

    def update_desk_open_card_telemetry_audit(
        self, pair: str, date_str: str, telemetry_audit_patch: Mapping[str, Any]
    ) -> None:
        current = (
            self._client_factory()
            .table("desk_open_cards")
            .select("telemetry_audit")
            .eq("pair", pair)
            .eq("date", date_str)
            .maybe_single()
            .execute()
        )
        current_row = cast(
            dict[str, Any] | None, current.data if current is not None else None
        )
        existing = (
            cast(dict[str, Any], current_row.get("telemetry_audit"))
            if current_row and isinstance(current_row.get("telemetry_audit"), dict)
            else {}
        )
        merged = {**existing, **dict(telemetry_audit_patch)}
        (
            self._client_factory()
            .table("desk_open_cards")
            .update({"telemetry_audit": merged})
            .eq("pair", pair)
            .eq("date", date_str)
            .execute()
        )
