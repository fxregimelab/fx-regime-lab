-- Phase 2.1: historical macro consensus vs actual (event risk foundation)

CREATE TABLE IF NOT EXISTS historical_macro_surprises (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name          TEXT NOT NULL,
    date                DATE NOT NULL,
    time                TEXT,
    actual              DOUBLE PRECISION,
    consensus           DOUBLE PRECISION,
    previous            DOUBLE PRECISION,
    surprise_bps        DOUBLE PRECISION,
    surprise_direction  TEXT NOT NULL CHECK (surprise_direction IN ('BEAT', 'MISS', 'IN-LINE')),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (event_name, date)
);

ALTER TABLE historical_macro_surprises ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_read_historical_macro_surprises"
ON historical_macro_surprises
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "anon_deny_insert_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_deny_insert_historical_macro_surprises"
ON historical_macro_surprises
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_deny_update_historical_macro_surprises"
ON historical_macro_surprises
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_deny_delete_historical_macro_surprises"
ON historical_macro_surprises
FOR DELETE
TO anon
USING (false);

CREATE INDEX IF NOT EXISTS idx_historical_macro_surprises_date
ON historical_macro_surprises (date);

CREATE INDEX IF NOT EXISTS idx_historical_macro_surprises_event_name
ON historical_macro_surprises (event_name);
