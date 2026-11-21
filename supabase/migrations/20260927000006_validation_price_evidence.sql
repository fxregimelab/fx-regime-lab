-- Forward-only price evidence contract. No published rows or statistics are rewritten.
BEGIN;
ALTER TABLE public.validation_log
    ADD COLUMN IF NOT EXISTS entry_price_evidence jsonb,
    ADD COLUMN IF NOT EXISTS price_evidence_t5 jsonb,
    ADD COLUMN IF NOT EXISTS price_evidence_t20 jsonb;
-- Keep the original scoring contract callable only through the version dispatcher.
DO $$ BEGIN
    IF to_regprocedure('public.append_validation_evaluation_v1(jsonb)') IS NULL THEN
        ALTER FUNCTION public.append_validation_evaluation(jsonb) RENAME TO append_validation_evaluation_v1;
    END IF;
END $$;
CREATE OR REPLACE FUNCTION public.validation_finite_number(value jsonb, positive boolean)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE number double precision;
BEGIN
    IF jsonb_typeof(value) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
    number := (value #>> '{}')::double precision;
    RETURN number > '-Infinity'::float8 AND number < 'Infinity'::float8
        AND (NOT positive OR number > 0);
EXCEPTION WHEN numeric_value_out_of_range OR invalid_text_representation THEN RETURN false;
END $$;
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
    original_signal jsonb;
    evidence jsonb;
    expected jsonb;
    expected_entry jsonb;
    endpoint_day date;
    steps integer;
    market_close double precision;
    raw_return double precision;
    net_return double precision;
    expected_cost double precision;
    expected_correct boolean;
    actual text;
    days text;
    allowed constant text[] := ARRAY[
        'call_id','date','call_date','pair','evaluation_version',
        'entry_price_evidence','price_evidence_t5','price_evidence_t20',
        'predicted_direction','predicted_regime','confidence','strategy_version','model_version','data_source',
        'log_return_t5_bps','correct_t5','brier_score_t5','actual_direction_t5',
        'actual_return_5d','correct_5d','brier_5d','log_return_net_bps_t5','correct_net_t5','cost_bps_t5',
        'log_return_t20_bps','correct_t20','brier_score_t20','actual_direction_t20',
        'actual_return_20d','correct_20d','brier_20d','log_return_net_bps_t20','correct_net_t20','cost_bps_t20'
    ];
BEGIN
    IF p_payload->>'evaluation_version' = 'published-direction-v1' THEN
        RETURN public.append_validation_evaluation_v1(p_payload);
    END IF;
    IF jsonb_typeof(p_payload) IS DISTINCT FROM 'object'
       OR p_payload->>'evaluation_version' IS DISTINCT FROM 'publication-snapshot-v2'
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

    SELECT signal_payload INTO original_signal FROM public.publication_evidence
        WHERE call_id = published.id;
    IF NOT FOUND OR original_signal->>'pair' IS DISTINCT FROM published.pair
       OR original_signal->>'date' IS DISTINCT FROM published.date::text
       OR NOT public.validation_finite_number(original_signal->'spot', true) THEN
        RAISE EXCEPTION 'Original publication entry evidence required';
    END IF;
    expected_entry := jsonb_build_object('kind','publication_signal','pair',published.pair,
        'date',published.date,'price',original_signal->'spot','call_id',published.id,
        'source','publication_evidence.signal_payload.spot');
    IF candidate->'entry_price_evidence' IS DISTINCT FROM expected_entry THEN
        RAISE EXCEPTION 'Entry evidence does not match original publication';
    END IF;
    IF prior_json->>'entry_price_evidence' IS NOT NULL
       AND candidate->'entry_price_evidence' IS DISTINCT FROM prior_json->'entry_price_evidence' THEN
        RAISE EXCEPTION 'Entry evidence is immutable';
    END IF;
    expected_cost := CASE published.pair WHEN 'EURUSD' THEN 0.2 WHEN 'USDJPY' THEN 0.3
        WHEN 'USDINR' THEN 10.0 ELSE NULL END;
    IF expected_cost IS NULL OR (published.confidence IS NOT NULL AND
       NOT (published.confidence >= 0 AND published.confidence <= 1))
       OR (published.predicted_direction <> 'NEUTRAL' AND published.confidence IS NULL) THEN
        RAISE EXCEPTION 'Invalid published confidence or pair';
    END IF;

    FOREACH horizon IN ARRAY ARRAY['t5','t20'] LOOP
        horizon_fields := ARRAY[
            'log_return_'||horizon||'_bps','correct_'||horizon,'brier_score_'||horizon,
            'actual_direction_'||horizon,'log_return_net_bps_'||horizon,
            'correct_net_'||horizon,'cost_bps_'||horizon,'price_evidence_'||horizon
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
            endpoint_day := published.date;
            steps := 0;
            WHILE steps < CASE horizon WHEN 't5' THEN 5 ELSE 20 END LOOP
                endpoint_day := endpoint_day + 1;
                IF extract(isodow FROM endpoint_day) < 6 THEN steps := steps + 1; END IF;
            END LOOP;
            evidence := candidate->('price_evidence_'||horizon);
            IF NOT public.validation_finite_number(evidence->'price', true) THEN
                RAISE EXCEPTION 'Finite positive endpoint evidence price required';
            END IF;
            expected := jsonb_build_object('kind','historical_close','pair',published.pair,
                'date',endpoint_day,'price',evidence->'price','source','historical_prices.close');
            IF evidence IS DISTINCT FROM expected THEN
                RAISE EXCEPTION 'Endpoint evidence identity or horizon mismatch';
            END IF;
            -- Check first completion against the selected storage row. Completed
            -- revisions never reread this mutable table, including retries.
            IF prior_json->>('log_return_'||horizon||'_bps') IS NULL THEN
                IF endpoint_day > (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date THEN
                    RAISE EXCEPTION 'Endpoint horizon has not matured';
                END IF;
                SELECT close INTO market_close FROM public.historical_prices
                    WHERE pair=published.pair AND date=endpoint_day FOR SHARE;
                IF NOT FOUND OR NOT public.validation_finite_number(to_jsonb(market_close),true)
                   OR to_jsonb(market_close) IS DISTINCT FROM evidence->'price' THEN
                    RAISE EXCEPTION 'Endpoint evidence does not match historical close';
                END IF;
            END IF;
            raw_return := 10000.0 * ln((evidence->>'price')::float8 /
                (expected_entry->>'price')::float8);
            actual := CASE WHEN raw_return > 5 THEN 'UP' WHEN raw_return < -5 THEN 'DOWN' ELSE 'NEUTRAL' END;
            expected_correct := CASE published.predicted_direction WHEN 'BULLISH' THEN actual='UP'
                WHEN 'BEARISH' THEN actual='DOWN' ELSE NULL END;
            net_return := CASE published.predicted_direction WHEN 'BULLISH' THEN raw_return-expected_cost
                WHEN 'BEARISH' THEN -raw_return-expected_cost ELSE NULL END;
            expected := jsonb_build_object('log_return_'||horizon||'_bps',raw_return,
                'actual_direction_'||horizon,actual,'correct_'||horizon,expected_correct,
                'cost_bps_'||horizon,expected_cost,'log_return_net_bps_'||horizon,net_return,
                'correct_net_'||horizon,net_return>0,'brier_score_'||horizon,
                CASE WHEN expected_correct IS NULL THEN NULL
                ELSE power(published.confidence - CASE WHEN expected_correct THEN 1 ELSE 0 END, 2) END);
            days := CASE horizon WHEN 't5' THEN '5d' ELSE '20d' END;
            expected := expected || jsonb_build_object('actual_return_'||days,raw_return/10000.0,
                'correct_'||days,expected_correct,'brier_'||days,expected->('brier_score_'||horizon));
            FOR key IN SELECT jsonb_object_keys(expected) LOOP
                -- Legacy aliases are optional but cannot contradict the canonical fields.
                IF key=ANY(ARRAY['actual_return_'||days,'correct_'||days,'brier_'||days])
                   AND candidate->>key IS NULL THEN CONTINUE; END IF;
                IF key='cost_bps_'||horizon AND candidate->key IS DISTINCT FROM expected->key THEN
                    RAISE EXCEPTION 'Metric inconsistent with price evidence: %',key;
                END IF;
                IF jsonb_typeof(expected->key)='number' THEN
                    IF NOT public.validation_finite_number(candidate->key,false)
                       OR abs((candidate->>key)::float8-(expected->>key)::float8) > 1e-9 THEN
                        RAISE EXCEPTION 'Metric inconsistent with price evidence: %',key;
                    END IF;
                ELSIF candidate->key IS DISTINCT FROM expected->key THEN
                    RAISE EXCEPTION 'Metric inconsistent with price evidence: %',key;
                END IF;
            END LOOP;
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
        ELSIF EXISTS (SELECT 1 FROM unnest(horizon_fields || CASE WHEN horizon='t5'
            THEN ARRAY['actual_return_5d','correct_5d','brier_5d']
            ELSE ARRAY['actual_return_20d','correct_20d','brier_20d'] END) AS f
            WHERE candidate->>f IS NOT NULL) THEN
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

CREATE OR REPLACE VIEW public.validation_observations
WITH (security_invoker = true) AS
SELECT c.id AS id, c.id AS call_id, c.date, c.date AS call_date, c.pair,
       c.predicted_direction, c.regime AS predicted_regime, c.confidence,
       COALESCE(NULLIF(trim(c.data_source), ''), 'unknown') AS data_source,
       COALESCE(NULLIF(trim(c.strategy_version), ''), 'unknown') AS strategy_version,
       COALESCE(NULLIF(trim(c.model_version), ''), 'unknown') AS model_version,
       'publication-snapshot-v2'::text AS evaluation_version,
       'published-calls-v1'::text AS population_version,
       v.id AS evaluation_id, (v.id IS NOT NULL) AS evaluation_present,
       v.log_return_t5_bps, v.correct_t5, v.brier_score_t5,
       v.log_return_net_bps_t5, v.correct_net_t5, v.cost_bps_t5,
       v.log_return_t20_bps, v.correct_t20, v.brier_score_t20,
       v.log_return_net_bps_t20, v.correct_net_t20, v.cost_bps_t20
FROM public.regime_calls c
LEFT JOIN public.validation_log v ON v.call_id = c.id
  AND v.evaluation_version = 'publication-snapshot-v2' AND v.is_superseded = false;
COMMENT ON VIEW public.validation_observations IS
  'Read-only published-call population for canonical scoring. Missing evaluation_id is not an evaluated outcome; evaluation_version names the requested scoring definition.';
REVOKE ALL ON public.validation_observations FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.validation_observations TO anon, authenticated, service_role;

REVOKE ALL ON FUNCTION public.append_validation_evaluation_v1(jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.validation_finite_number(jsonb,boolean) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.append_validation_evaluation(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.append_validation_evaluation(jsonb) TO service_role;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON public.validation_log FROM PUBLIC,anon,authenticated,service_role;
COMMENT ON COLUMN public.validation_log.entry_price_evidence IS 'Exact immutable original publication signal price; not an executable entry.';
COMMENT ON COLUMN public.validation_log.price_evidence_t5 IS 'Exact historical close storage snapshot, not proof of original provider provenance.';
COMMENT ON COLUMN public.validation_log.price_evidence_t20 IS 'Exact historical close storage snapshot, not proof of original provider provenance.';
NOTIFY pgrst, 'reload schema';
COMMIT;
