-- Migration: 20260505000000_round1_foundation_audit.sql
-- Goal: Align database with 3-Layer Signal Framework (CONTEXT.md)
-- Chambers: Strategy (Alpha) & Engineering (Engine)

-- 1. Update SIGNALS Table (Layer 2 + Layer 3 inputs per DATA_DICTIONARY.md)
ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS rate_diff_mom      double precision,
  ADD COLUMN IF NOT EXISTS cot_net_pos        integer,
  ADD COLUMN IF NOT EXISTS realized_vol_21    double precision,
  ADD COLUMN IF NOT EXISTS risk_reversal_25d  double precision;

COMMENT ON COLUMN public.signals.rate_diff_mom IS '4-week momentum of rate_diff_2y (Layer 2)';
COMMENT ON COLUMN public.signals.cot_net_pos IS 'NonCommercial net positioning, contracts (Layer 2)';
COMMENT ON COLUMN public.signals.realized_vol_21 IS '21-day annualized price volatility (Layer 3)';
COMMENT ON COLUMN public.signals.risk_reversal_25d IS '25-delta risk reversal (Put vs Call premium) (Layer 3)';

-- cot_percentile already exists (initial_schema); document Layer for framework alignment
COMMENT ON COLUMN public.signals.cot_percentile IS 'Net positioning vs 3-year rolling window (Layer 2)';

-- 2. Update REGIME_CALLS Table
ALTER TABLE public.regime_calls
  ADD COLUMN IF NOT EXISTS directional_bias      text,
  ADD COLUMN IF NOT EXISTS conviction            integer;

COMMENT ON COLUMN public.regime_calls.directional_bias IS 'Long, Short, or Neutral (Layer 2)';
COMMENT ON COLUMN public.regime_calls.conviction IS 'Conviction score from 1 (Low) to 5 (High) (Layer 2)';

-- regime is Layer 1 gate output (DATA_DICTIONARY); explicit comment for ledger clarity
COMMENT ON COLUMN public.regime_calls.regime IS 'Layer 1 regime classification (e.g. Carry Collapse)';

-- Named constraints: survive ADD COLUMN IF NOT EXISTS (column already present) and match DATA_DICTIONARY.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_conviction_range'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_conviction_range
      CHECK (conviction IS NULL OR (conviction >= 1 AND conviction <= 5));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_directional_bias_values'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_directional_bias_values
      CHECK (
        directional_bias IS NULL
        OR directional_bias IN ('Long', 'Short', 'Neutral')
      );
  END IF;
END $$;

-- 3. Update VALIDATION_LOG Table
ALTER TABLE public.validation_log
  ADD COLUMN IF NOT EXISTS call_id         integer REFERENCES public.regime_calls (id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS validation_date date,
  ADD COLUMN IF NOT EXISTS is_correct      boolean,
  ADD COLUMN IF NOT EXISTS pnl_bps         double precision;

COMMENT ON COLUMN public.validation_log.call_id IS 'Immutable reference to regime_calls.id';
COMMENT ON COLUMN public.validation_log.validation_date IS 'T+5 or T+20 observation date';
COMMENT ON COLUMN public.validation_log.is_correct IS 'True if directional bias matched price movement';
COMMENT ON COLUMN public.validation_log.pnl_bps IS 'Price movement in basis points since call';

-- FK joins and T+5 / T+20 lookups per call (PostgreSQL does not auto-index referencing columns)
CREATE INDEX IF NOT EXISTS idx_validation_log_call_id_valdate
  ON public.validation_log (call_id, validation_date)
  WHERE call_id IS NOT NULL;

-- 4. Enforcement of immutability (Phase 2)
-- Safe if mis-attached: only blocks UPDATE; INSERT/DELETE still work unless separate triggers exist.
CREATE OR REPLACE FUNCTION public.protect_immutable_calls()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'Regime calls are immutable once written to the ledger.';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Trigger not applied yet so the pipeline can settle (Chamber 2 audit).
