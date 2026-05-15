"""Stress mode detection and circuit breakers."""

from __future__ import annotations

from typing import Any

STRESS_RULES = {
    "VIX_GT_30": {
        "max_position_size": 0.005,
        "conviction_cap": 3,
        "skip_ai_briefs": True,
        "reduce_existing": 0.0,
        "description": "High volatility regime — reduce risk",
    },
    "VIX_GT_25": {
        "max_position_size": 0.0075,
        "conviction_cap": 4,
        "skip_ai_briefs": False,
        "reduce_existing": 0.0,
        "description": "Elevated volatility — moderate caution",
    },
    "DXY_MOVE_GT_1PCT": {
        "max_position_size": 0.005,
        "conviction_cap": 3,
        "skip_ai_briefs": False,
        "reduce_existing": 0.0,
        "description": "Dollar gap — reduce directional risk",
    },
    "PAIR_GAP_GT_2PCT": {
        "max_position_size": 0.0,
        "conviction_cap": 1,
        "skip_ai_briefs": True,
        "reduce_existing": 0.5,
        "description": "Pair gap — no new entries, reduce existing",
    },
    "CORRELATION_CLUSTER": {
        "max_position_size": 0.005,
        "conviction_cap": 3,
        "skip_ai_briefs": False,
        "reduce_existing": 0.25,
        "description": "High correlation cluster — diversify",
    },
}


def _is_correlation_cluster(
    correlation_matrix: dict[str, dict[str, float]],
) -> bool:
    """Check if top 3 pairs are all correlated > 0.90."""
    if not correlation_matrix:
        return False

    # Extract all unique pairs in the matrix
    all_pairs = sorted(
        {p for row in correlation_matrix.values() for p in row.keys()}
        | set(correlation_matrix.keys())
    )
    if len(all_pairs) < 3:
        return False

    # Check the first 3 pairs for high mutual correlation
    top3 = all_pairs[:3]
    for i in range(len(top3)):
        for j in range(i + 1, len(top3)):
            p1, p2 = top3[i], top3[j]
            corr = correlation_matrix.get(p1, {}).get(p2)
            if corr is None:
                corr = correlation_matrix.get(p2, {}).get(p1)
            if corr is None or abs(corr) < 0.90:
                return False
    return True


def assess_stress_mode(
    vix: float | None,
    dxy_overnight_pct: float | None,
    max_pair_overnight_pct: float | None,
    correlation_matrix: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Determine active stress modes and most restrictive settings."""
    active_modes: list[str] = []

    if vix is not None and vix > 30:
        active_modes.append("VIX_GT_30")
    elif vix is not None and vix > 25:
        active_modes.append("VIX_GT_25")

    if dxy_overnight_pct is not None and abs(dxy_overnight_pct) > 1.0:
        active_modes.append("DXY_MOVE_GT_1PCT")

    if max_pair_overnight_pct is not None and max_pair_overnight_pct > 2.0:
        active_modes.append("PAIR_GAP_GT_2PCT")

    if correlation_matrix is not None:
        # Check if top 3 pairs are all correlated > 0.90
        if _is_correlation_cluster(correlation_matrix):
            active_modes.append("CORRELATION_CLUSTER")

    # Apply most restrictive settings
    max_position = 0.01  # Default 1%
    conviction_cap = 5
    skip_ai = False
    reduce_existing = 0.0

    for mode in active_modes:
        rule = STRESS_RULES[mode]
        max_position = min(max_position, rule["max_position_size"])
        conviction_cap = min(conviction_cap, rule["conviction_cap"])
        skip_ai = skip_ai or rule["skip_ai_briefs"]
        reduce_existing = max(reduce_existing, rule["reduce_existing"])

    return {
        "active_modes": active_modes,
        "max_position_size": max_position,
        "conviction_cap": conviction_cap,
        "skip_ai_briefs": skip_ai,
        "reduce_existing": reduce_existing,
        "is_stress": len(active_modes) > 0,
    }
