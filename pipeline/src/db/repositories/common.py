"""Shared helpers for DB repositories (internal)."""

from __future__ import annotations

from datetime import date


def date_iso(d: date | str) -> str:
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]
