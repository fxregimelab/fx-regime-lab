"""Exercise real diagnostic/AI consumers without provider or database requests."""

from __future__ import annotations

import ast
import asyncio
import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.ai import client
from src.db import writer
from src.scheduler import orchestrator
from src.types import CotRow, DeskOpenCardRow, RegimeCall, SpotBar


@pytest.mark.parametrize(
    "case",
    [
        "EURUSD",
        "USDJPY",
        "USDINR",
        "missing_direction",
        "diagnostic_failure",
        "scheduler_wiring",
        "storage_expression",
        "sharing_sync",
        "sharing_async",
        "ai_model",
        "ai_fallback",
        "ai_thesis",
        "fallback_zero",
        "fallback_high",
        "fallback_invalid",
    ],
)
def test_crowding_consumer_contract(case: str, monkeypatch: pytest.MonkeyPatch) -> None:
    cutoff = date(2026, 9, 25)
    pair = case if case in {"EURUSD", "USDJPY", "USDINR"} else "EURUSD"
    call = RegimeCall(
        pair=pair,
        date=cutoff,
        regime="STRONG USD WEAKNESS",
        confidence=0.9,
        signal_composite=0.8,
        rate_signal="BULLISH",
        predicted_direction=None if case == "missing_direction" else "BEARISH",
    )
    bars = [
        SpotBar(cutoff - timedelta(days=39 - i), pair, p, p, p, p)
        for i, p in enumerate([90.0] * 20 + [110.0] * 20)
    ]
    cot = [CotRow(cutoff - timedelta(days=3), pair, 100, 500, 60, 40)]
    if case == "diagnostic_failure":
        monkeypatch.setattr(
            orchestrator, "compute_crowding_diagnostic", Mock(side_effect=ValueError("bad input"))
        )
    telemetry = orchestrator._crowding_telemetry_for_call(
        call=call,
        call_id=123,
        cot_rows=cot,
        spot_bars=list(reversed(bars)),
    )
    assert telemetry["cot_is_stale"] is None
    assert telemetry["underwater_triggered"] is None
    assert telemetry["Systemic_Cluster"] is None
    assert telemetry["ranking_status"] == "UNAVAILABLE_UNVALIDATED_MODEL"
    diagnostic = telemetry["crowding_diagnostic"]
    assert diagnostic["call_id"] == 123
    assert diagnostic["predicted_direction"] == call.predicted_direction
    assert diagnostic["as_of_date"] == "2026-09-25"
    assert diagnostic["point_in_time_qualified"] is False
    if case == "diagnostic_failure":
        assert diagnostic["cot"]["status"] == "UNAVAILABLE"
        assert diagnostic["price"]["status"] == "UNAVAILABLE"
        assert diagnostic["cot"]["reasons"] == ["DIAGNOSTIC_FAILED"]
        assert diagnostic["participant_loss_estimate"] is None
        assert diagnostic["squeeze_probability"] is None
        assert telemetry["cot_age_days"] is None
        return
    if case in {"EURUSD", "USDJPY", "USDINR", "missing_direction"}:
        assert diagnostic["price"]["mean_close_40"] == pytest.approx(100.0)
        assert diagnostic["price"]["relative_to_mean_pct"] == pytest.approx(10.0)
        assert diagnostic["participant_loss_estimate"] is None
        assert diagnostic["squeeze_probability"] is None
        expected = {"EURUSD": "OPPOSED", "USDJPY": "ALIGNED", "USDINR": "UNAVAILABLE"}
        assert diagnostic["cot"]["alignment"] == (
            "UNAVAILABLE" if case == "missing_direction" else expected[pair]
        )
        return

    if case in {"scheduler_wiring", "storage_expression"}:
        tree = ast.parse(Path(orchestrator.__file__).read_text(encoding="utf-8"))
        flow = next(
            n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_daily"
        )
        calls = [n for n in ast.walk(flow) if isinstance(n, ast.Call)]
        if case == "scheduler_wiring":
            bound = [
                n
                for n in calls
                if isinstance(n.func, ast.Name) and n.func.id == "_crowding_telemetry_for_call"
            ]
            assert len(bound) == 1
            args = {kw.arg: ast.unparse(kw.value) for kw in bound[0].keywords}
            assert args["call"] == "call"
            assert args["call_id"] == "persisted_call_id"
            spreads = [
                v
                for n in ast.walk(flow)
                if isinstance(n, ast.Dict)
                for k, v in zip(n.keys, n.values, strict=True)
                if k is None
            ]
            assert any(isinstance(v, ast.Name) and v.id == "crowding_telemetry" for v in spreads)
            names = {ast.unparse(n.func) for n in calls}
            assert not names & {
                "compute_pain_index",
                "assign_apex_ranking",
                "writer.get_desk_ranking_history",
            }
            # Both the model kwargs and card record must receive an unavailable legacy input.
            pain_values = [
                v
                for n in ast.walk(flow)
                if isinstance(n, ast.Dict)
                for k, v in zip(n.keys, n.values, strict=True)
                if isinstance(k, ast.Constant) and k.value == "pain_index"
            ]
            assert len(pain_values) == 2
            assert all(isinstance(v, ast.Constant) and v.value is None for v in pain_values)
            return
        constructor = next(
            n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "DeskOpenCardRow"
        )
        scope: dict[str, Any] = {
            "DeskOpenCardRow": DeskOpenCardRow,
            "cast": lambda _t, v: v,
            "Any": Any,
            "card": {
                "date": cutoff,
                "structural_regime": call.regime,
                "dominance_array": [],
                "pain_index": None,
                "markov_probabilities": {},
            },
            "pair_key": pair,
            "ai_brief": "{}",
            "telemetry_merged": telemetry,
        }
        # Execute the actual production constructor, not a test reconstruction of its defaults.
        record = eval(compile(ast.Expression(constructor), "production-desk-record", "eval"), scope)
        payload = asdict(record)
        assert payload["pain_index"] is None
        assert payload["global_rank"] is None
        assert payload["apex_score"] is None
        assert payload["telemetry_audit"]["crowding_diagnostic"]["call_id"] == 123
        return

    if case.startswith("sharing_"):
        sync_model = Mock(side_effect=AssertionError("must not call AI"))
        async_model = AsyncMock(side_effect=AssertionError("must not call AI"))
        monkeypatch.setattr(client, "_call_preferred_model", sync_model)
        monkeypatch.setattr(client, "_call_preferred_model_async", async_model)
        with pytest.raises(RuntimeError, match="Apex sharing is retired"):
            if case == "sharing_sync":
                client.generate_linkedin_alpha_hook({"pain_index": 99, "apex_score": 1})
            else:
                asyncio.run(
                    client.generate_linkedin_alpha_hook_async(
                        {"pain_index": 99, "apex_score": 1},
                        date_str="2026-09-25",
                    )
                )
        sync_model.assert_not_called()
        async_model.assert_not_awaited()
        return

    if case.startswith("fallback_"):
        pain = {"fallback_zero": 0.0, "fallback_high": 99.0, "fallback_invalid": float("nan")}[case]
        result = json.loads(
            client.desk_card_brief_fallback(
                regime="MODERATE USD STRENGTH",
                primary_driver="RATES",
                pain_index=pain,
                rvol=900.0,
                todays_event_matrix={"event_name": "CPI", "asymmetry_ratio": 999},
            )
        )
        assert result["squeeze_risk"] == "Participant losses and squeeze probability unavailable"
        assert result["bias_summary"] == "MODERATE USD STRENGTH"
        assert result["catalyst_driver"] == "RATES"
        return

    snapshot = Mock(
        return_value={"pair": pair, "date": cutoff.isoformat(), "rate_z_tactical": 1.25}
    )
    monkeypatch.setattr(writer, "get_publication_signal_for_call", snapshot)
    monkeypatch.setattr(
        writer,
        "get_latest_research_memo_thesis_bullets",
        lambda: ["Rates thesis"] if case == "ai_thesis" else [],
    )
    model = AsyncMock(
        return_value=json.dumps(
            {
                "bias_summary": "PUBLISHED BIAS",
                "catalyst_driver": "RATES",
                "squeeze_risk": "ELEVATED (PAIN 99), participants underwater",
            }
        )
    )
    if case == "ai_fallback":
        model.side_effect = TimeoutError("synthetic timeout")
    monkeypatch.setattr(client, "_call_preferred_model_async", model)
    result_text, grounded = asyncio.run(
        client.generate_desk_card_brief_async(
            call_id=123,
            pair=pair,
            regime=call.regime,
            date_str=cutoff.isoformat(),
            primary_driver="RATES",
            pain_index=99.0,
            rvol=900,
            todays_event_matrix={"event_name": "CPI", "asymmetry_ratio": 999},
        )
    )
    result = json.loads(result_text)
    snapshot.assert_called_once_with(123)
    assert result["squeeze_risk"] == "Participant losses and squeeze probability unavailable"
    assert result["catalyst_driver"] == "RATES"
    assert grounded is (case == "ai_thesis")
    assert model.await_count == (2 if case == "ai_fallback" else 1)
    for invocation in model.await_args_list:
        prompt = invocation.kwargs["messages"][0]["content"]
        assert "PAIN_INDEX" not in prompt
        assert "8-WEEK VWAP" not in prompt
        assert "CONTROLLED (PAIN" not in prompt
        assert "ELEVATED (PAIN" not in prompt
        assert "RATE_Z_TACTICAL_MAD:1.25" in prompt
    if case != "ai_fallback":
        assert result["bias_summary"] == "PUBLISHED BIAS"
