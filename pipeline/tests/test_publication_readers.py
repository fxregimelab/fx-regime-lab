"""Current publication readers must be versioned, causal, and evidence-bound."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai import client as ai_client
from src.db import writer
from src.scheduler import orchestrator


class _Query:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.filters: list[tuple[str, str, Any]] = []
        self.orders: list[tuple[str, bool]] = []
        self.window: tuple[int, int] | None = None
        self.single = False

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, column: str, value: Any) -> _Query:
        self.filters.append(("eq", column, value))
        return self

    def lt(self, column: str, value: Any) -> _Query:
        self.filters.append(("lt", column, value))
        return self

    def lte(self, column: str, value: Any) -> _Query:
        self.filters.append(("lte", column, value))
        return self

    def order(self, column: str, *, desc: bool = False) -> _Query:
        self.orders.append((column, desc))
        return self

    def range(self, start: int, end: int) -> _Query:
        self.window = (start, end)
        return self

    def limit(self, size: int) -> _Query:
        self.window = (0, size - 1)
        return self

    def maybe_single(self) -> _Query:
        self.single = True
        return self

    def execute(self) -> SimpleNamespace:
        rows = list(self.rows)
        for op, column, expected in self.filters:
            if op == "eq":
                rows = [row for row in rows if row.get(column) == expected]
            elif op == "lt":
                rows = [
                    row
                    for row in rows
                    if row.get(column) is not None and str(row[column]) < str(expected)
                ]
            else:
                rows = [
                    row
                    for row in rows
                    if row.get(column) is not None and str(row[column]) <= str(expected)
                ]
        for column, desc in reversed(self.orders):
            rows.sort(key=lambda row: row[column], reverse=desc)
        if self.window is not None:
            start, end = self.window
            rows = rows[start : end + 1]
        return SimpleNamespace(data=(rows[0] if rows else None) if self.single else rows)


class _Client:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables
        self.queries: list[tuple[str, _Query]] = []

    def table(self, name: str) -> _Query:
        query = _Query(self.tables.get(name, []))
        self.queries.append((name, query))
        return query


def _install_client(
    monkeypatch: pytest.MonkeyPatch, tables: dict[str, list[dict[str, Any]]]
) -> _Client:
    client = _Client(tables)
    monkeypatch.setattr(writer, "_client", lambda: client)
    return client


def _call(
    call_id: int,
    call_date: str,
    *,
    pair: str = "EURUSD",
    source: str = "live",
    strategy: str = "v2",
    created_at: str | None = "2026-09-25T12:00:00+00:00",
) -> dict[str, Any]:
    return {
        "id": call_id,
        "pair": pair,
        "date": call_date,
        "regime": f"R{call_id}",
        "data_source": source,
        "strategy_version": strategy,
        "model_version": f"m{call_id}",
        "created_at": created_at,
    }


def test_current_call_excludes_future_and_wrong_provenance_and_selects_highest_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        _call(10, "2026-09-25"),
        _call(12, "2026-09-25"),
        _call(99, "2026-09-25", source="backtest"),
        _call(98, "2026-09-25", source="legacy"),
        _call(97, "2026-09-25", strategy="v1"),
        _call(96, "2026-09-25", pair="USDJPY"),
        _call(100, "2026-09-27"),
    ]
    _install_client(monkeypatch, {"regime_calls": rows})

    selected = writer.get_current_live_regime_call("EURUSD", as_of="2026-09-26")

    assert selected is not None and selected["id"] == 12


def test_legacy_latest_wrapper_delegates_to_safe_utc_today(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = MagicMock(return_value={"id": 12})
    monkeypatch.setattr(writer, "get_current_live_regime_call", current)

    assert writer.get_latest_regime_call("EURUSD") == {"id": 12}
    assert current.call_args.args == ("EURUSD",)
    assert current.call_args.kwargs["as_of"] == datetime.now(UTC).date()


def test_history_paginates_raw_versions_before_session_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    busy_session = [_call(call_id, "2026-09-26") for call_id in range(1, 1006)]
    rows = [*busy_session, _call(2000, "2026-09-25"), _call(3000, "2026-09-24")]
    client = _install_client(monkeypatch, {"regime_calls": rows})

    selected = writer.get_current_live_regime_history(
        "EURUSD", as_of=date(2026, 9, 26), session_limit=3
    )

    assert [(row["date"], row["id"]) for row in selected] == [
        ("2026-09-26", 1005),
        ("2026-09-25", 2000),
        ("2026-09-24", 3000),
    ]
    query = client.queries[0][1]
    assert query.window == (1000, 1999)


def test_prior_selection_requires_earlier_session_and_prior_publication_availability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        _call(1, "2026-09-24", created_at="2026-09-24T12:00:00+00:00"),
        _call(2, "2026-09-24", created_at="2026-09-26T01:00:00+00:00"),
        _call(3, "2026-09-25", created_at="2026-09-25T10:00:00+00:00"),
        _call(4, "2026-09-23", created_at=None),
    ]
    _install_client(monkeypatch, {"regime_calls": rows})

    selected = writer.get_current_live_regime_call(
        "EURUSD",
        as_of="2026-09-25",
        strictly_before=True,
        published_before=datetime(2026, 9, 25, tzinfo=UTC),
    )

    assert selected is not None and selected["id"] == 1


def test_availability_cutoff_rejects_naive_datetime(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_client(monkeypatch, {"regime_calls": []})
    with pytest.raises(ValueError, match="explicit timezone"):
        writer.get_current_live_regime_call(
            "EURUSD",
            as_of="2026-09-25",
            published_before=datetime(2026, 9, 25),
        )


@pytest.mark.parametrize("invalid", ["2026-09-25garbage", "2026-09-25T00:00:00+00:00"])
def test_invalid_calendar_cutoff_fails_before_io(
    invalid: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", client)
    with pytest.raises(ValueError, match="calendar date"):
        writer.get_current_live_regime_call("EURUSD", as_of=invalid)
    client.assert_not_called()


def test_invalid_reader_response_is_not_reported_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = MagicMock()
    for method in ("select", "eq", "lt", "lte", "order", "range"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=None)
    client = MagicMock()
    client.table.return_value = query
    monkeypatch.setattr(writer, "_client", lambda: client)

    with pytest.raises(RuntimeError, match="invalid response"):
        writer.get_current_live_regime_call("EURUSD", as_of="2026-09-25")


def test_regime_age_uses_causal_prior_history_and_counts_current_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = MagicMock(
        return_value=[
            {"date": "2026-09-24", "regime": "RALLY"},
            {"date": "2026-09-23", "regime": "RALLY"},
            {"date": "2026-09-22", "regime": "RANGE"},
        ]
    )
    monkeypatch.setattr(writer, "get_current_live_regime_history", history)

    assert orchestrator.get_regime_age("EURUSD", "RALLY", as_of=date(2026, 9, 25)) == 3
    kwargs = history.call_args.kwargs
    assert kwargs["strictly_before"] is True
    assert kwargs["published_before"] == datetime(2026, 9, 25, tzinfo=UTC)


def test_exact_publication_signal_never_uses_newer_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_client(
        monkeypatch,
        {
            "publication_evidence": [
                {"call_id": 7, "signal_payload": {"pair": "EURUSD", "spot": 1.07}},
                {"call_id": 8, "signal_payload": {"pair": "EURUSD", "spot": 1.08}},
            ],
            "signals": [{"pair": "EURUSD", "spot": 9.99}],
        },
    )

    assert writer.get_publication_signal_for_call(7) == {"pair": "EURUSD", "spot": 1.07}
    assert [name for name, _query in client.queries] == ["publication_evidence"]
    assert writer.get_publication_signal_for_call(99) is None


def test_desk_card_uses_selected_call_evidence_and_skips_ai_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = AsyncMock(
        return_value=json.dumps(
            {"bias_summary": "RALLY", "catalyst_driver": "RATES", "squeeze_risk": "LOW"}
        )
    )
    monkeypatch.setattr(ai_client, "_call_preferred_model_async", model)
    monkeypatch.setattr(writer, "get_latest_research_memo_thesis_bullets", lambda: [])
    snapshots = {
        7: {
            "pair": "EURUSD",
            "date": "2026-09-25",
            "rate_z_tactical": 1.25,
            "rate_z_structural": 0.5,
            "z_blended": 0.95,
        }
    }
    monkeypatch.setattr(writer, "get_publication_signal_for_call", snapshots.get)

    asyncio.run(
        ai_client.generate_desk_card_brief_async(
            call_id=7,
            pair="EURUSD",
            regime="RALLY",
            date_str="2026-09-25",
            primary_driver="rates",
            pain_index=40.0,
        )
    )
    assert model.await_args is not None
    prompt = model.await_args.kwargs["messages"][0]["content"]
    assert "RATE_Z_TACTICAL_MAD:1.25" in prompt

    unavailable, grounded = asyncio.run(
        ai_client.generate_desk_card_brief_async(
            call_id=8,
            pair="EURUSD",
            regime="RALLY",
            date_str="2026-09-25",
            primary_driver="rates",
            pain_index=40.0,
        )
    )
    assert "ORIGINAL PUBLICATION INPUTS UNAVAILABLE" in unavailable
    assert grounded is False
    assert model.await_count == 1


def test_pair_brief_binds_selected_call_id_and_does_not_read_mutable_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_ids = {"EURUSD": 7, "USDJPY": 8, "USDINR": 9}
    monkeypatch.setattr(orchestrator, "PAIRS", tuple(call_ids))
    monkeypatch.setattr(
        writer,
        "get_current_live_regime_call",
        lambda pair, *, as_of: {
            "id": call_ids[pair],
            "pair": pair,
            "date": "2026-09-25",
            "regime": "RALLY",
            "confidence": 0.7,
            "signal_composite": 0.2,
            "primary_driver": "rates",
        },
    )
    monkeypatch.setattr(
        writer,
        "get_publication_signal_for_call",
        lambda call_id: {
            "pair": next(pair for pair, expected in call_ids.items() if expected == call_id),
            "date": "2026-09-25",
            "spot": 1.07,
        },
    )
    mutable = MagicMock(side_effect=AssertionError("mutable projection must not be read"))
    monkeypatch.setattr(writer, "get_signal_for_pair_date", mutable)
    writes = MagicMock()
    monkeypatch.setattr(writer, "write_brief", writes)
    generate = MagicMock(return_value="bound brief")
    monkeypatch.setattr(ai_client, "generate_brief", generate)

    contexts = orchestrator._upsert_pair_briefs_for_date("2026-09-25", "")

    assert contexts == ["bound brief", "bound brief", "bound brief"]
    assert all(call.kwargs["signal_row"].spot == 1.07 for call in generate.call_args_list)
    mutable.assert_not_called()


def test_validation_history_api_remains_complete_and_unfiltered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        _call(1, "2026-09-24", source="backtest"),
        _call(2, "2026-09-25", strategy="v1"),
    ]
    client = _install_client(monkeypatch, {"regime_calls": rows})

    returned = writer.get_historical_regime_calls("EURUSD", limit=None)

    assert [row["id"] for row in returned] == [1, 2]
    filters = client.queries[0][1].filters
    assert ("eq", "data_source", "live") not in filters
    assert ("eq", "strategy_version", "v2") not in filters


def test_exact_validation_price_never_uses_an_earlier_or_other_pair_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"pair": "EURUSD", "date": "2026-09-24", "close": 1.1},
        {"pair": "USDJPY", "date": "2026-09-25", "close": 150.0},
    ]
    client = _install_client(monkeypatch, {"historical_prices": rows})
    assert writer.get_exact_historical_price_for_date("EURUSD", "2026-09-25") is None
    assert len(client.queries) == 1
    assert client.queries[0][1].filters == [
        ("eq", "pair", "EURUSD"), ("eq", "date", "2026-09-25")
    ]
    rows.append({"pair": "EURUSD", "date": "2026-09-25", "close": 1.2})
    found = writer.get_exact_historical_price_for_date("EURUSD", "2026-09-25")
    assert found == rows[-1] and found is not rows[-1]


@pytest.mark.parametrize("pair,day", [
    ("GBPUSD", "2026-09-25"), ("EURUSD", "20260925"),
    ("EURUSD", "2026-09-25T12:00:00Z"), ("EURUSD", "2026-02-30"),
])
def test_exact_validation_price_rejects_ambiguous_identity_before_io(
    monkeypatch: pytest.MonkeyPatch, pair: str, day: str,
) -> None:
    client = _install_client(monkeypatch, {})
    with pytest.raises(ValueError):
        writer.get_exact_historical_price_for_date(pair, day)
    assert not client.queries


def test_exact_validation_price_rejects_malformed_response_and_propagates_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value = query
    query.maybe_single.return_value = query
    monkeypatch.setattr(writer, "_client", lambda: client)
    for response in [None, SimpleNamespace(data=[]), SimpleNamespace(data={
        "pair": "USDJPY", "date": "2026-09-25", "close": 150.0,
    })]:
        query.execute.return_value = response
        with pytest.raises((ValueError, RuntimeError)):
            writer.get_exact_historical_price_for_date("EURUSD", "2026-09-25")
    query.execute.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        writer.get_exact_historical_price_for_date("EURUSD", "2026-09-25")
