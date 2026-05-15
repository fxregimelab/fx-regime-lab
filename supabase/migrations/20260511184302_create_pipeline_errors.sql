-- Migration: create_pipeline_errors (schema repair)
-- The pipeline writes to this table via write_pipeline_error() for structured error logging.

CREATE TABLE IF NOT EXISTS public.pipeline_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step TEXT NOT NULL,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    traceback TEXT,
    correlation_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Service-role only: no anon or authenticated access
ALTER TABLE public.pipeline_errors ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.pipeline_errors FROM anon, authenticated;
GRANT ALL ON public.pipeline_errors TO service_role;

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_date ON public.pipeline_errors (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_corr ON public.pipeline_errors (correlation_id);
