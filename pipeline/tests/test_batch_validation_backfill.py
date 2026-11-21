from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.backfill import batch_validation_backfill as batch
from src.db import writer


def _call(call_id: int = 1) -> dict[str, Any]:
    return {
        "id": call_id,
        "date": "2024-01-02",
        "pair": "EURUSD",
        "regime": "RISK_OFF",
        "predicted_direction": "BEARISH",
        "confidence": 0.8,
    }


def test_batch_builder_uses_shared_call_bound_readers() -> None:
    seen_entries: list[int] = []
    seen_prices: list[tuple[str, date]] = []

    def read_entry(call_id: int) -> dict[str, Any]:
        seen_entries.append(call_id)
        return {"pair": "EURUSD", "date": "2024-01-02", "spot": 1.0}

    def read_price(pair: str, target: date) -> dict[str, Any]:
        seen_prices.append((pair, target))
        return {"pair": pair, "date": target.isoformat(), "close": 0.99}

    rows = batch._build_validation_rows(
        [_call()],
        date(2024, 1, 9),
        read_existing=lambda call_id: None,
        read_entry=read_entry,
        read_price=read_price,
    )

    assert seen_entries == [1]
    assert seen_prices == [("EURUSD", date(2024, 1, 9))]
    assert len(rows) == 1
    assert rows[0]["correct_t5"] is True
    assert rows[0]["entry_price_evidence"]["call_id"] == 1
    assert rows[0]["price_evidence_t5"]["date"] == "2024-01-09"


def test_batch_builder_skips_legacy_call_without_publication_evidence() -> None:
    assert (
        batch._build_validation_rows(
            [_call()],
            date(2024, 1, 9),
            read_existing=lambda call_id: None,
            read_entry=lambda call_id: None,
            read_price=lambda pair, target: pytest.fail("missing entry stops before price read"),
        )
        == []
    )


def test_batch_dry_run_reads_all_three_pair_histories_but_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[tuple[str, int | None]] = []

    def read_calls(pair: str, limit: int | None) -> list[dict[str, Any]]:
        requested.append((pair, limit))
        return []

    monkeypatch.setattr(
        writer,
        "get_historical_regime_calls",
        read_calls,
    )
    monkeypatch.setattr(
        writer,
        "write_validation_row",
        lambda row: pytest.fail("dry run wrote"),
    )

    assert batch.run_batch_backfill(dry_run=True, as_of=date(2024, 1, 9)) == (0, 0)
    assert requested == [("EURUSD", None), ("USDJPY", None), ("USDINR", None)]


def test_exact_map_helper_has_no_nearest_date_fallback() -> None:
    prices = {date(2024, 1, 8): 0.99, date(2024, 1, 10): 1.01}
    assert batch._get_spot(prices, date(2024, 1, 9)) is None
