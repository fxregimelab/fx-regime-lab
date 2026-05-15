-- Pipeline runs health snapshot table
-- Stores daily pipeline execution metadata for the health dashboard.
-- Safe to run multiple times (idempotent).

CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    steps_completed TEXT[] DEFAULT '{}',
    steps_failed TEXT[] DEFAULT '{}',
    dqs_score NUMERIC,
    regime_calls_count INT,
    validation_stats_computed BOOLEAN DEFAULT FALSE,
    ai_briefs_generated BOOLEAN DEFAULT FALSE,
    macro_event_briefs_generated BOOLEAN DEFAULT FALSE,
    errors JSONB DEFAULT '[]',
    duration_seconds NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_date
    ON public.pipeline_runs (date DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON public.pipeline_runs (status);

ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Drop any anon policies
DROP POLICY IF EXISTS "anon_read_pipeline_runs" ON public.pipeline_runs;
