"""Exercise actual offline consumers of the pair-direction boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backfill import simulation_engine as replay
from src.diagnostics import permutation_importance as diagnostic
from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.logic.layer2_directional import run_layer2_directional
from src.regime.classifier import classify_regime, get_regime_category, get_regime_metadata
from src.regime.composite import compute_composite
from src.scheduler import orchestrator as live
from src.signals.direction import DIRECTIONAL_MODEL_VERSION, directional_inputs
from src.signals.fpi import FPI_UNAVAILABLE_NOTES
from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.stages import signal_stage as staged
from src.types import SpotBar


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
@pytest.mark.parametrize("consumer", ["staged", "replay", "diagnostic", "scheduler", "metadata"])
def test_directional_consumers(pair: str, consumer: str, monkeypatch: pytest.MonkeyPatch) -> None:
    today = datetime.now(UTC).date()
    days = [today - timedelta(days=74 - i) for i in range(75)]
    bars = tuple(
        SpotBar(
            date=d,
            pair=pair,
            open=1 + i * 0.001,
            high=1 + i * 0.001,
            low=1 + i * 0.001,
            close=1 + i * 0.001,
            volume=1000 + i,
        )
        for i, d in enumerate(days)
    )
    raw_cot = 0.6 if pair != "USDINR" else None
    expected = directional_inputs(pair, rate=None, cot=raw_cot, special=0.4, fpi=None)
    expected_score = compute_composite(
        expected.rate,
        expected.cot,
        1,
        1,
        pair=pair,
        special_signal=expected.special,
    )

    if consumer == "metadata":
        label = classify_regime(1.5, pair)
        assert get_regime_metadata(label).base_regime == (
            "USD_WEAKNESS" if pair == "EURUSD" else "USD_STRENGTH"
        )
        assert get_regime_category(label) == "DIRECTIONAL_REFERENCE"

    elif consumer == "staged":
        monkeypatch.setattr(staged, "compute_cot_percentile", lambda *a, **k: 80)
        monkeypatch.setattr(staged, "compute_cot_smart_spread_percentile", lambda *a, **k: None)
        monkeypatch.setattr(staged, "compute_special_signal", lambda *a, **k: 0.4)
        snapshot = IngestionSnapshot(
            date=today,
            spots={pair: bars},
            yields={},
            cot_rows=[],
            cross_asset={},
        )
        with patch.object(staged, "run_layer2_directional", wraps=run_layer2_directional) as layer:
            result = staged.SignalStage().run(pair, snapshot)
        assert result.signal_row.fpi_flow is None
        for note in FPI_UNAVAILABLE_NOTES:
            assert (note in result.health.notes) == (pair == "USDINR")
            assert (note in (result.signal_row.data_quality_notes or [])) == (pair == "USDINR")
        assert result.cot_norm == expected.cot
        assert result.special_signal == expected.special
        assert result.composite == pytest.approx(expected_score)
        assert layer.call_args.kwargs["pair"] == pair
        assert result.cot_percentile == (80 if pair != "USDINR" else None)
        monkeypatch.setattr(staged, "compute_cot_percentile", lambda *a, **k: None)
        monkeypatch.setattr(staged, "compute_special_signal", lambda *a, **k: None)
        monkeypatch.setattr(staged, "compute_vol_signal", lambda *a, **k: 1)
        monkeypatch.setattr(staged, "compute_oi_from_cot", lambda *a, **k: 0)
        with pytest.raises(ValueError, match="directional_inputs_unavailable"):
            staged.SignalStage().run(pair, snapshot)

    elif consumer == "replay":
        monkeypatch.setattr(replay, "_load_all_spot_bars", lambda *a: {b.date: b for b in bars})
        monkeypatch.setattr(replay, "compute_special_signal", lambda *a, **k: 0.4)
        signals = {
            d: {"cot_percentile": 80, "oi_delta": (-1, 0, 1)[i % 3], "fpi_flow": 500000.0}
            for i, d in enumerate(days)
        }
        with patch.object(replay, "run_layer2_directional", wraps=run_layer2_directional) as layer:
            results = replay.simulate_all_days_v2(pair, days[0], today, {}, signals_by_date=signals)
        assert len(results) == 15
        assert all(c.signal_composite == pytest.approx(expected_score) for _, c in results)
        assert all(c.model_version == DIRECTIONAL_MODEL_VERSION for _, c in results)
        assert all(c.oi_signal == "UNAVAILABLE" for _, c in results)
        assert {s.oi_delta for s, _ in results} == {-1, 0, 1}
        assert all(s.fpi_flow is None for s, _ in results)
        for signal, _ in results:
            for note in FPI_UNAVAILABLE_NOTES:
                assert (note in (signal.data_quality_notes or [])) == (pair == "USDINR")
        assert all(call.kwargs["pair"] == pair for call in layer.call_args_list)
        legacy = replay.simulate_all_days(pair, days[0], today, {})
        assert all(c.signal_composite == expected.special for _, c in legacy)
        monkeypatch.setattr(replay, "compute_special_signal", lambda *a, **k: None)
        assert replay.simulate_all_days(pair, days[0], today, {}) == []

    elif consumer == "diagnostic":
        values: dict[str, list[float | None]] = {
            "rate": [None],
            "cot": [raw_cot],
            "vol": [1.0],
            "oi": [1.0],
            "special": [0.4],
            "fpi": [None],
        }
        with patch.object(diagnostic, "compute_composite", wraps=compute_composite) as composite:
            diagnostic._compute_accuracy(
                [{"date": days[0]}],
                {d: 1 + i * 0.01 for i, d in enumerate(days)},
                values,
                {"vol": 999.0},
                pair,
            )
        assert composite.call_args.args[:2] == (expected.rate, expected.cot)
        assert composite.call_args.kwargs["special_signal"] == expected.special

    else:
        # Stop at the real composite boundary, before any publication or AI path.
        buffer = {KEY_FX_SPOT: {pair: bars}, KEY_YIELDS: {}, KEY_COT: [], KEY_CROSS_ASSET: {}}
        monkeypatch.setattr(live, "PAIRS", [pair])
        monkeypatch.setattr(live, "_require_pipeline_runtime_env", lambda: None)
        monkeypatch.setattr(live, "load_universe", lambda: {})
        monkeypatch.setattr(live, "build_master_buffer_task", AsyncMock(return_value=buffer))
        monkeypatch.setattr(
            live,
            "validate_ingestion_buffer",
            lambda *a, **k: SimpleNamespace(telemetry_status="ONLINE", buffer=buffer),
        )
        quality = SimpleNamespace(
            score=0.95,
            rates_freshness=1,
            spots_freshness=1,
            cot_freshness=1,
            commodities_freshness=1,
            cross_asset_freshness=1,
            critical_penalty_applied=False,
            spot_observation_date=today,
            cot_observation_date=today,
        )
        monkeypatch.setattr(live, "compute_dqs", lambda *a, **k: quality)
        monkeypatch.setattr(live, "archive_price_snapshot", lambda *a, **k: None)
        monkeypatch.setattr(
            live, "_price_archive_stage_health", lambda *a: StageHealth("archive", "OK")
        )
        monkeypatch.setattr(live, "_dxy_overnight_pct_abs", lambda: 0)
        monkeypatch.setattr(
            live,
            "fetch_realized_vol",
            lambda *a: {pair: {"realized_vol_5d": 2, "realized_vol_20d": 1}},
        )
        monkeypatch.setattr(live, "fetch_macro_events", lambda: [])
        for name in (
            "fetch_ecb_balance_sheet",
            "fetch_bund_btp_spread",
            "fetch_boj_policy_rate",
            "fetch_india_vix",
            "fetch_inr_forward_premium",
            "fetch_implied_vol",
        ):
            monkeypatch.setattr(live, name, lambda *a, **k: None)
        writer = MagicMock()
        writer.get_historical_signals.return_value = [
            {"date": d.isoformat(), "fpi_flow": 500000.0} for d in reversed(days)
        ]
        writer.get_current_live_regime_call.return_value = None
        monkeypatch.setattr(live, "writer", writer)
        monkeypatch.setattr(live, "compute_cot_percentile", lambda *a, **k: 80)
        monkeypatch.setattr(live, "compute_cot_smart_spread_percentile", lambda *a, **k: None)
        monkeypatch.setattr(live, "compute_special_signal", lambda *a, **k: 0.4)
        with patch.object(
            live, "compute_composite", side_effect=RuntimeError("stop_before_publication")
        ) as composite:
            with pytest.raises(RuntimeError, match="stop_before_publication"):
                asyncio.run(live.run_daily.fn(today.isoformat()))
        assert composite.call_args.args[:2] == (expected.rate, expected.cot)
        assert composite.call_args.kwargs["special_signal"] == expected.special
        assert composite.call_args.kwargs["fpi_signal"] is None
        writer.publish_regime_call.assert_not_called()
