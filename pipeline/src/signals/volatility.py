"""Realized volatility signal."""

from __future__ import annotations

import numpy as np


def compute_vol_signal(rv_5d: float, rv_20d: float, threshold_90: float) -> float:
    if rv_5d > threshold_90:
        return 1.0
    ratio = rv_5d / rv_20d if rv_20d > 0 else 1.0
    return float(np.clip((ratio - 1.0) * 2.0, -1.0, 1.0))


def is_vol_expanding(rv_5d: float, threshold_90: float) -> bool:
    return rv_5d > threshold_90
