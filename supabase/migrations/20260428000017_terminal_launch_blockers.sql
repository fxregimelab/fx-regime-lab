-- G10 terminal: dual rate Z, breakeven, tail risk columns (service-role writes only; RLS unchanged).

ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS breakeven_inflation_10y double precision,
  ADD COLUMN IF NOT EXISTS rate_diff_10y_real double precision,
  ADD COLUMN IF NOT EXISTS rate_z_tactical double precision,
  ADD COLUMN IF NOT EXISTS rate_z_structural double precision;

COMMENT ON COLUMN public.signals.breakeven_inflation_10y IS 'FRED T10YIE (10Y breakeven inflation, %).';
COMMENT ON COLUMN public.signals.rate_diff_10y_real IS 'Nominal 10Y spread minus breakeven (real tilt, heuristic).';
COMMENT ON COLUMN public.signals.rate_z_tactical IS 'MAD Z on carry: 252-day window.';
COMMENT ON COLUMN public.signals.rate_z_structural IS 'MAD Z on carry: 2520-day window.';

ALTER TABLE public.event_risk_matrices
  ADD COLUMN IF NOT EXISTS t1_tail_risk_p95 double precision,
  ADD COLUMN IF NOT EXISTS t1_tail_risk_p05 double precision;

COMMENT ON COLUMN public.event_risk_matrices.t1_tail_risk_p95 IS 'Historical T+1 return 95th percentile (%).';
COMMENT ON COLUMN public.event_risk_matrices.t1_tail_risk_p05 IS 'Historical T+1 return 5th percentile (%).';
