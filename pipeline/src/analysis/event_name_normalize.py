"""Map raw macro release labels to canonical calendar keys via ``event_aliases``."""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _alias_maps() -> tuple[dict[str, str], dict[str, list[str]]]:
    try:
        from src.db import writer

        rows = writer.fetch_event_aliases()
    except Exception as exc:  # noqa: BLE001
        logger.warning("event_aliases load failed (%s); identity normalization only", exc)
        rows = []
    a2c: dict[str, str] = {}
    c2a: dict[str, list[str]] = {}
    for row in rows:
        c_raw, a_raw = row.get("canonical_name"), row.get("alias_name")
        if not isinstance(c_raw, str) or not isinstance(a_raw, str):
            continue
        c, a = c_raw.strip(), a_raw.strip()
        if not c or not a:
            continue
        a2c[a] = c
        c2a.setdefault(c, []).append(a)
    return a2c, c2a


def refresh_event_alias_cache() -> None:
    """Clear LRU cache (e.g. after tests mutate aliases)."""

    _alias_maps.cache_clear()


def normalize_event_name(raw_name: str) -> str:
    """Return canonical event key for joins and risk math."""

    s = raw_name.strip()
    if not s:
        return s
    a2c, _ = _alias_maps()
    return a2c.get(s, s)


def expand_event_names_for_query(canonical_name: str) -> list[str]:
    """All DB ``event_name`` values that belong to this canonical release."""

    c = normalize_event_name(canonical_name)
    _, c2a = _alias_maps()
    out: set[str] = {c}
    out.update(c2a.get(c, []))
    return sorted(out)
