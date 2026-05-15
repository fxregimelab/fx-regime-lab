-- Migration: create_pipeline_runs (schema repair)
-- The pipeline writes to this table daily via write_pipeline_run() for observability.

CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id TEXT,
    date DATE NOT NULL,
    status TEXT,
    dqs_score DOUBLE PRECISION,
    pairs_processed INTEGER,
    pairs_skipped JSONB,
    ai_calls_made INTEGER,
    ai_calls_failed INTEGER,
    sources_used JSONB,
    duration_seconds DOUBLE PRECISION,
    errors JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, correlation_id)
);

ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_pipeline_runs" ON public.pipeline_runs;
CREATE POLICY "anon_read_pipeline_runs"
    ON public.pipeline_runs
    FOR SELECT
    TO anon
    USING (true);

DROP POLICY IF EXISTS "anon_deny_insert_pipeline_runs" ON public.pipeline_runs;
CREATE POLICY "anon_deny_insert_pipeline_runs"
    ON public.pipeline_runs
    FOR INSERT
    TO anon
    WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_pipeline_runs" ON public.pipeline_runs;
CREATE POLICY "anon_deny_update_pipeline_runs"
    ON public.pipeline_runs
    FOR UPDATE
    TO anon
    USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_pipeline_runs" ON public.pipeline_runs;
CREATE POLICY "anon_deny_delete_pipeline_runs"
    ON public.pipeline_runs
    FOR DELETE
    TO anon
    USING (false);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_date ON public.pipeline_runs (date DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_corr ON public.pipeline_runs (correlation_id);
