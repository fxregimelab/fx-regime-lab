"""AD-T04 private desk control state: durable leases, fencing and reservations.

The suite proves the 002_control migration half-applies safely (a failing
second statement rolls back its first table and the journal fails closed),
that a lease held by one writer excludes another writer through the real
SQLite file (CONFLICT, no writes) and mints a monotonically increasing
fencing token on takeover, that stale fencing tokens are rejected for renew /
assert / release paths, that a possibly-sent reservation is NEVER auto-released
by TTL expiry without explicit no-send proof, that committed control intent
survives ``os._exit`` without a close while uncommitted intent is rolled back
(real SQLite subprocess crash), that module connections set ``busy_timeout``
and map database locks to ``JOURNAL_UNAVAILABLE`` without swallowing other
sqlite errors, and that every new mutation is reachable only through the
``src.db.writer`` facade (lazy production client mocked to raise). Every
database lives under ``tmp_path``; no network, broker or production client is
involved.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from src.db import writer
from src.db.repositories.private_desk import (
    GENESIS,
    DeskEvent,
    Lease,
    PrivateDeskHandle,
    Reservation,
)
from src.paper.contracts import ContractError

PIPELINE_DIR = Path(__file__).resolve().parents[1]
_LEXICAL_DIGEST = "a" * 64
_MAX_FENCING_TOKEN = 2**63 - 1

_CRASH_COMMIT_SCRIPT = """
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.db.repositories import private_desk
from src.db.repositories.private_desk import DeskEvent, GENESIS

handle = private_desk.open_private_desk(Path(sys.argv[1]))
private_desk.append_desk_event(
    handle,
    DeskEvent(
        event_id=str(uuid.uuid4()),
        aggregate_id="parent-crash",
        kind="heartbeat",
        actor_id="watchdog",
        happened_at=datetime.now(UTC),
        payload={"note": "durable"},
    ),
    GENESIS,
)
private_desk.create_reservation(
    handle,
    reservation_id=str(uuid.uuid4()),
    parent_id=str(uuid.uuid4()),
    amount_usd=Decimal("12.3400"),
    plan_digest="a" * 64,
    expires_at=datetime.now(UTC) + timedelta(minutes=5),
    owner_fencing_token=1,
)
os._exit(0)
"""

_CRASH_UNCOMMITTED_SCRIPT = """
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.db.repositories import private_desk

