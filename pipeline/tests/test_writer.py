"""Tests for writer utility functions (compute_write_hash, write_pipeline_error,
write_validation_row).
"""

from __future__ import annotations

from typing import Any
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


def _build_validation_select_mock(mock_table: MagicMock, data: Any) -> None:
    """Wire ``mock_table.select(...)`` to return *data* from execute()."""
    select = mock_table.select.return_value
    select.eq.return_value = select
    select.order.return_value = select
    select.limit.return_value = select
    select.maybe_single.return_value.execute.return_value = MagicMock(data=data)


class TestWriteValidationRow:
    @patch.object(writer, "_client")
    def test_inserts_when_no_existing_row(self, mock_client: MagicMock) -> None:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        _build_validation_select_mock(mock_table, None)
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )

        writer.write_validation_row(
            {
                "call_id": 42,
                "pair": "EURUSD",
                "call_date": "2026-05-01",
                "date": "2026-05-01",
                "log_return_t5_bps": 10.0,
                "correct_t5": True,
            }
        )

        mock_table.insert.assert_called_once()
        inserted = mock_table.insert.call_args[0][0]
        assert isinstance(inserted, list) and len(inserted) == 1
        payload = inserted[0]
        assert payload["call_id"] == 42
        assert payload["is_superseded"] is False
        mock_table.update.assert_not_called()

    @patch.object(writer, "_client")
    def test_skips_when_identical_payload(self, mock_client: MagicMock) -> None:
        existing = {
            "id": 1,
            "call_id": 42,
            "pair": "EURUSD",
            "call_date": "2026-05-01",
            "date": "2026-05-01",
            "log_return_t5_bps": 10.0,
            "correct_t5": True,
            "is_superseded": False,
        }
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        _build_validation_select_mock(mock_table, existing)

        writer.write_validation_row(
            {
                "call_id": 42,
                "pair": "EURUSD",
                "call_date": "2026-05-01",
                "date": "2026-05-01",
                "log_return_t5_bps": 10.0,
                "correct_t5": True,
            }
        )

        mock_table.insert.assert_not_called()
        mock_table.update.assert_not_called()

    @patch.object(writer, "_client")
    def test_supersede_and_insert_when_different(
        self, mock_client: MagicMock
    ) -> None:
        existing = {
            "id": 1,
            "call_id": 42,
            "pair": "EURUSD",
            "call_date": "2026-05-01",
            "date": "2026-05-01",
            "log_return_t5_bps": 10.0,
            "correct_t5": True,
            "is_superseded": False,
        }
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        _build_validation_select_mock(mock_table, existing)
        mock_table.update.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[{"id": 1}])
        )
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": 2}]
        )

        writer.write_validation_row(
            {
                "call_id": 42,
                "pair": "EURUSD",
                "call_date": "2026-05-01",
                "date": "2026-05-01",
                "log_return_t5_bps": 10.0,
                "correct_t5": True,
                "log_return_t20_bps": 25.0,
                "correct_t20": True,
            }
        )

        mock_table.update.assert_called_once_with({"is_superseded": True})
        mock_table.insert.assert_called_once()

    @patch.object(writer, "_client")
    def test_skips_when_existing_has_t5_and_no_t20_added(
        self, mock_client: MagicMock
    ) -> None:
        existing = {
            "id": 1,
            "call_id": 42,
            "pair": "EURUSD",
            "call_date": "2026-05-01",
            "date": "2026-05-01",
            "log_return_t5_bps": 10.0,
            "correct_t5": True,
            "is_superseded": False,
        }
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        _build_validation_select_mock(mock_table, existing)

        writer.write_validation_row(
            {
                "call_id": 42,
                "pair": "EURUSD",
                "call_date": "2026-05-01",
                "date": "2026-05-01",
                "log_return_t5_bps": 10.0,
                "correct_t5": True,
            }
        )

        mock_table.insert.assert_not_called()
        mock_table.update.assert_not_called()
