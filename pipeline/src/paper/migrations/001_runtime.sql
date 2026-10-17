-- AD private runtime journal schema, version 1 (SQLite only).
-- Applied by src/db/repositories/private_desk.py inside one BEGIN IMMEDIATE
-- transaction; never applied to any production or Supabase database.

CREATE TABLE events (
    seq               INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id          TEXT NOT NULL UNIQUE,
    aggregate_id      TEXT NOT NULL,
    kind              TEXT NOT NULL,
    actor_id          TEXT NOT NULL,
    happened_at       TEXT NOT NULL,
    recorded_at       TEXT NOT NULL,
    canonical_payload TEXT NOT NULL,
    prev_hash         TEXT NOT NULL,
    row_hash          TEXT NOT NULL
);

CREATE INDEX events_aggregate_seq ON events (aggregate_id, seq);

CREATE TABLE aggregate_heads (
    aggregate_id TEXT PRIMARY KEY,
    version      INTEGER NOT NULL,
    last_seq     INTEGER NOT NULL,
    last_hash    TEXT NOT NULL
);

CREATE TRIGGER events_no_update BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events is append-only: UPDATE forbidden');
END;

CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events is append-only: DELETE forbidden');
END;
