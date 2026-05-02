-- T+1 return distribution bands for Convexity Radar (percent units).

ALTER TABLE public.event_risk_matrices
  ADD COLUMN IF NOT EXISTS inline_median_return DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p2_5 DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p16 DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p84 DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p97_5 DOUBLE PRECISION;

COMMENT ON COLUMN public.event_risk_matrices.inline_median_return IS
  'Median T+1 close/close return (%) for IN-LINE surprise bucket.';
COMMENT ON COLUMN public.event_risk_matrices.t1_exhaustion_p16 IS
  '16th percentile of T+1 returns (%) — inner exhaustion band.';
COMMENT ON COLUMN public.event_risk_matrices.t1_exhaustion_p84 IS
  '84th percentile of T+1 returns (%) — inner exhaustion band.';
