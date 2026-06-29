"""Daily AI request cap via writer telemetry."""

from __future__ import annotations

from src.db import writer

DAILY_REQUEST_LIMIT = 180


def check_limit(date_str: str) -> None:
    count = writer.get_ai_request_count_today(date_str)
    if count >= DAILY_REQUEST_LIMIT:
        msg = f"Daily AI request limit reached ({count}/{DAILY_REQUEST_LIMIT})"
        raise RuntimeError(msg)
