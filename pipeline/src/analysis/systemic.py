"""Retired Apex entry points and retained systemic correlation descriptions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

CLUSTER_CORR_THRESHOLD: Final[float] = 0.90
OUTLIER_CORR_THRESHOLD: Final[float] = 0.3


def compute_apex_score(
    confidence: float,
    pain_index: float | None,
    rank_velocity: float,
) -> float | None:
    """Retired because the inputs do not support an Apex investment ranking."""

    return None


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
    """Legacy compatibility shape; new ranking calls return no rows."""

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
    """Retired because no validated cross-pair ranking model is available."""

    return []


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
    """Pair most detached from the FX basket on both 20d and 60d horizons."""

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
