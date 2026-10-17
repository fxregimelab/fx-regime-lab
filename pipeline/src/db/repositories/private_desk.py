"""Private runtime desk journal (SQLite) — append-only hash-chained events.

AD-T03 private storage. All mutation entry points are exposed through the
``src.db.writer`` facade; this repository never imports or calls the production
Supabase client path and requires no service-role environment.

Storage
    Migrations ship as ``src/paper/migrations/*.sql`` applied in numeric
    filename order and tracked in ``schema_migrations``; each migration runs
    inside one explicit ``BEGIN IMMEDIATE`` transaction with WAL journaling and
    ``synchronous=FULL``. A database whose applied versions are not exactly the
    shipped prefix (including any newer/unknown version) fails closed.

Integrity
    Events are chain-linked per aggregate: the first event of an aggregate uses
    the ``GENESIS`` sentinel, later events use the previous event's
    ``row_hash``. ``row_hash`` covers prev_hash, event_id, aggregate_id, kind,
    actor_id, happened_at, recorded_at and the payload's canonical JSON text —
    never ``seq`` (assigned by the insert). ``aggregate_heads`` is a rebuildable
    projection (version, last_seq, last_hash).

Reason codes (from ``src.paper.contracts``)
    ``INVALID_SCHEMA``
        Unknown event kind, non-JSON payload value (float/Decimal/NaN/bytes/
        tuple), malformed id/timestamp/expected_head, malformed migration file
        names, invalid read arguments.
    ``CONFLICT``
        Duplicate ``event_id`` whose content differs, or ``expected_head`` not
        matching the current aggregate head (nothing is written).
    ``HASH_MISMATCH``
        Chain corruption: row hash recomputation, per-aggregate prev linkage,
        seq gaps, ``aggregate_heads`` projection mismatch — or non-canonical
        stored row content in read paths.
    ``JOURNAL_UNAVAILABLE``
        Applied schema not a prefix of the shipped migrations (fail closed),
        operations on a closed handle, missing migration directory, or a
        migration that fails to apply.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.paper.contracts import ContractError

GENESIS = "GENESIS"

ALLOWED_EVENT_KINDS: frozenset[str] = frozenset(
    {
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
    }
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "paper" / "migrations"
_MIGRATION_FILENAME_RE = re.compile(r"(\d+)_([A-Za-z0-9_-]+)\.sql")
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z")
_ZERO_OFFSET = timedelta(0)


# ---------------------------------------------------------------------------
# Validation helpers


def _text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string required")
    return value


def _uuid(name: str, value: object) -> str:
    if type(value) is not str or _UUID_RE.fullmatch(value) is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: lowercase UUID string required")
    return value


def _utc_timestamp(name: str, value: object) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: timezone-aware datetime required")
    if value.utcoffset() != _ZERO_OFFSET:
        raise ContractError("INVALID_SCHEMA", f"{name}: only UTC datetimes are accepted")
    return value


def _format_timestamp(value: datetime) -> str:
    if value.microsecond:
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    return value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _parse_timestamp(name: str, value: object) -> datetime:
    if type(value) is not str or _TIMESTAMP_RE.fullmatch(value) is None:
        raise ContractError("HASH_MISMATCH", f"{name}: stored timestamp is not canonical UTC text")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ContractError(
            "HASH_MISMATCH", f"{name}: stored timestamp {value!r} is unparsable"
        ) from None


def _normalize_json(name: str, value: object) -> object:
    """Deep-copy/validate a JSON value: scalars, dicts and lists only, no floats."""
    if value is None or type(value) is bool or type(value) is str or type(value) is int:
        return value
    if type(value) is float:
        raise ContractError(
            "INVALID_SCHEMA", f"{name}: binary floats are not allowed; use decimal strings"
        )
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str or not key.strip():
                raise ContractError("INVALID_SCHEMA", f"{name}: non-empty string keys required")
            normalized[key] = _normalize_json(f"{name}.{key}", item)
        return normalized
    if type(value) is list:
        return [_normalize_json(f"{name}[{index}]", item) for index, item in enumerate(value)]
    raise ContractError(
        "INVALID_SCHEMA",
        f"{name}: JSON scalars, dicts and lists only; got {type(value).__name__}",
    )


def _normalized_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise ContractError("INVALID_SCHEMA", "payload: JSON object (mapping) required")
    normalized: dict[str, object] = {}
    for key, item in payload.items():
        if type(key) is not str or not key.strip():
            raise ContractError("INVALID_SCHEMA", "payload: non-empty string keys required")
        normalized[key] = _normalize_json(f"payload.{key}", item)
    return normalized


def canonical_payload_bytes(payload: Mapping[str, object]) -> bytes:
    """Deterministic UTF-8 compact JSON of a desk payload: sorted keys, no floats."""
    normalized = _normalized_payload(payload)
    text = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


# ---------------------------------------------------------------------------
# Records


@dataclass(frozen=True)
class DeskEvent:
    """One private journal event submitted for append; validated at construction."""

    event_id: str
    aggregate_id: str
    kind: str
    actor_id: str
    happened_at: datetime
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        _validate_event_fields(self)
        object.__setattr__(self, "payload", _normalized_payload(self.payload))


@dataclass(frozen=True)
class StoredEvent:
    """One persisted journal row (timestamps aware UTC; payload parsed JSON)."""

    seq: int
    event_id: str
    aggregate_id: str
    kind: str
    actor_id: str
    happened_at: datetime
    recorded_at: datetime
    prev_hash: str
    row_hash: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class AggregateHead:
    """The per-aggregate chain head (rebuildable projection over events)."""

    aggregate_id: str
    version: int
    last_seq: int
    last_hash: str


def _validate_event_fields(event: DeskEvent) -> None:
    _uuid("DeskEvent.event_id", event.event_id)
    _text("DeskEvent.aggregate_id", event.aggregate_id)
    _text("DeskEvent.actor_id", event.actor_id)
    if type(event.kind) is not str or event.kind not in ALLOWED_EVENT_KINDS:
        raise ContractError("INVALID_SCHEMA", f"DeskEvent.kind: unknown event kind {event.kind!r}")
    _utc_timestamp("DeskEvent.happened_at", event.happened_at)
    if not isinstance(event.payload, Mapping):
        raise ContractError("INVALID_SCHEMA", "DeskEvent.payload: JSON object (mapping) required")


def _expected_head_text(value: object) -> str:
    if type(value) is str and (value == GENESIS or _DIGEST_RE.fullmatch(value) is not None):
        return value
    raise ContractError(
        "INVALID_SCHEMA", f"expected_head: {GENESIS!r} or lowercase sha256 hex required"
    )


# ---------------------------------------------------------------------------
# Handle


class PrivateDeskHandle:
    """Open handle to one private runtime desk database (single process use)."""

    def __init__(self, path: Path, connection: sqlite3.Connection) -> None:
        self.path = path
        self.connection = connection
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Close the connection; safe to call more than once."""
        if not self._closed:
            self._closed = True
            self.connection.close()


