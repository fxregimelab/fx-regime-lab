"""Tests for writer utility functions (compute_write_hash, write_pipeline_error)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.db import writer


class TestComputeWriteHash:
    def test_deterministic_same_inputs(self) -> None:
        inputs = {"pair": "EURUSD", "confidence": 0.75, "regime": "BULLISH"}
        h1 = writer.compute_write_hash(inputs)
        h2 = writer.compute_write_hash(inputs)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_inputs_different_hash(self) -> None:
        h1 = writer.compute_write_hash({"pair": "EURUSD", "confidence": 0.75})
        h2 = writer.compute_write_hash({"pair": "EURUSD", "confidence": 0.76})
        assert h1 != h2

    def test_order_independence(self) -> None:
        h1 = writer.compute_write_hash({"a": 1, "b": 2})
        h2 = writer.compute_write_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_nested_dict(self) -> None:
        h1 = writer.compute_write_hash({"layer": {"score": 0.5}})
        h2 = writer.compute_write_hash({"layer": {"score": 0.5}})
        assert h1 == h2


class TestWritePipelineError:
    @patch.object(writer, "_client")
    def test_writes_structured_error(self, mock_client: MagicMock) -> None:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

        writer.write_pipeline_error(
            step="orchestrator",
            error_type="RuntimeError",
            message="DQS critical",
            traceback_str="Traceback...",
            correlation_id="corr-123",
        )

        mock_client.return_value.table.assert_called_once_with("pipeline_errors")
        payload = mock_table.insert.call_args[0][0]
        assert payload["step"] == "orchestrator"
        assert payload["error_type"] == "RuntimeError"
        assert payload["message"] == "DQS critical"
        assert payload["traceback"] == "Traceback..."
        assert payload["correlation_id"] == "corr-123"

    @patch.object(writer, "_client")
    def test_silently_ignores_db_errors(self, mock_client: MagicMock) -> None:
        mock_client.return_value.table.side_effect = RuntimeError("DB down")
        # Should not raise
        writer.write_pipeline_error(
            step="fetch",
            error_type="ConnectionError",
            message="timeout",
        )

    @patch.object(writer, "_client")
    def test_optional_fields_omitted(self, mock_client: MagicMock) -> None:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

        writer.write_pipeline_error(
            step="validation",
            error_type="ValueError",
            message="bad data",
        )

        payload = mock_table.insert.call_args[0][0]
        assert "traceback" not in payload
        assert "correlation_id" not in payload
