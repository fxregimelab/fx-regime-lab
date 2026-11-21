-- Aggregate snapshots are keyed by the exact evidence group, not date/pair alone.
BEGIN;
ALTER TABLE public.validation_stats
    ADD COLUMN IF NOT EXISTS data_source text DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS strategy_version text DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS model_version text DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS evaluation_version text DEFAULT 'legacy-unversioned',
    ADD COLUMN IF NOT EXISTS window_days integer DEFAULT 0,
    ADD COLUMN IF NOT EXISTS t5_rolling_90d_accuracy double precision,
    ADD COLUMN IF NOT EXISTS t20_rolling_90d_accuracy double precision,
    ADD COLUMN IF NOT EXISTS t5_mature_calls integer,
    ADD COLUMN IF NOT EXISTS t20_mature_calls integer,
    ADD COLUMN IF NOT EXISTS t5_pending_calls integer,
    ADD COLUMN IF NOT EXISTS t20_pending_calls integer,
    ADD COLUMN IF NOT EXISTS t5_unknown_direction_calls integer,
    ADD COLUMN IF NOT EXISTS t20_unknown_direction_calls integer,
    ADD COLUMN IF NOT EXISTS t5_abstention_calls integer,
    ADD COLUMN IF NOT EXISTS t20_abstention_calls integer,
    ADD COLUMN IF NOT EXISTS t5_missing_outcome_calls integer,
    ADD COLUMN IF NOT EXISTS t20_missing_outcome_calls integer,
    ADD COLUMN IF NOT EXISTS t5_probability_score_calls integer,
    ADD COLUMN IF NOT EXISTS t20_probability_score_calls integer,
    ADD COLUMN IF NOT EXISTS t5_calibration_calls integer,
    ADD COLUMN IF NOT EXISTS t20_calibration_calls integer,
    ADD COLUMN IF NOT EXISTS t5_net_directional_calls integer,
    ADD COLUMN IF NOT EXISTS t20_net_directional_calls integer,
    ADD COLUMN IF NOT EXISTS t5_mean_signed_gross_return_bps double precision,
    ADD COLUMN IF NOT EXISTS t20_mean_signed_gross_return_bps double precision,
    ADD COLUMN IF NOT EXISTS t5_cost_bps double precision,
    ADD COLUMN IF NOT EXISTS t20_cost_bps double precision;
-- Only derived snapshots are normalized here. Original calls/evaluations are untouched.
UPDATE public.validation_stats SET
    data_source = COALESCE(NULLIF(trim(data_source),''),'unknown'),
    strategy_version = COALESCE(NULLIF(trim(strategy_version),''),'unknown'),
    model_version = COALESCE(NULLIF(trim(model_version),''),'unknown'),
    evaluation_version = COALESCE(NULLIF(trim(evaluation_version),''),'legacy-unversioned'),
    window_days = COALESCE(window_days,0)
WHERE data_source IS NULL OR trim(data_source) = ''
   OR strategy_version IS NULL OR trim(strategy_version) = ''
   OR model_version IS NULL OR trim(model_version) = ''
   OR evaluation_version IS NULL OR trim(evaluation_version) = '' OR window_days IS NULL;
ALTER TABLE public.validation_stats
    ALTER COLUMN data_source SET NOT NULL,
    ALTER COLUMN strategy_version SET NOT NULL,
    ALTER COLUMN model_version SET NOT NULL,
    ALTER COLUMN evaluation_version SET NOT NULL,
    ALTER COLUMN window_days SET NOT NULL;
DROP INDEX IF EXISTS public.idx_validation_stats_as_of_pair;
DO $$ DECLARE c record; BEGIN
    FOR c IN SELECT con.conname FROM pg_constraint con
      WHERE con.conrelid = 'public.validation_stats'::regclass AND con.contype = 'u'
      AND (SELECT array_agg(a.attname::text ORDER BY a.attname)
           FROM unnest(con.conkey) AS k(attnum)
           JOIN pg_attribute a ON a.attrelid=con.conrelid AND a.attnum=k.attnum)
          = ARRAY['as_of_date','pair']
    LOOP EXECUTE format('ALTER TABLE public.validation_stats DROP CONSTRAINT %I',c.conname); END LOOP;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_stats_evidence_group
    ON public.validation_stats(as_of_date,pair,data_source,strategy_version,model_version,evaluation_version,window_days);
CREATE INDEX IF NOT EXISTS idx_validation_stats_evidence_lookup
    ON public.validation_stats(data_source,strategy_version,model_version,evaluation_version,window_days,pair,as_of_date DESC);
NOTIFY pgrst, 'reload schema';
COMMIT;
