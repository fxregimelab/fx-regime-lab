"""Systemic apex ranking (no Supabase)."""

from __future__ import annotations

from src.analysis.systemic import (
    assign_apex_ranking,
    build_yesterday_rank_maps,
    compute_apex_score,
    resolve_idiosyncratic_outlier,
    top_three_clustered,
)


def test_compute_apex_score_is_retired_and_input_invariant() -> None:
    assert compute_apex_score(0.5, None, 0.0) is None
    assert compute_apex_score(0.99, 100.0, 6.0) is None
    assert compute_apex_score(0.01, 0.0, -6.0) is None


def test_build_yesterday_rank_maps_incumbent() -> None:
    rows = [
        {"pair": "EURUSD", "global_rank": 2, "apex_score": 0.4},
        {"pair": "USDJPY", "global_rank": 1, "apex_score": 0.9},
    ]
    ranks, apex, inc = build_yesterday_rank_maps(rows)
    assert inc == "USDJPY"
    assert ranks["USDJPY"] == 1
    assert apex["USDJPY"] == 0.9


def test_assign_apex_ranking_is_retired_and_input_invariant() -> None:
    assert assign_apex_ranking(
        pairs=["EURUSD", "USDJPY"],
        confidences={"EURUSD": 0.9, "USDJPY": 0.5},
        pain_indices={"EURUSD": 0.0, "USDJPY": None},
        yesterday_rank_by_pair={"EURUSD": 2, "USDJPY": 1},
        yesterday_incumbent="USDJPY",
        yesterday_incumbent_apex=0.95,
    ) == []
    assert assign_apex_ranking(
        pairs=["EURUSD", "USDJPY"],
        confidences={"EURUSD": 0.01, "USDJPY": 0.99},
        pain_indices={"EURUSD": 100.0, "USDJPY": 100.0},
        yesterday_rank_by_pair={"EURUSD": 1, "USDJPY": 2},
        yesterday_incumbent="EURUSD",
        yesterday_incumbent_apex=0.01,
    ) == []


def test_cluster_detection_mutual_high_corr() -> None:
    m = {
        "A": {"B": 0.95, "C": 0.92},
        "B": {"C": 0.91},
    }
    assert top_three_clustered(("A", "B", "C"), m) is True


def test_resolve_idiosyncratic_outlier_requires_both_horizons_low() -> None:
    pairs = ("EURUSD", "USDJPY")
    c20 = {"EURUSD": 0.2, "USDJPY": 0.5}
    c60 = {"EURUSD": 0.25, "USDJPY": 0.2}
    assert resolve_idiosyncratic_outlier(pairs, c20, c60) == "EURUSD"


def test_resolve_idiosyncratic_outlier_none_when_aligned() -> None:
    pairs = ("EURUSD", "USDJPY")
    c20 = {"EURUSD": 0.8, "USDJPY": 0.7}
    c60 = {"EURUSD": 0.75, "USDJPY": 0.72}
    assert resolve_idiosyncratic_outlier(pairs, c20, c60) is None


def test_cluster_detection_fails_on_low_corr() -> None:
    m = {
        "A": {"B": 0.95, "C": 0.5},
        "B": {"C": 0.91},
    }
    assert top_three_clustered(("A", "B", "C"), m) is False
