"""Pre-math ingestion quorum, poison-row filtering, and DQS freshness helpers."""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, NamedTuple

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.types import CotRow, SpotBar

logger = logging.getLogger(__name__)

_QUORUM_FAILURE_RATIO = 0.50

# Weights from product spec (sum = 0.90 — normalized inside ``compute_dqs``).
_W_RATES = 0.25
_W_SPOTS = 0.20
_W_COT = 0.10
_W_COMMODITIES = 0.20
_W_CROSS_ASSET = 0.15
_WEIGHT_SUM = _W_RATES + _W_SPOTS + _W_COT + _W_COMMODITIES + _W_CROSS_ASSET

_MAX_AGE_SPOTS_H = 24.0
_MAX_AGE_RATES_H = 36.0
_MAX_AGE_COT_H = 168.0
_MAX_AGE_COMMODITIES_H = 36.0
_MAX_AGE_CROSS_ASSET_H = 24.0


class IngestionGate(NamedTuple):
    """Validated ingestion snapshot and telemetry for downstream math / DB."""

    buffer: dict[str, Any]
    telemetry_status: Literal["ONLINE", "OFFLINE"]


@dataclass(frozen=True)
class DqsResult:
    """Composite Data Quality Score and per-bucket freshness diagnostics."""

    score: float
    rates_freshness: float
    spots_freshness: float
    cot_freshness: float
    commodities_freshness: float
    cross_asset_freshness: float
    critical_penalty_applied: bool
    spot_observation_date: date | None
    cot_observation_date: date | None


def freshness_score_from_age_hours(age_hours: float, max_age_hours: float) -> float:
    """Piecewise freshness: 1.0 inside SLA, linear decay to 0 by ``2*max_age``, else 0.1."""

    if age_hours <= max_age_hours:
        return 1.0
    if age_hours <= 2.0 * max_age_hours:
        span = max_age_hours
        return max(0.0, 1.0 - (age_hours - max_age_hours) / span)
    return 0.1


def _us_federal_holidays(start_year: int, end_year: int) -> list[str]:
    """Return US federal holidays as ISO date strings for ``np.busday_count``."""
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=f"{start_year}-01-01", end=f"{end_year}-12-31")
    return [h.strftime("%Y-%m-%d") for h in holidays]


_US_HOLIDAYS_CACHE: list[str] | None = None


def _calendar_age_hours(as_of: date, observed: date | None) -> float | None:
    if observed is None:
        return None
    if observed > as_of:
        return 0.0
    global _US_HOLIDAYS_CACHE
    if _US_HOLIDAYS_CACHE is None:
        # Cache a ±5-year window around the observed date to avoid
        # repeated DataFrame construction.
        year = observed.year
        _US_HOLIDAYS_CACHE = _us_federal_holidays(year - 5, year + 5)
    trading_days = int(
        np.busday_count(
            observed.isoformat(),
            as_of.isoformat(),
            holidays=_US_HOLIDAYS_CACHE,
        )
    )
    return float(trading_days * 24)


def fx_pairs_from_universe(universe: dict[str, Any]) -> list[str]:
    """Public alias for FX pair symbols (class FX) in display order."""

    return _fx_pairs_ordered(universe)


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


def _latest_spot_observation_date(buffer: dict[str, Any], universe: dict[str, Any]) -> date | None:
    fx_any = buffer.get(KEY_FX_SPOT)
    fx = fx_any if isinstance(fx_any, dict) else {}
    latest: date | None = None
    for p in _fx_pairs_ordered(universe):
        bars_any = fx.get(p)
        if not _spot_print_ok(bars_any):
            continue
        bars = bars_any if isinstance(bars_any, list | tuple) else []
        if not bars:
            continue
        last = bars[-1]
        d_obs: date | None
        if isinstance(last, SpotBar):
            d_obs = last.date
        elif isinstance(last, dict):
            raw_d = last.get("date")
            try:
                d_obs = date.fromisoformat(str(raw_d)[:10]) if raw_d is not None else None
            except ValueError:
                d_obs = None
        else:
            d_obs = None
        if d_obs is None:
            continue
        latest = d_obs if latest is None else max(latest, d_obs)
    return latest


def _spots_bucket_freshness(buffer: dict[str, Any], universe: dict[str, Any], as_of: date) -> float:
    pairs = _fx_pairs_ordered(universe)
    if not pairs:
        return 0.1
    fx_any = buffer.get(KEY_FX_SPOT)
    fx = fx_any if isinstance(fx_any, dict) else {}
    stale = 0
    for p in pairs:
        if not _spot_print_ok(fx.get(p)):
            stale += 1
    ratio = stale / float(len(pairs))
    if ratio > _QUORUM_FAILURE_RATIO:
        return 0.1
    spot_date = _latest_spot_observation_date(buffer, universe)
    age_h = _calendar_age_hours(as_of, spot_date)
    if age_h is None:
        return 0.1
    return freshness_score_from_age_hours(age_h, _MAX_AGE_SPOTS_H)


