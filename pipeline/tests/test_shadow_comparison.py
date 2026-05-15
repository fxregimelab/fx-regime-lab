"""Tests for shadow_comparison fallback logic."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.shadow_comparison import _get_comparison_rows


def _resp(data: list[dict[str, Any]]) -> MagicMock:
    r = MagicMock()
    r.data = data
    return r


def _row(
    pair: str,
    model_version: str,
    regime: str,
    confidence: float,
    signal_composite: float,
    primary_driver: str,
) -> dict[str, Any]:
    return {
        "pair": pair,
        "model_version": model_version,
        "regime": regime,
        "confidence": confidence,
        "signal_composite": signal_composite,
        "primary_driver": primary_driver,
    }


class TestGetComparisonRows:
    """Tests for _get_comparison_rows fallback behaviour."""

    @patch("scripts.shadow_comparison.writer._client")
    def test_target_date_with_full_overlap(self, mock_client: MagicMock) -> None:
        """When target date has all 3 pairs with v2+v3, use it directly."""
        client = MagicMock()
        mock_client.return_value = client

        # Single query path: target date has full overlap
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _resp(
                [
                    _row("EURUSD", "v2", "NEUTRAL", 0.3, -0.1, "COT"),
                    _row("EURUSD", "v3", "RANGING", 10.0, -0.1, "Rate"),
                    _row("USDJPY", "v2", "BEARISH", 0.3, -0.2, "COT"),
                    _row("USDJPY", "v3", "RANGING", 10.0, -0.2, "Rate"),
                    _row("USDINR", "v2", "NEUTRAL", 0.3, 0.0, "COT"),
                    _row("USDINR", "v3", "RANGING", 10.0, 0.0, "Rate"),
                ]
            )
        )

        rows = _get_comparison_rows(date(2026, 5, 12))
        assert len(rows) == 3
        assert rows[0]["date"] == "2026-05-12"
        assert rows[0]["regime_match"] is False
        assert rows[0]["v2_regime"] == "NEUTRAL"
        assert rows[0]["v3_regime"] == "RANGING"

    @patch("scripts.shadow_comparison.writer._client")
    def test_no_data_returns_empty(self, mock_client: MagicMock) -> None:
        """When no data exists at all, return empty list."""
        client = MagicMock()
        mock_client.return_value = client

        empty = _resp([])
        # All queries return empty
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = empty
        (
            client.table.return_value.select.return_value.order.return_value
            .limit.return_value.execute.return_value
        ) = empty

        rows = _get_comparison_rows(date(2026, 5, 15))
        assert rows == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
