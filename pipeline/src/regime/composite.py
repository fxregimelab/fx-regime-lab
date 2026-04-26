"""Weighted composite score."""

from __future__ import annotations

import numpy as np

WEIGHTS = {"rate": 0.40, "cot": 0.30, "vol": 0.20, "oi": 0.10}


def compute_composite(
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
    oi_norm: float,
) -> float | None:
    if rate_norm is None and cot_norm is None:
        return None
    r = 0.0 if rate_norm is None else rate_norm
    c = 0.0 if cot_norm is None else cot_norm
    v = 0.0 if vol_norm is None else vol_norm
    composite = (
        r * WEIGHTS["rate"]
        + c * WEIGHTS["cot"]
        + v * WEIGHTS["vol"]
        + oi_norm * WEIGHTS["oi"]
    )
    return float(np.clip(composite, -2.0, 2.0))


def get_primary_driver(
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
) -> str:
    abs_rate = abs(rate_norm or 0.0)
    abs_cot = abs(cot_norm or 0.0)
    abs_vol = abs(vol_norm or 0.0)
    if abs_rate >= abs_cot and abs_rate >= abs_vol:
        return "Rate differential is the primary driver"
    if abs_cot >= abs_rate and abs_cot >= abs_vol:
        return "COT positioning is the primary driver"
    if abs_vol > 0.5:
        return "Volatility dynamics dominate"
    return "Mixed signals — no single dominant factor"
