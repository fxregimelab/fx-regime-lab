"""AD-T03 private desk journal: durable hash-chained events, no production side effects.

The suite proves that the private journal facade in ``src.db.writer`` never
touches the production Supabase client (lazy factory mocked to raise,
service-role env removed), enforces the 26-kind event vocabulary and strict
JSON-scalar payload rules, is idempotent on duplicate event ids, rejects stale
aggregate heads without partial writes, detects chain and head-projection
corruption, blocks raw UPDATE/DELETE and ``INSERT OR REPLACE`` hijacks through
database triggers on any connection (with ``recursive_triggers`` enabled on
module connections as the second line of defense), enforces the
``expected_aggregate_version`` CAS field, cross-checks ``aggregate_heads``
against authoritative events before append, fails typed on malformed stored
payloads instead of leaking ``JSONDecodeError``, routes head read/rebuild
through the writer facade, runs WAL + ``synchronous=FULL``, applies migrations
at most once and fails closed on a newer schema, and leaves the legacy
``paper_desk.sqlite3`` bytes untouched. Every database lives under
``tmp_path``; no network, broker or production client is involved.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from src.db import writer
from src.db.repositories import private_desk
from src.db.repositories.private_desk import (
    ALLOWED_EVENT_KINDS,
    GENESIS,
    AggregateHead,
    DeskEvent,
    PrivateDeskHandle,
)
from src.paper.contracts import ContractError
from src.paper.store import DEFAULT_DB_PATH

HAPPENED = datetime(2026, 10, 18, 9, 30, 15, 250000, tzinfo=UTC)

SPEC_EVENT_KINDS = (
    "spec_loaded",
    "snapshot_archived",
    "candidate_detected",
    "decision_recorded",
    "proposal_rejected",
    "risk_reserved",
    "permit_issued",
    "permit_consumed",
    "order_send_intent",
    "broker_observed",
    "child_state_changed",
    "parent_state_changed",
    "stop_change_intent",
    "stop_change_observed",
    "parent_settled",
    "score_updated",
    "experiment_registered",
    "evaluation_completed",
    "artifact_activated",
    "artifact_revoked",
    "incident_opened",
    "incident_resolved",
    "owner_stop",
    "owner_release",
    "heartbeat",
    "cashflow_observed",
)

# Spec 01 section 6 pins the exact ``events`` column list and order.
SPEC_EVENTS_COLUMNS = (
    "seq",
    "event_id",
    "aggregate_id",
    "expected_aggregate_version",
    "kind",
    "happened_at",
    "recorded_at",
    "canonical_payload",
    "prev_hash",
    "row_hash",
    "actor_id",
)


def _documented_row_hash(
    *,
    prev_hash: str,
    event_id: str,
    aggregate_id: str,
    kind: str,
    actor_id: str,
    happened_at: str,
    recorded_at: str,
    canonical_payload: str,
) -> str:
    """Independently recompute the module's documented row-hash content tuple.

    Kept separate from ``private_desk._compute_row_hash`` so the test pins the
    documented scheme (field order, JSON separators, SHA-256) rather than
    echoing whatever the module happens to compute.
    """
    material = json.dumps(
        [
            prev_hash,
            event_id,
            aggregate_id,
            kind,
            actor_id,
            happened_at,
            recorded_at,
            canonical_payload,
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _db_path(tmp_path: Path) -> Path:
    return tmp_path / "runtime.sqlite3"


def _raw_event(**overrides: object) -> DeskEvent:
    """Construct a DeskEvent from raw fields (tests may pass invalid values)."""
    base: dict[str, object] = {
        "event_id": str(uuid.uuid4()),
        "aggregate_id": "parent-1",
        "kind": "heartbeat",
        "actor_id": "watchdog",
        "happened_at": HAPPENED,
        "payload": {"note": "ok"},
    }
    base.update(overrides)
    factory = cast(Callable[..., DeskEvent], DeskEvent)
    return factory(**base)


def _event(
    *,
    event_id: str | None = None,
    aggregate_id: str = "parent-1",
    kind: str = "heartbeat",
    actor_id: str = "watchdog",
    happened_at: datetime = HAPPENED,
    payload: Mapping[str, object] | None = None,
    expected_aggregate_version: int | None = None,
) -> DeskEvent:
    return DeskEvent(
        event_id=event_id if event_id is not None else str(uuid.uuid4()),
        aggregate_id=aggregate_id,
        kind=kind,
        actor_id=actor_id,
        happened_at=happened_at,
        payload={"note": "ok"} if payload is None else payload,
        expected_aggregate_version=expected_aggregate_version,
    )


def _head(handle: PrivateDeskHandle, aggregate_id: str) -> AggregateHead | None:
    return writer.read_aggregate_head(handle, aggregate_id)


def _event_count(handle: PrivateDeskHandle) -> int:
    row = handle.connection.execute("SELECT COUNT(*) FROM events").fetchone()
    assert row is not None
    return int(row[0])


def test_private_journal_never_touches_production_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _explode() -> None:
        raise AssertionError("production Supabase client must not be created")

    monkeypatch.setattr(writer, "_client", _explode)
    handle = writer.open_private_desk(_db_path(tmp_path))
    stored = writer.append_desk_event(handle, _event(), GENESIS)
    assert stored.seq == 1
    assert [event.event_id for event in writer.read_desk_events(handle)] == [stored.event_id]
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)
    writer.close_private_desk(handle)


def test_private_journal_works_without_service_role_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    handle = writer.open_private_desk(_db_path(tmp_path))
    first = writer.append_desk_event(handle, _event(), GENESIS)
    second = writer.append_desk_event(handle, _event(aggregate_id="parent-2"), GENESIS)
    assert (first.seq, second.seq) == (1, 2)
    assert len(writer.read_desk_events(handle)) == 2
    writer.close_private_desk(handle)


def test_fresh_journal_verifies_and_has_no_heads(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    writer.verify_desk_chain(handle)
    assert writer.read_desk_events(handle) == ()
    assert _head(handle, "parent-1") is None
    writer.close_private_desk(handle)


def test_duplicate_event_id_identical_retry_returns_original(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    event = _event()
    first = writer.append_desk_event(handle, event, GENESIS)
    again = writer.append_desk_event(handle, event, GENESIS)
    assert again == first
    assert again.seq == first.seq
    assert again.row_hash == first.row_hash
    assert _event_count(handle) == 1
    assert _head(handle, "parent-1") == AggregateHead("parent-1", 1, first.seq, first.row_hash)
    writer.close_private_desk(handle)


def test_duplicate_event_id_changed_payload_conflict(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    event = _event()
    first = writer.append_desk_event(handle, event, GENESIS)
    changed_payload = _event(event_id=event.event_id, payload={"note": "changed"})
    with pytest.raises(ContractError) as payload_exc:
        writer.append_desk_event(handle, changed_payload, GENESIS)
    assert payload_exc.value.code == "CONFLICT"
    changed_time = _event(event_id=event.event_id, happened_at=HAPPENED.replace(hour=10))
    with pytest.raises(ContractError) as time_exc:
        writer.append_desk_event(handle, changed_time, GENESIS)
    assert time_exc.value.code == "CONFLICT"
    changed_actor = _event(event_id=event.event_id, actor_id="supervisor")
    with pytest.raises(ContractError) as actor_exc:
        writer.append_desk_event(handle, changed_actor, GENESIS)
    assert actor_exc.value.code == "CONFLICT"
    assert _event_count(handle) == 1
    assert _head(handle, "parent-1") == AggregateHead("parent-1", 1, first.seq, first.row_hash)
    writer.close_private_desk(handle)


def test_head_mismatch_conflict_no_partial_write(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    first = writer.append_desk_event(handle, _event(), GENESIS)
    stale = _event(aggregate_id="parent-1")
    with pytest.raises(ContractError) as exc:
        writer.append_desk_event(handle, stale, GENESIS)
    assert exc.value.code == "CONFLICT"
    assert _event_count(handle) == 1
    assert _head(handle, "parent-1") == AggregateHead("parent-1", 1, first.seq, first.row_hash)
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)


def test_new_aggregate_requires_genesis_head(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    with pytest.raises(ContractError) as exc:
        writer.append_desk_event(handle, _event(), "0" * 64)
    assert exc.value.code == "CONFLICT"
    with pytest.raises(ContractError) as fmt_exc:
        writer.append_desk_event(handle, _event(), "not-a-head")
    assert fmt_exc.value.code == "INVALID_SCHEMA"
    assert _event_count(handle) == 0
    writer.close_private_desk(handle)


def test_corrupted_event_row_hash_detected_and_not_repaired_by_rebuild(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    legit = writer.append_desk_event(handle, _event(), GENESIS)
    handle.connection.execute(
        "INSERT INTO events (event_id, aggregate_id, kind, actor_id, happened_at,"
        " recorded_at, canonical_payload, prev_hash, row_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            "parent-1",
            "heartbeat",
            "watchdog",
            "2026-10-18T10:00:00Z",
            "2026-10-18T10:00:00Z",
            '{"note":"forged"}',
            legit.row_hash,
            "0" * 64,
        ),
    )
    with pytest.raises(ContractError) as exc:
        writer.verify_desk_chain(handle)
    assert exc.value.code == "HASH_MISMATCH"
    writer.rebuild_heads(handle)
    with pytest.raises(ContractError) as still_exc:
        writer.verify_desk_chain(handle)
    assert still_exc.value.code == "HASH_MISMATCH"
    writer.close_private_desk(handle)
    with pytest.raises(ContractError) as open_exc:
        writer.open_private_desk(_db_path(tmp_path))
    assert open_exc.value.code == "HASH_MISMATCH"


def test_corrupted_head_projection_repaired_by_rebuild(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    stored = writer.append_desk_event(handle, _event(), GENESIS)
    handle.connection.execute(
        "UPDATE aggregate_heads SET last_hash = ?, version = 99 WHERE aggregate_id = ?",
        ("f" * 64, "parent-1"),
    )
    handle.connection.execute(
        "INSERT INTO aggregate_heads (aggregate_id, version, last_seq, last_hash)"
        " VALUES (?, ?, ?, ?)",
        ("ghost", 1, 999, "e" * 64),
    )
    with pytest.raises(ContractError) as exc:
        writer.verify_desk_chain(handle)
    assert exc.value.code == "HASH_MISMATCH"
    writer.rebuild_heads(handle)
    writer.verify_desk_chain(handle)
    assert _head(handle, "parent-1") == AggregateHead("parent-1", 1, stored.seq, stored.row_hash)
    assert _head(handle, "ghost") is None
    handle.connection.execute("DELETE FROM aggregate_heads WHERE aggregate_id = ?", ("parent-1",))
    with pytest.raises(ContractError) as missing_exc:
        writer.verify_desk_chain(handle)
    assert missing_exc.value.code == "HASH_MISMATCH"
    writer.rebuild_heads(handle)
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)


def test_illegal_event_kind_rejected() -> None:
    with pytest.raises(ContractError) as exc:
        _event(kind="order_approved")
    assert exc.value.code == "INVALID_SCHEMA"
    with pytest.raises(ContractError) as case_exc:
        _event(kind="Heartbeat")
    assert case_exc.value.code == "INVALID_SCHEMA"
    with pytest.raises(ContractError) as type_exc:
        _raw_event(kind=7)
    assert type_exc.value.code == "INVALID_SCHEMA"


def test_non_json_scalar_payloads_rejected() -> None:
    bad_values: tuple[object, ...] = (
        1.5,
        float("nan"),
        float("inf"),
        Decimal("1.5"),
        b"bytes",
        ("tuple",),
        {"nested": {"list": [1.5]}},
        {"when": datetime(2026, 10, 18, tzinfo=UTC)},
    )
    for bad in bad_values:
        with pytest.raises(ContractError) as exc:
            _raw_event(payload={"value": bad})
        assert exc.value.code == "INVALID_SCHEMA", bad
    with pytest.raises(ContractError) as top_exc:
        _raw_event(payload=[1, 2])
    assert top_exc.value.code == "INVALID_SCHEMA"
    with pytest.raises(ContractError) as key_exc:
        _raw_event(payload={"": 1})
    assert key_exc.value.code == "INVALID_SCHEMA"
    with pytest.raises(ContractError) as int_key_exc:
        _raw_event(payload={7: "x"})
    assert int_key_exc.value.code == "INVALID_SCHEMA"


def test_canonical_payload_bytes_sorted_compact_utf8() -> None:
    assert private_desk.canonical_payload_bytes({"b": 1, "a": "x"}) == b'{"a":"x","b":1}'
    assert private_desk.canonical_payload_bytes({"t": "caf\u00e9"}) == '{"t":"caf\u00e9"}'.encode()
    with pytest.raises(ContractError) as exc:
        private_desk.canonical_payload_bytes({"x": 1.5})
    assert exc.value.code == "INVALID_SCHEMA"


def test_append_only_triggers_block_update_and_delete(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    stored = writer.append_desk_event(handle, _event(), GENESIS)
    with pytest.raises(sqlite3.IntegrityError) as update_exc:
        handle.connection.execute(
            "UPDATE events SET kind = 'score_updated' WHERE seq = ?", (stored.seq,)
        )
    assert "append-only" in str(update_exc.value)
    with pytest.raises(sqlite3.IntegrityError) as delete_exc:
        handle.connection.execute("DELETE FROM events WHERE seq = ?", (stored.seq,))
    assert "append-only" in str(delete_exc.value)
    events = writer.read_desk_events(handle)
    assert len(events) == 1
    assert events[0].kind == "heartbeat"
    writer.close_private_desk(handle)


def test_wal_and_synchronous_full(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    mode_row = handle.connection.execute("PRAGMA journal_mode").fetchone()
    sync_row = handle.connection.execute("PRAGMA synchronous").fetchone()
    assert mode_row is not None and sync_row is not None
    assert str(mode_row[0]).lower() == "wal"
    assert int(sync_row[0]) == 2
    writer.close_private_desk(handle)
    reopened = writer.open_private_desk(_db_path(tmp_path))
    mode_row2 = reopened.connection.execute("PRAGMA journal_mode").fetchone()
    sync_row2 = reopened.connection.execute("PRAGMA synchronous").fetchone()
    assert mode_row2 is not None and sync_row2 is not None
    assert str(mode_row2[0]).lower() == "wal"
    assert int(sync_row2[0]) == 2
    writer.close_private_desk(reopened)


def test_migrations_apply_exactly_once_and_events_survive_reopen(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    first = writer.open_private_desk(db)
    stored = writer.append_desk_event(first, _event(), GENESIS)
    writer.close_private_desk(first)
    second = writer.open_private_desk(db)
    rows = second.connection.execute(
        "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert [(int(row[0]), str(row[1])) for row in rows] == [
        (1, "001_runtime.sql"),
        (2, "002_control.sql"),
    ]
    assert str(rows[0][2])
    events = writer.read_desk_events(second)
    assert [event.row_hash for event in events] == [stored.row_hash]
    writer.close_private_desk(second)


def test_newer_applied_schema_fails_closed(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    connection = sqlite3.connect(str(db))
    try:
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY,"
            " name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO schema_migrations (version, name, applied_at)"
            " VALUES (2, '002_future.sql', '2030-01-01T00:00:00Z')"
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ContractError) as exc:
        writer.open_private_desk(db)
    assert exc.value.code == "JOURNAL_UNAVAILABLE"


def test_chain_linkage_per_aggregate(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    a1 = writer.append_desk_event(handle, _event(aggregate_id="parent-1"), GENESIS)
    b1 = writer.append_desk_event(handle, _event(aggregate_id="parent-2"), GENESIS)
    a2 = writer.append_desk_event(handle, _event(aggregate_id="parent-1"), a1.row_hash)
    assert (a1.seq, b1.seq, a2.seq) == (1, 2, 3)
    assert a1.prev_hash == GENESIS
    assert b1.prev_hash == GENESIS
    assert a2.prev_hash == a1.row_hash
    assert _head(handle, "parent-1") == AggregateHead("parent-1", 2, a2.seq, a2.row_hash)
    assert _head(handle, "parent-2") == AggregateHead("parent-2", 1, b1.seq, b1.row_hash)
    assert _head(handle, "parent-3") is None
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)


def test_invalid_ids_actors_heads_and_timestamps_rejected() -> None:
    cases: tuple[dict[str, object], ...] = (
        {"aggregate_id": ""},
        {"aggregate_id": "   "},
        {"actor_id": ""},
        {"actor_id": "\t "},
        {"event_id": str(uuid.uuid4()).upper()},
        {"event_id": "not-a-uuid"},
        {"event_id": "550e8400-e29b-41d4-a716-44665544000"},
        {"happened_at": datetime(2026, 10, 18, 9, 0, 0)},
        {"happened_at": HAPPENED.astimezone(timezone(timedelta(hours=2)))},
    )
    for overrides in cases:
        with pytest.raises(ContractError) as exc:
            _raw_event(**overrides)
        assert exc.value.code == "INVALID_SCHEMA", overrides


def test_read_filters_by_after_seq_and_aggregate(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    a1 = writer.append_desk_event(handle, _event(aggregate_id="parent-1"), GENESIS)
    b1 = writer.append_desk_event(handle, _event(aggregate_id="parent-2"), GENESIS)
    a2 = writer.append_desk_event(handle, _event(aggregate_id="parent-1"), a1.row_hash)
    assert [event.seq for event in writer.read_desk_events(handle)] == [a1.seq, b1.seq, a2.seq]
    assert [event.seq for event in writer.read_desk_events(handle, after_seq=b1.seq)] == [a2.seq]
    assert [
        event.seq for event in writer.read_desk_events(handle, aggregate_id="parent-1")
    ] == [a1.seq, a2.seq]
    assert [
        event.seq
        for event in writer.read_desk_events(handle, after_seq=a1.seq, aggregate_id="parent-1")
    ] == [a2.seq]
    with pytest.raises(ContractError) as exc:
        writer.read_desk_events(handle, after_seq=-1)
    assert exc.value.code == "INVALID_SCHEMA"
    writer.close_private_desk(handle)


def test_stored_event_roundtrip_datetimes_and_payload(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    payload: dict[str, object] = {
        "pair": "EURUSD",
        "risk": "0.050000",
        "nested": {"levels": [1, "2", None, True], "label": "caf\u00e9"},
    }
    stored = writer.append_desk_event(handle, _event(payload=payload), GENESIS)
    assert stored.happened_at == HAPPENED
    assert stored.recorded_at.utcoffset() == timedelta(0)
    assert stored.payload == payload
    row = handle.connection.execute(
        "SELECT happened_at, recorded_at, canonical_payload FROM events WHERE seq = ?",
        (stored.seq,),
    ).fetchone()
    assert row is not None
    assert str(row[0]) == "2026-10-18T09:30:15.250000Z"
    assert str(row[1]).endswith("Z")
    assert str(row[2]) == private_desk.canonical_payload_bytes(payload).decode("utf-8")
    writer.close_private_desk(handle)


def test_closed_handle_operations_raise_journal_unavailable(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    writer.close_private_desk(handle)
    writer.close_private_desk(handle)
    assert handle.closed
    with pytest.raises(ContractError) as append_exc:
        writer.append_desk_event(handle, _event(), GENESIS)
    assert append_exc.value.code == "JOURNAL_UNAVAILABLE"
    with pytest.raises(ContractError) as read_exc:
        writer.read_desk_events(handle)
    assert read_exc.value.code == "JOURNAL_UNAVAILABLE"
    with pytest.raises(ContractError) as verify_exc:
        writer.verify_desk_chain(handle)
    assert verify_exc.value.code == "JOURNAL_UNAVAILABLE"


def test_legacy_paper_desk_db_bytes_unchanged(tmp_path: Path) -> None:
    existed = DEFAULT_DB_PATH.exists()
    before = hashlib.sha256(DEFAULT_DB_PATH.read_bytes()).hexdigest() if existed else None
    handle = writer.open_private_desk(_db_path(tmp_path))
    writer.append_desk_event(handle, _event(), GENESIS)
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)
    if before is None:
        assert not DEFAULT_DB_PATH.exists()
    else:
        assert hashlib.sha256(DEFAULT_DB_PATH.read_bytes()).hexdigest() == before


def test_event_vocabulary_is_exactly_the_spec_list() -> None:
    assert len(SPEC_EVENT_KINDS) == 26
    assert ALLOWED_EVENT_KINDS == frozenset(SPEC_EVENT_KINDS)


# ---------------------------------------------------------------------------
# HIGH-1: INSERT OR REPLACE cannot rewrite or fork the append-only events table.


def test_module_connections_enable_recursive_triggers(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    row = handle.connection.execute("PRAGMA recursive_triggers").fetchone()
    assert row is not None and int(row[0]) == 1
    writer.close_private_desk(handle)
    reopened = writer.open_private_desk(_db_path(tmp_path))
    row2 = reopened.connection.execute("PRAGMA recursive_triggers").fetchone()
    assert row2 is not None and int(row2[0]) == 1
    writer.close_private_desk(reopened)


def test_insert_or_replace_hijack_aborted_on_raw_connection(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    handle = writer.open_private_desk(db)
    stored = writer.append_desk_event(handle, _event(), GENESIS)
    writer.close_private_desk(handle)

    raw = sqlite3.connect(str(db))
    try:
        row = raw.execute("PRAGMA recursive_triggers").fetchone()
        assert row is not None and int(row[0]) == 0  # guard must not rely on the pragma
        with pytest.raises(sqlite3.IntegrityError) as id_exc:
            raw.execute(
                "INSERT OR REPLACE INTO events (event_id, aggregate_id, kind, actor_id,"
                " happened_at, recorded_at, canonical_payload, prev_hash, row_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    stored.event_id,
                    "parent-1",
                    "heartbeat",
                    "attacker",
                    "2026-10-18T10:00:00Z",
                    "2026-10-18T10:00:00Z",
                    '{"note":"hijack"}',
                    GENESIS,
                    "0" * 64,
                ),
            )
        assert "append-only" in str(id_exc.value)
        with pytest.raises(sqlite3.IntegrityError) as seq_exc:
            raw.execute(
                "INSERT OR REPLACE INTO events (seq, event_id, aggregate_id, kind, actor_id,"
                " happened_at, recorded_at, canonical_payload, prev_hash, row_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    stored.seq,
                    str(uuid.uuid4()),
                    "parent-1",
                    "heartbeat",
                    "attacker",
                    "2026-10-18T10:00:00Z",
                    "2026-10-18T10:00:00Z",
                    '{"note":"hijack"}',
                    GENESIS,
                    "0" * 64,
                ),
            )
        assert "append-only" in str(seq_exc.value)
        rows = raw.execute(
            "SELECT seq, event_id, row_hash, canonical_payload, actor_id FROM events"
        ).fetchall()
        assert rows == [(stored.seq, stored.event_id, stored.row_hash, '{"note":"ok"}', "watchdog")]
    finally:
        raw.close()


# ---------------------------------------------------------------------------
# HIGH-2: expected_aggregate_version column, validation and CAS semantics.


def test_events_table_columns_pin_spec_section_6(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    rows = handle.connection.execute("PRAGMA table_info(events)").fetchall()
    assert tuple(str(row["name"]) for row in rows) == SPEC_EVENTS_COLUMNS
    by_name = {str(row["name"]): row for row in rows}
    assert int(by_name["expected_aggregate_version"]["notnull"]) == 0
    writer.close_private_desk(handle)


def test_expected_aggregate_version_roundtrip_and_conflict(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    first = writer.append_desk_event(handle, _event(expected_aggregate_version=0), GENESIS)
    assert first.expected_aggregate_version == 0
    second = writer.append_desk_event(
        handle, _event(expected_aggregate_version=1), first.row_hash
    )
    assert second.expected_aggregate_version == 1
    assert [event.expected_aggregate_version for event in writer.read_desk_events(handle)] == [0, 1]
    count_before = _event_count(handle)
    head_before = _head(handle, "parent-1")
    with pytest.raises(ContractError) as exc:
        writer.append_desk_event(
            handle, _event(expected_aggregate_version=1), second.row_hash
        )
    assert exc.value.code == "CONFLICT"
    assert _event_count(handle) == count_before
    assert _head(handle, "parent-1") == head_before
    writer.close_private_desk(handle)


def test_expected_aggregate_version_none_accepted_and_invalid_rejected(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    stored = writer.append_desk_event(handle, _event(), GENESIS)
    assert stored.expected_aggregate_version is None
    row = handle.connection.execute(
        "SELECT expected_aggregate_version FROM events WHERE seq = ?", (stored.seq,)
    ).fetchone()
    assert row is not None and row[0] is None
    assert writer.read_desk_events(handle)[0].expected_aggregate_version is None
    writer.close_private_desk(handle)
    for bad in (True, False, -1, "0", 1.5, 2.0):
        with pytest.raises(ContractError) as exc:
            _raw_event(expected_aggregate_version=bad)
        assert exc.value.code == "INVALID_SCHEMA", bad


def test_expected_aggregate_version_not_part_of_retry_identity(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    event = _event(expected_aggregate_version=0)
    first = writer.append_desk_event(handle, event, GENESIS)
    retry = writer.append_desk_event(
        handle, _event(event_id=event.event_id, expected_aggregate_version=7), GENESIS
    )
    assert retry == first
    assert retry.expected_aggregate_version == 0
    assert _event_count(handle) == 1
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# HIGH-3: head read/rebuild are reachable through the writer facade only.


def test_writer_facade_delegates_head_read_and_rebuild(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    stored = writer.append_desk_event(handle, _event(), GENESIS)
    assert writer.read_aggregate_head(handle, "parent-1") == AggregateHead(
        "parent-1", 1, stored.seq, stored.row_hash
    )
    assert writer.read_aggregate_head(handle, "parent-2") is None
    handle.connection.execute("DELETE FROM aggregate_heads WHERE aggregate_id = ?", ("parent-1",))
    assert writer.read_aggregate_head(handle, "parent-1") is None
    writer.rebuild_heads(handle)
    assert writer.read_aggregate_head(handle, "parent-1") == AggregateHead(
        "parent-1", 1, stored.seq, stored.row_hash
    )
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# LOW-4: append cross-checks aggregate_heads against authoritative events.


def test_missing_heads_row_aborts_append_hash_mismatch(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    first = writer.append_desk_event(handle, _event(), GENESIS)
    handle.connection.execute("DELETE FROM aggregate_heads WHERE aggregate_id = ?", ("parent-1",))
    with pytest.raises(ContractError) as exc:
        writer.append_desk_event(handle, _event(), GENESIS)
    assert exc.value.code == "HASH_MISMATCH"
    assert _event_count(handle) == 1
    assert [event.seq for event in writer.read_desk_events(handle)] == [first.seq]
    writer.rebuild_heads(handle)
    writer.verify_desk_chain(handle)
    second = writer.append_desk_event(handle, _event(), first.row_hash)
    assert second.seq == 2
    writer.close_private_desk(handle)


def test_heads_row_without_events_aborts_append(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    handle.connection.execute(
        "INSERT INTO aggregate_heads (aggregate_id, version, last_seq, last_hash)"
        " VALUES (?, 1, 7, ?)",
        ("parent-1", "a" * 64),
    )
    with pytest.raises(ContractError) as exc:
        writer.append_desk_event(handle, _event(), GENESIS)
    assert exc.value.code == "HASH_MISMATCH"
    assert _event_count(handle) == 0
    writer.close_private_desk(handle)


def test_corrupted_heads_projection_aborts_append(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    first = writer.append_desk_event(handle, _event(), GENESIS)
    handle.connection.execute(
        "UPDATE aggregate_heads SET last_hash = ? WHERE aggregate_id = ?",
        ("f" * 64, "parent-1"),
    )
    with pytest.raises(ContractError) as hash_exc:
        writer.append_desk_event(handle, _event(), first.row_hash)
    assert hash_exc.value.code == "HASH_MISMATCH"
    handle.connection.execute(
        "UPDATE aggregate_heads SET last_hash = ?, last_seq = ? WHERE aggregate_id = ?",
        (first.row_hash, first.seq + 5, "parent-1"),
    )
    with pytest.raises(ContractError) as seq_exc:
        writer.append_desk_event(handle, _event(), first.row_hash)
    assert seq_exc.value.code == "HASH_MISMATCH"
    assert _event_count(handle) == 1
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# LOW-5: malformed stored payloads fail typed instead of leaking JSONDecodeError.


def test_malformed_stored_payload_fails_verify_and_read(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    event_id = str(uuid.uuid4())
    happened = "2026-10-18T09:30:15.250000Z"
    recorded = "2026-10-18T09:30:15.250000Z"
    broken_payload = "{not json"
    row_hash = _documented_row_hash(
        prev_hash=GENESIS,
        event_id=event_id,
        aggregate_id="parent-1",
        kind="heartbeat",
        actor_id="watchdog",
        happened_at=happened,
        recorded_at=recorded,
        canonical_payload=broken_payload,
    )
    handle.connection.execute(
        "INSERT INTO events (event_id, aggregate_id, kind, actor_id, happened_at,"
        " recorded_at, canonical_payload, prev_hash, row_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event_id,
            "parent-1",
            "heartbeat",
            "watchdog",
            happened,
            recorded,
            broken_payload,
            GENESIS,
            row_hash,
        ),
    )
    with pytest.raises(ContractError) as verify_exc:
        writer.verify_desk_chain(handle)
    assert verify_exc.value.code == "HASH_MISMATCH"
    with pytest.raises(ContractError) as read_exc:
        writer.read_desk_events(handle)
    assert read_exc.value.code == "HASH_MISMATCH"
    assert not isinstance(read_exc.value, json.JSONDecodeError)
    writer.close_private_desk(handle)
