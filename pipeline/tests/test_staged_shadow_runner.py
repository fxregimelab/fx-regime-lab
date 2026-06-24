"""Tests for the staged v2 shadow-run harness."""

from __future__ import annotations

import asyncio
import datetime
from typing import Any

from src.staged.contracts import IngestionSnapshot
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.staged.orchestrator import run_multi_pair_flow
from src.staged.shadow_runner import (
    ShadowRunResult,
    compare_briefs,
    compare_desk_cards,
    compare_regime_calls,
    count_consecutive_equivalent_days,
    make_comparison,
    run_shadow_comparison,
)
from src.types import CotRow, RegimeCall, SpotBar


def _spot_bar(pair: str, d: datetime.date, close: float) -> SpotBar:
    return SpotBar(
        date=d,
        pair=pair,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000.0,
    )


def _trading_date_range(start: datetime.date, days: int) -> list[datetime.date]:
    dates: list[datetime.date] = []
    current = start
    while len(dates) < days:
        if current.weekday() < 5:
            dates.append(current)
        current += datetime.timedelta(days=1)
    return dates


def _make_pair_spots(pair: str, as_of: datetime.date, base: float) -> tuple[SpotBar, ...]:
    start = as_of - datetime.timedelta(days=60)
    dates = _trading_date_range(start, 40)
    return tuple(
        _spot_bar(pair, d, round(base + i * 0.0005, 4))
        for i, d in enumerate(dates)
    )


def _make_cot_rows(pair: str, as_of: datetime.date) -> list[CotRow]:
    cot_start = as_of - datetime.timedelta(weeks=11)
    rows: list[CotRow] = []
    for i in range(10):
        report_date = cot_start + datetime.timedelta(weeks=i)
        rows.append(
            CotRow(
                date=report_date,
                pair=pair,
                net_long=10_000 + i * 500,
                open_interest=50_000 + i * 1_000,
                asset_mgr_net=6_000 + i * 300,
                lev_money_net=-2_000 - i * 100,
            )
        )
    return rows


def _make_multi_pair_snapshot() -> IngestionSnapshot:
    as_of = datetime.date(2026, 5, 20)
    pairs = [("EURUSD", 1.0800), ("USDJPY", 145.00), ("USDINR", 85.50)]
    spots = {pair: _make_pair_spots(pair, as_of, base) for pair, base in pairs}
    cot_rows: list[CotRow] = []
    for pair, _ in pairs:
        cot_rows.extend(_make_cot_rows(pair, as_of))

    return IngestionSnapshot(
        date=as_of,
        spots=spots,
        yields={
            "DGS2": 4.0,
            "ECBDFR": 2.0,
            "IRLTLT01JPM156N": 0.5,
            "INDIRLTLT01STM": 6.5,
            "us_10y": 4.5,
            "de_10y": 2.5,
            "jp_10y": 1.0,
            "in_10y": 7.0,
            "T10YIE": 2.0,
        },
        cot_rows=cot_rows,
        cross_asset={
            "vix": 18.0,
            "dxy": 104.0,
            "oil": 75.0,
            "gold": 2000.0,
            "copper": 4.0,
            "stoxx": 4500.0,
        },
        macro={
            "ecb_balance_sheet": 7000.0,
            "bund_btp_spread": 1.5,
            "boj_policy_rate": 0.25,
            "india_vix": 15.0,
            "inr_forward_premium": 1.5,
        },
        dqs_score=0.95,
        stress_level="GREEN",
    )


def _sample_regime_call(**overrides: Any) -> RegimeCall:
    defaults: dict[str, Any] = {
        "pair": "EURUSD",
        "date": datetime.date(2026, 5, 20),
        "regime": "RALLY",
        "confidence": 0.72,
        "signal_composite": 0.35,
        "rate_signal": "BULLISH",
        "primary_driver": "rates",
        "entry_timing": "ENTER",
        "position_size": "FULL",
        "stop_level": 1.06,
        "data_quality_score": 0.95,
        "stress_level": "GREEN",
        "predicted_direction": "UP",
        "directional_bias": "BULLISH",
        "conviction": 3,
        "cot_signal": "BULLISH",
        "vol_signal": "NEUTRAL",
        "oi_signal": "NEUTRAL",
        "rr_signal": None,
        "special_signal_value": 0.0,
        "special_signal_label": None,
        "regime_category": "TREND",
        "model_version": "v2.0",
    }
    defaults.update(overrides)
    return RegimeCall(**defaults)


def test_compare_regime_calls_empty_for_identical_calls() -> None:
    call = _sample_regime_call()
    assert compare_regime_calls(call, call) == ()


def test_compare_regime_calls_reports_field_differences() -> None:
    v1 = _sample_regime_call(confidence=0.72)
    v2 = _sample_regime_call(confidence=0.75)
    diffs = compare_regime_calls(v1, v2)
    assert len(diffs) == 1
    assert diffs[0].field == "confidence"


def test_compare_regime_calls_allows_numeric_tolerance() -> None:
    v1 = _sample_regime_call(confidence=0.721)
    v2 = _sample_regime_call(confidence=0.729)
    assert compare_regime_calls(v1, v2) == ()


def test_compare_regime_calls_handles_missing_call() -> None:
    call = _sample_regime_call()
    diffs = compare_regime_calls(None, call)
    assert len(diffs) == 1
    assert diffs[0].field == "regime_call"


