"""Tests for auto/plan.py — spec generation engine."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.auto.plan import _find_relevant_files, create_plan


def _make_codemap() -> dict:
    return {
        "web": {
            "pages": [
                "web/src/app/page.tsx",
                "web/src/app/layout.tsx",
                "web/src/app/about/page.tsx",
                "web/src/app/chart/page.tsx",
            ],
            "components": [
                "web/src/components/Button.tsx",
                "web/src/components/Chart.tsx",
                "web/src/components/Table.tsx",
            ],
        },
        "pipeline": {
            "signals": [
                "pipeline/src/signals/volatility.py",
                "pipeline/src/signals/cot.py",
                "pipeline/src/signals/carry.py",
            ],
            "logic": [
                "pipeline/src/logic/layer1_gate.py",
                "pipeline/src/logic/layer2_directional.py",
                "pipeline/src/logic/layer3_execution.py",
            ],
        },
    }


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        # Create CODEMAP
        maps_dir = repo / ".agent" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "CODEMAP.json").write_text(json.dumps(_make_codemap()))
        yield repo


class TestFindRelevantFiles:
    def test_tier_1_ui_keywords(self, temp_repo):
        files = _find_relevant_files(_make_codemap(), "Add a new chart page", 1)
        assert any("chart" in f for f in files)

    def test_tier_2_signal_keywords(self, temp_repo):
        files = _find_relevant_files(_make_codemap(), "Add a new volatility signal", 2)
        assert any("volatility" in f for f in files)
        # logic files are added separately in create_plan based on layer mentions

    def test_empty_directive_returns_empty(self):
        files = _find_relevant_files(_make_codemap(), "", 1)
        assert files == []


class TestCreatePlan:
    def test_tier_1_generates_spec(self, temp_repo):
        result = create_plan("Add a new dashboard page", 1, temp_repo)
        assert result.tier == 1
        assert result.directive == "Add a new dashboard page"
        assert result.spec_path != ""
        assert Path(temp_repo / result.spec_path).exists()

    def test_tier_2_generates_spec(self, temp_repo):
        result = create_plan("Add a new carry signal for Layer 2", 2, temp_repo)
        assert result.tier == 2
        assert result.directive == "Add a new carry signal for Layer 2"
        assert result.spec_path != ""
        assert Path(temp_repo / result.spec_path).exists()
        # Should identify Layer 2 logic file
        assert any("layer2" in f for f in result.files_to_modify)

    def test_tier_3_raises(self, temp_repo):
        with pytest.raises(ValueError, match="Tier 3 not supported"):
            create_plan("Add a new migration", 3, temp_repo)

    def test_spec_content_includes_directive(self, temp_repo):
        result = create_plan("Build a correlation chart", 1, temp_repo)
        spec_path = temp_repo / result.spec_path
        content = spec_path.read_text()
        assert "Build a correlation chart" in content
        assert "Acceptance Criteria" in content

    def test_spec_content_has_files_to_read(self, temp_repo):
        result = create_plan("Add a volatility signal", 2, temp_repo)
        assert len(result.files_to_read) > 0

    def test_plan_result_is_frozen(self, temp_repo):
        result = create_plan("Test", 1, temp_repo)
        with pytest.raises(AttributeError):
            result.tier = 99  # type: ignore[misc]
