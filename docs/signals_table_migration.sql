-- FX Regime Lab — `signals` table alignment with Python upserts
-- Apply in Supabase SQL Editor or via Supabase MCP `apply_migration`.
-- Idempotent: safe to re-run.

-- Spot price (master CSV EURUSD / USDJPY / USDINR) — required by core/signal_write._row_to_signal
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS spot double precision;
COMMENT ON COLUMN public.signals.spot IS 'FX spot from merged master (pair-specific)';

-- Upsert target: PostgREST on_conflict=date,pair requires a unique constraint on (date, pair).
-- (Usually already present as idx_signals_unique — verify with:)
-- SELECT indexname FROM pg_indexes WHERE tablename = 'signals';