def test_compare_briefs_ignores_whitespace() -> None:
    assert compare_briefs("Line one.\n\nLine two.", "Line one. Line two.") is True


def test_compare_briefs_detects_different_content() -> None:
    assert compare_briefs("Bullish case.", "Bearish case.") is False


def test_compare_desk_cards_ignores_whitespace_in_strings() -> None:
    assert compare_desk_cards(
        {"title": "EURUSD Rally", "score": 3},
        {"title": "EURUSD  Rally", "score": 3},
    )


def test_compare_desk_cards_detects_missing_card() -> None:
    assert compare_desk_cards({"title": "x"}, None) is False


def test_make_comparison_equivalent_when_all_match() -> None:
    call = _sample_regime_call()
    comparison = make_comparison(
        pair="EURUSD",
        as_of=call.date,
        v1_call=call,
        v2_call=call,
        v1_brief="Brief.",
        v2_brief="Brief.",
        v1_desk_card=None,
        v2_desk_card=None,
    )
    assert comparison.equivalent is True
    assert comparison.brief_match is True


def test_make_comparison_not_equivalent_when_brief_differs() -> None:
    call = _sample_regime_call()
    comparison = make_comparison(
        pair="EURUSD",
        as_of=call.date,
        v1_call=call,
        v2_call=call,
        v1_brief="Bullish.",
        v2_brief="Bearish.",
        v1_desk_card=None,
        v2_desk_card=None,
    )
    assert comparison.equivalent is False
    assert comparison.brief_match is False


def test_count_consecutive_equivalent_days_stops_at_first_mismatch() -> None:
    as_of = datetime.date(2026, 5, 20)

    def _result(equivalent: bool) -> ShadowRunResult:
        comparison = make_comparison(
            pair="EURUSD",
            as_of=as_of,
            v1_call=_sample_regime_call(),
            v2_call=_sample_regime_call(),
            v1_brief=None,
            v2_brief=None,
            v1_desk_card=None,
            v2_desk_card=None,
        )
        if not equivalent:
            comparison = make_comparison(
                pair="EURUSD",
                as_of=as_of,
                v1_call=_sample_regime_call(),
                v2_call=_sample_regime_call(confidence=0.99),
                v1_brief=None,
                v2_brief=None,
                v1_desk_card=None,
                v2_desk_card=None,
            )
        return ShadowRunResult(
            date=as_of,
            comparisons={"EURUSD": comparison},
            equivalent=comparison.equivalent,
            v2_outputs={},
        )

    history = [_result(True), _result(True), _result(False), _result(True)]
    assert count_consecutive_equivalent_days(history, "EURUSD") == 1


def test_run_shadow_comparison_runs_v2_and_compares() -> None:
    """Shadow runner executes v2 with shadow ports and compares to v1 outputs."""

    snapshot = _make_multi_pair_snapshot()
    fetcher = FakeFetcherPort(snapshot)

    # First run v2 to obtain shadow outputs that we treat as the v1 baseline.
    baseline_output = asyncio.run(
        run_multi_pair_flow(
            snapshot.date,
            fetcher=fetcher,
            writer=FakeWriterPort(),
            alert=FakeAlertPort(),
            run_validation=False,
        )
    )
    v1_calls = {
        pair: output.regime_call for pair, output in baseline_output.outputs.items()
    }
    v1_briefs = {
        pair: output.brief_markdown for pair, output in baseline_output.outputs.items()
    }

    shadow_writer = FakeWriterPort()
    shadow_alert = FakeAlertPort()
    result = asyncio.run(
        run_shadow_comparison(
            snapshot.date,
            v1_calls=v1_calls,
            v1_briefs=v1_briefs,
            fetcher=fetcher,
            shadow_writer=shadow_writer,
            shadow_alert=shadow_alert,
            run_validation=False,
        )
    )

    assert result.date == snapshot.date
    assert set(result.comparisons.keys()) == {"EURUSD", "USDJPY", "USDINR"}
    assert result.equivalent is True
    # Shadow ports captured v2 side effects but did not touch the live ledger.
    assert len(shadow_writer.regime_calls) == 3
    assert len(shadow_alert.successes) == 3


def test_run_shadow_comparison_detects_v1_v2_divergence() -> None:
    """When v1 baseline differs from v2, the run is flagged non-equivalent."""

    snapshot = _make_multi_pair_snapshot()
    fetcher = FakeFetcherPort(snapshot)

    baseline_output = asyncio.run(
        run_multi_pair_flow(
            snapshot.date,
            fetcher=fetcher,
            writer=FakeWriterPort(),
            alert=FakeAlertPort(),
            run_validation=False,
        )
    )
    v1_calls = {
        pair: output.regime_call for pair, output in baseline_output.outputs.items()
    }
    # Introduce a divergence on EURUSD.
    eurusd_call = v1_calls["EURUSD"]
    v1_calls["EURUSD"] = RegimeCall(
        **{**eurusd_call.__dict__, "confidence": 0.99}
    )

    result = asyncio.run(
        run_shadow_comparison(
            snapshot.date,
            v1_calls=v1_calls,
            v1_briefs={pair: None for pair in v1_calls},
            fetcher=fetcher,
            run_validation=False,
        )
    )

    assert result.equivalent is False
    assert result.comparisons["EURUSD"].equivalent is False
    assert any(d.field == "confidence" for d in result.comparisons["EURUSD"].regime_call_diffs)
    assert result.comparisons["USDJPY"].equivalent is True
    assert result.comparisons["USDINR"].equivalent is True
