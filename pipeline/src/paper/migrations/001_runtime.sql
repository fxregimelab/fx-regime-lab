-- AD private runtime journal schema, version 1 (SQLite only).
-- Applied by src/db/repositories/private_desk.py inside one BEGIN IMMEDIATE
-- transaction; never applied to any production or Supabase database.
--
-- This file is edited in place instead of adding an 002 patch: version 1 has
-- never been applied outside ephemeral pytest tmp_path databases — no
-- persistent runtime.sqlite3 has ever been created (data/desk/ holds only the
-- untouched legacy paper_desk.sqlite3) — which means no deployed database ever
-- recorded the old column order. The events column list and order below are
-- pinned exactly to spec 01 section 6. Any change after the first persistent
-- runtime database exists MUST be a new migration.
--
-- Append-only is enforced by triggers on ANY connection (pragmas are
-- per-connection and cannot be trusted): UPDATE and DELETE abort, and the
-- BEFORE INSERT guard aborts a duplicate event_id or an explicit seq
-- collision, so INSERT OR REPLACE cannot silently rewrite an existing row
-- even when recursive_triggers is off. Module connections additionally set
-- recursive_triggers=ON so REPLACE's implicit DELETE also fires the delete
-- trigger.

CREATE TABLE events (
    seq                        INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id                   TEXT NOT NULL UNIQUE,
    aggregate_id               TEXT NOT NULL,
    expected_aggregate_version INTEGER,
    kind                       TEXT NOT NULL,
    happened_at                TEXT NOT NULL,
    recorded_at                TEXT NOT NULL,
    canonical_payload          TEXT NOT NULL,
    prev_hash                  TEXT NOT NULL,
    row_hash                   TEXT NOT NULL,
    actor_id                   TEXT NOT NULL
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

CREATE TRIGGER events_guard_insert BEFORE INSERT ON events
WHEN EXISTS (SELECT 1 FROM events WHERE event_id = NEW.event_id)
  OR (NEW.seq IS NOT NULL AND EXISTS (SELECT 1 FROM events WHERE seq = NEW.seq))
BEGIN
    SELECT RAISE(ABORT, 'events is append-only: duplicate event_id or seq forbidden');
END;
