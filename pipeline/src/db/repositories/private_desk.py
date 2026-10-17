"""Private runtime desk journal (SQLite) — append-only hash-chained events.

AD-T03 private storage (journal) and AD-T04 control state (writer leases,
fencing tokens, reservations). All mutation entry points are exposed through the
``src.db.writer`` facade; this repository never imports or calls the production
Supabase client path and requires no service-role environment.

Schema
    Migration ``src/paper/migrations/001_runtime.sql`` is edited in place rather
    than extended by an 002 patch: version 1 has never been applied outside
    ephemeral pytest tmp databases — no persistent ``runtime.sqlite3`` has ever
    been created (``data/desk/`` holds only the untouched legacy
    ``paper_desk.sqlite3``) — and an in-place edit keeps the ``events`` column
    list/order pinned to spec 01 section 6. Once any persistent runtime database
    exists, every further change goes through a new versioned migration file.

    Migration ``002_control.sql`` (AD-T04) adds the control state machines:
    ``writer_leases`` (single terminal-writer lease with a monotonic fencing
    token; ``state`` is ``held`` or ``released``) and ``reservations``
    (``status`` is ``reserved`` or ``released``; money as a canonical decimal
    string; ``plan_digest`` is a deliberate addition to spec 01 section 6's
    minimum column list so a replayed ``parent_id`` is idempotent only when the
    immutable amount and plan identity match). Both tables are updated ONLY
    through the control API in this module; no triggers guard them because
    they are state machines rather than append-only ledgers.

    Migrations ship as ``src/paper/migrations/*.sql`` applied in numeric
    filename order and tracked in ``schema_migrations``; each migration runs
    inside one explicit ``BEGIN IMMEDIATE`` transaction with WAL journaling and
    ``synchronous=FULL``. Every module-opened connection also sets
    ``PRAGMA recursive_triggers=ON`` and ``PRAGMA busy_timeout=5000``. A
    database whose applied versions are not exactly the shipped prefix
    (including any newer/unknown version) fails closed.

Integrity
    Events are chain-linked per aggregate: the first event of an aggregate uses
    the ``GENESIS`` sentinel, later events use the previous event's
    ``row_hash``. ``row_hash`` covers prev_hash, event_id, aggregate_id, kind,
    actor_id, happened_at, recorded_at and the payload's canonical JSON text —
    never ``seq`` (assigned by the insert) and never
    ``expected_aggregate_version``. ``aggregate_heads`` is a rebuildable
    projection (version, last_seq, last_hash); append re-derives the chain head
    from ``events`` and refuses to write when the projection and the events
    disagree (``HASH_MISMATCH``), so a stale or forged head cannot fork the
    chain.

    Append-only is enforced by database triggers on ANY connection, because
    pragmas are per-connection and cannot be trusted: UPDATE and DELETE abort,
    and a BEFORE INSERT guard aborts a duplicate ``event_id`` or an explicit
    ``seq`` collision, so ``INSERT OR REPLACE`` cannot rewrite an existing row
    even with ``recursive_triggers`` off. Enabling
    ``recursive_triggers=ON`` on module connections is the second line of
    defense: it also makes REPLACE's implicit DELETE fire the delete trigger.

    ``expected_aggregate_version`` is an optional optimistic-concurrency CAS
    consulted for fresh appends only: when set it must equal 0 for a brand-new
    aggregate or ``aggregate_heads.version`` otherwise (after the same
    projection-consistency check above); a mismatch is a ``CONFLICT`` with no
    writes. It is stored verbatim, is not part of the row hash, and is not part
    of the ``event_id`` idempotency identity — a retry of an existing
    ``event_id`` returns the stored event even when this field differs.

Reason codes (from ``src.paper.contracts``)
    ``INVALID_SCHEMA``
        Unknown event kind, non-JSON payload value (float/Decimal/NaN/bytes/
        tuple), malformed id/timestamp/expected_head/expected_aggregate_version,
        malformed migration file names, invalid read arguments, or malformed
        control arguments (lease name/owner, ttl_seconds, fencing token,
        reservation ids, plan_digest, proof flag, or an expiry that is not an
        aware-UTC timestamp strictly in the future).
    ``CONFLICT``
        Duplicate ``event_id`` whose content differs, ``expected_head`` not
        matching the aggregate's last stored event hash, or
        ``expected_aggregate_version`` not matching the aggregate version
        (nothing is written in any case). Control state: a live lease held by
        another owner (no write), a reservation for the same ``parent_id``
        whose amount or ``plan_digest`` differs, or a ``reservation_id``
        reused for another parent.
    ``HASH_MISMATCH``
        Chain corruption: row hash recomputation, per-aggregate prev linkage,
        seq gaps, ``aggregate_heads``/events disagreement, malformed stored
        payload text — or non-canonical stored row content in read paths
        (including a malformed control-table row).
    ``FENCE_STALE``
        Lease authority failure: no stored lease, owner/fencing-token
        mismatch, a released lease, an expired lease on renew/assert, or a
        reservation whose ``owner_fencing_token`` differs from the caller.
    ``ORDER_UNKNOWN``
        Unknown ``reservation_id`` for mark/release, or a release of a
        ``broker_pending`` reservation without ``proof_no_send`` (the row is
        left unchanged even when ``expires_at`` has passed — TTL expiry never
        releases a possibly-sent request).
    ``STALE_STATE``
        A reservation state transition invalid for the current stored status
        (marking a released reservation broker-pending).
    ``JOURNAL_UNAVAILABLE``
        Applied schema not a prefix of the shipped migrations (fail closed),
        operations on a closed handle, missing migration directory, a
        migration that fails to apply, a write lock that outlasts
        ``busy_timeout`` (5000 ms), or a fencing-token counter at the signed
        64-bit maximum that cannot be advanced safely.
    ``INVALID_NUMBER``
        A reservation amount that is not a finite, positive ``Decimal``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
_DECIMAL_TEXT_RE = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")
_ZERO_OFFSET = timedelta(0)

_BUSY_TIMEOUT_MS = 5000
_MAX_FENCING_TOKEN = 2**63 - 1
_LEASE_STATES: frozenset[str] = frozenset({"held", "released"})
_RESERVATION_STATUSES: frozenset[str] = frozenset({"reserved", "released"})


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


def _digest(name: str, value: object) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise ContractError("INVALID_SCHEMA", f"{name}: lowercase sha256 hex required")
    return value


def _fence_token(name: str, value: object) -> int:
    if type(value) is not int or value < 1:
        raise ContractError("INVALID_SCHEMA", f"{name}: integer >= 1 required")
    return value


def _ttl_seconds(value: object) -> int:
    if type(value) is not int or value < 1:
        raise ContractError("INVALID_SCHEMA", "ttl_seconds: positive integer required")
    return value


def _positive_decimal(name: str, value: object) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ContractError("INVALID_NUMBER", f"{name}: finite Decimal required")
    if value <= 0:
        raise ContractError("INVALID_NUMBER", f"{name}: positive decimal required")
    return value


def _strict_flag(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise ContractError("INVALID_SCHEMA", f"{name}: strict boolean required")
    return value


def _format_decimal(value: Decimal) -> str:
    """Canonical decimal text (mirrors ``src.paper.contracts._format_decimal``)."""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _stored_int(name: str, value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ContractError(
            "HASH_MISMATCH", f"{name}: stored value is not an integer >= {minimum}"
        )
    return value


def _stored_decimal(name: str, value: object) -> Decimal:
    if type(value) is not str or _DECIMAL_TEXT_RE.fullmatch(value) is None:
        raise ContractError("HASH_MISMATCH", f"{name}: stored text is not a canonical decimal")
    return Decimal(value)


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
    expected_aggregate_version: int | None = None

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
    expected_aggregate_version: int | None = None

    def __post_init__(self) -> None:
        _expected_aggregate_version(
            "StoredEvent.expected_aggregate_version", self.expected_aggregate_version
        )


@dataclass(frozen=True)
class AggregateHead:
    """The per-aggregate chain head (rebuildable projection over events)."""

    aggregate_id: str
    version: int
    last_seq: int
    last_hash: str


@dataclass(frozen=True)
class Lease:
    """One writer lease row: fenced authority over a named terminal-write scope."""

    lease_name: str
    owner_id: str
    fencing_token: int
    acquired_at: datetime
    renewed_at: datetime
    expires_at: datetime
    state: str

    def __post_init__(self) -> None:
        _text("Lease.lease_name", self.lease_name)
        _text("Lease.owner_id", self.owner_id)
        _fence_token("Lease.fencing_token", self.fencing_token)
        _utc_timestamp("Lease.acquired_at", self.acquired_at)
        _utc_timestamp("Lease.renewed_at", self.renewed_at)
        _utc_timestamp("Lease.expires_at", self.expires_at)
        if self.state not in _LEASE_STATES:
            raise ContractError("INVALID_SCHEMA", f"Lease.state: unknown state {self.state!r}")


@dataclass(frozen=True)
class Reservation:
    """One risk reservation row; money crosses the boundary as a Decimal."""

    reservation_id: str
    parent_id: str
    status: str
    amount_usd: Decimal
    plan_digest: str
    expires_at: datetime
    broker_pending: bool
    owner_fencing_token: int
    last_event_seq: int | None
    created_at: datetime
    released_at: datetime | None

    def __post_init__(self) -> None:
        _uuid("Reservation.reservation_id", self.reservation_id)
        _uuid("Reservation.parent_id", self.parent_id)
        if self.status not in _RESERVATION_STATUSES:
            raise ContractError(
                "INVALID_SCHEMA", f"Reservation.status: unknown status {self.status!r}"
            )
        _positive_decimal("Reservation.amount_usd", self.amount_usd)
        _digest("Reservation.plan_digest", self.plan_digest)
        _utc_timestamp("Reservation.expires_at", self.expires_at)
        _strict_flag("Reservation.broker_pending", self.broker_pending)
        _fence_token("Reservation.owner_fencing_token", self.owner_fencing_token)
        if self.last_event_seq is not None:
            _count("Reservation.last_event_seq", self.last_event_seq)
        _utc_timestamp("Reservation.created_at", self.created_at)
        if self.released_at is not None:
            _utc_timestamp("Reservation.released_at", self.released_at)


def _count(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ContractError("INVALID_SCHEMA", f"{name}: integer >= 0 required")
    return value


def _validate_event_fields(event: DeskEvent) -> None:
    _uuid("DeskEvent.event_id", event.event_id)
    _text("DeskEvent.aggregate_id", event.aggregate_id)
    _text("DeskEvent.actor_id", event.actor_id)
    if type(event.kind) is not str or event.kind not in ALLOWED_EVENT_KINDS:
        raise ContractError("INVALID_SCHEMA", f"DeskEvent.kind: unknown event kind {event.kind!r}")
    _utc_timestamp("DeskEvent.happened_at", event.happened_at)
    if not isinstance(event.payload, Mapping):
        raise ContractError("INVALID_SCHEMA", "DeskEvent.payload: JSON object (mapping) required")
    _expected_aggregate_version(
        "DeskEvent.expected_aggregate_version", event.expected_aggregate_version
    )


def _expected_aggregate_version(name: str, value: object) -> int | None:
    """Validate an optional aggregate version: None or a non-bool integer >= 0."""
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ContractError("INVALID_SCHEMA", f"{name}: None or integer >= 0 required")
    return value


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


def _discover_migrations(directory: Path | None = None) -> tuple[_Migration, ...]:
    resolved = _MIGRATIONS_DIR if directory is None else Path(directory)
    if not resolved.is_dir():
        raise ContractError("JOURNAL_UNAVAILABLE", f"migration directory missing: {resolved}")
    migrations: list[_Migration] = []
    seen: set[int] = set()
    for path in resolved.glob("*.sql"):
        match = _MIGRATION_FILENAME_RE.fullmatch(path.name)
        if match is None:
            raise ContractError("INVALID_SCHEMA", f"malformed migration file name {path.name!r}")
        version = int(match.group(1))
        if version in seen:
            raise ContractError("INVALID_SCHEMA", f"duplicate migration version {version}")
        seen.add(version)
        migrations.append(_Migration(version=version, name=path.name, path=path))
    if not migrations:
        raise ContractError("JOURNAL_UNAVAILABLE", f"no migrations found in {resolved}")
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


def open_private_desk(
    path: Path, *, migrations_dir: Path | None = None
) -> PrivateDeskHandle:
    """Open (creating if needed) the private runtime journal at ``path``.

    Fails closed when the database's applied schema is not the shipped prefix.
    ``migrations_dir`` optionally overrides the shipped ``src/paper/migrations``
    directory (test hook for half-apply fixtures); the default is unchanged.
    """
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        str(db_path), timeout=_BUSY_TIMEOUT_MS / 1000, isolation_level=None
    )
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA recursive_triggers=ON")
        connection.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        _ensure_migrations_table(connection)
        applied_versions = _applied_versions(connection)
        migrations = _discover_migrations(migrations_dir)
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


def _stored_expected_version(value: object) -> int | None:
    """Validate the stored column value; stored corruption is HASH_MISMATCH."""
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ContractError(
            "HASH_MISMATCH",
            "stored expected_aggregate_version is not NULL or a non-negative integer",
        )
    return value


def _row_to_stored(row: sqlite3.Row) -> StoredEvent:
    try:
        payload = json.loads(str(row["canonical_payload"]))
    except json.JSONDecodeError:
        raise ContractError(
            "HASH_MISMATCH", "stored canonical_payload is not valid JSON"
        ) from None
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
        expected_aggregate_version=_stored_expected_version(row["expected_aggregate_version"]),
    )


def _stored_digest(name: str, value: object) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise ContractError(
            "HASH_MISMATCH", f"{name}: stored value is not a lowercase sha256 hex digest"
        )
    return value


def _row_to_lease(row: sqlite3.Row) -> Lease:
    state = str(row["state"])
    if state not in _LEASE_STATES:
        raise ContractError(
            "HASH_MISMATCH", f"writer_leases.state: unknown stored state {state!r}"
        )
    return Lease(
        lease_name=str(row["lease_name"]),
        owner_id=str(row["owner_id"]),
        fencing_token=_stored_int("writer_leases.fencing_token", row["fencing_token"], 1),
        acquired_at=_parse_timestamp("writer_leases.acquired_at", row["acquired_at"]),
        renewed_at=_parse_timestamp("writer_leases.renewed_at", row["renewed_at"]),
        expires_at=_parse_timestamp("writer_leases.expires_at", row["expires_at"]),
        state=state,
    )


def _row_to_reservation(row: sqlite3.Row) -> Reservation:
    status = str(row["status"])
    if status not in _RESERVATION_STATUSES:
        raise ContractError(
            "HASH_MISMATCH", f"reservations.status: unknown stored status {status!r}"
        )
    pending = _stored_int("reservations.broker_pending", row["broker_pending"])
    if pending not in (0, 1):
        raise ContractError(
            "HASH_MISMATCH", "reservations.broker_pending: stored value is not 0 or 1"
        )
    last_event_raw = row["last_event_seq"]
    released_raw = row["released_at"]
    return Reservation(
        reservation_id=str(row["reservation_id"]),
        parent_id=str(row["parent_id"]),
        status=status,
        amount_usd=_stored_decimal("reservations.amount_usd", row["amount_usd"]),
        plan_digest=_stored_digest("reservations.plan_digest", row["plan_digest"]),
        expires_at=_parse_timestamp("reservations.expires_at", row["expires_at"]),
        broker_pending=bool(pending),
        owner_fencing_token=_stored_int(
            "reservations.owner_fencing_token", row["owner_fencing_token"], 1
        ),
        last_event_seq=None
        if last_event_raw is None
        else _stored_int("reservations.last_event_seq", last_event_raw),
        created_at=_parse_timestamp("reservations.created_at", row["created_at"]),
        released_at=None
        if released_raw is None
        else _parse_timestamp("reservations.released_at", released_raw),
    )


# ---------------------------------------------------------------------------
# Operations


def append_desk_event(
    handle: PrivateDeskHandle, event: DeskEvent, expected_head: str
) -> StoredEvent:
    """Append one event in a single BEGIN IMMEDIATE transaction.

    Idempotent on ``event_id`` with identical content (returns the stored
    event unchanged); any content difference is a ``CONFLICT``. A fresh append
    cross-checks ``aggregate_heads`` against the aggregate's last stored event
    (disagreement is ``HASH_MISMATCH``), compares ``expected_head`` against
    that event's ``row_hash``, and — when ``expected_aggregate_version`` is set
    — requires the aggregate's current version (0 for a brand-new aggregate).
    No path writes partially.
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
        # The authoritative chain head comes from events, never from the
        # rebuildable aggregate_heads projection; a projection that disagrees
        # with the events must abort the append instead of forking the chain.
        last_row = connection.execute(
            "SELECT seq, row_hash FROM events WHERE aggregate_id = ?"
            " ORDER BY seq DESC LIMIT 1",
            (event.aggregate_id,),
        ).fetchone()
        heads_row = connection.execute(
            "SELECT version, last_seq, last_hash FROM aggregate_heads WHERE aggregate_id = ?",
            (event.aggregate_id,),
        ).fetchone()
        if (last_row is None) != (heads_row is None):
            raise ContractError(
                "HASH_MISMATCH",
                f"aggregate {event.aggregate_id!r}: events and aggregate_heads disagree",
            )
        if (
            last_row is not None
            and heads_row is not None
            and (
                int(heads_row["last_seq"]) != int(last_row["seq"])
                or str(heads_row["last_hash"]) != str(last_row["row_hash"])
            )
        ):
            raise ContractError(
                "HASH_MISMATCH",
                f"aggregate {event.aggregate_id!r}: aggregate_heads does not match the last"
                " stored event",
            )
        current_head = GENESIS if last_row is None else str(last_row["row_hash"])
        if head_token != current_head:
            raise ContractError(
                "CONFLICT",
                f"expected_head {head_token!r} does not match aggregate head {current_head!r}",
            )
        if event.expected_aggregate_version is not None:
            current_version = 0 if heads_row is None else int(heads_row["version"])
            if event.expected_aggregate_version != current_version:
                raise ContractError(
                    "CONFLICT",
                    f"expected_aggregate_version {event.expected_aggregate_version} does not"
                    f" match aggregate version {current_version}",
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
            "INSERT INTO events (event_id, aggregate_id, expected_aggregate_version, kind,"
            " actor_id, happened_at, recorded_at, canonical_payload, prev_hash, row_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.aggregate_id,
                event.expected_aggregate_version,
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
        expected_aggregate_version=event.expected_aggregate_version,
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
        try:
            json.loads(str(row["canonical_payload"]))
        except json.JSONDecodeError:
            raise ContractError(
                "HASH_MISMATCH", f"events seq {seq}: canonical_payload is not valid JSON"
            ) from None
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


# ---------------------------------------------------------------------------
# Control state (AD-T04): writer leases, fencing tokens and reservations.
#
# Every function validates its arguments before issuing SQL, runs inside one
# explicit BEGIN IMMEDIATE transaction, and raises ContractError with the
# module-documented vocabulary. These functions are the ONLY write path for
# writer_leases/reservations; callers reach them through src.db.writer.


def _locked_error(action: str, exc: sqlite3.Error) -> ContractError | None:
    """Map only a busy/locked database; every other sqlite error stays visible."""
    if isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower():
        return ContractError(
            "JOURNAL_UNAVAILABLE",
            f"{action}: database is locked after busy_timeout {_BUSY_TIMEOUT_MS} ms",
        )
    return None


@contextmanager
def _write_transaction(
    handle: PrivateDeskHandle, action: str
) -> Iterator[sqlite3.Connection]:
    """One explicit BEGIN IMMEDIATE transaction with typed lock mapping."""
    connection = _require_open(handle)
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        mapped = _locked_error(action, exc)
        if mapped is not None:
            raise mapped from exc
        raise
    try:
        yield connection
    except BaseException as exc:
        connection.execute("ROLLBACK")
        if isinstance(exc, sqlite3.Error):
            mapped = _locked_error(action, exc)
            if mapped is not None:
                raise mapped from exc
        raise
    try:
        connection.execute("COMMIT")
    except sqlite3.Error as exc:
        connection.execute("ROLLBACK")
        mapped = _locked_error(action, exc)
        if mapped is not None:
            raise mapped from exc
        raise


def _insert_lease(connection: sqlite3.Connection, lease: Lease) -> None:
    connection.execute(
        "INSERT INTO writer_leases (lease_name, owner_id, fencing_token, acquired_at,"
        " renewed_at, expires_at, state) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            lease.lease_name,
            lease.owner_id,
            lease.fencing_token,
            _format_timestamp(lease.acquired_at),
            _format_timestamp(lease.renewed_at),
            _format_timestamp(lease.expires_at),
            lease.state,
        ),
    )


