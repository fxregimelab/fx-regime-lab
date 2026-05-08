-- P1-T3: Audit Trail Schema Fix
-- Fixes partial migration state by adding missing columns idempotently.
-- Safe to run multiple times.

-- ───────────────────────────────────────────────────────────────────────────
-- 1. regime_calls: add audit columns if missing
-- ───────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'regime_calls' AND column_name = 'correlation_id'
    ) THEN
        ALTER TABLE public.regime_calls ADD COLUMN correlation_id TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'regime_calls' AND column_name = 'write_hash'
    ) THEN
        ALTER TABLE public.regime_calls ADD COLUMN write_hash TEXT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_regime_calls_correlation_id
    ON public.regime_calls (correlation_id);

-- ───────────────────────────────────────────────────────────────────────────
-- 2. audit_log: add correlation_id if missing
-- ───────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_log' AND column_name = 'correlation_id'
    ) THEN
        ALTER TABLE public.audit_log ADD COLUMN correlation_id TEXT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_audit_log_correlation
    ON public.audit_log (correlation_id)
    WHERE correlation_id IS NOT NULL;

-- ───────────────────────────────────────────────────────────────────────────
-- 3. pipeline_errors: add missing columns to existing table
-- ───────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'step'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN step TEXT NOT NULL DEFAULT 'unknown';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'error_type'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN error_type TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'message'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN message TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'traceback'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN traceback TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'correlation_id'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN correlation_id TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pipeline_errors' AND column_name = 'run_date'
    ) THEN
        ALTER TABLE public.pipeline_errors ADD COLUMN run_date DATE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_created_at
    ON public.pipeline_errors (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_correlation_id
    ON public.pipeline_errors (correlation_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_run_date
    ON public.pipeline_errors (run_date DESC);

-- Enable RLS if not already enabled
ALTER TABLE public.pipeline_errors ENABLE ROW LEVEL SECURITY;

-- Drop any anon policies
DROP POLICY IF EXISTS "anon_read_pipeline_errors" ON public.pipeline_errors;
