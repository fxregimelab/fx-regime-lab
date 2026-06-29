"""FPI (Foreign Portfolio Investment) flow signal normalization for USDINR.

Converts SEBI daily FPI net flow (INR crores) into a [-1, +1] z-score signal
using a 20-day rolling window. Positive flow = INR inflow = INR strength bias.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW = 20
_MIN_WINDOW = 10
MAD_NORMAL_SCALE = 1.4826
MAD_NOISE_FLOOR = 0.0001


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs)


def _mad_z(values: Sequence[float], value: float) -> float | None:
    """Robust Z-score using Median Absolute Deviation."""
    arr: npt.NDArray[np.float64] = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return None
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    if mad < MAD_NOISE_FLOOR:
        return 0.0
    z = (value - med) / (mad * MAD_NORMAL_SCALE)
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
        Z-score clipped to [-1, 1], or None if insufficient data.
    """

    if latest_flow is None:
        return None

    hist = list(history or [])
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
    z = _mad_z(win, latest_flow)
    if z is None:
        return 0.0
    # Clip to [-1, 1] — FPI flows can have extreme outliers on event days
    return float(max(-1.0, min(1.0, z)))
