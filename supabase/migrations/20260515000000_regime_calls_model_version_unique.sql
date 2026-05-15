-- Update UNIQUE constraint on regime_calls to allow v2 and v3 calls
-- for the same (pair, date) combination by including model_version.

-- 1. Drop the old unique constraint on (date, pair)
DROP INDEX IF EXISTS public.idx_regime_unique;

-- 2. Create a new unique index on (date, pair, model_version)
--    This allows one call per pair/date for each model version.
CREATE UNIQUE INDEX idx_regime_unique_model_version
  ON public.regime_calls (date, pair, model_version);

-- 3. Backfill existing rows: set NULL model_version to 'v2' (legacy)
UPDATE public.regime_calls
  SET model_version = 'v2'
  WHERE model_version IS NULL;