def acquire_lease(
    handle: PrivateDeskHandle, name: str, owner_id: str, ttl_seconds: int
) -> Lease:
    """Acquire or take over the named writer lease (single terminal writer).

    A free, released or expired lease mints ``old fencing_token + 1`` for the
    new owner (also for the same owner: any expiry voids the old token). The
    same owner re-acquiring an unexpired lease gets the stored lease unchanged.
    A live lease held by another owner raises ``CONFLICT`` with no writes.
    """
    lease_name = _text("name", name)
    owner = _text("owner_id", owner_id)
    ttl = _ttl_seconds(ttl_seconds)
    with _write_transaction(handle, "acquire_lease") as connection:
        now = datetime.now(UTC)
        row = connection.execute(
            "SELECT * FROM writer_leases WHERE lease_name = ?", (lease_name,)
        ).fetchone()
        if row is None:
            lease = Lease(
                lease_name=lease_name,
                owner_id=owner,
                fencing_token=1,
                acquired_at=now,
                renewed_at=now,
                expires_at=now + timedelta(seconds=ttl),
                state="held",
            )
            _insert_lease(connection, lease)
            return lease
        stored = _row_to_lease(row)
        if stored.state == "held" and stored.expires_at > now:
            if stored.owner_id == owner:
                return stored
            raise ContractError(
                "CONFLICT",
                f"lease {lease_name!r} is held by another owner until"
                f" {_format_timestamp(stored.expires_at)}",
            )
        if stored.fencing_token >= _MAX_FENCING_TOKEN:
            raise ContractError(
                "JOURNAL_UNAVAILABLE",
                f"lease {lease_name!r}: fencing token {stored.fencing_token} is at the"
                " signed 64-bit maximum and cannot be advanced safely",
            )
        lease = Lease(
            lease_name=lease_name,
            owner_id=owner,
            fencing_token=stored.fencing_token + 1,
            acquired_at=now,
            renewed_at=now,
            expires_at=now + timedelta(seconds=ttl),
            state="held",
        )
        connection.execute(
            "UPDATE writer_leases SET owner_id = ?, fencing_token = ?, acquired_at = ?,"
            " renewed_at = ?, expires_at = ?, state = 'held' WHERE lease_name = ?",
            (
                lease.owner_id,
                lease.fencing_token,
                _format_timestamp(lease.acquired_at),
                _format_timestamp(lease.renewed_at),
                _format_timestamp(lease.expires_at),
                lease_name,
            ),
        )
        return lease


