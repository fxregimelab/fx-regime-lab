"""FPI (Foreign Portfolio Investment) flow signal normalization for USDINR.

Converts daily FPI net flow (INR crores) into a [-1, +1] robust deviation
from its prior 20-observation median. Positive raw flow means net inflow;
a positive score means above-reference flow, not necessarily positive cash flow.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from numbers import Real

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW = 20
_MIN_WINDOW = 10
MAD_NORMAL_SCALE = 1.4826
MAD_NOISE_FLOOR = 0.0001
FPI_UNAVAILABLE_NOTES = ("fpi_source_unqualified", "fpi_history_unavailable")


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs)


def _mad_z(values: Sequence[float], value: float) -> float | None:
    """Robust Z-score using Median Absolute Deviation."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return None
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    scale = mad * MAD_NORMAL_SCALE
    if not all(math.isfinite(v) for v in (med, mad, scale)):
        return None
    if mad < MAD_NOISE_FLOOR:
        return None
    z = (value - med) / scale
    return float(z)


def normalize_fpi_signal(
    latest_flow: float | None,
    history: Sequence[float] | None = None,
    *,
    window: int = _DEFAULT_WINDOW,
) -> float | None:
    """Return a z-scored FPI signal clipped to [-1, 1].

    Parameters
    ----------
    latest_flow:
        Latest daily net FPI flow in INR crores (positive = inflow).
    history:
        Chronological series of prior daily flows (oldest first).
    window:
        Lookback window for z-score computation (default 20 days).

    Returns
    -------
    float | None
        Z-score clipped to [-1, 1], or None for missing, invalid or insufficient
        observations, degenerate dispersion, or non-finite arithmetic.
        Window must be a positive integer.
    """

    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("FPI window must be a positive integer")
    if latest_flow is None:
        return None

    hist = list(history) if history is not None else []
    # Missing/invalid observations are not zero flow and cannot be repaired by clipping.
    for value in [latest_flow, *hist]:
        if isinstance(value, bool) or not isinstance(value, Real):
            return None
        try:
            if not math.isfinite(float(value)):
                return None
        except (OverflowError, ValueError):
            return None
    if len(hist) < _MIN_WINDOW:
        logger.debug(
            "FPI normalization skipped: history too short (%s < %s)",
            len(hist),
            _MIN_WINDOW,
        )
        return None

    win = hist[-window:] if len(hist) >= window else hist
    if len(win) < _MIN_WINDOW:
        return None

    # Use MAD-based robust Z-score (causal: win already excludes latest_flow).
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        z = _mad_z(win, latest_flow)
    if z is None or not math.isfinite(z):
        return None
    # Clip to [-1, 1] — FPI flows can have extreme outliers on event days
    return float(max(-1.0, min(1.0, z)))
