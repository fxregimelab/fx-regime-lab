-- Phase 2.2: pre-computed regime-conditioned event risk matrices

CREATE TABLE IF NOT EXISTS event_risk_matrices (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date                   DATE NOT NULL,
    pair                   TEXT NOT NULL,
    event_name             TEXT NOT NULL,
    active_regime          TEXT NOT NULL,
    sample_size            INT NOT NULL,
    median_mie_multiplier  DOUBLE PRECISION,
    beat_median_return     DOUBLE PRECISION,
    miss_median_return     DOUBLE PRECISION,
    asymmetry_ratio        DOUBLE PRECISION,
    asymmetry_direction    TEXT,
    ai_context             TEXT,
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, pair, event_name)
);

ALTER TABLE event_risk_matrices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_read_event_risk_matrices"
ON event_risk_matrices
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "anon_deny_insert_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_deny_insert_event_risk_matrices"
ON event_risk_matrices
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_deny_update_event_risk_matrices"
ON event_risk_matrices
FOR UPDATE
TO anon
USING (false)
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_delete_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_deny_delete_event_risk_matrices"
ON event_risk_matrices
FOR DELETE
TO anon
USING (false);

CREATE INDEX IF NOT EXISTS idx_event_risk_matrices_date
ON event_risk_matrices (date);

CREATE INDEX IF NOT EXISTS idx_event_risk_matrices_pair_event
ON event_risk_matrices (pair, event_name);
