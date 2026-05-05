-- Migration: 20260505000001_layer3_execution_schema.sql
-- Goal: Add columns for Layer 3 (Execution HUD) tracking.
-- Chambers: Strategy (Alpha) & Engineering (Engine)

-- 1. Update SIGNALS Table
ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS realized_vol_rank  double precision,
  ADD COLUMN IF NOT EXISTS skew_alignment      integer;

COMMENT ON COLUMN public.signals.realized_vol_rank IS 'Empirical CDF rank of 21d realized vol vs 3-year history (Layer 3)';
COMMENT ON COLUMN public.signals.skew_alignment IS 'Alignment between bias and 25d risk reversal (-1, 0, 1) (Layer 3)';

-- 2. Update REGIME_CALLS Table
ALTER TABLE public.regime_calls
  ADD COLUMN IF NOT EXISTS entry_timing   text,
  ADD COLUMN IF NOT EXISTS position_size  text,
  ADD COLUMN IF NOT EXISTS stop_level     double precision;

COMMENT ON COLUMN public.regime_calls.entry_timing IS 'ENTER or WAIT (Layer 3)';
COMMENT ON COLUMN public.regime_calls.position_size IS 'FULL or HALF (Layer 3)';
COMMENT ON COLUMN public.regime_calls.stop_level IS 'Calculated stop-loss level based on MIE/ADR (Layer 3)';

-- Constraints for Layer 3
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_entry_timing_values'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_entry_timing_values
      CHECK (entry_timing IS NULL OR entry_timing IN ('ENTER', 'WAIT'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_position_size_values'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_position_size_values
      CHECK (position_size IS NULL OR position_size IN ('FULL', 'HALF'));
  END IF;
END $$;
