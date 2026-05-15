"""Tests for scheduler orchestrator health report and env validation."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db import writer
from src.scheduler.orchestrator import (
    _finalize_health_report,
    _validate_env,
    batch_desk_briefs_task,
    run_daily,
)


class TestValidateEnv:
    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "a" * 21,
            "OPENROUTER_API_KEY": "sk-test",
            "FRED_API_KEY": "fred-key",
            "POLYGON_API_KEY": "poly-key",
        },
        clear=True,
    )
    def test_all_valid_passes(self) -> None:
        _validate_env()

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_all_raises(self, caplog: pytest.LogCaptureFixture) -> None:
        with pytest.raises(RuntimeError, match="Environment validation failed"):
            _validate_env()
        assert any("Environment validation failed" in r.message for r in caplog.records)
        assert any(r.levelno == logging.CRITICAL for r in caplog.records)

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "http://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "short",
            "OPENROUTER_API_KEY": "",
            "FRED_API_KEY": "",
            "POLYGON_API_KEY": "",
        },
        clear=True,
    )
    def test_invalid_formats_raises(self) -> None:
        with pytest.raises(RuntimeError, match="SUPABASE_URL must start with https://"):
            _validate_env()

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "a" * 21,
            "OPENROUTER_API_KEY": "not-sk-prefix",
            "FRED_API_KEY": "fred-key",
            "POLYGON_API_KEY": "poly-key",
        },
        clear=True,
    )
    def test_openrouter_non_empty_passes(self) -> None:
        _validate_env()


class TestWritePipelineRun:
    @patch.object(writer, "_client")
    def test_inserts_new_run(self, mock_client: MagicMock) -> None:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        select_chain = mock_table.select.return_value
        eq_chain = select_chain.eq.return_value
        eq_chain.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

        writer.write_pipeline_run(
            {
                "correlation_id": "corr-123",
                "date": "2026-05-11",
                "status": "COMPLETE",
                "dqs_score": 0.85,
                "pairs_processed": 3,
                "pairs_skipped": [],
                "ai_calls_made": 10,
                "ai_calls_failed": 0,
                "sources_used": {"polygon": True},
                "duration_seconds": 45.2,
                "errors": [],
            }
        )

        mock_client.return_value.table.assert_any_call("pipeline_runs")
        payload = mock_table.insert.call_args[0][0]
        assert payload["correlation_id"] == "corr-123"
        assert payload["status"] == "COMPLETE"
        assert payload["dqs_score"] == 0.85

    @patch.object(writer, "_client")
    def test_skips_existing_run(self, mock_client: MagicMock) -> None:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        select_chain = mock_table.select.return_value
        eq_chain = select_chain.eq.return_value
        eq_chain.maybe_single.return_value.execute.return_value = MagicMock(data={"id": 1})

        writer.write_pipeline_run(
            {
                "correlation_id": "corr-123",
                "date": "2026-05-11",
                "status": "COMPLETE",
                "dqs_score": 0.85,
                "pairs_processed": 3,
                "pairs_skipped": [],
                "ai_calls_made": 10,
                "ai_calls_failed": 0,
                "sources_used": {"polygon": True},
                "duration_seconds": 45.2,
                "errors": [],
            }
        )

        mock_table.insert.assert_not_called()

    @patch.object(writer, "_client")
    def test_silently_ignores_db_errors(self, mock_client: MagicMock) -> None:
        mock_client.return_value.table.side_effect = RuntimeError("DB down")
        writer.write_pipeline_run(
            {
                "correlation_id": "corr-123",
                "date": "2026-05-11",
                "status": "COMPLETE",
                "dqs_score": 0.85,
                "pairs_processed": 3,
                "pairs_skipped": [],
                "ai_calls_made": 10,
                "ai_calls_failed": 0,
                "sources_used": {"polygon": True},
                "duration_seconds": 45.2,
                "errors": [],
            }
        )


class TestFinalizeHealthReport:
    @patch.object(writer, "_client")
    def test_writes_to_db(self, mock_client: MagicMock) -> None:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        select_chain = mock_table.select.return_value
        eq_chain = select_chain.eq.return_value
        eq_chain.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

        import time

        hr = {
            "correlation_id": "c1",
            "date": "2026-05-11",
            "status": "COMPLETE",
            "dqs_score": 0.9,
            "pairs_processed": 3,
            "pairs_skipped": [],
            "ai_calls_made": 5,
            "ai_calls_failed": 0,
            "sources_used": {"polygon": True},
            "duration_seconds": 0.0,
            "errors": [],
        }
        _finalize_health_report(hr, time.perf_counter())

        mock_client.return_value.table.assert_any_call("pipeline_runs")
        payload = mock_table.insert.call_args[0][0]
        assert payload["correlation_id"] == "c1"
        assert payload["status"] == "COMPLETE"


class TestRunDailyHealthReport:
    @pytest.mark.anyio
    async def test_telemetry_offline_aborts(self) -> None:
        with (
            patch("src.scheduler.orchestrator._validate_env"),
            patch("src.scheduler.orchestrator.load_universe", return_value={}),
            patch(
                "src.scheduler.orchestrator.build_master_buffer_task",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("src.scheduler.orchestrator.validate_ingestion_buffer") as mock_gate,
            patch("src.scheduler.orchestrator.writer") as mock_writer,
        ):
            mock_gate.return_value = MagicMock(telemetry_status="OFFLINE", buffer={})

            await run_daily("2026-05-11", correlation_id="test-corr")

            mock_writer.write_pipeline_run.assert_called_once()
            hr = mock_writer.write_pipeline_run.call_args[0][0]
            assert hr["status"] == "ABORTED"
            assert hr["correlation_id"] == "test-corr"
            assert hr["date"] == "2026-05-11"
            assert any("OFFLINE" in e for e in hr["errors"])

    @pytest.mark.anyio
    async def test_dqs_critical_aborts(self) -> None:
        with (
            patch("src.scheduler.orchestrator._validate_env"),
            patch("src.scheduler.orchestrator.load_universe", return_value={}),
            patch(
                "src.scheduler.orchestrator.build_master_buffer_task",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("src.scheduler.orchestrator.validate_ingestion_buffer") as mock_gate,
            patch("src.scheduler.orchestrator.compute_dqs") as mock_dqs,
            patch("src.scheduler.orchestrator.writer") as mock_writer,
        ):
            mock_gate.return_value = MagicMock(telemetry_status="ONLINE", buffer={})
            mock_dqs.return_value = MagicMock(score=0.45)

            with pytest.raises(RuntimeError, match="Data Quality Score critical"):
                await run_daily("2026-05-11", correlation_id="test-corr")

            mock_writer.write_pipeline_run.assert_called_once()
            hr = mock_writer.write_pipeline_run.call_args[0][0]
            assert hr["status"] == "ABORTED"
            assert hr["dqs_score"] == 0.45

    @pytest.mark.anyio
    async def test_invalid_env_aborts(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("src.scheduler.orchestrator.writer") as mock_writer,
        ):
            with pytest.raises(RuntimeError, match="Environment validation failed"):
                await run_daily("2026-05-11")

            mock_writer.write_pipeline_run.assert_called_once()
            hr = mock_writer.write_pipeline_run.call_args[0][0]
            assert hr["status"] == "ABORTED"
            assert any("Environment validation failed" in e for e in hr["errors"])


class TestBatchDeskBriefsTask:
    @pytest.mark.anyio
    async def test_timeout_falls_back_to_deterministic(self) -> None:
        """D4: asyncio.TimeoutError in batch_desk_briefs_task falls back for all pairs."""
        with patch(
            "src.ai.client.generate_desk_card_brief_async",
            side_effect=asyncio.TimeoutError,
        ):
            pending = [
                {
                    "brief_kw": {
                        "pair": "EURUSD",
                        "regime": "CARRY_POSITIVE",
                        "date_str": "2026-05-11",
                        "primary_driver": "rate",
                        "pain_index": None,
                        "rvol": None,
                        "todays_event_matrix": None,
                        "dollar_dominance_score": None,
                        "dollar_bias": None,
                    },
                    "card": {"pair": "EURUSD"},
                }
            ]
            outcomes, stats = await batch_desk_briefs_task(pending)
            assert len(outcomes) == 1
            assert isinstance(outcomes[0], tuple)
            assert outcomes[0][1] is False
            assert stats["ai_calls_made"] == 0
            assert stats["ai_calls_failed"] == 1


class TestRunDailyDegradedMode:
    @pytest.mark.anyio
    async def test_dqs_degraded_skips_ai_briefs(self) -> None:
        """D5: 0.50 <= DQS < 0.70 runs math but skips AI briefs and sets DEGRADED."""
        from src.fx_types import SpotBar

        test_date = "2026-05-11"
        as_of = date.fromisoformat(test_date)
        spot_bar = SpotBar(
            date=as_of,
            pair="EURUSD",
            open=1.08,
            high=1.09,
            low=1.07,
            close=1.085,
            volume=1000.0,
        )

        with (
            patch("src.scheduler.orchestrator._validate_env"),
            patch(
                "src.scheduler.orchestrator.load_universe",
                return_value={
                    "EURUSD": {
                        "class": "FX",
                        "tickers": {
                            "spot_ticker": "EURUSD=X",
                            "yield_base": "^UST2Y",
                            "yield_quote": "^DE2Y",
                        },
                    },
                    "USDJPY": {
                        "class": "FX",
                        "tickers": {
                            "spot_ticker": "USDJPY=X",
                            "yield_base": "^UST2Y",
                            "yield_quote": "^JP2Y",
                        },
                    },
                    "USDINR": {
                        "class": "FX",
                        "tickers": {
                            "spot_ticker": "USDINR=X",
                            "yield_base": "^UST2Y",
                            "yield_quote": "^IN2Y",
                        },
                    },
                },
            ),
            patch(
                "src.scheduler.orchestrator.build_master_buffer_task",
                new_callable=AsyncMock,
                return_value={
                    "fx_spot": {
                        "EURUSD": [spot_bar],
                        "USDJPY": [spot_bar],
                        "USDINR": [spot_bar],
                    },
                    "yields": {"us_2y": 4.5, "de_2y": 2.5, "jp_2y": 0.5, "in_2y": 6.5},
                    "cot": [],
                    "cross_asset": {
                        "vix": 15.0,
                        "dxy": 105.0,
                        "oil": 80.0,
                        "gold": 2000.0,
                        "copper": 4.0,
                        "stoxx": 4500.0,
                    },
                },
            ),
            patch("src.scheduler.orchestrator.validate_ingestion_buffer") as mock_gate,
            patch("src.scheduler.orchestrator.compute_dqs") as mock_dqs,
            patch("src.scheduler.orchestrator.writer") as mock_writer,
            patch("src.scheduler.orchestrator.fetch_macro_events", return_value=[]),
            patch("src.scheduler.orchestrator.fetch_realized_vol", return_value={}),
            patch("src.scheduler.orchestrator.fetch_implied_vol", return_value=None),
            patch("src.scheduler.orchestrator.batch_desk_briefs_task") as mock_batch,
            patch("src.scheduler.orchestrator.upsert_pair_briefs_task") as mock_pair_briefs,
        ):
            mock_gate.return_value = MagicMock(telemetry_status="ONLINE", buffer={})
            mock_dqs.return_value = MagicMock(
                score=0.60,
                rates_freshness=0.8,
                spots_freshness=0.8,
                cot_freshness=0.0,
                commodities_freshness=0.8,
                cross_asset_freshness=0.8,
                critical_penalty_applied=False,
                spot_observation_date=None,
                cot_observation_date=None,
            )
            mock_writer.get_latest_regime_call.return_value = None
            mock_writer.get_historical_signals.return_value = []
            mock_writer.get_historical_prices.return_value = []
            mock_writer.get_historical_regime_calls.return_value = []
            mock_writer.get_rpc_historical_analogs.return_value = []
            mock_writer.get_desk_open_cards_for_date.return_value = []
            mock_writer.get_rpc_g10_correlation_matrix.return_value = {}
            mock_writer.get_latest_research_memo_thesis_bullets.return_value = []
            mock_writer.research_memo_exists.return_value = True
            mock_writer.get_rpc_calculate_dual_correlation.return_value = 0.5

            await run_daily(test_date, correlation_id="test-degraded")

            mock_writer.write_pipeline_run.assert_called_once()
            hr = mock_writer.write_pipeline_run.call_args[0][0]
            assert hr["status"] == "DEGRADED"
            assert hr["dqs_score"] == 0.60
            mock_batch.assert_not_called()
            mock_pair_briefs.assert_not_called()
