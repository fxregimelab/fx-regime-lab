-- Every persisted call stays visible even when no canonical evaluation exists.
-- PostgreSQL 15+ security_invoker keeps the caller's underlying table RLS.
BEGIN;
CREATE OR REPLACE VIEW public.validation_observations
WITH (security_invoker = true) AS
SELECT c.id AS id, c.id AS call_id, c.date, c.date AS call_date, c.pair,
       c.predicted_direction, c.regime AS predicted_regime, c.confidence,
       COALESCE(NULLIF(trim(c.data_source), ''), 'unknown') AS data_source,
       COALESCE(NULLIF(trim(c.strategy_version), ''), 'unknown') AS strategy_version,
       COALESCE(NULLIF(trim(c.model_version), ''), 'unknown') AS model_version,
       'published-direction-v1'::text AS evaluation_version,
       'published-calls-v1'::text AS population_version,
       v.id AS evaluation_id, (v.id IS NOT NULL) AS evaluation_present,
       v.log_return_t5_bps, v.correct_t5, v.brier_score_t5,
       v.log_return_net_bps_t5, v.correct_net_t5, v.cost_bps_t5,
       v.log_return_t20_bps, v.correct_t20, v.brier_score_t20,
       v.log_return_net_bps_t20, v.correct_net_t20, v.cost_bps_t20
FROM public.regime_calls c
LEFT JOIN public.validation_log v ON v.call_id = c.id
  AND v.evaluation_version = 'published-direction-v1' AND v.is_superseded = false;
COMMENT ON VIEW public.validation_observations IS
  'Read-only published-call population for canonical scoring. Missing evaluation_id is not an evaluated outcome; evaluation_version names the requested scoring definition.';
REVOKE ALL ON public.validation_observations FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.validation_observations TO anon, authenticated, service_role;

ALTER TABLE public.validation_stats
  ADD COLUMN IF NOT EXISTS population_version text NOT NULL DEFAULT 'evaluation-records-v1',
  ADD COLUMN IF NOT EXISTS t5_evaluation_calls integer,
  ADD COLUMN IF NOT EXISTS t20_evaluation_calls integer,
  ADD COLUMN IF NOT EXISTS t5_missing_evaluation_calls integer,
  ADD COLUMN IF NOT EXISTS t20_missing_evaluation_calls integer;
DROP INDEX IF EXISTS public.idx_validation_stats_evidence_group;
CREATE UNIQUE INDEX idx_validation_stats_evidence_group
  ON public.validation_stats(as_of_date,pair,data_source,strategy_version,model_version,
                            evaluation_version,window_days,population_version);
CREATE INDEX IF NOT EXISTS idx_validation_stats_population_lookup
  ON public.validation_stats(population_version,data_source,strategy_version,model_version,
                            evaluation_version,window_days,pair,as_of_date DESC);
NOTIFY pgrst, 'reload schema';
COMMIT;
