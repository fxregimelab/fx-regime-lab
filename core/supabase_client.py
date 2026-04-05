# core/supabase_client.py
# Lazy Supabase client — never raises on import. CI writes use SERVICE ROLE only (RLS bypass).

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    # override=True: empty User/system env vars (e.g. SUPABASE_URL="") must not block .env values
    load_dotenv(_REPO_ROOT / ".env", override=True)
except ImportError:
    pass

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = Any  # type: ignore

SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

_client: Optional["Client"] = None
_client_attempted: bool = False


def get_client() -> Optional["Client"]:
    """Return Supabase client or None. Prints once if misconfigured. Never raises here."""
    global _client, _client_attempted
    if _client_attempted:
        return _client
    _client_attempted = True
    if not create_client:
        print("[Supabase] supabase-py not installed — run: pip install supabase")
        _client = None
        return None
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print(
            "[Supabase] Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY "
            "(check repo-root .env; clear empty Windows env vars if set)"
        )
        _client = None
        return None
    try:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:  # pragma: no cover
        print(f"[Supabase] create_client failed: {e}")
        _client = None
    return _client


def __getattr__(name: str) -> Any:
    if name == "supabase":
        return get_client()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