def _require_open(handle: PrivateDeskHandle) -> sqlite3.Connection:
    if not isinstance(handle, PrivateDeskHandle):
        raise ContractError("INVALID_SCHEMA", "handle: PrivateDeskHandle required")
    if handle.closed:
        raise ContractError("JOURNAL_UNAVAILABLE", "private desk handle is closed")
    return handle.connection


# ---------------------------------------------------------------------------
# Migrations


@dataclass(frozen=True)
class _Migration:
    version: int
    name: str
    path: Path


def _discover_migrations() -> tuple[_Migration, ...]:
    directory = _MIGRATIONS_DIR
    if not directory.is_dir():
        raise ContractError("JOURNAL_UNAVAILABLE", f"migration directory missing: {directory}")
    migrations: list[_Migration] = []
    seen: set[int] = set()
    for path in directory.glob("*.sql"):
        match = _MIGRATION_FILENAME_RE.fullmatch(path.name)
        if match is None:
            raise ContractError("INVALID_SCHEMA", f"malformed migration file name {path.name!r}")
        version = int(match.group(1))
        if version in seen:
            raise ContractError("INVALID_SCHEMA", f"duplicate migration version {version}")
        seen.add(version)
        migrations.append(_Migration(version=version, name=path.name, path=path))
    if not migrations:
        raise ContractError("JOURNAL_UNAVAILABLE", f"no migrations found in {directory}")
    migrations.sort(key=lambda migration: migration.version)
    return tuple(migrations)


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise ContractError(
            "JOURNAL_UNAVAILABLE", f"cannot start schema_migrations transaction: {exc}"
        ) from exc
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
    except sqlite3.Error as exc:
        connection.execute("ROLLBACK")
        raise ContractError(
            "JOURNAL_UNAVAILABLE", f"cannot create schema_migrations: {exc}"
        ) from exc
    connection.execute("COMMIT")


