# core/pipeline_status.py
# Writes site/data/pipeline_status.json for Cloudflare Pages dashboard (Phase 0A).

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

from core.paths import PIPELINE_STATUS_JSON, SUPABASE_SYNC_SIDECAR


def _read_supabase_sidecar() -> dict[str, Any]:
    if not os.path.isfile(SUPABASE_SYNC_SIDECAR):
        return {}
    try:
        with open(SUPABASE_SYNC_SIDECAR, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_pipeline_status(
    *,
    ok: bool,
    steps_completed: Optional[List[str]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Atomically write JSON consumed by fxregimelab.com /dashboard."""
    payload: dict[str, Any] = {
        "last_run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_run_status": "ok" if ok else "failed",
        "steps_completed": steps_completed or [],
        "source": "fx_regime_pipeline",
    }
    if error_message:
        payload["error_message"] = error_message[:500]

    sb = _read_supabase_sidecar()
    payload["supabase_write_status"] = sb.get("supabase_write_status", "skipped")
    payload["supabase_rows_written"] = int(sb.get("supabase_rows_written", 0))
    payload["last_supabase_write"] = sb.get("last_supabase_write")

    os.makedirs(os.path.dirname(PIPELINE_STATUS_JSON), exist_ok=True)
    tmp = PIPELINE_STATUS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, PIPELINE_STATUS_JSON)
