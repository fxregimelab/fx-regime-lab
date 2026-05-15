-- Migration: create_brief_log (schema repair)
-- The pipeline writes to this table daily via write_brief_log().

CREATE TABLE IF NOT EXISTS public.brief_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    brief_text TEXT,
    macro_context TEXT,
    dollar_dominance DOUBLE PRECISION,
    idiosyncratic_outlier TEXT,
    sentiment_json JSONB,
    pair_regimes JSONB,
    eurusd_regime TEXT,
    usdjpy_regime TEXT,
    usdinr_regime TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date)
);

ALTER TABLE public.brief_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_brief_log" ON public.brief_log;
CREATE POLICY "anon_read_brief_log"
    ON public.brief_log
    FOR SELECT
    TO anon
    USING (true);

DROP POLICY IF EXISTS "anon_deny_insert_brief_log" ON public.brief_log;
CREATE POLICY "anon_deny_insert_brief_log"
    ON public.brief_log
    FOR INSERT
    TO anon
    WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_brief_log" ON public.brief_log;
CREATE POLICY "anon_deny_update_brief_log"
    ON public.brief_log
    FOR UPDATE
    TO anon
    USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_brief_log" ON public.brief_log;
CREATE POLICY "anon_deny_delete_brief_log"
    ON public.brief_log
    FOR DELETE
    TO anon
    USING (false);

CREATE INDEX IF NOT EXISTS idx_brief_log_date ON public.brief_log (date DESC);
