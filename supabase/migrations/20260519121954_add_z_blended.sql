-- Add z_blended column to signals table (M.3.2 dual-horizon MAD Z blend)
-- This separates the composite rate signal (60% tactical + 40% structural)
-- from the raw tactical Z, fixing a semantic bug where rate_z_tactical
-- held different values in orchestrator vs simulation_engine.

ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS z_blended real;

COMMENT ON COLUMN public.signals.z_blended IS
  'Composite rate normalization: 60% tactical MAD Z + 40% structural MAD Z. The actual signal fed into the regime composite. (M.3.2)';
