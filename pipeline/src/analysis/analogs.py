"""Historical analog engine for contextual research insights."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class AnalogResult:
    rank: int
    match_date: str
    match_score: float
    forward_30d_return: float
    regime_stability: float
    context_label: str
    current_trend_5d: float
    matched_trend_5d: float
    current_composite: float


def _safe_trend_5d(closes: Sequence[float]) -> float:
    if len(closes) < 6:
        return 0.0
    base = closes[-6]
    if base == 0:
        return 0.0
    return ((closes[-1] / base) - 1.0) * 100.0


def _context_label(match_dt: date) -> str:
    if match_dt.year <= 2009:
        return "Post-GFC"
    if match_dt.year <= 2016:
        return "QE Divergence"
    if match_dt.year <= 2020:
        return "Late-Cycle / Election"
    if match_dt.year <= 2022:
        return "Pandemic / Shock"
    return "Tightening Cycle"


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


def compute_historical_analogs(
    pair: str,
    as_of_date: str,
    current_composite: float,
    recent_spot_closes: Sequence[float],
    historical_rows: Sequence[dict[str, Any]],
) -> list[AnalogResult]:
    """Find the top-3 analog periods by matching current trend+composite proxy.

    The engine compares today's 5-day trend and composite to deep historical prices.
    It returns top matches and each match's 30-day forward return and stability score.
    """
    if len(recent_spot_closes) < 6 or len(historical_rows) < 60:
        return []

    current_trend_5d = _safe_trend_5d(recent_spot_closes)
    target_sign = 1 if current_composite >= 0 else -1

    cutoff = _to_date(as_of_date)
    series: list[tuple[date, float]] = []
    for row in historical_rows:
        close = row.get("close")
        dt = row.get("date")
        if close is None or dt is None:
            continue
        try:
            point_date = _to_date(dt)
            if point_date >= cutoff:
                continue
            series.append((point_date, float(close)))
        except (TypeError, ValueError):
            continue
    series.sort(key=lambda x: x[0])
    if len(series) < 60:
        return []

    candidates: list[AnalogResult] = []
    for idx in range(5, len(series) - 30):
        window_prev = series[idx - 5][1]
        current_px = series[idx][1]
        forward_px = series[idx + 30][1]
        if window_prev == 0 or current_px == 0:
            continue

        hist_trend_5d = ((current_px / window_prev) - 1.0) * 100.0
        trend_diff = abs(current_trend_5d - hist_trend_5d)
        trend_similarity = 1.0 / (1.0 + (trend_diff / 2.0))

        # Composite proxy from historical trend magnitude/sign.
        hist_composite_proxy = max(-2.0, min(2.0, hist_trend_5d / 2.0))
        composite_diff = abs(current_composite - hist_composite_proxy)
        composite_similarity = 1.0 / (1.0 + (composite_diff / 1.5))

        match_score = 100.0 * (0.75 * trend_similarity + 0.25 * composite_similarity)
        forward_return = ((forward_px / current_px) - 1.0) * 100.0

        aligned = 0
        total = 0
        for j in range(idx + 1, idx + 31):
            prev_px = series[j - 1][1]
            cur_px = series[j][1]
            if prev_px == 0:
                continue
            day_ret = (cur_px / prev_px) - 1.0
            total += 1
            if day_ret == 0:
                aligned += 1
            elif day_ret > 0 and target_sign > 0:
                aligned += 1
            elif day_ret < 0 and target_sign < 0:
                aligned += 1
        stability = (aligned / total * 100.0) if total else 0.0

        candidates.append(
            AnalogResult(
                rank=0,
                match_date=series[idx][0].isoformat(),
                match_score=match_score,
                forward_30d_return=forward_return,
                regime_stability=stability,
                context_label=_context_label(series[idx][0]),
                current_trend_5d=current_trend_5d,
                matched_trend_5d=hist_trend_5d,
                current_composite=current_composite,
            )
        )

    top = sorted(candidates, key=lambda c: c.match_score, reverse=True)[:3]
    ranked: list[AnalogResult] = []
    for i, row in enumerate(top, start=1):
        ranked.append(
            AnalogResult(
                rank=i,
                match_date=row.match_date,
                match_score=row.match_score,
                forward_30d_return=row.forward_30d_return,
                regime_stability=row.regime_stability,
                context_label=row.context_label,
                current_trend_5d=row.current_trend_5d,
                matched_trend_5d=row.matched_trend_5d,
                current_composite=row.current_composite,
            )
        )
    return ranked