def renew_lease(
    handle: PrivateDeskHandle,
    name: str,
    owner_id: str,
    fencing_token: int,
    ttl_seconds: int,
) -> Lease:
    """Extend a live held lease; any owner/token mismatch or expiry is FENCE_STALE.

    Renewal cannot resurrect an expired lease: recovery is ``acquire_lease``,
    which mints a newer fencing token.
    """
    lease_name = _text("name", name)
    owner = _text("owner_id", owner_id)
    token = _fence_token("fencing_token", fencing_token)
    ttl = _ttl_seconds(ttl_seconds)
    with _write_transaction(handle, "renew_lease") as connection:
        now = datetime.now(UTC)
        row = connection.execute(
            "SELECT * FROM writer_leases WHERE lease_name = ?", (lease_name,)
        ).fetchone()
        if row is None:
            raise ContractError("FENCE_STALE", f"lease {lease_name!r} does not exist")
        stored = _row_to_lease(row)
        if (
            stored.owner_id != owner
            or stored.fencing_token != token
            or stored.state != "held"
        ):
            raise ContractError(
                "FENCE_STALE",
                f"lease {lease_name!r}: owner/fencing token does not match a held lease",
            )
        if stored.expires_at <= now:
            raise ContractError(
                "FENCE_STALE",
                f"lease {lease_name!r}: expired at {_format_timestamp(stored.expires_at)};"
                " acquire a new token",
            )
        renewed = Lease(
            lease_name=lease_name,
            owner_id=owner,
            fencing_token=token,
            acquired_at=stored.acquired_at,
            renewed_at=now,
            expires_at=now + timedelta(seconds=ttl),
            state="held",
        )
        connection.execute(
            "UPDATE writer_leases SET renewed_at = ?, expires_at = ? WHERE lease_name = ?",
            (
                _format_timestamp(renewed.renewed_at),
                _format_timestamp(renewed.expires_at),
                lease_name,
            ),
        )
        return renewed


