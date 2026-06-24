"""Shared constants for the staged pipeline v2."""

from __future__ import annotations

# Prefect task retry policy applied at each stage boundary. Two retries with a
# 30-second delay lets transient database or Slack failures clear without
# corrupting the immutable ledger (writes are idempotent by ``(date, pair)``).
STAGE_TASK_RETRIES = 2
STAGE_TASK_RETRY_DELAY_SECONDS = 30