def _rates_bucket_freshness(buffer: dict[str, Any], universe: dict[str, Any], as_of: date) -> float:
    """Missing required yield legs ⇒ stale (critical).
    Else freshness vs 36h using spot observation age."""

    y_any = buffer.get(KEY_YIELDS)
    if not isinstance(y_any, dict):
        return 0.1
    yields_dict: dict[str, float | None] = dict(y_any)
    required: set[str] = set()
    for p in _fx_pairs_ordered(universe):
        meta = universe.get(p)
        if not isinstance(meta, dict):
            continue
        tickers = meta.get("tickers") or {}
        if not isinstance(tickers, dict):
            continue
        for key in ("yield_base", "yield_quote"):
            tid = tickers.get(key)
            if isinstance(tid, str):
                required.add(tid)
    if not required:
        return 1.0
    for sid in required:
        if yields_dict.get(sid) is None:
            logger.warning("DQS rates bucket: missing yield series %s", sid)
            return 0.1
    spot_date = _latest_spot_observation_date(buffer, universe)
    age_h = _calendar_age_hours(as_of, spot_date)
    if age_h is None:
        return 0.1
    return freshness_score_from_age_hours(age_h, _MAX_AGE_RATES_H)


def _cot_bucket_freshness(buffer: dict[str, Any], universe: dict[str, Any], as_of: date) -> float:
    cot_any = buffer.get(KEY_COT)
    rows: list[Any] = cot_any if isinstance(cot_any, list) else []
    pairs_set = set(_fx_pairs_ordered(universe))
    latest: date | None = None
    for row in rows:
        if isinstance(row, CotRow):
            if row.pair in pairs_set:
                latest = row.date if latest is None else max(latest, row.date)
        elif isinstance(row, dict):
            pr = row.get("pair")
            raw_d = row.get("date")
            if pr not in pairs_set:
                continue
            try:
                d_obs = date.fromisoformat(str(raw_d)[:10]) if raw_d is not None else None
            except ValueError:
                continue
            if d_obs is None:
                continue
            latest = d_obs if latest is None else max(latest, d_obs)
    age_h = _calendar_age_hours(as_of, latest)
    if age_h is None:
        return 0.1
    return freshness_score_from_age_hours(age_h, _MAX_AGE_COT_H)


def _commodities_bucket_freshness(
    buffer: dict[str, Any],
    universe: dict[str, Any],
    as_of: date,
) -> float:
    cross_any = buffer.get(KEY_CROSS_ASSET)
    cross = cross_any if isinstance(cross_any, dict) else {}
    legs = ("oil", "gold", "copper")
    fresh_vals: list[float] = []
    spot_date = _latest_spot_observation_date(buffer, universe)
    age_h = _calendar_age_hours(as_of, spot_date)
    for leg in legs:
        if cross.get(leg) is None:
            fresh_vals.append(0.1)
        elif age_h is None:
            fresh_vals.append(0.1)
        else:
            fresh_vals.append(freshness_score_from_age_hours(age_h, _MAX_AGE_COMMODITIES_H))
    return sum(fresh_vals) / float(len(legs))


def _cross_asset_bucket_freshness(
    buffer: dict[str, Any],
    universe: dict[str, Any],
    as_of: date,
) -> float:
    cross_any = buffer.get(KEY_CROSS_ASSET)
    cross = cross_any if isinstance(cross_any, dict) else {}
    spot_date = _latest_spot_observation_date(buffer, universe)
    age_h = _calendar_age_hours(as_of, spot_date)
    parts: list[float] = []
    for leg in ("vix", "dxy"):
        if cross.get(leg) is None:
            parts.append(0.1)
        elif age_h is None:
            parts.append(0.1)
        else:
            parts.append(freshness_score_from_age_hours(age_h, _MAX_AGE_CROSS_ASSET_H))
    return sum(parts) / float(len(parts))


def compute_dqs(buffer: dict[str, Any], universe: dict[str, Any], as_of: date) -> DqsResult:
    """Weighted freshness composite with critical-leg penalty (rates + spots)."""

    rates_f = _rates_bucket_freshness(buffer, universe, as_of)
    spots_f = _spots_bucket_freshness(buffer, universe, as_of)
    cot_f = _cot_bucket_freshness(buffer, universe, as_of)
    comm_f = _commodities_bucket_freshness(buffer, universe, as_of)
    x_f = _cross_asset_bucket_freshness(buffer, universe, as_of)

    wr = _W_RATES / _WEIGHT_SUM
    ws = _W_SPOTS / _WEIGHT_SUM
    wc = _W_COT / _WEIGHT_SUM
    wm = _W_COMMODITIES / _WEIGHT_SUM
    wx = _W_CROSS_ASSET / _WEIGHT_SUM

    raw = wr * rates_f + ws * spots_f + wc * cot_f + wm * comm_f + wx * x_f
    critical_penalty = rates_f <= 0.1 or spots_f <= 0.1
    score = raw * 0.45 if critical_penalty else raw

    cot_any = buffer.get(KEY_COT)
    cot_rows: list[Any] = cot_any if isinstance(cot_any, list) else []
    pairs_set = set(_fx_pairs_ordered(universe))
    cot_latest: date | None = None
    for row in cot_rows:
        if isinstance(row, CotRow) and row.pair in pairs_set:
            cot_latest = row.date if cot_latest is None else max(cot_latest, row.date)
        elif isinstance(row, dict) and row.get("pair") in pairs_set:
            raw_d = row.get("date")
            try:
                d_obs = date.fromisoformat(str(raw_d)[:10]) if raw_d is not None else None
            except ValueError:
                continue
            if d_obs is not None:
                cot_latest = d_obs if cot_latest is None else max(cot_latest, d_obs)

    return DqsResult(
        score=min(1.0, max(0.0, score)),
        rates_freshness=rates_f,
        spots_freshness=spots_f,
        cot_freshness=cot_f,
        commodities_freshness=comm_f,
        cross_asset_freshness=x_f,
        critical_penalty_applied=critical_penalty,
        spot_observation_date=_latest_spot_observation_date(buffer, universe),
        cot_observation_date=cot_latest,
    )
