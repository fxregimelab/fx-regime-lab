-- Update UNIQUE constraint on regime_calls to allow v2 and v3 calls
-- for the same (pair, date) combination.

-- 1. Drop the old unique constraint on (pair, date)
DO $$
BEGIN
  ALTER TABLE public.regime_calls
    DROP CONSTRAINT IF EXISTS regime_calls_pair_date_key;
EXCEPTION
  WHEN undefined_object THEN
    NULL;
END $$;

-- 2. Add a new partial unique index:
--    v2 calls remain unique on (pair, date) as before
--    v3 calls are also unique on (pair, date) within their own model_version
--    This allows one v2 + one v3 call per pair/date.
CREATE UNIQUE INDEX IF NOT EXISTS idx_regime_calls_pair_date_model
  ON public.regime_calls (pair, date, (COALESCE(meta->>'model_version', 'v2')));

-- 3. Keep a plain unique index for v2 (backward compatibility / safety)
CREATE UNIQUE INDEX IF NOT EXISTS idx_regime_calls_pair_date_v2
  ON public.regime_calls (pair, date)
  WHERE meta->>'model_version' IS NULL OR meta->>'model_version' = 'v2';

-- 4. Add a check constraint to prevent duplicate v3 calls
CREATE UNIQUE INDEX IF NOT EXISTS idx_regime_calls_pair_date_v3
  ON public.regime_calls (pair, date)
  WHERE meta->>'model_version' = 'v3';
