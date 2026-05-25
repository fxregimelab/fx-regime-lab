"""
@agent_context: Computes realized volatility signals and expansion status
based on short-term vs long-term RV ratios.
@allowed_imports: [numpy]
@forbidden_imports: [src.db, src.ai]
@obsidian_link: [[Signal Generation#Volatility]]
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

# 3-year trading calendar (Layer 3 vol rank); matches ``TRADING_DAYS_3Y`` in composite regime math.
TRADING_DAYS_3Y_VOL_RANK = 756
# Minimum 21 daily log returns need 22 closes; require a floor of points for a stable empirical CDF.
_MIN_RANK_SAMPLE = 30


def compute_vol_signal(
    rv_5d: float | None, rv_20d: float | None, threshold_90: float | None
) -> float | None:
    if rv_5d is None or rv_20d is None:
        return None
    if rv_20d <= 0.0:
        return None
    if threshold_90 is not None and rv_5d > threshold_90:
        return 1.0
    ratio = rv_5d / rv_20d
    return float(np.clip((ratio - 1.0) * 2.0, -1.0, 1.0))


def is_vol_expanding(rv_5d: float, threshold_90: float) -> bool:
    return rv_5d > threshold_90


def compute_rvol(volumes: list[float], window: int = 20) -> float | None:
    """Relative Volume (RVOL): Current volume vs N-day Average Daily Volume (ADV)."""
    if len(volumes) < window:
        return None
    # Filter out zero volume days if any (managed currencies)
    clean_v = [v for v in volumes if v > 0]
    if len(clean_v) < window:
        return None
    current = clean_v[-1]
    adv = float(np.mean(clean_v[-window:]))
    if adv <= 0.0:
        return None
    return float(current / adv)


def realized_vol21_series_annualized_pct(closes: np.ndarray) -> np.ndarray:
    """Rolling 21-return annualized realized vol (%), aligned to each close index.

    For close index ``j >= 21``, uses log returns ``lr[j-21:j]`` (21 points). Earlier
    indices are ``nan``. No look-ahead: each ``out[j]`` uses only prices on or before ``j``.
    """

    n = int(closes.size)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < 22 or np.any(closes <= 0):
        return out
    lr = np.diff(np.log(closes.astype(np.float64)))
    for j in range(21, n):
        seg = lr[j - 21 : j]
        if seg.size != 21:
            continue
        # v2.1: Use sample standard deviation (Bessel's correction)
        out[j] = float(np.std(seg, ddof=1) * np.sqrt(252.0) * 100.0)
    return out


def empirical_cdf_rank(x: float, sample: np.ndarray) -> float:
    """Empirical CDF ÔF(x) = (1/n) Σ 1[X_i ≤ x] on a strictly causal sample (double precision)."""

    s = sample.astype(np.float64)
    s = s[np.isfinite(s)]
    if s.size == 0:
        return 0.0
    return float(np.mean(s <= float(x)))


def compute_realized_vol_rank_from_closes(
    closes: Sequence[float],
    *,
    window: int = TRADING_DAYS_3Y_VOL_RANK,
) -> float | None:
    """``q^σ_t``: empirical CDF rank of today's 21d annualized RV vs **prior** trailing RVs.

    The benchmark sample is the last ``window`` realized-vol points **excluding** today's
    value (strictly causal / no self-comparison in the ECDF denominator). Returns ``None``
    if history is too short or closes are invalid.
    """

    arr = np.asarray(list(closes), dtype=np.float64)
    if arr.size < 22 or np.any(arr <= 0):
        return None
    series = realized_vol21_series_annualized_pct(arr)
    # RV21 values for end indices 21 .. n-1
    tail = series[21:]
    if tail.size < _MIN_RANK_SAMPLE:
        return None
    win = tail[-int(window) :] if tail.size > int(window) else tail
    if win.size < 2:
        return None
    current = float(win[-1])
    hist = win[:-1]
    return empirical_cdf_rank(current, hist)
