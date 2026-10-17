-- AD private runtime control schema, version 2 (SQLite only).
-- Applied by src/db/repositories/private_desk.py inside one BEGIN IMMEDIATE
-- transaction; never applied to any production or Supabase database.
--
-- AD-T04 deliberately extends spec 01 section 6's minimum ``reservations``
-- column list with ``plan_digest``: replaying the same ``parent_id`` is
-- idempotent only while the immutable plan identity matches, so
-- (parent_id, amount_usd, plan_digest) is the documented idempotency key and
-- any difference is CONFLICT (see create_reservation).
--
-- writer_leases and reservations are state machines, not append-only ledgers:
-- they transition only through the private_desk control API (acquire/renew/
-- release lease, create/mark/release reservation), which validates fencing
-- tokens and reservation status before every write. No UPDATE/DELETE triggers
-- are attached because a lease must move held -> released and a reservation
-- reserved -> released; the fence/status checks are the write barriers. A
-- possibly-sent reservation (broker_pending = 1) is never released by TTL
-- expiry — only by an explicit no-send proof through release_reservation.
--
-- Money stays a canonical decimal string (no binary floats): amount_usd is
-- TEXT written by the API as ``format(value.normalize(), 'f')``.

CREATE TABLE writer_leases (
    lease_name    TEXT PRIMARY KEY,
    owner_id      TEXT NOT NULL,
    fencing_token INTEGER NOT NULL CHECK (fencing_token >= 1),
    acquired_at   TEXT NOT NULL,
    renewed_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    state         TEXT NOT NULL CHECK (state IN ('held', 'released'))
);

CREATE TABLE reservations (
    reservation_id      TEXT PRIMARY KEY,
    parent_id           TEXT NOT NULL UNIQUE,
    status              TEXT NOT NULL CHECK (status IN ('reserved', 'released')),
    amount_usd          TEXT NOT NULL,
    plan_digest         TEXT NOT NULL,
    expires_at          TEXT NOT NULL,
    broker_pending      INTEGER NOT NULL DEFAULT 0 CHECK (broker_pending IN (0, 1)),
    owner_fencing_token INTEGER NOT NULL CHECK (owner_fencing_token >= 1),
    last_event_seq      INTEGER,
    created_at          TEXT NOT NULL,
    released_at         TEXT
);
