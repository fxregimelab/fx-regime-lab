"""Tests for src/signals/intervention.py USDJPY intervention heuristic."""

from __future__ import annotations

import pytest

from src.signals.intervention import compute_intervention_proximity


class TestComputeInterventionProximity:
    def test_none_returns_none(self) -> None:
        assert compute_intervention_proximity(None) is None

    def test_at_or_above_160_returns_one(self) -> None:
        assert compute_intervention_proximity(160.0) == pytest.approx(1.0)
        assert compute_intervention_proximity(165.0) == pytest.approx(1.0)

    def test_at_or_below_150_returns_zero(self) -> None:
        assert compute_intervention_proximity(150.0) == pytest.approx(0.0)
        assert compute_intervention_proximity(140.0) == pytest.approx(0.0)

    def test_midpoint_returns_half(self) -> None:
        assert compute_intervention_proximity(155.0) == pytest.approx(0.5)

    def test_linear_interpolation(self) -> None:
        assert compute_intervention_proximity(152.0) == pytest.approx(0.2)
        assert compute_intervention_proximity(158.0) == pytest.approx(0.8)
