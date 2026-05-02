"""Regime-conditioned macro event risk matrix — asymmetry, MIE, exhaustion bands."""

from __future__ import annotations

import bisect
import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median, stdev
from typing import Any

from src.analysis.event_name_normalize import normalize_event_name
from src.fetchers.macro_calendar import _impact_meta

logger = logging.getLogger(__name__)

_HIGH_IMPACT_CACHE: frozenset[str] | None = None


def high_impact_canonical_event_names() -> frozenset[str]:
    global _HIGH_IMPACT_CACHE
    if _HIGH_IMPACT_CACHE is None:
        _HIGH_IMPACT_CACHE = frozenset(
            k for k, v in _impact_meta().items() if v[1] == "HIGH"
        )
    return _HIGH_IMPACT_CACHE


@dataclass(frozen=True)
class EventRiskResult:
    date: str
    pair: str
    event_name: str
    active_regime: str
    sample_size: int
    median_mie_multiplier: float | None
    beat_median_return: float | None
    miss_median_return: float | None
    inline_median_return: float | None
    asymmetry_ratio: float | None
    asymmetry_direction: str | None
    t1_exhaustion_p2_5: float | None
    t1_exhaustion_p16: float | None
    t1_exhaustion_p84: float | None
    t1_exhaustion_p97_5: float | None
    t1_tail_risk_p95: float | None
    t1_tail_risk_p05: float | None


def _to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique_event_names_by_date_normalized(
    rows: list[dict[str, Any]],
) -> dict[date, set[str]]:
    out: dict[date, set[str]] = {}
    for row in rows:
        dt = _to_date(row.get("date"))
        en = row.get("event_name")
        if dt is None or en is None:
            continue
        out.setdefault(dt, set()).add(normalize_event_name(str(en)))
    return out


def _multiple_high_events_in_window(
    center: date,
    names_per_date: dict[date, set[str]],
    high_canonicals: frozenset[str],
) -> bool:
    """True if more than one distinct HIGH-impact canonical event appears in T-1..T+1."""

    seen: set[str] = set()
    for delta in (-1, 0, 1):
        d = center + timedelta(days=delta)
        for name in names_per_date.get(d, set()):
            if name in high_canonicals:
                seen.add(name)
    return len(seen) > 1


def _median_prior_daily_range(
    prices_by_date: dict[date, tuple[float, float, float, float]],
    sorted_dates: list[date],
    dt: date,
    lookback: int = 10,
) -> float:
    try:
        idx = sorted_dates.index(dt)
    except ValueError:
        return 0.0
    ranges: list[float] = []
    for j in range(max(0, idx - lookback), idx):
        _o, h, low_px, _c = prices_by_date[sorted_dates[j]]
        ranges.append(abs(h - low_px))
    if not ranges:
        return 0.0
    return float(median(ranges))


def _daily_sigma_price(closes: list[float]) -> float:
    if not closes:
        return 1e-9
    if len(closes) < 2:
        return max(abs(closes[-1]) * 0.01, 1e-9)
    log_r: list[float] = []
    for i in range(1, len(closes)):
        a, b = closes[i - 1], closes[i]
        if a in (0, 0.0):
            continue
        log_r.append(math.log(b / a))
    if len(log_r) < 2:
        sd = 0.01
    else:
        sd = stdev(log_r)
    return max(sd * closes[-1], 1e-9)


def _next_trading_date(sorted_dates: list[date], dt: date) -> date | None:
    i = bisect.bisect_right(sorted_dates, dt)
    return sorted_dates[i] if i < len(sorted_dates) else None


