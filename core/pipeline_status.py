# core/pipeline_status.py
# Writes site/data/pipeline_status.json for Cloudflare Pages dashboard (Phase 0A).

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

from core.paths import PIPELINE_STATUS_JSON


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

    os.makedirs(os.path.dirname(PIPELINE_STATUS_JSON), exist_ok=True)
    tmp = PIPELINE_STATUS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, PIPELINE_STATUS_JSON)
