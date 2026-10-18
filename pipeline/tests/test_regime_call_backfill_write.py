"""Replay-writer safety tests for ``RegimeCallRepository.bulk_write_backfill_results``.

These tests never touch a real database: the repository's module-level
``_pg_conn`` is patched with a fake connection that records every statement.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.db.repositories.regime_call import RegimeCallRepository
from src.types import RegimeCall, SignalRow

_SIGNALS_INSERT_PREFIX = "INSERT INTO signals"
_REGIME_INSERT_PREFIX = "INSERT INTO regime_calls"
_PROTECTED_SELECT_PREFIX = "SELECT DISTINCT date FROM regime_calls"

# Columns the backfill writer owns on ``signals`` (everything else is
# auxiliary/derived data that must survive a replay re-run).
_SIGNALS_WRITTEN_COLUMNS = {
    "rate_diff_2y",
    "rate_diff_10y",
    "cot_percentile",
    "realized_vol_20d",
    "realized_vol_5d",
    "implied_vol_30d",
    "spot",
    "day_change",
    "day_change_pct",
    "cross_asset_vix",
    "cross_asset_dxy",
    "cross_asset_oil",
    "cross_asset_us10y",
    "cross_asset_gold",
    "cross_asset_copper",
    "cross_asset_stoxx",
    "oi_delta",
    "volume_rvol",
    "structural_instability",
    "breakeven_inflation_10y",
    "rate_diff_10y_real",
    "rate_z_tactical",
    "rate_z_structural",
    "realized_vol_rank",
    "skew_alignment",
}

_SIGNALS_AUX_COLUMNS = (
    "cot_asset_mgr_net",
    "cot_lev_money_net",
    "cot_net_pos",
    "z_blended",
    "bund_btp_spread",
    "fpi_flow",
    "boj_policy_rate",
    "india_vix",
    "inr_forward_premium",
)

# Columns the backfill writer owns on ``regime_calls`` (everything else is
# untouched by the upsert).
_REGIME_WRITTEN_COLUMNS = {
    "regime",
    "confidence",
    "signal_composite",
    "rate_signal",
    "primary_driver",
    "entry_timing",
    "position_size",
    "stop_level",
    "data_quality_score",
    "stress_level",
    "predicted_direction",
    "directional_bias",
    "conviction",
    "cot_signal",
    "vol_signal",
    "oi_signal",
    "rr_signal",
    "special_signal_value",
    "special_signal_label",
    "model_version",
    "strategy_version",
    "data_source",
}


class FakeConn:
    """Records every ``run`` call; scripts protected dates and injected faults."""

    def __init__(
        self,
        protected_dates: list[str | date] | None = None,
        fail_on: tuple[str, ...] = (),
    ) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []
        self.protected_dates = protected_dates if protected_dates is not None else []
        self.fail_on = fail_on
        self.closed = False

    def run(self, sql: str, **params: Any) -> list[tuple[Any, ...]]:
        self.statements.append((sql, params))
        if sql.startswith(_PROTECTED_SELECT_PREFIX):
            return [(d,) for d in self.protected_dates]
        if any(needle in sql for needle in self.fail_on):
            raise RuntimeError("simulated connection failure")
        return []

    def close(self) -> None:
        self.closed = True

    @property
    def sqls(self) -> list[str]:
        return [sql for sql, _ in self.statements]

    def inserts(self, prefix: str) -> list[tuple[str, dict[str, Any]]]:
        return [(sql, p) for sql, p in self.statements if sql.startswith(prefix)]


def _signal(day: date, pair: str = "EURUSD") -> SignalRow:
    return SignalRow(
        pair=pair,
        date=day,
        rate_diff_2y=0.5,
        rate_diff_10y=0.6,
        cot_percentile=55.0,
        realized_vol_20d=8.0,
        realized_vol_5d=7.5,
        implied_vol_30d=9.0,
        spot=1.08,
        day_change=0.001,
        day_change_pct=0.1,
        cross_asset_vix=15.0,
        cross_asset_dxy=100.0,
        cross_asset_oil=70.0,
        cross_asset_us10y=4.2,
        cross_asset_gold=1800.0,
        cross_asset_copper=4.0,
        cross_asset_stoxx=4000.0,
        oi_delta=100,
    )


def _call(
    day: date, pair: str = "EURUSD", model_version: str | None = "2.1-m3"
) -> RegimeCall:
    return RegimeCall(
        pair=pair,
        date=day,
        regime="RANGE",
        confidence=0.5,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
        model_version=model_version,
    )


def _repo() -> RegimeCallRepository:
    return RegimeCallRepository(client_factory=MagicMock())


def _run(fake: FakeConn, rows: list[tuple[SignalRow, RegimeCall]]) -> None:
    with patch("src.db.repositories.regime_call._pg_conn", return_value=fake):
        _repo().bulk_write_backfill_results("EURUSD", rows)


def test_upsert_uses_on_conflict_and_never_deletes() -> None:
    fake = FakeConn()
    day = date(2026, 5, 7)
    _run(fake, [(_signal(day), _call(day))])

    all_sql = " ".join(fake.sqls)
    assert "DELETE FROM signals" not in all_sql
    assert "DELETE FROM regime_calls" not in all_sql

    (signal_sql, signal_params) = fake.inserts(_SIGNALS_INSERT_PREFIX)[0]
    (regime_sql, _) = fake.inserts(_REGIME_INSERT_PREFIX)[0]
    assert "ON CONFLICT (pair, date) DO UPDATE SET" in signal_sql
    assert "ON CONFLICT (pair, date) DO UPDATE SET" in regime_sql
    assert signal_params["r0_pair"] == "EURUSD"
    assert signal_params["r0_date"] == "2026-05-07"
    assert fake.closed


def test_insert_placeholders_match_params_exactly() -> None:
    fake = FakeConn()
    day = date(2026, 5, 7)
    _run(fake, [(_signal(day), _call(day))])

    for prefix, per_row in (
        (_SIGNALS_INSERT_PREFIX, 27),
        (_REGIME_INSERT_PREFIX, 24),
    ):
        (sql, params) = fake.inserts(prefix)[0]
        placeholders = re.findall(r":(\w+)", sql)
        assert len(placeholders) == per_row
        assert set(placeholders) == set(params.keys())


def test_protected_dates_are_skipped_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Mixed str/date inputs emulate pg8000 returning date objects.
    fake = FakeConn(protected_dates=[date(2026, 5, 10), "2026-05-12"])
    rows = [
        (_signal(date(2026, 5, 8)), _call(date(2026, 5, 8))),
        (_signal(date(2026, 5, 10)), _call(date(2026, 5, 10))),
        (_signal(date(2026, 5, 12)), _call(date(2026, 5, 12))),
    ]
    with caplog.at_level(logging.WARNING, logger="src.db.repositories.regime_call"):
        _run(fake, rows)

    (select_sql, select_params) = next(
        (sql, p) for sql, p in fake.statements if sql.startswith(_PROTECTED_SELECT_PREFIX)
    )
    assert "model_version IS NULL OR model_version NOT IN" in select_sql
    assert select_params["pair"] == "EURUSD"
    assert ":mv0" in select_sql
    assert select_params["mv0"] == "2.1-m3"

    insert_params = [p for _, p in fake.inserts("INSERT")]
    assert insert_params, "expected the surviving row to be written"
    written_values = {str(value) for params in insert_params for value in params.values()}
    assert "2026-05-08" in written_values
    assert "2026-05-10" not in written_values
    assert "2026-05-12" not in written_values

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "skipped 2 of 3" in message and "2026-05-10..2026-05-12" in message
        for message in warnings
    )


def test_all_rows_protected_writes_nothing() -> None:
    fake = FakeConn(protected_dates=["2026-05-10"])
    day = date(2026, 5, 10)
    _run(fake, [(_signal(day), _call(day))])

    assert fake.inserts("INSERT") == []
    assert not any("DISABLE" in sql for sql in fake.sqls)
    assert not any("ENABLE" in sql for sql in fake.sqls)
    assert fake.closed


def test_signals_upsert_set_list_contains_only_written_columns() -> None:
    fake = FakeConn()
    day = date(2026, 5, 7)
    _run(fake, [(_signal(day), _call(day))])

    (signal_sql, _) = fake.inserts(_SIGNALS_INSERT_PREFIX)[0]
    set_clause = signal_sql.split("ON CONFLICT (pair, date) DO UPDATE SET", 1)[1]
    updated_columns = {part.split("=")[0].strip() for part in set_clause.split(",")}
    assert updated_columns == _SIGNALS_WRITTEN_COLUMNS

    for aux in _SIGNALS_AUX_COLUMNS:
        assert aux not in signal_sql


def test_regime_upsert_set_list_contains_model_version_and_written_columns() -> None:
    fake = FakeConn()
    day = date(2026, 5, 7)
    _run(fake, [(_signal(day), _call(day))])

    (regime_sql, _) = fake.inserts(_REGIME_INSERT_PREFIX)[0]
    set_clause = regime_sql.split("ON CONFLICT (pair, date) DO UPDATE SET", 1)[1]
    updated_columns = {part.split("=")[0].strip() for part in set_clause.split(",")}
    assert updated_columns == _REGIME_WRITTEN_COLUMNS
    assert "model_version = EXCLUDED.model_version" in regime_sql


def test_triggers_restored_after_success() -> None:
    fake = FakeConn()
    day = date(2026, 5, 7)
    _run(fake, [(_signal(day), _call(day))])

    sqls = fake.sqls
    disabled = [sql for sql in sqls if "DISABLE TRIGGER" in sql]
    enabled = [sql for sql in sqls if "ENABLE TRIGGER" in sql]
    assert disabled == [
        "ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls",
        "ALTER TABLE regime_calls DISABLE TRIGGER trg_log_regime_call_audit",
    ]
    assert enabled == [
        "ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls",
        "ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit",
    ]
    last_write = max(i for i, sql in enumerate(sqls) if sql.startswith("INSERT"))
    first_enable = min(i for i, sql in enumerate(sqls) if "ENABLE TRIGGER" in sql)
    assert first_enable > last_write


def test_triggers_restored_when_conn_raises_mid_write() -> None:
    fake = FakeConn(fail_on=("INSERT INTO regime_calls",))
    day = date(2026, 5, 7)
    with patch("src.db.repositories.regime_call._pg_conn", return_value=fake):
        with pytest.raises(RuntimeError, match="simulated connection failure"):
            _repo().bulk_write_backfill_results("EURUSD", [(_signal(day), _call(day))])

    sqls = fake.sqls
    assert any("DISABLE TRIGGER" in sql for sql in sqls)
    enabled = [sql for sql in sqls if "ENABLE TRIGGER" in sql]
    assert enabled == [
        "ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls",
        "ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit",
    ]
    assert fake.closed


def test_enable_failure_is_logged_and_does_not_mask_original_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeConn(fail_on=("INSERT INTO regime_calls", "ENABLE TRIGGER"))
    day = date(2026, 5, 7)
    with caplog.at_level(logging.WARNING, logger="src.db.repositories.regime_call"):
        with patch("src.db.repositories.regime_call._pg_conn", return_value=fake):
            with pytest.raises(RuntimeError, match="simulated connection failure"):
                _repo().bulk_write_backfill_results(
                    "EURUSD", [(_signal(day), _call(day))]
                )

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("failed to re-enable trigger" in message for message in messages)


def test_empty_results_is_early_noop_without_connection() -> None:
    with patch("src.db.repositories.regime_call._pg_conn") as pg_conn:
        _repo().bulk_write_backfill_results("EURUSD", [])
    pg_conn.assert_not_called()


def test_falsy_model_version_raises_before_connecting() -> None:
    day = date(2026, 5, 7)
    rows = [(_signal(day), _call(day, model_version=None))]
    with patch("src.db.repositories.regime_call._pg_conn") as pg_conn:
        with pytest.raises(ValueError, match="model_version"):
            _repo().bulk_write_backfill_results("EURUSD", rows)
    pg_conn.assert_not_called()


def test_501_rows_split_into_two_batches() -> None:
    fake = FakeConn()
    start = date(2025, 1, 1)
    rows = [
        (_signal(start + timedelta(days=i)), _call(start + timedelta(days=i)))
        for i in range(501)
    ]
    _run(fake, rows)

    signal_inserts = fake.inserts(_SIGNALS_INSERT_PREFIX)
    regime_inserts = fake.inserts(_REGIME_INSERT_PREFIX)
    assert len(signal_inserts) == 2
    assert len(regime_inserts) == 2

    first_batch_pairs = [k for k in signal_inserts[0][1] if k.endswith("_pair")]
    second_batch_pairs = [k for k in signal_inserts[1][1] if k.endswith("_pair")]
    assert len(first_batch_pairs) == 500
    assert len(second_batch_pairs) == 1