def release_lease(
    handle: PrivateDeskHandle, name: str, owner_id: str, fencing_token: int
) -> None:
    """Release a held lease; owner/token mismatch or a released lease is FENCE_STALE.

    An expired-but-still-held lease may be released (relinquishment only; it
    never extends authority), which lets a clean shutdown shorten the window
    before a takeover.
    """
    lease_name = _text("name", name)
    owner = _text("owner_id", owner_id)
    token = _fence_token("fencing_token", fencing_token)
    with _write_transaction(handle, "release_lease") as connection:
        row = connection.execute(
            "SELECT * FROM writer_leases WHERE lease_name = ?", (lease_name,)
        ).fetchone()
        if row is None:
            raise ContractError("FENCE_STALE", f"lease {lease_name!r} does not exist")
        stored = _row_to_lease(row)
        if (
            stored.owner_id != owner
            or stored.fencing_token != token
            or stored.state != "held"
        ):
            raise ContractError(
                "FENCE_STALE",
                f"lease {lease_name!r}: owner/fencing token does not match a held lease",
            )
        connection.execute(
            "UPDATE writer_leases SET state = 'released' WHERE lease_name = ?", (lease_name,)
        )


def assert_fence(
    handle: PrivateDeskHandle, name: str, owner_id: str, fencing_token: int
) -> None:
    """Require a held, unexpired lease matching owner+token exactly (hook for writes)."""
    lease_name = _text("name", name)
    owner = _text("owner_id", owner_id)
    token = _fence_token("fencing_token", fencing_token)
    with _write_transaction(handle, "assert_fence") as connection:
        now = datetime.now(UTC)
        row = connection.execute(
            "SELECT * FROM writer_leases WHERE lease_name = ?", (lease_name,)
        ).fetchone()
        if row is None:
            raise ContractError("FENCE_STALE", f"lease {lease_name!r} does not exist")
        stored = _row_to_lease(row)
        if stored.owner_id != owner or stored.fencing_token != token:
            raise ContractError(
                "FENCE_STALE", f"lease {lease_name!r}: owner/fencing token mismatch"
            )
        if stored.state != "held":
            raise ContractError("FENCE_STALE", f"lease {lease_name!r} is released")
        if stored.expires_at <= now:
            raise ContractError(
                "FENCE_STALE",
                f"lease {lease_name!r}: expired at {_format_timestamp(stored.expires_at)}",
            )


