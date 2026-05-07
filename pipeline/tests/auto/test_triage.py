"""Tests for auto/triage.py task classification engine."""

from __future__ import annotations

from src.auto.triage import classify


class TestTriageClassification:
    """Test task classification into tiers."""

    def test_tier_1_ui_request(self) -> None:
        result = classify("Add a mobile responsive layout to the pair desk page")
        assert result.tier == 1
        assert result.tier_name == "Terminal Polish"
        assert result.confidence > 0.9
        assert result.estimated_risk == "low"
        assert result.suggested_approval == "fully_autonomous"

    def test_tier_1_component_request(self) -> None:
        result = classify("Create a new chart component for the about page")
        assert result.tier == 1
        assert result.tier_name == "Terminal Polish"

    def test_tier_2_signal_request(self) -> None:
        result = classify("Add a COT crowding signal to Layer 2")
        assert result.tier == 2
        assert result.tier_name == "Signal & Logic"
        assert result.estimated_risk == "medium"
        assert result.suggested_approval == "auto_up_to_merge"

    def test_tier_2_fetcher_request(self) -> None:
        result = classify("Add a new fetcher for BoJ policy rate")
        assert result.tier == 2
        assert result.tier_name == "Signal & Logic"

    def test_tier_2_test_request(self) -> None:
        result = classify("Add unit tests for the volatility signal")
        assert result.tier == 2

    def test_tier_3_threshold_request(self) -> None:
        result = classify("Change the Layer 1 bullish threshold from 0.3 to 0.25")
        assert result.tier == 3
        assert result.tier_name == "Schema & Thresholds"
        assert result.estimated_risk == "high"
        assert result.suggested_approval == "human_required"

    def test_tier_3_migration_request(self) -> None:
        result = classify("Add a new column to the signals table")
        assert result.tier == 3

    def test_tier_3_deploy_request(self) -> None:
        result = classify("Deploy the pipeline to Prefect Cloud")
        assert result.tier == 3

    def test_tier_4_backfill_request(self) -> None:
        result = classify("Backfill historical regime calls for 2024")
        assert result.tier == 4
        assert result.tier_name == "Immutable Ledger"
        assert result.estimated_risk == "critical"
        assert result.suggested_approval == "human_required_audit"
        assert "regime_calls" in result.immutable_tables_touched

    def test_tier_4_regenerate_request(self) -> None:
        result = classify("Regenerate old briefs from January")
        assert result.tier == 4

    def test_empty_request_defaults_to_tier_3(self) -> None:
        result = classify("")
        assert result.tier == 3
        assert result.confidence == 1.0

    def test_whitespace_request_defaults_to_tier_3(self) -> None:
        result = classify("   ")
        assert result.tier == 3

    def test_mixed_ui_and_signal_defaults_to_tier_2(self) -> None:
        result = classify("Add a chart component showing the new COT signal")
        assert result.tier == 2
        assert "Mixed request" in result.reasoning

    def test_unknown_keywords_default_to_tier_3(self) -> None:
        result = classify("Make the system better")
        assert result.tier == 3
        assert "ambiguous" in result.reasoning

    def test_tier_4_overrides_tier_3(self) -> None:
        """Tier 4 keywords should override Tier 3 even if both match."""
        result = classify("Delete the regime_calls table and rebuild")
        assert result.tier == 4

    def test_tier_4_overrides_tier_2(self) -> None:
        result = classify("Reprocess all historical signals and backfill validation")
        assert result.tier == 4
