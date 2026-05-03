"""Pre-math ingestion quorum and poison-row filtering (stdlib only)."""

from __future__ import annotations

import copy
import logging
import math
from typing import Any, Literal, NamedTuple

from src.fetchers.buffer_keys import KEY_FX_SPOT
from src.types import SpotBar

logger = logging.getLogger(__name__)

_QUORUM_FAILURE_RATIO = 0.50


class IngestionGate(NamedTuple):
    """Validated ingestion snapshot and telemetry for downstream math / DB."""

    buffer: dict[str, Any]
    telemetry_status: Literal["ONLINE", "OFFLINE"]


def _fx_pairs_ordered(universe: dict[str, Any]) -> list[str]:
    return [
        k
        for k, meta in universe.items()
        if isinstance(meta, dict) and meta.get("class") == "FX"
    ]


def _spot_print_ok(bars: Any) -> bool:
    if not isinstance(bars, list | tuple) or len(bars) == 0:
        return False
    last = bars[-1]
    if isinstance(last, SpotBar):
        c: float | None = last.close
    elif isinstance(last, dict):
        raw = last.get("close")
        c = float(raw) if raw is not None else None
    else:
        return False
    if c is None:
        return False
    try:
        cf = float(c)
    except (TypeError, ValueError):
        return False
    return not math.isnan(cf) and cf > 0.0


def validate_ingestion_buffer(buffer: dict[str, Any], *, universe: dict[str, Any]) -> IngestionGate:
    """Quorum-check spot ingestion, then drop poisoned pairs or abort the run.

    * If strictly more than 50% of configured FX pairs lack a valid spot print,
      returns ``telemetry_status='OFFLINE'`` — caller must abort before math/DB.
    * Otherwise drops only failed pairs from ``fx_spot``, freezes bar lists to tuples
      (immutable container) for a stable snapshot — do not mutate after this returns.
    """

    pairs = _fx_pairs_ordered(universe)
    n = len(pairs)
    if n == 0:
        logger.critical("validate_ingestion_buffer: empty FX universe")
        return IngestionGate(buffer=copy.deepcopy(buffer), telemetry_status="OFFLINE")

    fx_any = buffer.get(KEY_FX_SPOT)
    fx = fx_any if isinstance(fx_any, dict) else {}

    failed = 0
    for p in pairs:
        if not _spot_print_ok(fx.get(p)):
            failed += 1

    ratio = failed / float(n)
    if ratio > _QUORUM_FAILURE_RATIO:
        logger.critical(
            "Ingestion quorum breach: %s/%s pairs missing spot "
            "(%.1f%% > %.0f%%) — telemetry OFFLINE",
            failed,
            n,
            100.0 * ratio,
            100.0 * _QUORUM_FAILURE_RATIO,
        )
        return IngestionGate(buffer=copy.deepcopy(buffer), telemetry_status="OFFLINE")

    ok_spot = n - failed
    logger.info(
        "Ingestion gate ONLINE: %s/%s FX pairs have valid spot (quorum within %.0f%% failure cap)",
        ok_spot,
        n,
        100.0 * _QUORUM_FAILURE_RATIO,
    )

    out = copy.deepcopy(buffer)
    fx_out_any = out.get(KEY_FX_SPOT)
    if not isinstance(fx_out_any, dict):
        return IngestionGate(buffer=out, telemetry_status="ONLINE")

    fx_out: dict[str, Any] = fx_out_any
    for p in pairs:
        if not _spot_print_ok(fx_out.get(p)):
            logger.error("[ DATA CORRUPTION: %s dropped from ingestion buffer (no spot) ]", p)
            fx_out.pop(p, None)

    for k, v in list(fx_out.items()):
        if isinstance(v, list):
            fx_out[k] = tuple(v)

    return IngestionGate(buffer=out, telemetry_status="ONLINE")