handle = private_desk.open_private_desk(Path(sys.argv[1]))
connection = handle.connection
connection.execute("BEGIN IMMEDIATE")
connection.execute(
    "INSERT INTO events (event_id, aggregate_id, kind, actor_id, happened_at,"
    " recorded_at, canonical_payload, prev_hash, row_hash)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (
        str(uuid.uuid4()),
        "parent-crash",
        "heartbeat",
        "watchdog",
        datetime.now(UTC).isoformat(),
        datetime.now(UTC).isoformat(),
        '{"note":"uncommitted"}',
        "GENESIS",
        "0" * 64,
    ),
)
os._exit(0)
"""


def _db_path(tmp_path: Path) -> Path:
    return tmp_path / "runtime.sqlite3"


def _run_crash_script(script: str, db: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", script, str(db)],
        cwd=str(PIPELINE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def _timestamp_text(value: datetime) -> str:
    if value.microsecond:
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    return value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _future(seconds: float = 300.0) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


def _expire_lease(handle: PrivateDeskHandle, name: str) -> None:
    handle.connection.execute(
        "UPDATE writer_leases SET expires_at = ? WHERE lease_name = ?",
        (_timestamp_text(datetime.now(UTC) - timedelta(seconds=5)), name),
    )


def _expire_reservation(handle: PrivateDeskHandle, reservation_id: str) -> None:
    handle.connection.execute(
        "UPDATE reservations SET expires_at = ? WHERE reservation_id = ?",
        (_timestamp_text(datetime.now(UTC) - timedelta(seconds=5)), reservation_id),
    )


def _reservation(
    handle: PrivateDeskHandle,
    *,
    reservation_id: str | None = None,
    parent_id: str | None = None,
    amount_usd: Decimal = Decimal("10.00"),
    plan_digest: str = _LEXICAL_DIGEST,
    expires_at: datetime | None = None,
    owner_fencing_token: int = 1,
) -> Reservation:
    return writer.create_reservation(
        handle,
        reservation_id=reservation_id if reservation_id is not None else str(uuid.uuid4()),
        parent_id=parent_id if parent_id is not None else str(uuid.uuid4()),
        amount_usd=amount_usd,
        plan_digest=plan_digest,
        expires_at=expires_at if expires_at is not None else _future(),
        owner_fencing_token=owner_fencing_token,
    )


def _event() -> DeskEvent:
    return DeskEvent(
        event_id=str(uuid.uuid4()),
        aggregate_id="parent-1",
        kind="heartbeat",
        actor_id="watchdog",
        happened_at=datetime.now(UTC),
        payload={"note": "ok"},
    )


# ---------------------------------------------------------------------------
# Packet case 1: two writers both acquire authority through the real file.


def test_two_writers_conflict_then_release_allows_fenced_takeover(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    handle_a = writer.open_private_desk(db)
    handle_b = writer.open_private_desk(db)
    lease_a = writer.acquire_lease(handle_a, "terminal-write", "process-a", 60)
    assert isinstance(lease_a, Lease)
    assert (lease_a.owner_id, lease_a.fencing_token, lease_a.state) == (
        "process-a",
        1,
        "held",
    )
    with pytest.raises(ContractError) as exc:
        writer.acquire_lease(handle_b, "terminal-write", "process-b", 60)
    assert exc.value.code == "CONFLICT"
    unchanged = writer.acquire_lease(handle_a, "terminal-write", "process-a", 60)
    assert unchanged == lease_a
    writer.release_lease(handle_a, "terminal-write", "process-a", lease_a.fencing_token)
    lease_b = writer.acquire_lease(handle_b, "terminal-write", "process-b", 60)
    assert lease_b.owner_id == "process-b"
    assert lease_b.fencing_token == lease_a.fencing_token + 1
    assert lease_b.acquired_at >= lease_a.acquired_at
    writer.close_private_desk(handle_a)
    writer.close_private_desk(handle_b)


# ---------------------------------------------------------------------------
# Packet case 2: stale fencing tokens are rejected on every authority path.


def test_stale_fencing_token_rejected_after_takeover(tmp_path: Path) -> None:
    handle_a = writer.open_private_desk(_db_path(tmp_path))
    handle_b = writer.open_private_desk(_db_path(tmp_path))
    lease_a = writer.acquire_lease(handle_a, "terminal-write", "process-a", 60)
    stale_token = lease_a.fencing_token
    _expire_lease(handle_a, "terminal-write")
    lease_b = writer.acquire_lease(handle_b, "terminal-write", "process-b", 60)
    assert lease_b.fencing_token == stale_token + 1
    reservation = _reservation(handle_b, owner_fencing_token=lease_b.fencing_token)
    calls: list[Callable[[], object]] = [
        lambda: writer.renew_lease(handle_a, "terminal-write", "process-a", stale_token, 60),
        lambda: writer.assert_fence(handle_a, "terminal-write", "process-a", stale_token),
        lambda: writer.release_lease(handle_a, "terminal-write", "process-a", stale_token),
        lambda: writer.release_reservation(
            handle_a, reservation.reservation_id, stale_token, proof_no_send=True
        ),
    ]
    for call in calls:
        with pytest.raises(ContractError) as exc:
            call()
        assert exc.value.code == "FENCE_STALE"
    stored = writer.read_reservation(handle_b, reservation.reservation_id)
    assert stored is not None and stored.status == "reserved"
    writer.close_private_desk(handle_a)
    writer.close_private_desk(handle_b)


# ---------------------------------------------------------------------------
# Packet case 3: a half-applied migration fails closed and rolls back.


def test_migration_half_apply_rolls_back_and_reopens_clean(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    shipped_001 = PIPELINE_DIR / "src" / "paper" / "migrations" / "001_runtime.sql"
    valid = shipped_001.read_text(encoding="utf-8")
    (migrations_dir / "001_valid.sql").write_text(valid, encoding="utf-8")
    (migrations_dir / "002_partial.sql").write_text(
        "CREATE TABLE probe_b (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE probe_c (id INTEGER PRIMARY KEY, );\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractError) as exc:
        writer.open_private_desk(db, migrations_dir=migrations_dir)
    assert exc.value.code == "JOURNAL_UNAVAILABLE"
    raw = sqlite3.connect(str(db))
    try:
        names = {
            str(row[0])
            for row in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        applied = raw.execute("SELECT version, name FROM schema_migrations ORDER BY version")
        applied_rows = [(int(row[0]), str(row[1])) for row in applied.fetchall()]
    finally:
        raw.close()
    assert "events" in names
    assert "probe_b" not in names
    assert applied_rows == [(1, "001_valid.sql")]
    (migrations_dir / "002_partial.sql").unlink()
    handle = writer.open_private_desk(db, migrations_dir=migrations_dir)
    rows = handle.connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert [int(row[0]) for row in rows] == [1]
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Packet case 4: TTL expiry NEVER auto-releases a possibly-sent reservation.


def test_expired_possible_send_reservation_not_auto_released(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    lease = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    reservation = _reservation(handle, owner_fencing_token=lease.fencing_token)
    marked = writer.mark_broker_pending(handle, reservation.reservation_id, lease.fencing_token)
    assert marked.broker_pending is True
    _expire_reservation(handle, reservation.reservation_id)
    with pytest.raises(ContractError) as exc:
        writer.release_reservation(
            handle, reservation.reservation_id, lease.fencing_token, proof_no_send=False
        )
    assert exc.value.code == "ORDER_UNKNOWN"
    stored = writer.read_reservation(handle, reservation.reservation_id)
    assert stored is not None
    assert stored.status == "reserved"
    assert stored.broker_pending is True
    assert stored.released_at is None
    released = writer.release_reservation(
        handle, reservation.reservation_id, lease.fencing_token, proof_no_send=True
    )
    assert released.status == "released"
    assert released.broker_pending is True
    assert released.released_at is not None
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Packet case 5: real-SQLite subprocess crash, no close, no graceful shutdown.


def test_crash_without_close_keeps_committed_event_and_reservation(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    _run_crash_script(_CRASH_COMMIT_SCRIPT, db)
    handle = writer.open_private_desk(db)
    events = writer.read_desk_events(handle)
    assert len(events) == 1
    assert events[0].aggregate_id == "parent-crash"
    assert events[0].payload == {"note": "durable"}
    rows = handle.connection.execute(
        "SELECT amount_usd, typeof(amount_usd), status, broker_pending FROM reservations"
    ).fetchall()
    assert [(str(row[0]), str(row[1]), str(row[2]), int(row[3])) for row in rows] == [
        ("12.34", "text", "reserved", 0)
    ]
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)


def test_crash_rolls_back_uncommitted_event(tmp_path: Path) -> None:
    db = _db_path(tmp_path)
    _run_crash_script(_CRASH_UNCOMMITTED_SCRIPT, db)
    handle = writer.open_private_desk(db)
    assert writer.read_desk_events(handle) == ()
    count = handle.connection.execute("SELECT COUNT(*) FROM events").fetchone()
    assert count is not None and int(count[0]) == 0
    writer.verify_desk_chain(handle)
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Lease lifecycle details.


def test_lease_renew_extends_expiry(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    lease = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    renewed = writer.renew_lease(handle, "terminal-write", "process-a", lease.fencing_token, 600)
    assert renewed.fencing_token == lease.fencing_token
    assert renewed.owner_id == lease.owner_id
    assert renewed.state == "held"
    assert renewed.expires_at > lease.expires_at
    assert renewed.renewed_at >= lease.renewed_at
    with pytest.raises(ContractError) as exc:
        writer.renew_lease(handle, "terminal-write", "process-a", lease.fencing_token + 1, 60)
    assert exc.value.code == "FENCE_STALE"
    _expire_lease(handle, "terminal-write")
    with pytest.raises(ContractError) as expired_exc:
        writer.renew_lease(handle, "terminal-write", "process-a", lease.fencing_token, 60)
    assert expired_exc.value.code == "FENCE_STALE"
    writer.close_private_desk(handle)


def test_same_owner_reacquire_is_idempotent_while_unexpired(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    lease = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    again = writer.acquire_lease(handle, "terminal-write", "process-a", 600)
    assert again == lease
    rows = handle.connection.execute("SELECT COUNT(*) FROM writer_leases").fetchone()
    assert rows is not None and int(rows[0]) == 1
    writer.close_private_desk(handle)


def test_release_lease_then_acquire_keeps_monotonic_token(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    first = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    writer.release_lease(handle, "terminal-write", "process-a", first.fencing_token)
    row = handle.connection.execute(
        "SELECT state FROM writer_leases WHERE lease_name = ?", ("terminal-write",)
    ).fetchone()
    assert row is not None and str(row[0]) == "released"
    with pytest.raises(ContractError) as repeat_exc:
        writer.release_lease(handle, "terminal-write", "process-a", first.fencing_token)
    assert repeat_exc.value.code == "FENCE_STALE"
    second = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    assert second.fencing_token == first.fencing_token + 1
    assert second.state == "held"
    writer.close_private_desk(handle)


def test_assert_fence_requires_live_matching_lease(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    lease = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    writer.assert_fence(handle, "terminal-write", "process-a", lease.fencing_token)
    for args in (
        ("process-b", lease.fencing_token),
        ("process-a", lease.fencing_token + 1),
    ):
        with pytest.raises(ContractError) as exc:
            writer.assert_fence(handle, "terminal-write", args[0], args[1])
        assert exc.value.code == "FENCE_STALE"
    with pytest.raises(ContractError) as unknown_exc:
        writer.assert_fence(handle, "other-lease", "process-a", lease.fencing_token)
    assert unknown_exc.value.code == "FENCE_STALE"
    _expire_lease(handle, "terminal-write")
    with pytest.raises(ContractError) as expired_exc:
        writer.assert_fence(handle, "terminal-write", "process-a", lease.fencing_token)
    assert expired_exc.value.code == "FENCE_STALE"
    writer.close_private_desk(handle)


def test_acquire_lease_validates_arguments(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    # The cast lets the test smuggle runtime-invalid argument types past mypy.
    raw_acquire = cast(Callable[..., Lease], writer.acquire_lease)
    bad_calls: list[Callable[[], object]] = [
        lambda: raw_acquire(handle, "", "process-a", 60),
        lambda: raw_acquire(handle, "terminal-write", "  ", 60),
        lambda: raw_acquire(handle, "terminal-write", "process-a", 0),
        lambda: raw_acquire(handle, "terminal-write", "process-a", -5),
        lambda: raw_acquire(handle, "terminal-write", "process-a", True),
        lambda: raw_acquire(handle, "terminal-write", "process-a", 60.0),
        lambda: raw_acquire(handle, "terminal-write", "process-a", "60"),
    ]
    for call in bad_calls:
        with pytest.raises(ContractError) as exc:
            call()
        assert exc.value.code == "INVALID_SCHEMA"
    rows = handle.connection.execute("SELECT COUNT(*) FROM writer_leases").fetchone()
    assert rows is not None and int(rows[0]) == 0
    writer.close_private_desk(handle)


def test_fencing_token_overflow_guard_fails_closed(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    handle.connection.execute(
        "UPDATE writer_leases SET fencing_token = ?, expires_at = ? WHERE lease_name = ?",
        (_MAX_FENCING_TOKEN, _timestamp_text(datetime.now(UTC) - timedelta(seconds=5)),
         "terminal-write"),
    )
    with pytest.raises(ContractError) as exc:
        writer.acquire_lease(handle, "terminal-write", "process-b", 60)
    assert exc.value.code == "JOURNAL_UNAVAILABLE"
    stored = handle.connection.execute(
        "SELECT fencing_token, owner_id FROM writer_leases WHERE lease_name = ?",
        ("terminal-write",),
    ).fetchone()
    assert stored is not None
    assert (int(stored[0]), str(stored[1])) == (_MAX_FENCING_TOKEN, "process-a")
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Reservation idempotency and conflict rules.


def test_reservation_duplicate_parent_identical_returns_stored(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    parent_id = str(uuid.uuid4())
    first = _reservation(
        handle, parent_id=parent_id, amount_usd=Decimal("25.50"), expires_at=_future(60)
    )
    retry = _reservation(
        handle, parent_id=parent_id, amount_usd=Decimal("25.5000"), expires_at=_future(600)
    )
    assert retry == first
    assert retry.amount_usd == Decimal("25.50")
    count = handle.connection.execute("SELECT COUNT(*) FROM reservations").fetchone()
    assert count is not None and int(count[0]) == 1
    writer.close_private_desk(handle)


def test_reservation_conflict_on_changed_amount_or_digest(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    parent_id = str(uuid.uuid4())
    reservation = _reservation(handle, parent_id=parent_id, amount_usd=Decimal("25.50"))
    with pytest.raises(ContractError) as amount_exc:
        _reservation(handle, parent_id=parent_id, amount_usd=Decimal("25.51"))
    assert amount_exc.value.code == "CONFLICT"
    with pytest.raises(ContractError) as digest_exc:
        _reservation(handle, parent_id=parent_id, plan_digest="b" * 64)
    assert digest_exc.value.code == "CONFLICT"
    with pytest.raises(ContractError) as id_exc:
        _reservation(handle, reservation_id=reservation.reservation_id)
    assert id_exc.value.code == "CONFLICT"
    stored = writer.read_reservation(handle, reservation.reservation_id)
    assert stored is not None and stored.amount_usd == Decimal("25.50")
    assert stored.plan_digest == _LEXICAL_DIGEST
    count = handle.connection.execute("SELECT COUNT(*) FROM reservations").fetchone()
    assert count is not None and int(count[0]) == 1
    writer.close_private_desk(handle)


def test_create_reservation_validates_amounts_ids_and_digest(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    base: dict[str, object] = {
        "reservation_id": str(uuid.uuid4()),
        "parent_id": str(uuid.uuid4()),
        "amount_usd": Decimal("10.00"),
        "plan_digest": _LEXICAL_DIGEST,
        "expires_at": _future(),
        "owner_fencing_token": 1,
    }
    factory = cast(Callable[..., Reservation], writer.create_reservation)
    bad_amounts: tuple[object, ...] = (
        Decimal("0"),
        Decimal("-1.00"),
        Decimal("NaN"),
        Decimal("Infinity"),
        10.0,
        10,
        "10.00",
    )
    for bad in bad_amounts:
        overrides = dict(base, amount_usd=bad)
        with pytest.raises(ContractError) as exc:
            factory(handle, **overrides)
        assert exc.value.code == "INVALID_NUMBER", bad
    bad_calls: list[dict[str, object]] = [
        dict(base, reservation_id=str(uuid.uuid4()).upper()),
        dict(base, reservation_id="not-a-uuid"),
        dict(base, parent_id="parent-1"),
        dict(base, plan_digest="A" * 64),
        dict(base, plan_digest="abc"),
        dict(base, owner_fencing_token=0),
        dict(base, owner_fencing_token=True),
    ]
    for overrides in bad_calls:
        with pytest.raises(ContractError) as exc:
            factory(handle, **overrides)
        assert exc.value.code == "INVALID_SCHEMA", overrides
    count = handle.connection.execute("SELECT COUNT(*) FROM reservations").fetchone()
    assert count is not None and int(count[0]) == 0
    writer.close_private_desk(handle)


def test_create_reservation_rejects_naive_or_past_expiry(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    naive = datetime(2030, 1, 1, 12, 0, 0)
    non_utc = datetime.now(timezone(timedelta(hours=2))) + timedelta(hours=1)
    past = datetime.now(UTC) - timedelta(seconds=1)
    for expires_at in (naive, non_utc, past):
        with pytest.raises(ContractError) as exc:
            _reservation(handle, expires_at=expires_at)
        assert exc.value.code == "INVALID_SCHEMA", expires_at
    count = handle.connection.execute("SELECT COUNT(*) FROM reservations").fetchone()
    assert count is not None and int(count[0]) == 0
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Reservation state transitions.


def test_mark_broker_pending_unknown_and_fence_rules(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    with pytest.raises(ContractError) as unknown_exc:
        writer.mark_broker_pending(handle, str(uuid.uuid4()), 1)
    assert unknown_exc.value.code == "ORDER_UNKNOWN"
    reservation = _reservation(handle, owner_fencing_token=7)
    with pytest.raises(ContractError) as fence_exc:
        writer.mark_broker_pending(handle, reservation.reservation_id, 8)
    assert fence_exc.value.code == "FENCE_STALE"
    stored = writer.read_reservation(handle, reservation.reservation_id)
    assert stored is not None and stored.broker_pending is False
    marked = writer.mark_broker_pending(handle, reservation.reservation_id, 7)
    assert marked.broker_pending is True
    again = writer.mark_broker_pending(handle, reservation.reservation_id, 7)
    assert again.broker_pending is True
    writer.release_reservation(handle, reservation.reservation_id, 7, proof_no_send=True)
    with pytest.raises(ContractError) as released_exc:
        writer.mark_broker_pending(handle, reservation.reservation_id, 7)
    assert released_exc.value.code == "STALE_STATE"
    writer.close_private_desk(handle)


def test_release_reservation_rules_and_token_check(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    with pytest.raises(ContractError) as unknown_exc:
        writer.release_reservation(handle, str(uuid.uuid4()), 1, proof_no_send=True)
    assert unknown_exc.value.code == "ORDER_UNKNOWN"
    reservation = _reservation(handle, owner_fencing_token=3)
    with pytest.raises(ContractError) as fence_exc:
        writer.release_reservation(handle, reservation.reservation_id, 4, proof_no_send=True)
    assert fence_exc.value.code == "FENCE_STALE"
    released = writer.release_reservation(
        handle, reservation.reservation_id, 3, proof_no_send=True
    )
    assert released.status == "released"
    assert released.released_at is not None
    retry = writer.release_reservation(handle, reservation.reservation_id, 3, proof_no_send=True)
    assert retry == released
    writer.close_private_desk(handle)


def test_reservation_decimal_string_round_trip(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    reservation = _reservation(handle, amount_usd=Decimal("12.3400"))
    assert reservation.amount_usd == Decimal("12.34")
    row = handle.connection.execute(
        "SELECT amount_usd, typeof(amount_usd) FROM reservations WHERE reservation_id = ?",
        (reservation.reservation_id,),
    ).fetchone()
    assert row is not None
    assert (str(row[0]), str(row[1])) == ("12.34", "text")
    read_back = writer.read_reservation(handle, reservation.reservation_id)
    assert read_back is not None and read_back.amount_usd == Decimal("12.34")
    unknown = writer.read_reservation(handle, str(uuid.uuid4()))
    assert unknown is None
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Connection settings, lock mapping and migrations on the shipped schema.


def test_busy_timeout_is_5000ms_on_module_connections(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    row = handle.connection.execute("PRAGMA busy_timeout").fetchone()
    assert row is not None and int(row[0]) == 5000
    writer.close_private_desk(handle)
    reopened = writer.open_private_desk(_db_path(tmp_path))
    row2 = reopened.connection.execute("PRAGMA busy_timeout").fetchone()
    assert row2 is not None and int(row2[0]) == 5000
    writer.close_private_desk(reopened)


def test_database_lock_maps_to_journal_unavailable_but_other_errors_propagate(
    tmp_path: Path,
) -> None:
    db = _db_path(tmp_path)
    handle = writer.open_private_desk(db)
    handle.connection.execute("PRAGMA busy_timeout=50")
    blocker = sqlite3.connect(str(db), isolation_level=None)
    try:
        blocker.execute("BEGIN IMMEDIATE")
        with pytest.raises(ContractError) as exc:
            writer.acquire_lease(handle, "terminal-write", "process-a", 60)
        assert exc.value.code == "JOURNAL_UNAVAILABLE"
        assert "locked" in exc.value.detail
        blocker.execute("ROLLBACK")
    finally:
        blocker.close()
    handle.connection.execute("DROP TABLE writer_leases")
    with pytest.raises(sqlite3.OperationalError) as raw_exc:
        writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    assert not isinstance(raw_exc.value, ContractError)
    assert "no such table" in str(raw_exc.value)
    writer.close_private_desk(handle)


def test_wal_and_synchronous_full_survive_control_migration(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    mode_row = handle.connection.execute("PRAGMA journal_mode").fetchone()
    sync_row = handle.connection.execute("PRAGMA synchronous").fetchone()
    assert mode_row is not None and str(mode_row[0]).lower() == "wal"
    assert sync_row is not None and int(sync_row[0]) == 2
    writer.close_private_desk(handle)


def test_control_migration_applied_and_rebuild_heads_replay(tmp_path: Path) -> None:
    handle = writer.open_private_desk(_db_path(tmp_path))
    rows = handle.connection.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert [(int(row[0]), str(row[1])) for row in rows] == [
        (1, "001_runtime.sql"),
        (2, "002_control.sql"),
    ]
    lease_columns = handle.connection.execute("PRAGMA table_info(writer_leases)").fetchall()
    assert tuple(str(row["name"]) for row in lease_columns) == (
        "lease_name",
        "owner_id",
        "fencing_token",
        "acquired_at",
        "renewed_at",
        "expires_at",
        "state",
    )
    reservation_columns = handle.connection.execute("PRAGMA table_info(reservations)").fetchall()
    assert tuple(str(row["name"]) for row in reservation_columns) == (
        "reservation_id",
        "parent_id",
        "status",
        "amount_usd",
        "plan_digest",
        "expires_at",
        "broker_pending",
        "owner_fencing_token",
        "last_event_seq",
        "created_at",
        "released_at",
    )
    first = writer.append_desk_event(handle, _event(), GENESIS)
    handle.connection.execute("DELETE FROM aggregate_heads")
    writer.rebuild_heads(handle)
    writer.verify_desk_chain(handle)
    head = writer.read_aggregate_head(handle, "parent-1")
    assert head is not None and head.last_hash == first.row_hash
    writer.close_private_desk(handle)


# ---------------------------------------------------------------------------
# Facade rule: every control mutation is reachable only through writer.py.


def test_writer_facade_control_delegates_never_touch_production_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _explode() -> None:
        raise AssertionError("production Supabase client must not be created")

    monkeypatch.setattr(writer, "_client", _explode)
    handle = writer.open_private_desk(_db_path(tmp_path))
    lease = writer.acquire_lease(handle, "terminal-write", "process-a", 60)
    renewed = writer.renew_lease(handle, "terminal-write", "process-a", lease.fencing_token, 120)
    assert renewed.expires_at > lease.expires_at
    writer.assert_fence(handle, "terminal-write", "process-a", lease.fencing_token)
    reservation = _reservation(handle, owner_fencing_token=lease.fencing_token)
    writer.mark_broker_pending(handle, reservation.reservation_id, lease.fencing_token)
    released = writer.release_reservation(
        handle, reservation.reservation_id, lease.fencing_token, proof_no_send=True
    )
    assert isinstance(released, Reservation) and released.status == "released"
    assert (
        writer.read_reservation(handle, reservation.reservation_id) == released
    )
    writer.release_lease(handle, "terminal-write", "process-a", lease.fencing_token)
    writer.close_private_desk(handle)
    with pytest.raises(ContractError) as closed_exc:
        writer.read_reservation(handle, reservation.reservation_id)
    assert closed_exc.value.code == "JOURNAL_UNAVAILABLE"
