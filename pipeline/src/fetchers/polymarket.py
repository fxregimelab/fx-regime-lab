"""Polymarket Gamma API — Economics-tilted active markets (async + sync helpers)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Final

import aiohttp

logger = logging.getLogger(__name__)

GAMMA_BASE: Final[str] = "https://gamma-api.polymarket.com"
_MARKETS_PATH: Final[str] = "/markets"
_DEFAULT_LIMIT: Final[int] = 250
_MIN_VOLUME_USD: Final[float] = 50_000.0

_ECON_PAT = re.compile(
    r"econ|macro|fed|recession|cpi|pce|rates?\b|treasury|gdp|employment|nfp|jobs report",
    re.IGNORECASE,
)


def _cast_dict(m: Any) -> dict[str, Any]:
    return dict(m) if isinstance(m, dict) else {}


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _market_volume(m: dict[str, Any]) -> float:
    return max(
        _to_float(m.get("volume24hr")),
        _to_float(m.get("volume")),
        _to_float(m.get("volumeNum")),
        _to_float(m.get("volumeClob")),
    )


def _is_economics_market(m: dict[str, Any]) -> bool:
    tags = m.get("tags")
    if isinstance(tags, list):
        for t in tags:
            if not isinstance(t, dict):
                continue
            blob = f"{t.get('label') or ''} {t.get('slug') or ''}"
            if _ECON_PAT.search(blob):
                return True
    cat = str(m.get("category") or "")
    if _ECON_PAT.search(cat):
        return True
    question = str(m.get("question") or m.get("title") or "")
    return bool(_ECON_PAT.search(question))


def _first_outcome_probability(m: dict[str, Any]) -> float | None:
    raw = m.get("outcomePrices")
    if isinstance(raw, str) and raw.strip():
        try:
            arr = json.loads(raw)
            if isinstance(arr, list) and arr:
                return float(arr[0])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    outcomes = m.get("outcomes")
    if isinstance(outcomes, list) and outcomes:
        first = outcomes[0]
        if isinstance(first, dict) and first.get("price") is not None:
            try:
                return float(first["price"])
            except (TypeError, ValueError):
                return None
    return None


def normalize_polymarket_record(m: dict[str, Any]) -> dict[str, Any]:
    """Stable shape for prompts + ``sentiment_json``."""
    question = str(m.get("question") or m.get("title") or "Unknown")
    prob = _first_outcome_probability(m)
    return {
        "question": question,
        "probability": prob,
        "volume_usd": _market_volume(m),
        "slug": m.get("slug"),
        "condition_id": m.get("conditionId"),
    }


async def fetch_economics_markets_async(
    *,
    session: aiohttp.ClientSession | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch active markets and retain high-volume Economics-themed rows."""

    url = f"{GAMMA_BASE}{_MARKETS_PATH}"
    params: dict[str, str] = {
        "closed": "false",
        "limit": str(limit),
        "order": "volume24hr",
        "ascending": "false",
    }
    owns_session = session is None
    sess = session or aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=45),
        headers={"Accept": "application/json"},
    )
    try:
        async with sess.get(url, params=params) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.warning("Polymarket Gamma HTTP %s: %s", resp.status, body[:200])
                return []
            payload = await resp.json()
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Polymarket Gamma request failed: %s", exc)
        return []
    finally:
        if owns_session:
            await sess.close()

    if not isinstance(payload, list):
        return []

    econ = [m for m in payload if isinstance(m, dict) and _is_economics_market(m)]
    ranked = sorted(
        econ,
        key=_market_volume,
        reverse=True,
    )
    out = [
        normalize_polymarket_record(_cast_dict(m))
        for m in ranked
        if _market_volume(m) >= _MIN_VOLUME_USD
    ]
    return out


def get_active_economics_markets() -> list[dict[str, Any]]:
    """Sync entrypoint for orchestrator (no parallel daily guard)."""

    return asyncio.run(fetch_economics_markets_async())


def polymarket_odds_json_for_prompt(markets: list[dict[str, Any]]) -> str:
    """Compact JSON array for LLM consumption."""

    slim = []
    for m in markets[:12]:
        slim.append(
            {
                "question": m.get("question"),
                "probability": m.get("probability"),
                "volume_usd": m.get("volume_usd"),
            }
        )
    return json.dumps(slim)
