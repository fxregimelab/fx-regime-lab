-- Forward repair for the documented integer-ID live schema (not a replacement
-- for the incomplete historical baseline). Old evaluation rows stay untouched.
BEGIN;

ALTER TABLE public.validation_log
    ADD COLUMN IF NOT EXISTS evaluation_version text NOT NULL DEFAULT 'legacy-unversioned',
    ADD COLUMN IF NOT EXISTS predicted_direction text,
    ADD COLUMN IF NOT EXISTS predicted_regime text,
    ADD COLUMN IF NOT EXISTS strategy_version text,
    ADD COLUMN IF NOT EXISTS model_version text,
    ADD COLUMN IF NOT EXISTS data_source text,
    ADD COLUMN IF NOT EXISTS log_return_net_bps_t5 double precision,
    ADD COLUMN IF NOT EXISTS log_return_net_bps_t20 double precision,
    ADD COLUMN IF NOT EXISTS correct_net_t5 boolean,
    ADD COLUMN IF NOT EXISTS correct_net_t20 boolean,
    ADD COLUMN IF NOT EXISTS cost_bps_t5 double precision,
    ADD COLUMN IF NOT EXISTS cost_bps_t20 double precision;

-- The legacy binary outcome cannot represent pending or abstained calls.
ALTER TABLE public.validation_log ALTER COLUMN outcome DROP NOT NULL;

-- Compare the whole record, so removed or newly added columns cannot bypass
-- immutability or make the trigger refer to columns that no longer exist.
CREATE OR REPLACE FUNCTION public.protect_immutable_validation()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.is_superseded = false AND NEW.is_superseded = true
       AND (to_jsonb(OLD) - 'is_superseded') = (to_jsonb(NEW) - 'is_superseded') THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Validation_log is immutable; append a new evaluation version';
END;
$$;
DROP TRIGGER IF EXISTS trg_protect_immutable_validation ON public.validation_log;
CREATE TRIGGER trg_protect_immutable_validation
    BEFORE UPDATE OR DELETE ON public.validation_log FOR EACH ROW
    EXECUTE FUNCTION public.protect_immutable_validation();

DROP INDEX IF EXISTS public.idx_validation_unique;
DROP INDEX IF EXISTS public.idx_validation_call_id;
DROP INDEX IF EXISTS public.idx_validation_call_pair;
-- An early baseline also used a table-level UNIQUE(pair,date) constraint.
DO $$
DECLARE c record;
BEGIN
    FOR c IN
        SELECT con.conname FROM pg_constraint con
        WHERE con.conrelid = 'public.validation_log'::regclass AND con.contype = 'u'
          AND (SELECT array_agg(a.attname::text ORDER BY a.attname)
               FROM unnest(con.conkey) AS k(attnum)
               JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum)
              IN (ARRAY['date','pair'], ARRAY['call_date','pair'], ARRAY['call_id'])
    LOOP
        EXECUTE format('ALTER TABLE public.validation_log DROP CONSTRAINT %I', c.conname);
    END LOOP;
END;
$$;
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_current_evaluation
    ON public.validation_log(call_id, evaluation_version)
    WHERE call_id IS NOT NULL AND is_superseded = false;
CREATE INDEX IF NOT EXISTS idx_validation_evaluation_pair_date
    ON public.validation_log(evaluation_version, pair, call_date)
    WHERE is_superseded = false;

