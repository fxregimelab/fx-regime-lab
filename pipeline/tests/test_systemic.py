"""Systemic apex ranking (no Supabase)."""

from __future__ import annotations

from src.analysis.systemic import (
    assign_apex_ranking,
    build_yesterday_rank_maps,
    compute_apex_score,
    normalize_rank_velocity,
    resolve_idiosyncratic_outlier,
    top_three_clustered,
)


def test_compute_apex_score_pain_none_penalizes() -> None:
    with_pain = compute_apex_score(0.5, 50.0, 0.0)
    no_pain = compute_apex_score(0.5, None, 0.0)
    assert no_pain < with_pain


def test_normalize_rank_velocity_bounds() -> None:
    assert normalize_rank_velocity(0.0) == 0.5
    assert normalize_rank_velocity(-6.0) == 0.0
    assert normalize_rank_velocity(6.0) == 1.0


def test_build_yesterday_rank_maps_incumbent() -> None:
    rows = [
        {"pair": "EURUSD", "global_rank": 2, "apex_score": 0.4},
        {"pair": "USDJPY", "global_rank": 1, "apex_score": 0.9},
    ]
    ranks, apex, inc = build_yesterday_rank_maps(rows)
    assert inc == "USDJPY"
    assert ranks["USDJPY"] == 1
    assert apex["USDJPY"] == 0.9


def test_hysteresis_keeps_incumbent() -> None:
    pairs = ["EURUSD", "USDJPY"]
    conf = {"EURUSD": 0.9, "USDJPY": 0.5}
    pain = {"EURUSD": 50.0, "USDJPY": 50.0}
    y_rank = {"EURUSD": 2, "USDJPY": 1}
    out = assign_apex_ranking(
        pairs=pairs,
        confidences=conf,
        pain_indices=pain,
        yesterday_rank_by_pair=y_rank,
        yesterday_incumbent="USDJPY",
        yesterday_incumbent_apex=0.95,
    )
    top = out[0]
    assert top.pair == "USDJPY"
    assert top.global_rank == 1


def test_cluster_detection_mutual_high_corr() -> None:
    m = {
        "A": {"B": 0.95, "C": 0.92},
        "B": {"C": 0.91},
    }
    assert top_three_clustered(("A", "B", "C"), m) is True


def test_resolve_idiosyncratic_outlier_requires_both_horizons_low() -> None:
    pairs = ("EURUSD", "GBPUSD")
    c20 = {"EURUSD": 0.2, "GBPUSD": 0.5}
    c60 = {"EURUSD": 0.25, "GBPUSD": 0.2}
    assert resolve_idiosyncratic_outlier(pairs, c20, c60) == "EURUSD"


def test_resolve_idiosyncratic_outlier_none_when_aligned() -> None:
    pairs = ("EURUSD", "GBPUSD")
    c20 = {"EURUSD": 0.8, "GBPUSD": 0.7}
    c60 = {"EURUSD": 0.75, "GBPUSD": 0.72}
    assert resolve_idiosyncratic_outlier(pairs, c20, c60) is None


def test_cluster_detection_fails_on_low_corr() -> None:
    m = {
        "A": {"B": 0.95, "C": 0.5},
        "B": {"C": 0.91},
    }
    assert top_three_clustered(("A", "B", "C"), m) is False
