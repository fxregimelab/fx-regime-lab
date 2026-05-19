"""Intervention proximity heuristic for USDJPY."""

from __future__ import annotations


def compute_intervention_proximity(spot: float | None) -> float | None:
    """Return intervention proximity score for USDJPY.

    - spot >= 160 → returns 1.0 (intervention zone)
    - spot <= 150 → returns 0.0 (safe zone)
    - 150 < spot < 160 → linear interpolation
    - spot is None → returns None

    This is a heuristic, not a prediction. Documented in methodology.
    """
    if spot is None:
        return None
    if spot >= 160.0:
        return 1.0
    if spot <= 150.0:
        return 0.0
    return (spot - 150.0) / 10.0