def create_reservation(
    handle: PrivateDeskHandle,
    reservation_id: str,
    parent_id: str,
    amount_usd: Decimal,
    plan_digest: str,
    expires_at: datetime,
    owner_fencing_token: int,
) -> Reservation:
    """Create one risk reservation; replay of the same parent+plan is idempotent.

    The same ``parent_id`` with an identical amount and ``plan_digest`` returns
    the stored row (whatever its status); any difference is ``CONFLICT``. Money
    is stored as canonical decimal text; ``expires_at`` must be aware UTC and
    strictly in the future of the system clock.
    """
    rid = _uuid("reservation_id", reservation_id)
    parent = _uuid("parent_id", parent_id)
    amount = _positive_decimal("amount_usd", amount_usd)
    digest = _digest("plan_digest", plan_digest)
    expiry = _utc_timestamp("expires_at", expires_at)
    token = _fence_token("owner_fencing_token", owner_fencing_token)
    now = datetime.now(UTC)
    if expiry <= now:
        raise ContractError("INVALID_SCHEMA", "expires_at: must be strictly in the future")
    with _write_transaction(handle, "create_reservation") as connection:
        parent_row = connection.execute(
            "SELECT * FROM reservations WHERE parent_id = ?", (parent,)
        ).fetchone()
        if parent_row is not None:
            stored = _row_to_reservation(parent_row)
            if stored.amount_usd == amount and stored.plan_digest == digest:
                return stored
            raise ContractError(
                "CONFLICT",
                f"parent_id {parent!r} already has a reservation with a different"
                " amount or plan_digest",
            )
        id_row = connection.execute(
            "SELECT 1 FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if id_row is not None:
            raise ContractError(
                "CONFLICT", f"reservation_id {rid!r} already exists for another parent"
            )
        connection.execute(
            "INSERT INTO reservations (reservation_id, parent_id, status, amount_usd,"
            " plan_digest, expires_at, broker_pending, owner_fencing_token,"
            " last_event_seq, created_at, released_at)"
            " VALUES (?, ?, 'reserved', ?, ?, ?, 0, ?, NULL, ?, NULL)",
            (
                rid,
                parent,
                _format_decimal(amount),
                digest,
                _format_timestamp(expiry),
                token,
                _format_timestamp(now),
            ),
        )
        created = connection.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if created is None:
            raise ContractError("JOURNAL_UNAVAILABLE", "reservation insert was not persisted")
        return _row_to_reservation(created)


def mark_broker_pending(
    handle: PrivateDeskHandle, reservation_id: str, owner_fencing_token: int
) -> Reservation:
    """Persist that a send may leave the process (broker_pending = 1).

    Unknown id is ``ORDER_UNKNOWN``; a token mismatch is ``FENCE_STALE``; a
    released reservation is ``STALE_STATE``. Re-marking is idempotent.
    """
    rid = _uuid("reservation_id", reservation_id)
    token = _fence_token("owner_fencing_token", owner_fencing_token)
    with _write_transaction(handle, "mark_broker_pending") as connection:
        row = connection.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if row is None:
            raise ContractError("ORDER_UNKNOWN", f"reservation {rid!r} does not exist")
        stored = _row_to_reservation(row)
        if stored.owner_fencing_token != token:
            raise ContractError(
                "FENCE_STALE",
                f"reservation {rid!r}: owner_fencing_token does not match the caller",
            )
        if stored.status != "reserved":
            raise ContractError(
                "STALE_STATE", f"reservation {rid!r} is already {stored.status}"
            )
        connection.execute(
            "UPDATE reservations SET broker_pending = 1 WHERE reservation_id = ?", (rid,)
        )
        updated = connection.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if updated is None:
            raise ContractError("JOURNAL_UNAVAILABLE", "reservation update was not persisted")
        return _row_to_reservation(updated)


def release_reservation(
    handle: PrivateDeskHandle,
    reservation_id: str,
    owner_fencing_token: int,
    *,
    proof_no_send: bool,
) -> Reservation:
    """Release a reservation without ever guessing that an ambiguous send failed.

    A ``broker_pending`` reservation is released only with ``proof_no_send``;
    otherwise the call raises ``ORDER_UNKNOWN`` and the row is unchanged, even
    when ``expires_at`` has passed. TTL expiry never auto-releases a request
    that may have left the process.
    """
    rid = _uuid("reservation_id", reservation_id)
    token = _fence_token("owner_fencing_token", owner_fencing_token)
    proof = _strict_flag("proof_no_send", proof_no_send)
    with _write_transaction(handle, "release_reservation") as connection:
        row = connection.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if row is None:
            raise ContractError("ORDER_UNKNOWN", f"reservation {rid!r} does not exist")
        stored = _row_to_reservation(row)
        if stored.owner_fencing_token != token:
            raise ContractError(
                "FENCE_STALE",
                f"reservation {rid!r}: owner_fencing_token does not match the caller",
            )
        if stored.broker_pending and not proof:
            raise ContractError(
                "ORDER_UNKNOWN",
                f"reservation {rid!r} may have been sent; proof_no_send required to release",
            )
        if stored.status == "released":
            return stored
        now = datetime.now(UTC)
        connection.execute(
            "UPDATE reservations SET status = 'released', released_at = ?"
            " WHERE reservation_id = ?",
            (_format_timestamp(now), rid),
        )
        updated = connection.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if updated is None:
            raise ContractError("JOURNAL_UNAVAILABLE", "reservation update was not persisted")
        return _row_to_reservation(updated)


def read_reservation(
    handle: PrivateDeskHandle, reservation_id: str
) -> Reservation | None:
    """Read one reservation by id, or None when unknown (local SQLite only)."""
    rid = _uuid("reservation_id", reservation_id)
    with _write_transaction(handle, "read_reservation") as connection:
        row = connection.execute(
            "SELECT * FROM reservations WHERE reservation_id = ?", (rid,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_reservation(row)
