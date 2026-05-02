"""Cross-sectional G10 apex ranking, hysteresis, and systemic cluster detection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

import numpy as np

# Hysteresis threshold on a 0–100 apex scale (stored apex remains 0–1 float).
HYSTERESIS_MARGIN_POINTS: Final[float] = 10.0
CLUSTER_CORR_THRESHOLD: Final[float] = 0.90
OUTLIER_CORR_THRESHOLD: Final[float] = 0.3
DEFAULT_RANK_FALLBACK: Final[int] = 7
RANK_VELOCITY_CLIP: Final[float] = 6.0

WEIGHT_CONFIDENCE: Final[float] = 0.4
WEIGHT_PAIN: Final[float] = 0.4
WEIGHT_RANK_VELOCITY: Final[float] = 0.2


def normalize_rank_velocity(velocity: float) -> float:
    """Map rank improvement (yesterday_rank - raw_rank) to [0, 1]."""

    return float(
        np.clip((float(velocity) + RANK_VELOCITY_CLIP) / (2.0 * RANK_VELOCITY_CLIP), 0.0, 1.0)
    )


def compute_apex_score(
    confidence: float,
    pain_index: float | None,
    rank_velocity: float,
) -> float:
    """Apex score from confidence, pain (None → 0), and rank velocity."""

    pain_term = 0.0 if pain_index is None else float(pain_index) / 100.0
    vel_term = normalize_rank_velocity(rank_velocity)
    return (
        float(confidence) * WEIGHT_CONFIDENCE
        + pain_term * WEIGHT_PAIN
        + vel_term * WEIGHT_RANK_VELOCITY
    )


def _corr_lookup(matrix: dict[str, Any], a: str, b: str) -> float | None:
    if a == b:
        return 1.0
    inner_a = matrix.get(a)
    if isinstance(inner_a, dict) and b in inner_a:
        v = inner_a.get(b)
        return float(v) if v is not None else None
    inner_b = matrix.get(b)
    if isinstance(inner_b, dict) and a in inner_b:
        v = inner_b.get(a)
        return float(v) if v is not None else None
    return None


def top_three_clustered(
    top_pairs: tuple[str, str, str],
    matrix: dict[str, Any],
) -> bool:
    """True if mutual correlations among the top 3 pairs all exceed the threshold."""

    p0, p1, p2 = top_pairs
    c01 = _corr_lookup(matrix, p0, p1)
    c02 = _corr_lookup(matrix, p0, p2)
    c12 = _corr_lookup(matrix, p1, p2)
    for c in (c01, c02, c12):
        if c is None or c <= CLUSTER_CORR_THRESHOLD:
            return False
    return True


@dataclass(frozen=True)
class ApexRankingResult:
    """Per-pair outputs after hysteresis and global ordering."""

    pair: str
    global_rank: int
    apex_score: float
    raw_rank: int


def build_yesterday_rank_maps(
    yesterday_rows: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, float], str | None]:
    """Maps pair → rank / apex; incumbent is the pair with global_rank == 1."""

    rank_by_pair: dict[str, int] = {}
    apex_by_pair: dict[str, float] = {}
    incumbent: str | None = None
    for row in yesterday_rows:
        p = str(row.get("pair") or "")
        if not p:
            continue
        gr = row.get("global_rank")
        if gr is not None:
            rank_by_pair[p] = int(gr)
            if int(gr) == 1:
                incumbent = p
        ax = row.get("apex_score")
        if ax is not None:
            apex_by_pair[p] = float(ax)
    return rank_by_pair, apex_by_pair, incumbent


def assign_apex_ranking(
    *,
    pairs: list[str],
    confidences: dict[str, float],
    pain_indices: dict[str, float | None],
    yesterday_rank_by_pair: dict[str, int],
    yesterday_incumbent: str | None,
    yesterday_incumbent_apex: float | None,
) -> list[ApexRankingResult]:
    """Compute apex scores, apply rank hysteresis for #1, return globally ordered results."""

    if not pairs:
        return []

    # Raw score ordering (before velocity — velocity needs raw rank)
    # First pass: velocity uses yesterday vs provisional raw rank from score-only
    score_only: dict[str, float] = {}
    for p in pairs:
        pain = pain_indices.get(p)
        pain_c = 0.0 if pain is None else float(pain) / 100.0
        score_only[p] = confidences[p] * WEIGHT_CONFIDENCE + pain_c * WEIGHT_PAIN

    raw_by_score = sorted(pairs, key=lambda x: score_only[x], reverse=True)
    raw_rank_map: dict[str, int] = {p: i + 1 for i, p in enumerate(raw_by_score)}

    apex_by_pair: dict[str, float] = {}
    for p in pairs:
        vel = float(yesterday_rank_by_pair.get(p, DEFAULT_RANK_FALLBACK) - raw_rank_map[p])
        apex_by_pair[p] = compute_apex_score(confidences[p], pain_indices.get(p), vel)

    # Re-rank by full apex score
    order_by_apex = sorted(pairs, key=lambda x: apex_by_pair[x], reverse=True)
    apex_rank_map: dict[str, int] = {p: i + 1 for i, p in enumerate(order_by_apex)}
    challenger = order_by_apex[0]

    leader: str
    if yesterday_incumbent is None or yesterday_incumbent not in pairs:
        leader = challenger
    elif challenger == yesterday_incumbent:
        leader = challenger
    elif yesterday_incumbent_apex is None:
        leader = challenger
    elif (apex_by_pair[challenger] * 100.0) > (
        float(yesterday_incumbent_apex) * 100.0 + HYSTERESIS_MARGIN_POINTS
    ):
        leader = challenger
    else:
        leader = yesterday_incumbent

    rest = sorted(
        (p for p in order_by_apex if p != leader),
        key=lambda x: apex_by_pair[x],
        reverse=True,
    )
    final_order = [leader, *rest]

    results: list[ApexRankingResult] = []
    for i, p in enumerate(final_order):
        results.append(
            ApexRankingResult(
                pair=p,
                global_rank=i + 1,
                apex_score=apex_by_pair[p],
                raw_rank=apex_rank_map[p],
            )
        )

    return results


