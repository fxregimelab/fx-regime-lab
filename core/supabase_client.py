# core/supabase_client.py
# Lazy Supabase client — never raises on import (CURSOR_RULES / PLAN Phase 0B).

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = Any  # type: ignore

SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

supabase: Optional["Client"] = None
if create_client and SUPABASE_URL and _key:
    try:
        supabase = create_client(SUPABASE_URL, _key)
    except Exception as e:  # pragma: no cover
        logger.warning("Supabase create_client failed: %s", e)
        supabase = None
elif not SUPABASE_URL or not _key:
    logger.debug("Supabase URL/key not set — remote writes skipped")
