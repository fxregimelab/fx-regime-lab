-- ============================================
-- FX Regime Lab v2.1.1 Migration
-- Add unique target for call_rationale ON CONFLICT upserts
-- ============================================

-- call_rationale is upserted by call_id in the pipeline. Postgres requires a
-- unique index/constraint as the ON CONFLICT target. The pre-existing plain
-- index on call_id is not sufficient and caused a 42P10 error on every run.
ALTER TABLE call_rationale
    ADD CONSTRAINT IF NOT EXISTS uq_call_rationale_call_id UNIQUE (call_id);

-- Keep the old plain index for any legacy query patterns that reference it.
CREATE INDEX IF NOT EXISTS idx_call_rationale_call_id ON call_rationale(call_id);