CREATE OR REPLACE FUNCTION public.append_validation_evaluation(p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public AS $$
DECLARE
    published public.regime_calls%ROWTYPE;
    prior public.validation_log%ROWTYPE;
    prior_json jsonb;
    candidate jsonb;
    saved jsonb;
    key text;
    horizon text;
    horizon_fields text[];
    cols text;
    allowed constant text[] := ARRAY[
        'call_id','date','call_date','pair','evaluation_version',
        'predicted_direction','predicted_regime','confidence','strategy_version','model_version','data_source',
        'log_return_t5_bps','correct_t5','brier_score_t5','actual_direction_t5',
        'actual_return_5d','correct_5d','brier_5d','log_return_net_bps_t5','correct_net_t5','cost_bps_t5',
        'log_return_t20_bps','correct_t20','brier_score_t20','actual_direction_t20',
        'actual_return_20d','correct_20d','brier_20d','log_return_net_bps_t20','correct_net_t20','cost_bps_t20'
    ];
BEGIN
    IF jsonb_typeof(p_payload) IS DISTINCT FROM 'object'
       OR p_payload->>'evaluation_version' IS DISTINCT FROM 'published-direction-v1'
       OR nullif(p_payload->>'call_id','') IS NULL THEN
        RAISE EXCEPTION 'Explicit published call identity and supported evaluation version required';
    END IF;
    FOR key IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT key = ANY(allowed) THEN
            RAISE EXCEPTION 'Unknown evaluation field: %', key;
        END IF;
    END LOOP;
    -- Lock the immutable parent, including when no evaluation row exists yet.
    -- This serializes simultaneous T+5/T+20 writers without a lost update.
    SELECT * INTO published FROM public.regime_calls
        WHERE id::text = p_payload->>'call_id' FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Published call does not exist'; END IF;
    IF p_payload->>'pair' IS DISTINCT FROM published.pair
       OR p_payload->>'call_date' IS DISTINCT FROM published.date::text
       OR (p_payload ? 'date' AND p_payload->>'date' IS DISTINCT FROM published.date::text)
       OR published.predicted_direction IS NULL
       OR published.predicted_direction NOT IN ('BULLISH','BEARISH','NEUTRAL') THEN
        RAISE EXCEPTION 'Evaluation does not match the published call';
    END IF;
    candidate := jsonb_build_object(
        'call_id', published.id, 'date', published.date, 'call_date', published.date,
        'pair', published.pair, 'evaluation_version', p_payload->>'evaluation_version',
        'predicted_direction', published.predicted_direction,
        'predicted_regime', published.regime, 'confidence', published.confidence,
        'strategy_version', published.strategy_version, 'model_version', published.model_version,
        'data_source', published.data_source
    );
    FOREACH key IN ARRAY ARRAY['predicted_direction','predicted_regime','confidence','strategy_version','model_version','data_source'] LOOP
        IF p_payload ? key AND p_payload->key IS DISTINCT FROM candidate->key THEN
            RAISE EXCEPTION 'Published metadata mismatch: %', key;
        END IF;
    END LOOP;
    SELECT * INTO prior FROM public.validation_log
        WHERE call_id = published.id
          AND evaluation_version = p_payload->>'evaluation_version'
          AND is_superseded = false FOR UPDATE;
    prior_json := CASE WHEN FOUND THEN to_jsonb(prior) ELSE '{}'::jsonb END;
    -- Carry the previous row forward, excluding its generated identity/time.
    candidate := (prior_json - ARRAY['id','created_at']) || p_payload || candidate;
    candidate := candidate || jsonb_build_object('call', published.predicted_direction, 'is_superseded', false);

    FOREACH horizon IN ARRAY ARRAY['t5','t20'] LOOP
        horizon_fields := ARRAY[
            'log_return_'||horizon||'_bps','correct_'||horizon,'brier_score_'||horizon,
            'actual_direction_'||horizon,'log_return_net_bps_'||horizon,
            'correct_net_'||horizon,'cost_bps_'||horizon
        ];
        IF prior_json->>('log_return_'||horizon||'_bps') IS NOT NULL THEN
            FOREACH key IN ARRAY horizon_fields || CASE WHEN horizon='t5'
                THEN ARRAY['actual_return_5d','correct_5d','brier_5d']
                ELSE ARRAY['actual_return_20d','correct_20d','brier_20d'] END LOOP
                IF p_payload ? key AND p_payload->key IS DISTINCT FROM prior_json->key THEN
                    RAISE EXCEPTION 'Completed horizon is immutable: %', key;
                END IF;
            END LOOP;
        END IF;
        IF candidate->>('log_return_'||horizon||'_bps') IS NOT NULL THEN
            IF NOT candidate ?& horizon_fields THEN RAISE EXCEPTION 'Incomplete horizon: %', horizon; END IF;
            FOREACH key IN ARRAY ARRAY['log_return_'||horizon||'_bps','cost_bps_'||horizon] LOOP
                IF jsonb_typeof(candidate->key) IS DISTINCT FROM 'number' THEN
                    RAISE EXCEPTION 'Finite numeric horizon field required: %', key;
                END IF;
            END LOOP;
            IF (candidate->>('cost_bps_'||horizon))::float8 <= 0 THEN
                RAISE EXCEPTION 'Positive cost assumption required';
            END IF;
            IF candidate->>('actual_direction_'||horizon) IS NULL
               OR candidate->>('actual_direction_'||horizon) NOT IN ('UP','DOWN','NEUTRAL') THEN
                RAISE EXCEPTION 'Actual direction required';
            END IF;
            IF published.predicted_direction = 'NEUTRAL' THEN
                FOREACH key IN ARRAY ARRAY['correct_'||horizon,'brier_score_'||horizon,
                    'log_return_net_bps_'||horizon,'correct_net_'||horizon] LOOP
                    IF candidate->key IS DISTINCT FROM 'null'::jsonb THEN
                        RAISE EXCEPTION 'Abstention must have null scores: %', key;
                    END IF;
                END LOOP;
            ELSE
                IF jsonb_typeof(candidate->('correct_'||horizon)) IS DISTINCT FROM 'boolean'
                   OR jsonb_typeof(candidate->('correct_net_'||horizon)) IS DISTINCT FROM 'boolean'
                   OR jsonb_typeof(candidate->('log_return_net_bps_'||horizon)) IS DISTINCT FROM 'number'
                   OR jsonb_typeof(candidate->('brier_score_'||horizon)) IS DISTINCT FROM 'number'
                   OR (candidate->>('brier_score_'||horizon))::float8 NOT BETWEEN 0 AND 1 THEN
                    RAISE EXCEPTION 'Directional scores must be valid numbers and booleans';
                END IF;
            END IF;
        ELSIF EXISTS (SELECT 1 FROM unnest(horizon_fields) AS f WHERE candidate->>f IS NOT NULL) THEN
            RAISE EXCEPTION 'Horizon fields without a market return';
        END IF;
    END LOOP;
    IF candidate->>'log_return_t5_bps' IS NULL AND candidate->>'log_return_t20_bps' IS NULL THEN
        RAISE EXCEPTION 'At least one completed horizon required';
    END IF;
    -- Legacy outcome remains unavailable; horizon-specific flags are authoritative.
    candidate := candidate || jsonb_build_object('outcome', NULL);
    IF (prior_json - ARRAY['id','created_at']) = candidate THEN RETURN prior_json; END IF;
    IF prior_json <> '{}'::jsonb THEN
        UPDATE public.validation_log SET is_superseded = true WHERE id = prior.id;
    END IF;
    SELECT string_agg(format('%I', k), ',' ORDER BY k) INTO cols FROM jsonb_object_keys(candidate) AS k;
    EXECUTE format(
        'INSERT INTO public.validation_log (%s) SELECT %s FROM jsonb_populate_record(NULL::public.validation_log, $1) RETURNING to_jsonb(validation_log)',
        cols, cols
    ) INTO saved USING candidate;
    RETURN saved;
END;
$$;

REVOKE ALL ON FUNCTION public.append_validation_evaluation(jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.append_validation_evaluation(jsonb) TO service_role;
COMMENT ON COLUMN public.validation_log.evaluation_version IS
    'Scoring definition, separate from forecast model version. Legacy rows are not retrospectively relabeled.';
NOTIFY pgrst, 'reload schema';
COMMIT;
