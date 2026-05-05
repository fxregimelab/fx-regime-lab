-- Pillar 3: Mean Reversion Tracking for Event Risk Radar

ALTER TABLE public.event_risk_matrices 
ADD COLUMN IF NOT EXISTS mean_reversion_prob DOUBLE PRECISION;

COMMENT ON COLUMN public.event_risk_matrices.mean_reversion_prob 
IS 'Probability (0-100) that price returns to within 20% of the daily range from the Open by end of T+0.';
