"""Confidence score from composite magnitude and signal agreement."""

from __future__ import annotations

import numpy as np


def compute_confidence(
    composite: float,
    rate_norm: float | None,
    cot_norm: float | None,
) -> float:
    thresholds = (-1.0, -0.4, 0.4, 1.0)
    distance = min(abs(composite - t) for t in thresholds)
    base_conf = float(np.clip(distance / 0.6, 0.10, 0.90))
    bonus = 0.0
    if rate_norm is not None and cot_norm is not None:
        if (rate_norm > 0 and cot_norm > 0) or (rate_norm < 0 and cot_norm < 0):
            bonus += 0.05
        if abs(rate_norm) > 0.3 and abs(cot_norm) > 0.3:
            bonus += 0.05
    raw = float(np.clip(base_conf + bonus, 0.40, 0.95))
    # Institutional −5pp haircut (under-promise / over-deliver).
    return float(np.clip(raw - 0.05, 0.40, 0.90))