def apply_cluster_to_telemetry(
    telemetry: dict[str, Any],
    systemic_cluster: bool,
) -> dict[str, Any]:
    out = {**telemetry, "Systemic_Cluster": systemic_cluster}
    return out


def resolve_idiosyncratic_outlier(
    pairs: Sequence[str],
    corr_20: Mapping[str, float | None],
    corr_60: Mapping[str, float | None],
) -> str | None:
    """Pair most detached from the G10 basket on both 20d and 60d horizons."""

    candidates: list[tuple[str, float]] = []
    for p in pairs:
        a = corr_20.get(p)
        b = corr_60.get(p)
        if a is None or b is None:
            continue
        if a < OUTLIER_CORR_THRESHOLD and b < OUTLIER_CORR_THRESHOLD:
            candidates.append((p, (float(a) + float(b)) / 2.0))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1], x[0]))
    return candidates[0][0]


def compute_dollar_dominance_score(
    pair_regimes: Mapping[str, str],
) -> tuple[float, str | None]:
    """Book-wide USD thematic alignment (0–1) and brief bias for systemic AI context.

    Uses ``get_regime_metadata`` base_regime so INR crosses count toward USD strength/weakness.
    Returns ``(score, bias)`` where ``bias`` is ``Strength`` or ``Weakness`` only if
    ``score > 0.7`` (else ``None``).
    """

    from src.regime.classifier import get_regime_metadata

    n = len(pair_regimes)
    if n == 0:
        return 0.0, None
    strength_ct = 0
    weakness_ct = 0
    for regime in pair_regimes.values():
        base = get_regime_metadata(regime).base_regime
        if base == "USD_STRENGTH":
            strength_ct += 1
        elif base == "USD_WEAKNESS":
            weakness_ct += 1
    score = max(strength_ct, weakness_ct) / float(n)
    if score <= 0.7:
        return score, None
    bias = "Strength" if strength_ct >= weakness_ct else "Weakness"
    return score, bias