def _quantile_q(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    sorted_vals = sorted(xs)
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    w = pos - lo
    return float(sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w)


def _norm_surprise_direction(raw: Any) -> str:
    u = str(raw or "").strip().upper().replace("_", " ")
    compact = u.replace(" ", "")
    if compact == "INLINE":
        return "IN-LINE"
    return u


def compute_event_risk_matrix(
    pair: str,
    event_name: str,
    target_date: date,
    current_regime: str,
    historical_prices: list[dict[str, Any]],
    historical_surprises: list[dict[str, Any]],
    regime_calls: list[dict[str, Any]],
    *,
    all_surprises_for_pure_dates: list[dict[str, Any]] | None = None,
) -> EventRiskResult | None:
    canonical_event = normalize_event_name(event_name)
    high_canonicals = high_impact_canonical_event_names()

    regime_by_date: dict[date, str] = {}
    for row in regime_calls:
        dt = _to_date(row.get("date"))
        regime = row.get("regime")
        if dt is None or regime is None:
            continue
        regime_by_date[dt] = str(regime)

    prices_by_date: dict[date, tuple[float, float, float, float]] = {}
    for row in historical_prices:
        dt = _to_date(row.get("date"))
        open_px = _safe_float(row.get("open"))
        high_px = _safe_float(row.get("high"))
        low_px = _safe_float(row.get("low"))
        close_px = _safe_float(row.get("close"))
        if dt is None or None in (open_px, high_px, low_px, close_px):
            continue
        assert (
            open_px is not None
            and high_px is not None
            and low_px is not None
            and close_px is not None
        )
        prices_by_date[dt] = (open_px, high_px, low_px, close_px)

    sorted_price_dates = sorted(prices_by_date.keys())
    names_per_date = (
        _unique_event_names_by_date_normalized(all_surprises_for_pure_dates)
        if all_surprises_for_pure_dates
        else None
    )
    contaminated = 0

    mie_multipliers: list[float] = []
    beat_returns: list[float] = []
    miss_returns: list[float] = []
    inline_returns: list[float] = []
    all_t1_returns: list[float] = []

    for surprise in historical_surprises:
        row_canon = normalize_event_name(str(surprise.get("event_name", "")))
        if row_canon != canonical_event:
            continue
        dt = _to_date(surprise.get("date"))
        if dt is None:
            continue
        if names_per_date is not None:
            if _multiple_high_events_in_window(dt, names_per_date, high_canonicals):
                contaminated += 1
                continue
        matched_regime = regime_by_date.get(dt)
        if matched_regime != current_regime:
            continue
        price_row = prices_by_date.get(dt)
        if price_row is None:
            continue

        open_px, high_px, low_px, close_px = price_row
        baseline_1h = _median_prior_daily_range(prices_by_date, sorted_price_dates, dt) * 0.25
        mie_raw = max(abs(high_px - open_px), abs(low_px - open_px))
        mie_refined = max(0.0, mie_raw - baseline_1h)

        try:
            ev_idx = sorted_price_dates.index(dt)
        except ValueError:
            continue
        closes_for_vol = [
            prices_by_date[sorted_price_dates[k]][3]
            for k in range(max(0, ev_idx - 20), ev_idx)
        ]
        sigma_scale = (
            _daily_sigma_price(closes_for_vol)
            if len(closes_for_vol) >= 2
            else max(abs(close_px) * 0.01, 1e-9)
        )
        vol_mult = mie_refined / sigma_scale
        mie_multipliers.append(vol_mult)

        t1d = _next_trading_date(sorted_price_dates, dt)
        t1_pct: float | None = None
        if t1d is not None and t1d in prices_by_date and close_px != 0.0:
            _o2, _h2, _l2, c2 = prices_by_date[t1d]
            t1_pct = (c2 - close_px) / close_px * 100.0
            all_t1_returns.append(t1_pct)

        direction = _norm_surprise_direction(surprise.get("surprise_direction"))
        if t1_pct is None:
            continue
        if direction == "BEAT":
            beat_returns.append(t1_pct)
        elif direction == "MISS":
            miss_returns.append(t1_pct)
        elif direction == "IN-LINE":
            inline_returns.append(t1_pct)

    if names_per_date is not None:
        logger.info(
            "Event risk: skipped %s HIGH-contaminated windows (48h) for %s %s (%s)",
            contaminated,
            pair,
            canonical_event,
            current_regime,
        )

    n = len(mie_multipliers)
    logger.info(
        "Event risk matrix N=%s for %s %s (%s)",
        n,
        pair,
        canonical_event,
        current_regime,
    )
    if n == 0:
        return None

    median_mie = float(median(mie_multipliers))

    if n < 5:
        return EventRiskResult(
            date=target_date.isoformat(),
            pair=pair,
            event_name=canonical_event,
            active_regime=current_regime,
            sample_size=n,
            median_mie_multiplier=median_mie,
            beat_median_return=None,
            miss_median_return=None,
            inline_median_return=None,
            asymmetry_ratio=None,
            asymmetry_direction=None,
            t1_exhaustion_p2_5=None,
            t1_exhaustion_p16=None,
            t1_exhaustion_p84=None,
            t1_exhaustion_p97_5=None,
            t1_tail_risk_p95=None,
            t1_tail_risk_p05=None,
        )

    beat_med = float(median(beat_returns)) if beat_returns else None
    miss_med = float(median(miss_returns)) if miss_returns else None
    inline_med = float(median(inline_returns)) if inline_returns else None

    abs_for_ratio: list[float] = []
    if beat_returns:
        abs_for_ratio.append(abs(float(median(beat_returns))))
    if miss_returns:
        abs_for_ratio.append(abs(float(median(miss_returns))))
    if inline_returns:
        abs_for_ratio.append(abs(float(median(inline_returns))))

    asymmetry_ratio: float | None = None
    if len(abs_for_ratio) >= 2:
        srt = sorted(abs_for_ratio)
        asymmetry_ratio = srt[-1] / max(srt[0], 1e-9)

    asymmetry_direction: str | None = None
    candidates: list[tuple[str, float]] = []
    if beat_returns:
        candidates.append(("UPSIDE", float(median(beat_returns))))
    if miss_returns:
        candidates.append(("DOWNSIDE", float(median(miss_returns))))
    if inline_returns:
        candidates.append(("NEUTRAL", float(median(inline_returns))))
    if candidates:
        dominant = max(candidates, key=lambda x: abs(x[1]))
        asymmetry_direction = dominant[0]

    n_t1 = len(all_t1_returns)
    p25 = _quantile_q(all_t1_returns, 0.025) if n_t1 >= 5 else None
    p16 = _quantile_q(all_t1_returns, 0.16) if n_t1 >= 5 else None
    p84 = _quantile_q(all_t1_returns, 0.84) if n_t1 >= 5 else None
    p975 = _quantile_q(all_t1_returns, 0.975) if n_t1 >= 5 else None
    p95_tail = _quantile_q(all_t1_returns, 0.95) if n_t1 >= 5 else None
    p05_tail = _quantile_q(all_t1_returns, 0.05) if n_t1 >= 5 else None

    return EventRiskResult(
        date=target_date.isoformat(),
        pair=pair,
        event_name=canonical_event,
        active_regime=current_regime,
        sample_size=n,
        median_mie_multiplier=median_mie,
        beat_median_return=beat_med,
        miss_median_return=miss_med,
        inline_median_return=inline_med,
        asymmetry_ratio=asymmetry_ratio,
        asymmetry_direction=asymmetry_direction,
        t1_exhaustion_p2_5=p25,
        t1_exhaustion_p16=p16,
        t1_exhaustion_p84=p84,
        t1_exhaustion_p97_5=p975,
        t1_tail_risk_p95=p95_tail,
        t1_tail_risk_p05=p05_tail,
    )
