-- P1-T3: Audit Trail Hardening
-- Adds write_hash, correlation_id, and pipeline_errors table

-- ───────────────────────────────────────────────────────────────────────────
-- 1. regime_calls: tamper-evident hash + distributed tracing
-- ───────────────────────────────────────────────────────────────────────────

ALTER TABLE public.regime_calls
    ADD COLUMN IF NOT EXISTS write_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_regime_calls_correlation
    ON public.regime_calls (correlation_id)
    WHERE correlation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_regime_calls_write_hash
    ON public.regime_calls (write_hash)
    WHERE write_hash IS NOT NULL;

-- ───────────────────────────────────────────────────────────────────────────
-- 2. audit_log: link audit events to pipeline runs
-- ───────────────────────────────────────────────────────────────────────────

ALTER TABLE public.audit_log
    ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_audit_log_correlation
    ON public.audit_log (correlation_id)
    WHERE correlation_id IS NOT NULL;

-- ───────────────────────────────────────────────────────────────────────────
-- 3. pipeline_errors: structured exception logging
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.pipeline_errors (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id VARCHAR(64),
    step           TEXT NOT NULL,
    error_type     TEXT,
    message        TEXT,
    traceback      TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_correlation
    ON public.pipeline_errors (correlation_id)
    WHERE correlation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_created
    ON public.pipeline_errors (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_errors_step
    ON public.pipeline_errors (step, created_at DESC);

ALTER TABLE public.pipeline_errors ENABLE ROW LEVEL SECURITY;

-- No anon SELECT policy — internal ops only