def _applied_versions(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    return [int(row[0]) for row in rows]


def _execute_script(connection: sqlite3.Connection, script: str) -> None:
    """Execute a migration script statement-by-statement via complete_statement.

    ``sqlite3.complete_statement`` understands CREATE TRIGGER bodies, so a
    script flushes one statement at a time and never silently drops trailing
    text. Migration files must end each statement with ``;``.
    """
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                connection.execute(statement)
            buffer = ""
    remainder = "\n".join(
        line for line in buffer.splitlines() if not line.strip().startswith("--")
    ).strip()
    if remainder:
        raise ContractError(
            "INVALID_SCHEMA", f"migration script ends mid-statement: {remainder[:80]!r}"
        )


def _apply_migration(connection: sqlite3.Connection, migration: _Migration) -> None:
    try:
        sql_text = migration.path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(
            "JOURNAL_UNAVAILABLE", f"cannot read migration {migration.name}: {exc}"
        ) from exc
    applied_at = _format_timestamp(datetime.now(UTC))
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise ContractError(
            "JOURNAL_UNAVAILABLE", f"cannot start migration {migration.name}: {exc}"
        ) from exc
    try:
        _execute_script(connection, sql_text)
        connection.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (migration.version, migration.name, applied_at),
        )
    except BaseException as exc:
        connection.execute("ROLLBACK")
        if isinstance(exc, sqlite3.Error):
            raise ContractError(
                "JOURNAL_UNAVAILABLE", f"migration {migration.name} failed: {exc}"
            ) from exc
        raise
    connection.execute("COMMIT")


def open_private_desk(path: Path) -> PrivateDeskHandle:
    """Open (creating if needed) the private runtime journal at ``path``.

    Fails closed when the database's applied schema is not the shipped prefix.
    """
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        _ensure_migrations_table(connection)
        applied_versions = _applied_versions(connection)
        migrations = _discover_migrations()
        shipped_versions = [migration.version for migration in migrations]
        if applied_versions != shipped_versions[: len(applied_versions)]:
            raise ContractError(
                "JOURNAL_UNAVAILABLE",
                f"applied schema versions {applied_versions} are not the shipped prefix "
                f"{shipped_versions[: len(applied_versions)]}",
            )
        for migration in migrations[len(applied_versions) :]:
            _apply_migration(connection, migration)
    except BaseException:
        connection.close()
        raise
    handle = PrivateDeskHandle(db_path, connection)
    try:
        verify_desk_chain(handle)
    except BaseException:
        handle.close()
        raise
    return handle


# ---------------------------------------------------------------------------
# Hash and row mapping


