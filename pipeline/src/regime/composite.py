"""Weighted composite score and dynamic Spearman betas (signal return vs spot return)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
import numpy.typing as npt

WEIGHTS = {"rate": 0.40, "cot": 0.30, "vol": 0.20, "oi": 0.10}
logger = logging.getLogger(__name__)

# `get_historical_signals` returns newest-first; slice [:N] for the latest N sessions.
TRADING_DAYS_3Y = 756
TRADING_DAYS_5Y = 1260

_DRIVER_LABELS: dict[str, str] = {
    "rate": "Rate differential is the primary driver",
    "cot": "COT positioning is the primary driver",
    "vol": "Volatility dynamics dominate",
    "oi": "Open interest flow is the primary driver",
}


@dataclass(frozen=True)
class DominanceScore:
    rank: int
    signal_family: str
    signal_strength: float
    beta: float
    dominance_score: float


def _to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _average_ranks_np(a: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """1-based average ranks with tie handling (numpy vectorized sort)."""

    n = int(a.size)
    if n == 0:
        return np.array([], dtype=float)
    sorter = np.argsort(a, kind="mergesort")
    sorted_a = a[sorter]
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_a[j] == sorted_a[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        ranks[sorter[i:j]] = avg_rank
        i = j
    return ranks


def _spearman_corr_np(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> float:
    if x.size < 2 or y.size < 2 or x.size != y.size:
        return 0.0
    if np.all(x == x[0]) or np.all(y == y[0]):
        return 0.0
    rx = _average_ranks_np(x)
    ry = _average_ranks_np(y)
    rx = rx - float(np.mean(rx))
    ry = ry - float(np.mean(ry))
    denom = float(np.sqrt(np.sum(rx * rx) * np.sum(ry * ry)))
    if denom <= 0.0:
        return 0.0
    corr = float(np.sum(rx * ry) / denom)
    if math.isnan(corr):
        return 0.0
    return float(np.clip(corr, -1.0, 1.0))


def _ema(values: list[float], span: int = 5) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (float(span) + 1.0)
    ema = values[0]
    for value in values[1:]:
        ema = alpha * value + (1.0 - alpha) * ema
    return ema


def compute_dynamic_betas(
    historical_rows: list[dict[str, Any]],
    corr_window: int = 30,
    ema_span: int = 5,
) -> dict[str, float]:
    """Rolling Spearman (30D) between signal return and spot return; 5D EMA of correlations."""

    series_by_date: dict[date, dict[str, float]] = {}
    for row in historical_rows:
        dt = _to_date(row.get("date"))
        if dt is None:
            continue
        spot_value = _to_float(row.get("spot"))
        if spot_value is None:
            continue
        point: dict[str, float] = {"spot": spot_value}

        rate_2y = _to_float(row.get("rate_diff_2y"))
        rv20f = _to_float(row.get("realized_vol_20d"))
        if rate_2y is not None and rv20f is not None:
            if rv20f > 0.0:
                point["rate"] = rate_2y / rv20f

        cot_pct = _to_float(row.get("cot_percentile"))
        if cot_pct is not None:
            point["cot"] = (cot_pct - 50.0) / 50.0

        rv5 = _to_float(row.get("realized_vol_5d"))
        if rv5 is not None and rv20f is not None:
            if rv20f > 0.0:
                point["vol"] = ((rv5 / rv20f) - 1.0) * 2.0

        oi_delta = _to_float(row.get("oi_delta"))
        if oi_delta is not None:
            point["oi"] = oi_delta

        series_by_date[dt] = point

    ordered_dates = sorted(series_by_date)
    if len(ordered_dates) < corr_window + 1:
        logger.info("Dynamic beta fallback: insufficient rows (%s)", len(ordered_dates))
        return {"rate": 0.0, "cot": 0.0, "vol": 0.0, "oi": 0.0}

    spot_returns: dict[date, float] = {}
    for prev_dt, curr_dt in zip(ordered_dates[:-1], ordered_dates[1:], strict=True):
        prev_spot = series_by_date[prev_dt]["spot"]
        curr_spot = series_by_date[curr_dt]["spot"]
        if prev_spot == 0.0:
            continue
        spot_returns[curr_dt] = (curr_spot / prev_spot) - 1.0

    betas: dict[str, float] = {}
    for family in ("rate", "cot", "vol", "oi"):
        aligned: list[tuple[date, float, float]] = []
        for idx in range(1, len(ordered_dates)):
            curr_dt = ordered_dates[idx]
            prev_dt = ordered_dates[idx - 1]
            sig_curr = series_by_date[curr_dt].get(family)
            sig_prev = series_by_date[prev_dt].get(family)
            ret = spot_returns.get(curr_dt)
            if sig_curr is None or sig_prev is None or ret is None:
                continue
            sig_ret = float(sig_curr) - float(sig_prev)
            aligned.append((curr_dt, sig_ret, ret))

        if len(aligned) < corr_window:
            betas[family] = 0.0
            continue

        rolling_corrs: list[float] = []
        for idx in range(corr_window - 1, len(aligned)):
            window = aligned[idx - corr_window + 1 : idx + 1]
            x_vals = np.array([item[1] for item in window], dtype=np.float64)
            y_vals = np.array([item[2] for item in window], dtype=np.float64)
            corr = _spearman_corr_np(x_vals, y_vals)
            rolling_corrs.append(0.0 if math.isnan(corr) else corr)

        betas[family] = _ema(rolling_corrs, span=ema_span) if rolling_corrs else 0.0

    logger.info("Dynamic Spearman betas (EMA): %s", betas)
    return betas


def compute_dominance_scores(
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
    oi_norm: float | None,
    betas: dict[str, float],
) -> list[DominanceScore]:
    strengths = {
        "rate": 0.0 if rate_norm is None else rate_norm,
        "cot": 0.0 if cot_norm is None else cot_norm,
        "vol": 0.0 if vol_norm is None else vol_norm,
        "oi": 0.0 if oi_norm is None else oi_norm,
    }
    rows: list[DominanceScore] = []
    for family in ("rate", "cot", "vol", "oi"):
        strength = strengths[family]
        beta = float(betas.get(family, 0.0))
        rows.append(
            DominanceScore(
                rank=0,
                signal_family=family,
                signal_strength=float(strength),
                beta=beta,
                dominance_score=float(strength * beta),
            )
        )
    ranked = sorted(rows, key=lambda row: abs(row.dominance_score), reverse=True)
    return [
        DominanceScore(
            rank=index,
            signal_family=row.signal_family,
            signal_strength=row.signal_strength,
            beta=row.beta,
            dominance_score=row.dominance_score,
        )
        for index, row in enumerate(ranked, start=1)
    ]


def dominance_top_family(
    betas: dict[str, float],
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
    oi_norm: float | None,
) -> str | None:
    """Family with largest |strength * beta| (same strength map as dominance scores)."""

    strengths = {
        "rate": 0.0 if rate_norm is None else rate_norm,
        "cot": 0.0 if cot_norm is None else cot_norm,
        "vol": 0.0 if vol_norm is None else vol_norm,
        "oi": 0.0 if oi_norm is None else oi_norm,
    }
    best: str | None = None
    best_abs = 0.0
    for family in ("rate", "cot", "vol", "oi"):
        strength = strengths[family]
        beta = float(betas.get(family, 0.0))
        score_abs = abs(strength * beta)
        if score_abs > best_abs:
            best_abs = score_abs
            best = family
    return best if best_abs > 0.0 else None


def compute_composite(
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
    oi_norm: float | None,
) -> float | None:
    """Weighted composite; missing legs drop out and remaining weights renormalize."""

    values: dict[str, float | None] = {
        "rate": rate_norm,
        "cot": cot_norm,
        "vol": vol_norm,
        "oi": oi_norm,
    }
    active = [k for k, v in values.items() if v is not None]
    if not active:
        return None
    wsum = sum(WEIGHTS[k] for k in active)
    if wsum <= 0.0:
        return None
    acc = 0.0
    for k in active:
        v = values[k]
        if v is None:
            continue
        acc += float(v) * (WEIGHTS[k] / wsum)
    composite = acc
    return float(np.clip(composite, -2.0, 2.0))


def get_primary_driver(betas: dict[str, float]) -> str:
    """Driver = signal family with largest magnitude of smoothed Spearman beta."""

    best = max(("rate", "cot", "vol", "oi"), key=lambda f: abs(float(betas.get(f, 0.0))))
    mag = abs(float(betas.get(best, 0.0)))
    if mag < 1e-9:
        return "Mixed signals — no single dominant factor"
    return _DRIVER_LABELS.get(best, "Mixed signals — no single dominant factor")
