"""Vectorized Z-score, momentum, and composite hysteresis helpers."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt


def _to_float64_array(values: npt.NDArray[np.float64] | Sequence[float]) -> npt.NDArray[np.float64]:
    arr = np.asarray(values, dtype=np.float64)
    return arr.reshape(-1)


def rolling_zscore_series(
    values: npt.NDArray[np.float64] | Sequence[float],
    window: int,
    *,
    min_periods: int | None = None,
) -> npt.NDArray[np.float64]:
    """Rolling (population) Z-score for each end-of-window point; NaN where undefined.

    For index ``i`` the statistic uses ``values[i - window + 1 : i + 1]`` when enough
    finite samples exist. Purely vectorized via cumulative sums on finite masks.
    """

    if window < 2:
        raise ValueError("window must be >= 2")
    mp = window if min_periods is None else max(2, min_periods)
    x = _to_float64_array(values)
    n = int(x.size)
    if n == 0:
        return np.array([], dtype=np.float64)

    finite = np.isfinite(x)
    xf = np.where(finite, x, 0.0)
    ones = finite.astype(np.float64)
    csum_x = np.cumsum(xf)
    csum_x2 = np.cumsum(xf * xf)
    csum_1 = np.cumsum(ones)

    def _window_sum(csum: npt.NDArray[np.float64], i1: int, i0: int) -> float:
        top = float(csum[i1])
        bot = float(csum[i0 - 1]) if i0 > 0 else 0.0
        return top - bot

    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        i0 = i - window + 1
        if i0 < 0:
            continue
        cnt = _window_sum(csum_1, i, i0)
        if cnt < float(mp):
            continue
        sum_x = _window_sum(csum_x, i, i0)
        sum_x2 = _window_sum(csum_x2, i, i0)
        mean = sum_x / cnt
        var = max(sum_x2 / cnt - mean * mean, 0.0)
        # Sample variance when window has >1 point; population uses /cnt
        std = math.sqrt(var) if cnt >= 2 else 0.0
        if std <= 1e-12 or not finite[i]:
            continue
        out[i] = (float(x[i]) - mean) / std
    return out


def rolling_zscore_last(
    values: npt.NDArray[np.float64] | Sequence[float],
    window: int,
    *,
    min_periods: int | None = None,
) -> float | None:
    """Z-score of the last observation; ``None`` if undefined."""

    series = rolling_zscore_series(values, window, min_periods=min_periods)
    if series.size == 0:
        return None
    last = float(series[-1])
    if math.isnan(last):
        return None
    return last


def momentum_last(
    values: npt.NDArray[np.float64] | Sequence[float],
    lag: int,
) -> float | None:
    """Level momentum ``x[-1] - x[-1-lag]`` using finite values only; ``None`` if gaps."""

    if lag < 1:
        raise ValueError("lag must be >= 1")
    x = _to_float64_array(values)
    if x.size <= lag:
        return None
    if not np.isfinite(x[-1]) or not np.isfinite(x[-1 - lag]):
        return None
    return float(x[-1] - x[-1 - lag])


def log_return_series(closes: npt.NDArray[np.float64] | Sequence[float]) -> npt.NDArray[np.float64]:
    """Log returns r_t = ln(S_t) - ln(S_{t-1}); NaN at first index or non-positive closes."""

    s = _to_float64_array(closes)
    if s.size < 2:
        return np.array([], dtype=np.float64)
    prev = s[:-1]
    nxt = s[1:]
    valid = (prev > 0.0) & (nxt > 0.0) & np.isfinite(prev) & np.isfinite(nxt)
    out = np.full(s.size - 1, np.nan, dtype=np.float64)
    out[valid] = np.log(nxt[valid]) - np.log(prev[valid])
    return out


def hysteresis_tier_composite(
    composite: float,
    prior_tier: int | None,
) -> int:
    """Five-tier Schmitt map on ``composite`` with memory of ``prior_tier``
    (0=strong bear … 4=strong bull).
    """

    def snap(c: float) -> int:
        if c > 1.0:
            return 4
        if c > 0.4:
            return 3
        if c >= -0.4:
            return 2
        if c >= -1.0:
            return 1
        return 0

    t_new = snap(composite)
    if prior_tier is None or not (0 <= prior_tier <= 4):
        return t_new

    pt = prior_tier
    if abs(t_new - pt) >= 2:
        return t_new

    if pt == 4 and composite >= 0.85:
        return 4
    if pt == 0 and composite <= -0.85:
        return 0

    if pt == 4 and composite < 0.85:
        return min(t_new, 3)
    if pt == 0 and composite > -0.85:
        return max(t_new, 1)

    if pt == 3 and composite > 1.0:
        return 4
    if pt == 3 and composite < 0.28:
        return t_new

    if pt == 1 and composite < -1.0:
        return 0
    if pt == 1 and composite > -0.28:
        return t_new

    if pt == 2 and abs(composite) < 0.15:
        return 2

    return t_new
