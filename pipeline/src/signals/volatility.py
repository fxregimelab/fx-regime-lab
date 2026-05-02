"""Realized volatility signal."""

from __future__ import annotations

import numpy as np


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