def _compute_row_hash(
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


def _row_to_stored(row: sqlite3.Row) -> StoredEvent:
    payload = json.loads(str(row["canonical_payload"]))
    if not isinstance(payload, dict):
        raise ContractError("HASH_MISMATCH", "stored payload is not a JSON object")
    return StoredEvent(
        seq=int(row["seq"]),
        event_id=str(row["event_id"]),
        aggregate_id=str(row["aggregate_id"]),
        kind=str(row["kind"]),
        actor_id=str(row["actor_id"]),
        happened_at=_parse_timestamp("happened_at", row["happened_at"]),
        recorded_at=_parse_timestamp("recorded_at", row["recorded_at"]),
        prev_hash=str(row["prev_hash"]),
        row_hash=str(row["row_hash"]),
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Operations


def append_desk_event(
    handle: PrivateDeskHandle, event: DeskEvent, expected_head: str
) -> StoredEvent:
    """Append one event in a single BEGIN IMMEDIATE transaction.

    Idempotent on ``event_id`` with identical content (returns the stored
    event unchanged); any content difference or a stale ``expected_head`` is a
    ``CONFLICT`` with no partial writes.
    """
    connection = _require_open(handle)
    if not isinstance(event, DeskEvent):
        raise ContractError("INVALID_SCHEMA", "event: DeskEvent required")
    _validate_event_fields(event)
    canonical_text = canonical_payload_bytes(event.payload).decode("utf-8")
    happened_text = _format_timestamp(event.happened_at)
    head_token = _expected_head_text(expected_head)

    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise ContractError(
            "JOURNAL_UNAVAILABLE", f"cannot start append transaction: {exc}"
        ) from exc
    try:
        existing = connection.execute(
            "SELECT * FROM events WHERE event_id = ?", (event.event_id,)
        ).fetchone()
        if existing is not None:
            stored = _row_to_stored(existing)
            identical = (
                stored.aggregate_id == event.aggregate_id
                and stored.kind == event.kind
                and stored.actor_id == event.actor_id
                and _format_timestamp(stored.happened_at) == happened_text
                and str(existing["canonical_payload"]) == canonical_text
            )
            if not identical:
                raise ContractError(
                    "CONFLICT",
                    f"event_id {event.event_id} already exists with different content",
                )
            connection.execute("ROLLBACK")
            return stored
        head_row = connection.execute(
            "SELECT last_hash FROM aggregate_heads WHERE aggregate_id = ?",
            (event.aggregate_id,),
        ).fetchone()
        current_head = GENESIS if head_row is None else str(head_row["last_hash"])
        if head_token != current_head:
            raise ContractError(
                "CONFLICT",
                f"expected_head {head_token!r} does not match aggregate head {current_head!r}",
            )
        recorded_dt = datetime.now(UTC)
        recorded_text = _format_timestamp(recorded_dt)
        row_hash = _compute_row_hash(
            prev_hash=current_head,
            event_id=event.event_id,
            aggregate_id=event.aggregate_id,
            kind=event.kind,
            actor_id=event.actor_id,
            happened_at=happened_text,
            recorded_at=recorded_text,
            canonical_payload=canonical_text,
        )
        cursor = connection.execute(
            "INSERT INTO events (event_id, aggregate_id, kind, actor_id, happened_at,"
            " recorded_at, canonical_payload, prev_hash, row_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.aggregate_id,
                event.kind,
                event.actor_id,
                happened_text,
                recorded_text,
                canonical_text,
                current_head,
                row_hash,
            ),
        )
        new_seq = cursor.lastrowid
        if new_seq is None:
            raise ContractError("JOURNAL_UNAVAILABLE", "append did not return a row id")
        seq = int(new_seq)
        connection.execute(
            "INSERT INTO aggregate_heads (aggregate_id, version, last_seq, last_hash)"
            " VALUES (?, 1, ?, ?)"
            " ON CONFLICT(aggregate_id) DO UPDATE SET"
            " version = aggregate_heads.version + 1,"
            " last_seq = excluded.last_seq,"
            " last_hash = excluded.last_hash",
            (event.aggregate_id, seq, row_hash),
        )
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    return StoredEvent(
        seq=seq,
        event_id=event.event_id,
        aggregate_id=event.aggregate_id,
        kind=event.kind,
        actor_id=event.actor_id,
        happened_at=event.happened_at,
        recorded_at=recorded_dt,
        prev_hash=current_head,
        row_hash=row_hash,
        payload=event.payload,
    )


def read_desk_events(
    handle: PrivateDeskHandle,
    after_seq: int = 0,
    aggregate_id: str | None = None,
) -> tuple[StoredEvent, ...]:
    """Read stored events ordered by seq, optionally filtered."""
    connection = _require_open(handle)
    if type(after_seq) is not int or after_seq < 0:
        raise ContractError("INVALID_SCHEMA", "after_seq: integer >= 0 required")
    sql = "SELECT * FROM events WHERE seq > ?"
    params: list[object] = [after_seq]
    if aggregate_id is not None:
        params.append(_text("aggregate_id", aggregate_id))
        sql += " AND aggregate_id = ?"
    sql += " ORDER BY seq"
    rows = connection.execute(sql, params).fetchall()
    return tuple(_row_to_stored(row) for row in rows)


def read_aggregate_head(handle: PrivateDeskHandle, aggregate_id: str) -> AggregateHead | None:
    """Return the projected head for one aggregate, or None when unknown."""
    connection = _require_open(handle)
    aggregate = _text("aggregate_id", aggregate_id)
    row = connection.execute(
        "SELECT aggregate_id, version, last_seq, last_hash FROM aggregate_heads"
        " WHERE aggregate_id = ?",
        (aggregate,),
    ).fetchone()
    if row is None:
        return None
    return AggregateHead(
        aggregate_id=str(row["aggregate_id"]),
        version=int(row["version"]),
        last_seq=int(row["last_seq"]),
        last_hash=str(row["last_hash"]),
    )


def verify_desk_chain(handle: PrivateDeskHandle) -> None:
    """Recompute the event chain and head projection; raise HASH_MISMATCH on any drift."""
    connection = _require_open(handle)
    rows = connection.execute(
        "SELECT seq, event_id, aggregate_id, kind, actor_id, happened_at, recorded_at,"
        " canonical_payload, prev_hash, row_hash FROM events ORDER BY seq"
    ).fetchall()
    expected_seq = 1
    last_hash_by_aggregate: dict[str, str] = {}
    counts: dict[str, int] = {}
    last_seq_by_aggregate: dict[str, int] = {}
    for row in rows:
        seq = int(row["seq"])
        if seq != expected_seq:
            raise ContractError(
                "HASH_MISMATCH", f"events: seq gap at {seq} (expected {expected_seq})"
            )
        aggregate_id = str(row["aggregate_id"])
        prev_hash = str(row["prev_hash"])
        row_hash = str(row["row_hash"])
        expected_prev = last_hash_by_aggregate.get(aggregate_id, GENESIS)
        if prev_hash != expected_prev:
            raise ContractError(
                "HASH_MISMATCH",
                f"events seq {seq}: prev_hash {prev_hash!r} does not link {aggregate_id!r}",
            )
        recomputed = _compute_row_hash(
            prev_hash=prev_hash,
            event_id=str(row["event_id"]),
            aggregate_id=aggregate_id,
            kind=str(row["kind"]),
            actor_id=str(row["actor_id"]),
            happened_at=str(row["happened_at"]),
            recorded_at=str(row["recorded_at"]),
            canonical_payload=str(row["canonical_payload"]),
        )
        if recomputed != row_hash:
            raise ContractError(
                "HASH_MISMATCH", f"events seq {seq}: row_hash does not match content"
            )
        last_hash_by_aggregate[aggregate_id] = row_hash
        counts[aggregate_id] = counts.get(aggregate_id, 0) + 1
        last_seq_by_aggregate[aggregate_id] = seq
        expected_seq += 1
    heads = connection.execute(
        "SELECT aggregate_id, version, last_seq, last_hash FROM aggregate_heads"
    ).fetchall()
    seen: set[str] = set()
    for head in heads:
        aggregate_id = str(head["aggregate_id"])
        seen.add(aggregate_id)
        if aggregate_id not in last_hash_by_aggregate:
            raise ContractError(
                "HASH_MISMATCH", f"aggregate_heads: row for unknown aggregate {aggregate_id!r}"
            )
        if (
            int(head["version"]) != counts[aggregate_id]
            or int(head["last_seq"]) != last_seq_by_aggregate[aggregate_id]
            or str(head["last_hash"]) != last_hash_by_aggregate[aggregate_id]
        ):
            raise ContractError(
                "HASH_MISMATCH", f"aggregate_heads: projection mismatch for {aggregate_id!r}"
            )
    missing = sorted(set(last_hash_by_aggregate) - seen)
    if missing:
        raise ContractError("HASH_MISMATCH", f"aggregate_heads: missing rows for {missing!r}")


def rebuild_heads(handle: PrivateDeskHandle) -> None:
    """Recompute the ``aggregate_heads`` projection from events (upsert-based)."""
    connection = _require_open(handle)
    rows = connection.execute(
        "SELECT aggregate_id, seq, row_hash FROM events ORDER BY seq"
    ).fetchall()
    heads: dict[str, tuple[int, int, str]] = {}
    for row in rows:
        aggregate_id = str(row["aggregate_id"])
        version = heads[aggregate_id][0] + 1 if aggregate_id in heads else 1
        heads[aggregate_id] = (version, int(row["seq"]), str(row["row_hash"]))
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise ContractError(
            "JOURNAL_UNAVAILABLE", f"cannot start head rebuild transaction: {exc}"
        ) from exc
    try:
        connection.executemany(
            "INSERT INTO aggregate_heads (aggregate_id, version, last_seq, last_hash)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(aggregate_id) DO UPDATE SET"
            " version = excluded.version,"
            " last_seq = excluded.last_seq,"
            " last_hash = excluded.last_hash",
            [
                (aggregate_id, version, last_seq, last_hash)
                for aggregate_id, (version, last_seq, last_hash) in heads.items()
            ],
        )
        connection.execute(
            "DELETE FROM aggregate_heads WHERE aggregate_id NOT IN"
            " (SELECT DISTINCT aggregate_id FROM events)"
        )
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise


def close_private_desk(handle: PrivateDeskHandle) -> None:
    """Close a private desk handle; safe to call more than once."""
    handle.close()
