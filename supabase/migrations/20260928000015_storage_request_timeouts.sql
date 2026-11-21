-- Bound storage requests using the inherited top-level request timer.
-- Function-local statement_timeout cannot arm that timer.
BEGIN;

CREATE OR REPLACE FUNCTION public.append_validation_evaluation(p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
SET lock_timeout = '10s' AS $$
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
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
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

CREATE OR REPLACE FUNCTION public.append_regime_publication(
  p_call jsonb, p_signal jsonb, p_rationale jsonb,
  p_supersedes_call_id integer DEFAULT NULL
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public
SET lock_timeout = '10s' AS $$
DECLARE
  call_data jsonb;
  signal_data jsonb;
  rationale_data jsonb;
  semantic jsonb;
  fingerprint text;
  saved public.publication_evidence%ROWTYPE;
  published_id integer;
  predecessor public.regime_calls%ROWTYPE;
  key text;
  value jsonb;
  columns_sql text;
  updates_sql text;
  row_data jsonb;
  call_fields constant text[] := ARRAY[
    'pair','date','regime','confidence','signal_composite','rate_signal','primary_driver',
    'entry_timing','position_size','stop_level','data_quality_score','stress_level',
    'predicted_direction','directional_bias','conviction','cot_signal','vol_signal','oi_signal',
    'rr_signal','special_signal_value','special_signal_label','regime_category','model_version',
    'strategy_version','data_source'];
  signal_fields constant text[] := ARRAY[
    'pair','date','rate_diff_2y','rate_diff_10y','cot_percentile','realized_vol_20d',
    'realized_vol_5d','implied_vol_30d','spot','day_change','day_change_pct','cross_asset_vix',
    'cross_asset_dxy','cross_asset_oil','cross_asset_us10y','cross_asset_gold','cross_asset_copper',
    'cross_asset_stoxx','oi_delta','volume_rvol','structural_instability','breakeven_inflation_10y',
    'rate_diff_10y_real','rate_z_tactical','rate_z_structural','z_blended','realized_vol_rank',
    'skew_alignment','risk_reversal_25d','risk_reversal_source','days_since_cot','fpi_flow',
    'cot_net_pos','cot_asset_mgr_net','cot_lev_money_net','ecb_balance_sheet','bund_btp_spread',
    'boj_policy_rate','india_vix','inr_forward_premium','data_quality_notes'];
  rationale_fields constant text[] := ARRAY['pair','date','layer1_reasoning','layer2_reasoning',
    'layer3_reasoning','primary_driver_detail','confidence_explanation','contrarian_flags'];
  ignored constant text[] := ARRAY['id','call_id','created_at','updated_at','correlation_id','write_hash'];
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
  IF jsonb_typeof(p_call) IS DISTINCT FROM 'object'
     OR jsonb_typeof(p_signal) IS DISTINCT FROM 'object'
     OR (p_rationale IS NOT NULL AND jsonb_typeof(p_rationale) NOT IN ('object','null')) THEN
    RAISE EXCEPTION 'Publication call/signal must be objects and rationale an object or null';
  END IF;
  call_data := p_call - ignored;
  signal_data := p_signal - ignored;
  rationale_data := CASE WHEN p_rationale IS NULL OR p_rationale='null'::jsonb THEN
    jsonb_build_object('confidence_explanation','Rationale not supplied; signal snapshot retained.')
    ELSE p_rationale - ignored END;
  FOREACH key IN ARRAY ARRAY['pair','date','model_version','strategy_version','data_source','regime','rate_signal','predicted_direction'] LOOP
    IF jsonb_typeof(call_data->key) IS DISTINCT FROM 'string' OR btrim(call_data->>key)='' THEN
      RAISE EXCEPTION 'Required publication string: %',key;
    END IF;
  END LOOP;
  IF call_data->>'pair' NOT IN ('EURUSD','USDJPY','USDINR')
     OR call_data->>'data_source' NOT IN ('live','backtest') THEN
    RAISE EXCEPTION 'Invalid pair or publication provenance';
  END IF;
  IF call_data->>'predicted_direction' NOT IN ('BULLISH','BEARISH','NEUTRAL') THEN
    RAISE EXCEPTION 'Invalid published direction';
  END IF;
  IF call_data->>'date' !~ '^\d{4}-\d{2}-\d{2}$' THEN RAISE EXCEPTION 'Invalid publication date'; END IF;
  PERFORM (call_data->>'date')::date;
  FOREACH key IN ARRAY ARRAY['pair','date'] LOOP
    IF signal_data->key IS DISTINCT FROM call_data->key THEN
      RAISE EXCEPTION 'Signal identity does not match publication';
    END IF;
    IF rationale_data ? key AND rationale_data->key IS DISTINCT FROM call_data->key THEN
      RAISE EXCEPTION 'Rationale identity does not match publication';
    END IF;
  END LOOP;
  IF rationale_data IS NOT NULL THEN
    rationale_data := rationale_data || jsonb_build_object('pair',call_data->'pair','date',call_data->'date');
  END IF;
  FOR key,value IN SELECT * FROM jsonb_each(call_data) LOOP
    IF NOT key=ANY(call_fields) THEN RAISE EXCEPTION 'Unknown call field: %',key; END IF;
    IF key=ANY(ARRAY['confidence','signal_composite','stop_level','data_quality_score','conviction','special_signal_value']) THEN
      IF value <> 'null'::jsonb AND jsonb_typeof(value)<>'number' THEN RAISE EXCEPTION 'Invalid numeric call field: %',key; END IF;
    ELSIF value <> 'null'::jsonb AND jsonb_typeof(value)<>'string' THEN
      RAISE EXCEPTION 'Invalid string call field: %',key;
    END IF;
  END LOOP;
  FOREACH key IN ARRAY ARRAY['confidence','signal_composite'] LOOP
    IF jsonb_typeof(call_data->key) IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'Required numeric call field: %',key; END IF;
  END LOOP;
  IF (call_data->>'confidence')::numeric NOT BETWEEN 0 AND 1 THEN RAISE EXCEPTION 'Invalid confidence'; END IF;
  IF call_data->>'conviction' IS NOT NULL AND (
    (call_data->>'conviction')::numeric <> trunc((call_data->>'conviction')::numeric)
    OR (call_data->>'conviction')::numeric NOT BETWEEN 1 AND 5) THEN
    RAISE EXCEPTION 'Invalid integer conviction';
  END IF;
  FOR key,value IN SELECT * FROM jsonb_each(signal_data) LOOP
    IF NOT key=ANY(signal_fields) THEN RAISE EXCEPTION 'Unknown signal field: %',key; END IF;
    IF value='null'::jsonb THEN CONTINUE; END IF;
    IF key=ANY(ARRAY['pair','date','risk_reversal_source']) THEN
      IF jsonb_typeof(value)<>'string' THEN RAISE EXCEPTION 'Invalid string signal field: %',key; END IF;
    ELSIF key='structural_instability' THEN
      IF jsonb_typeof(value)<>'boolean' THEN RAISE EXCEPTION 'Invalid boolean signal field'; END IF;
    ELSIF key='data_quality_notes' THEN
      IF jsonb_typeof(value)<>'array' THEN RAISE EXCEPTION 'Invalid signal notes'; END IF;
      IF EXISTS(SELECT 1 FROM jsonb_array_elements(value) v WHERE jsonb_typeof(v)<>'string') THEN RAISE EXCEPTION 'Invalid signal notes'; END IF;
    ELSIF jsonb_typeof(value)<>'number' THEN RAISE EXCEPTION 'Invalid numeric signal field: %',key;
    END IF;
    IF key=ANY(ARRAY['oi_delta','skew_alignment','days_since_cot','cot_net_pos','cot_asset_mgr_net','cot_lev_money_net'])
       AND value::text::numeric <> trunc(value::text::numeric) THEN
      RAISE EXCEPTION 'Invalid integer signal field: %',key;
    END IF;
  END LOOP;
  FOR key,value IN SELECT * FROM jsonb_each(rationale_data) LOOP
    IF NOT key=ANY(rationale_fields) THEN RAISE EXCEPTION 'Unknown rationale field: %',key; END IF;
    IF value='null'::jsonb THEN CONTINUE; END IF;
    IF key='contrarian_flags' THEN
      IF jsonb_typeof(value)<>'array' THEN RAISE EXCEPTION 'Invalid rationale flags'; END IF;
      IF EXISTS(SELECT 1 FROM jsonb_array_elements(value) v WHERE jsonb_typeof(v)<>'string') THEN RAISE EXCEPTION 'Invalid rationale flags'; END IF;
    ELSIF jsonb_typeof(value)<>'string' THEN RAISE EXCEPTION 'Invalid rationale string: %',key;
    END IF;
  END LOOP;
  IF p_supersedes_call_id IS NOT NULL THEN
    SELECT * INTO predecessor FROM public.regime_calls WHERE id=p_supersedes_call_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Predecessor does not exist'; END IF;
    IF predecessor.pair IS DISTINCT FROM call_data->>'pair' OR predecessor.date IS DISTINCT FROM (call_data->>'date')::date THEN
      RAISE EXCEPTION 'Predecessor pair/date does not match publication';
    END IF;
  END IF;
  row_data := call_data;
  FOREACH key IN ARRAY ARRAY['correlation_id','write_hash'] LOOP
    IF p_call ? key THEN
      IF jsonb_typeof(p_call->key) NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid operational field: %',key; END IF;
      row_data := row_data || jsonb_build_object(key,p_call->key);
    END IF;
  END LOOP;
  semantic := public.publication_canonical_json(jsonb_build_object(
    'call',call_data,'signal',signal_data,'rationale',rationale_data,'supersedes_call_id',p_supersedes_call_id));
  fingerprint := encode(sha256(convert_to(semantic::text,'UTF8')),'hex');
  PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(call_data->'pair',call_data->'date',
    'publication')::text,0));
  SELECT id INTO published_id FROM public.regime_calls
    WHERE pair=call_data->>'pair' AND date=(call_data->>'date')::date
      AND data_source=call_data->>'data_source' AND strategy_version=call_data->>'strategy_version'
      AND model_version=call_data->>'model_version';
  IF FOUND THEN
    SELECT * INTO saved FROM public.publication_evidence WHERE call_id=published_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Legacy publication lacks evidence; use a new model version'; END IF;
    IF saved.payload_hash IS DISTINCT FROM fingerprint THEN
      RAISE EXCEPTION 'Publication content conflict; use a new model version';
    END IF;
    RETURN published_id;
  END IF;

  -- Names come only from pg_attribute for fixed, qualified table names, never JSON keys.
  SELECT string_agg(format('%I',a.attname),',' ORDER BY a.attnum) INTO columns_sql
    FROM pg_catalog.pg_attribute a WHERE a.attrelid='public.regime_calls'::regclass
      AND a.attnum>0 AND NOT a.attisdropped AND a.attgenerated='' AND a.attidentity=''
      AND row_data ? a.attname::text;
  EXECUTE format('INSERT INTO public.regime_calls(%s) SELECT %s FROM jsonb_populate_record(NULL::public.regime_calls,$1) RETURNING id',columns_sql,columns_sql)
    INTO published_id USING row_data;
  INSERT INTO public.publication_evidence(call_id,call_payload,signal_payload,rationale_payload,payload_hash,supersedes_call_id)
    VALUES(published_id,call_data,signal_data,rationale_data,fingerprint,p_supersedes_call_id);
  IF rationale_data IS NOT NULL THEN
    row_data := rationale_data || jsonb_build_object('call_id',published_id);
    SELECT string_agg(format('%I',a.attname),',' ORDER BY a.attnum) INTO columns_sql
      FROM pg_catalog.pg_attribute a WHERE a.attrelid='public.call_rationale'::regclass
        AND a.attnum>0 AND NOT a.attisdropped AND a.attgenerated='' AND a.attidentity=''
        AND row_data ? a.attname::text;
    EXECUTE format('INSERT INTO public.call_rationale(%s) SELECT %s FROM jsonb_populate_record(NULL::public.call_rationale,$1)',columns_sql,columns_sql) USING row_data;
  END IF;
  IF call_data->>'data_source'='live' THEN
    SELECT string_agg(format('%I',a.attname),',' ORDER BY a.attnum),
      string_agg(format('%1$I=EXCLUDED.%1$I',a.attname),',' ORDER BY a.attnum) FILTER(WHERE a.attname NOT IN ('pair','date'))
      INTO columns_sql,updates_sql
      FROM pg_catalog.pg_attribute a WHERE a.attrelid='public.signals'::regclass
        AND a.attnum>0 AND NOT a.attisdropped AND a.attgenerated='' AND a.attidentity=''
        AND signal_data ? a.attname::text;
    IF updates_sql IS NULL THEN RAISE EXCEPTION 'Signal snapshot has no projection fields'; END IF;
    EXECUTE format('INSERT INTO public.signals(%s) SELECT %s FROM jsonb_populate_record(NULL::public.signals,$1) ON CONFLICT(pair,date) DO UPDATE SET %s',columns_sql,columns_sql,updates_sql) USING signal_data;
  END IF;
  RETURN published_id;
END $$;

CREATE OR REPLACE FUNCTION public.append_price_observations(p_observations jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public
SET lock_timeout = '10s' AS $$
DECLARE
    observation jsonb;
    key text;
    fingerprint text;
    observation_id bigint;
    observation_ids jsonb := '[]'::jsonb;
    inserted_count integer := 0;
    existing_count integer := 0;
    number double precision;
    instant timestamptz;
    receipt timestamptz;
    provider_time timestamptz;
    window_start timestamptz;
    window_end timestamptz;
    received_before constant timestamptz := clock_timestamp();
    fields constant text[] := ARRAY[
        'pair','date','open','high','low','close','volume','provider','instrument',
        'retrieved_at','provider_timestamp','session_timezone','session_definition',
        'window_start','window_end','provider_metadata','volume_source','volume_instrument'
    ];
    metadata_fields constant text[] := ARRAY[
        'date_label_policy','response_ticker','response_status','request_id','adjusted',
        'raw_timestamp_ms','provider_timezone','last_refreshed','from_symbol','to_symbol',
        'index_timezone','raw_index'
    ];
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
    IF jsonb_typeof(p_observations) IS DISTINCT FROM 'array' THEN
        RAISE EXCEPTION 'Price observation batch must be an array';
    END IF;
    IF jsonb_array_length(p_observations) > 5000 THEN
        RAISE EXCEPTION 'Price observation batch exceeds 5000';
    END IF;
    -- Validate the entire batch before any insert, including sequence allocation.
    FOR observation IN SELECT value FROM jsonb_array_elements(p_observations) LOOP
        IF jsonb_typeof(observation) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'Price observation must be an object';
        END IF;
        IF NOT observation ?& fields OR observation - fields <> '{}'::jsonb THEN
            RAISE EXCEPTION 'Price observation requires exactly the contract fields';
        END IF;
        FOREACH key IN ARRAY ARRAY['pair','date','provider','instrument','retrieved_at'] LOOP
            IF jsonb_typeof(observation->key) IS DISTINCT FROM 'string'
               OR btrim(observation->>key) = '' THEN
                RAISE EXCEPTION 'Required observation string: %',key;
            END IF;
        END LOOP;
        IF observation->>'pair' NOT IN ('EURUSD','USDJPY','USDINR')
           OR observation->>'provider' NOT IN ('polygon','alphavantage','yahoo') THEN
            RAISE EXCEPTION 'Unsupported observation pair or provider';
        END IF;
        IF observation->>'date' !~ '^\d{4}-\d{2}-\d{2}$' THEN
            RAISE EXCEPTION 'Observation date must be YYYY-MM-DD';
        END IF;
        PERFORM (observation->>'date')::date;
        FOREACH key IN ARRAY ARRAY['open','high','low','close','volume'] LOOP
            IF jsonb_typeof(observation->key) IS DISTINCT FROM 'number' THEN
                RAISE EXCEPTION 'Finite observation number required: %',key;
            END IF;
            BEGIN
                number := (observation->>key)::double precision;
            EXCEPTION WHEN numeric_value_out_of_range OR invalid_text_representation THEN
                RAISE EXCEPTION 'Finite observation number required: %',key;
            END;
            IF NOT (number > '-Infinity'::float8 AND number < 'Infinity'::float8)
               OR (key = 'volume' AND number < 0)
               OR (key <> 'volume' AND number <= 0) THEN
                RAISE EXCEPTION 'Invalid observation price or volume: %',key;
            END IF;
        END LOOP;
        -- Compare exact JSON numeric values, without binary-float rounding.
        IF (observation->>'low')::numeric > least((observation->>'open')::numeric,(observation->>'close')::numeric)
           OR (observation->>'high')::numeric < greatest((observation->>'open')::numeric,(observation->>'close')::numeric) THEN
            RAISE EXCEPTION 'Invalid observation OHLC ordering';
        END IF;
        FOREACH key IN ARRAY ARRAY['session_timezone','session_definition','volume_source','volume_instrument'] LOOP
            IF observation->key <> 'null'::jsonb AND
               (jsonb_typeof(observation->key) IS DISTINCT FROM 'string' OR btrim(observation->>key) = '') THEN
                RAISE EXCEPTION 'Observation metadata must be a nonblank string or null: %',key;
            END IF;
        END LOOP;
        IF jsonb_typeof(observation->'provider_metadata') IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'provider_metadata must be an object';
        END IF;
        IF (observation->'provider_metadata') - metadata_fields <> '{}'::jsonb THEN
            RAISE EXCEPTION 'Unknown provider_metadata field';
        END IF;
        FOR key IN SELECT jsonb_object_keys(observation->'provider_metadata') LOOP
            IF jsonb_typeof(observation->'provider_metadata'->key) NOT IN ('string','number','boolean','null') THEN
                RAISE EXCEPTION 'provider_metadata fields must be scalar';
            END IF;
        END LOOP;
        receipt := NULL;
        provider_time := NULL;
        window_start := NULL;
        window_end := NULL;
        FOREACH key IN ARRAY ARRAY['retrieved_at','provider_timestamp','window_start','window_end'] LOOP
            IF observation->key = 'null'::jsonb THEN CONTINUE; END IF;
            IF jsonb_typeof(observation->key) IS DISTINCT FROM 'string'
               OR observation->>key !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$' THEN
                RAISE EXCEPTION 'Observation timestamp must include an ISO offset: %',key;
            END IF;
            instant := (observation->>key)::timestamptz;
            IF NOT isfinite(instant) THEN RAISE EXCEPTION 'Finite observation timestamp required'; END IF;
            IF key IN ('retrieved_at','provider_timestamp') AND instant > received_before THEN
                RAISE EXCEPTION 'Future observation timestamp: %',key;
            END IF;
            CASE key
                WHEN 'retrieved_at' THEN receipt := instant;
                WHEN 'provider_timestamp' THEN provider_time := instant;
                WHEN 'window_start' THEN window_start := instant;
                WHEN 'window_end' THEN window_end := instant;
                ELSE NULL;
            END CASE;
        END LOOP;
        IF provider_time > receipt THEN
            RAISE EXCEPTION 'Provider timestamp follows retrieval';
        END IF;
        IF (window_start IS NULL) <> (window_end IS NULL)
           OR window_end <= window_start OR receipt < window_start THEN
            RAISE EXCEPTION 'Invalid observation window or retrieval before window start';
        END IF;
    END LOOP;

    -- Stable lock order also avoids deadlocks for overlapping, reversed batches.
    FOR fingerprint IN
        SELECT DISTINCT encode(sha256(convert_to(public.publication_canonical_json(value)::text,'UTF8')),'hex')
        FROM jsonb_array_elements(p_observations) ORDER BY 1
    LOOP
        PERFORM pg_advisory_xact_lock(hashtextextended(fingerprint,0));
    END LOOP;
    FOR observation IN SELECT value FROM jsonb_array_elements(p_observations) LOOP
        fingerprint := encode(sha256(convert_to(public.publication_canonical_json(observation)::text,'UTF8')),'hex');
        observation_id := NULL;
        INSERT INTO public.price_observations(pair,date,provider,instrument,retrieved_at,observation,payload_hash)
        VALUES(observation->>'pair',(observation->>'date')::date,observation->>'provider',
               observation->>'instrument',(observation->>'retrieved_at')::timestamptz,observation,fingerprint)
        ON CONFLICT(payload_hash) DO NOTHING RETURNING id INTO observation_id;
        IF observation_id IS NULL THEN
            SELECT id INTO STRICT observation_id FROM public.price_observations WHERE payload_hash=fingerprint;
            existing_count := existing_count + 1;
        ELSE
            inserted_count := inserted_count + 1;
        END IF;
        observation_ids := observation_ids || to_jsonb(observation_id);
    END LOOP;
    RETURN jsonb_build_object('observation_ids',observation_ids,
                             'inserted_count',inserted_count,'existing_count',existing_count);
END $$;

CREATE OR REPLACE FUNCTION public.append_quote_capture(p_capture_sha256 text, p_unsigned_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public
SET lock_timeout = '10s' AS $$
DECLARE
    doc jsonb; body json; body_valid boolean := true; key text; val jsonb;
    first_request boolean; receipt timestamptz; requested timestamptz;
    inserted boolean; saved text; issue_order integer := 0; issue_index integer;
    next_url text;
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
    IF p_unsigned_json IS NULL OR octet_length(convert_to(p_unsigned_json,'UTF8')) > 33554432
       OR p_capture_sha256 IS NULL OR p_capture_sha256 !~ '^[0-9a-f]{64}$'
       OR encode(sha256(convert_to(p_unsigned_json,'UTF8')),'hex') <> p_capture_sha256 THEN
        RAISE EXCEPTION 'Invalid quote capture envelope';
    END IF;
    IF NOT public.quote_storage_unique_json(p_unsigned_json::json) THEN
        RAISE EXCEPTION 'Invalid quote capture envelope';
    END IF;
    doc := p_unsigned_json::jsonb;
    IF NOT public.quote_storage_keys(doc, ARRAY[
        'version','provider','pair','instrument','window_start_ns','window_end_ns',
        'page_index','request_parameters','request_cursor_sha256','requested_at',
        'received_at','http_status','response_headers','body_text','raw_body_sha256',
        'body_sha256','raw_size_bytes','next_cursor_sha256','issues'])
       OR doc->>'version' IS DISTINCT FROM 'quote-page-v1'
       OR doc->>'provider' IS DISTINCT FROM 'massive'
       OR NOT public.quote_storage_identity(doc) THEN RAISE EXCEPTION 'Invalid quote capture schema'; END IF;
    FOREACH key IN ARRAY ARRAY['page_index','http_status','raw_size_bytes'] LOOP
        IF jsonb_typeof(doc->key) IS DISTINCT FROM 'number' OR
           doc->>key !~ '^(0|[1-9][0-9]*)$' THEN RAISE EXCEPTION 'Invalid quote capture integer'; END IF;
    END LOOP;
    IF (doc->>'http_status')::numeric NOT BETWEEN 100 AND 599 OR
       (doc->>'raw_size_bytes')::numeric > 16777216 THEN RAISE EXCEPTION 'Invalid quote capture integer'; END IF;
    requested := public.quote_storage_time(doc->'requested_at');
    receipt := public.quote_storage_time(doc->'received_at');
    IF receipt < requested OR receipt > clock_timestamp() THEN RAISE EXCEPTION 'Invalid quote capture time order'; END IF;
    FOREACH key IN ARRAY ARRAY['raw_body_sha256','body_sha256','request_cursor_sha256','next_cursor_sha256'] LOOP
        IF key IN ('request_cursor_sha256','next_cursor_sha256') AND doc->key = 'null'::jsonb THEN CONTINUE; END IF;
        IF jsonb_typeof(doc->key) IS DISTINCT FROM 'string' OR doc->>key !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'Invalid quote capture fingerprint';
        END IF;
    END LOOP;
    first_request := (doc->>'page_index')::numeric = 0;
    IF first_request <> (doc->'request_cursor_sha256' = 'null'::jsonb) THEN
        RAISE EXCEPTION 'Invalid quote request cursor';
    END IF;
    IF jsonb_typeof(doc->'request_parameters') IS DISTINCT FROM 'object' OR
       jsonb_typeof(doc->'response_headers') IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'Invalid quote request metadata';
    END IF;
    IF first_request AND NOT public.quote_storage_keys(doc->'request_parameters',
       ARRAY['timestamp.gte','timestamp.lt','sort','order','limit']) THEN
        RAISE EXCEPTION 'Invalid quote request parameters';
    END IF;
    FOR key,val IN SELECT * FROM jsonb_each(doc->'request_parameters') LOOP
        IF jsonb_typeof(val) <> 'string' OR key NOT IN ('timestamp.gte','timestamp.lt','sort','order','limit') THEN
            RAISE EXCEPTION 'Invalid quote request parameters';
        END IF;
        IF (key='timestamp.gte' AND val <> doc->'window_start_ns') OR
           (key='timestamp.lt' AND val <> doc->'window_end_ns') OR
           (key='sort' AND val <> '"timestamp"'::jsonb) OR
           (key='order' AND val <> '"asc"'::jsonb) THEN RAISE EXCEPTION 'Invalid quote request parameters'; END IF;
        IF key='limit' THEN
            IF val #>> '{}' !~ '^[1-9][0-9]{0,4}$' THEN RAISE EXCEPTION 'Invalid quote page limit'; END IF;
            IF (val #>> '{}')::integer > 50000 THEN RAISE EXCEPTION 'Invalid quote page limit'; END IF;
        END IF;
    END LOOP;
    FOR key,val IN SELECT * FROM jsonb_each(doc->'response_headers') LOOP
        IF key NOT IN ('content-type','x-request-id') OR jsonb_typeof(val) <> 'string' THEN
            RAISE EXCEPTION 'Invalid quote response headers';
        END IF;
    END LOOP;
    IF jsonb_typeof(doc->'issues') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Invalid quote capture issues'; END IF;
    FOR val IN SELECT * FROM jsonb_array_elements(doc->'issues') LOOP
        issue_index := array_position(ARRAY['invalid_utf8','invalid_json','invalid_cursor','non_integer_quote_timestamp','text_storage_escaped'],val #>> '{}');
        IF jsonb_typeof(val) <> 'string' OR issue_index IS NULL OR issue_index <= issue_order THEN
            RAISE EXCEPTION 'Invalid quote capture issues';
        END IF;
        issue_order := issue_index;
    END LOOP;
    IF jsonb_typeof(doc->'body_text') IS DISTINCT FROM 'string' OR
       encode(sha256(convert_to(doc->>'body_text','UTF8')),'hex') <> doc->>'body_sha256' THEN
        RAISE EXCEPTION 'Invalid quote body fingerprint';
    END IF;
    BEGIN
        body := (doc->>'body_text')::json;
        body_valid := public.quote_storage_unique_json(body);
    EXCEPTION WHEN OTHERS THEN body_valid := false;
    END;
    IF NOT body_valid THEN
        IF NOT doc->'issues' ? 'invalid_json' OR doc->'next_cursor_sha256' <> 'null'::jsonb
           OR doc->'issues' ? 'invalid_cursor' THEN RAISE EXCEPTION 'Invalid quote body diagnosis'; END IF;
    ELSE
        next_url := CASE WHEN json_typeof(body)='object' THEN body->>'next_url' END;
        IF doc->'issues' ? 'invalid_cursor' THEN
            IF next_url IS DISTINCT FROM '[INVALID_CURSOR]' OR doc->'next_cursor_sha256' <> 'null'::jsonb THEN
                RAISE EXCEPTION 'Invalid quote next cursor evidence';
            END IF;
        ELSIF next_url IS NOT NULL THEN
            IF json_typeof(body->'next_url') <> 'string' OR next_url NOT IN (
                'https://api.massive.com/v3/quotes/' || (doc->>'instrument') || '?cursor=[REDACTED]',
                'https://api.polygon.io/v3/quotes/' || (doc->>'instrument') || '?cursor=[REDACTED]')
               OR doc->'next_cursor_sha256' = 'null'::jsonb THEN RAISE EXCEPTION 'Invalid quote next cursor evidence'; END IF;
        ELSIF doc->'next_cursor_sha256' <> 'null'::jsonb THEN RAISE EXCEPTION 'Invalid quote next cursor evidence'; END IF;
    END IF;
    INSERT INTO public.quote_captures(capture_sha256,unsigned_json,document,pair,instrument,window_start_ns,window_end_ns,received_at)
        VALUES(p_capture_sha256,p_unsigned_json,doc,doc->>'pair',doc->>'instrument',
               (doc->>'window_start_ns')::numeric,(doc->>'window_end_ns')::numeric,receipt)
        ON CONFLICT(capture_sha256) DO NOTHING;
    inserted := FOUND;
    SELECT unsigned_json INTO saved FROM public.quote_captures WHERE capture_sha256=p_capture_sha256;
    IF saved IS DISTINCT FROM p_unsigned_json THEN RAISE EXCEPTION 'Quote capture fingerprint conflict'; END IF;
    RETURN jsonb_build_object('capture_sha256',p_capture_sha256,'inserted',inserted);
EXCEPTION WHEN OTHERS THEN
    -- Never repeat source text, credentials, opaque cursors or cast error details.
    RAISE EXCEPTION USING MESSAGE='Quote capture rejected: invalid input or storage conflict', ERRCODE='22023';
END $$;

CREATE OR REPLACE FUNCTION public.append_quote_snapshot(p_snapshot_sha256 text, p_unsigned_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public
SET lock_timeout = '10s' AS $$
DECLARE
    doc jsonb; ref jsonb; val jsonb; key text; capture_hash text;
    instant timestamptz; n integer; inserted boolean; saved text; input_text text;
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
    IF p_unsigned_json IS NULL OR octet_length(convert_to(p_unsigned_json,'UTF8')) > 1048576
       OR p_snapshot_sha256 IS NULL OR p_snapshot_sha256 !~ '^[0-9a-f]{64}$'
       OR encode(sha256(convert_to(p_unsigned_json,'UTF8')),'hex') <> p_snapshot_sha256 THEN
        RAISE EXCEPTION 'Invalid quote snapshot envelope';
    END IF;
    IF NOT public.quote_storage_unique_json(p_unsigned_json::json) THEN RAISE EXCEPTION 'Invalid quote snapshot JSON'; END IF;
    doc := p_unsigned_json::jsonb;
    IF NOT public.quote_storage_keys(doc,ARRAY['version','implementation_sha256','client_version','reference'])
       OR doc->>'version' IS DISTINCT FROM 'quote-snapshot-v1'
       OR jsonb_typeof(doc->'implementation_sha256') IS DISTINCT FROM 'string'
       OR doc->>'implementation_sha256' !~ '^[0-9a-f]{64}$'
       OR jsonb_typeof(doc->'client_version') IS DISTINCT FROM 'string'
       OR doc->>'client_version' !~ '^[A-Za-z0-9._-]{1,128}$' THEN RAISE EXCEPTION 'Invalid quote snapshot provenance'; END IF;
    ref := doc->'reference';
    IF NOT public.quote_storage_keys(ref, ARRAY[
        'series_id','algorithm_version','pair','instrument','window_start_ns','window_end_ns','as_of',
        'capture_sha256','input_sha256','acquisition_complete','source_occurrence_count','distinct_row_count',
        'duplicate_count','unique_timestamp_count','invalid_occurrence_count','out_of_window_count',
        'first_timestamp_ns','last_timestamp_ns','first_event_offset_ns','last_event_age_ns',
        'open','high','low','close','ambiguous_open','ambiguous_close','exclusion_reasons',
        'provider_finality','project_maturity','validation_eligible'])
       OR NOT public.quote_storage_identity(ref)
       OR ref->>'series_id' IS DISTINCT FROM 'massive-fx-bbo-mid-utc-v1'
       OR ref->>'algorithm_version' IS DISTINCT FROM 'quote-midpoint-utc-v1'
       OR ref->>'provider_finality' IS DISTINCT FROM 'unknown'
       OR ref->>'project_maturity' IS DISTINCT FROM 'provisional'
       OR ref->'validation_eligible' IS DISTINCT FROM 'false'::jsonb THEN
        RAISE EXCEPTION 'Invalid quote snapshot reference';
    END IF;
    instant := public.quote_storage_time(ref->'as_of');
    IF instant > clock_timestamp() THEN RAISE EXCEPTION 'Future quote snapshot'; END IF;
    FOREACH key IN ARRAY ARRAY['acquisition_complete','ambiguous_open','ambiguous_close'] LOOP
        IF jsonb_typeof(ref->key) IS DISTINCT FROM 'boolean' THEN RAISE EXCEPTION 'Invalid quote snapshot boolean'; END IF;
    END LOOP;
    FOREACH key IN ARRAY ARRAY['source_occurrence_count','distinct_row_count','duplicate_count',
                              'unique_timestamp_count','invalid_occurrence_count','out_of_window_count'] LOOP
        IF jsonb_typeof(ref->key) IS DISTINCT FROM 'number' OR ref->>key !~ '^(0|[1-9][0-9]*)$' THEN
            RAISE EXCEPTION 'Invalid quote snapshot counter';
        END IF;
    END LOOP;
    FOREACH key IN ARRAY ARRAY['first_timestamp_ns','last_timestamp_ns','first_event_offset_ns','last_event_age_ns'] LOOP
        IF ref->key = 'null'::jsonb THEN CONTINUE; END IF;
        IF jsonb_typeof(ref->key) <> 'string' OR ref->>key !~ '^(0|[1-9][0-9]*)$' THEN
            RAISE EXCEPTION 'Invalid quote snapshot timing';
        END IF;
    END LOOP;
    FOREACH key IN ARRAY ARRAY['open','high','low','close'] LOOP
        IF ref->key = 'null'::jsonb THEN CONTINUE; END IF;
        IF jsonb_typeof(ref->key) <> 'string' OR ref->>key !~ '^[0-9]+(\.[0-9]+)?(e-?[0-9]+)?$' THEN
            RAISE EXCEPTION 'Invalid quote snapshot price';
        END IF;
    END LOOP;
    IF jsonb_typeof(ref->'exclusion_reasons') IS DISTINCT FROM 'array' OR
       NOT ref->'exclusion_reasons' @> '["coverage_policy_unverified"]'::jsonb THEN
        RAISE EXCEPTION 'Invalid quote snapshot exclusions';
    END IF;
    FOR val IN SELECT * FROM jsonb_array_elements(ref->'exclusion_reasons') LOOP
        IF jsonb_typeof(val) <> 'string' OR length(val #>> '{}') = 0 THEN RAISE EXCEPTION 'Invalid quote snapshot exclusions'; END IF;
    END LOOP;
    IF NOT (ref->>'acquisition_complete')::boolean AND EXISTS (
        SELECT 1 FROM unnest(ARRAY['open','high','low','close']) AS e(k) WHERE ref->k <> 'null'::jsonb
    ) THEN RAISE EXCEPTION 'Incomplete quote snapshot has prices'; END IF;
    IF jsonb_typeof(ref->'capture_sha256') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Invalid quote snapshot lineage'; END IF;
    n := jsonb_array_length(ref->'capture_sha256');
    IF n NOT BETWEEN 1 AND 10000 THEN RAISE EXCEPTION 'Invalid quote snapshot lineage size'; END IF;
    FOR val IN SELECT * FROM jsonb_array_elements(ref->'capture_sha256') LOOP
        capture_hash := val #>> '{}';
        IF jsonb_typeof(val) <> 'string' OR capture_hash !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid quote snapshot capture'; END IF;
        IF NOT EXISTS (SELECT 1 FROM public.quote_captures c WHERE c.capture_sha256=capture_hash
            AND c.pair=ref->>'pair' AND c.instrument=ref->>'instrument'
            AND c.window_start_ns=(ref->>'window_start_ns')::numeric AND c.window_end_ns=(ref->>'window_end_ns')::numeric) THEN
            RAISE EXCEPTION 'Missing or inconsistent quote snapshot capture';
        END IF;
    END LOOP;
    SELECT '{"algorithm_version":"quote-midpoint-utc-v1","capture_sha256":[' ||
        string_agg('"' || value || '"',',' ORDER BY ordinal) || ']}' INTO input_text
        FROM jsonb_array_elements_text(ref->'capture_sha256') WITH ORDINALITY AS e(value,ordinal);
    IF jsonb_typeof(ref->'input_sha256') IS DISTINCT FROM 'string' OR
       ref->>'input_sha256' IS DISTINCT FROM encode(sha256(convert_to(input_text,'UTF8')),'hex') THEN
        RAISE EXCEPTION 'Invalid quote snapshot input fingerprint';
    END IF;
    INSERT INTO public.quote_snapshots(snapshot_sha256,unsigned_json,document,pair,instrument,window_start_ns,window_end_ns,as_of)
        VALUES(p_snapshot_sha256,p_unsigned_json,doc,ref->>'pair',ref->>'instrument',
               (ref->>'window_start_ns')::numeric,(ref->>'window_end_ns')::numeric,instant)
        ON CONFLICT(snapshot_sha256) DO NOTHING;
    inserted := FOUND;
    SELECT unsigned_json INTO saved FROM public.quote_snapshots WHERE snapshot_sha256=p_snapshot_sha256;
    IF saved IS DISTINCT FROM p_unsigned_json THEN RAISE EXCEPTION 'Quote snapshot fingerprint conflict'; END IF;
    IF inserted THEN
        INSERT INTO public.quote_snapshot_pages(snapshot_sha256,ordinal,capture_sha256)
            SELECT p_snapshot_sha256,(ordinal-1)::integer,value
            FROM jsonb_array_elements_text(ref->'capture_sha256') WITH ORDINALITY AS e(value,ordinal);
    END IF;
    RETURN jsonb_build_object('snapshot_sha256',p_snapshot_sha256,'inserted',inserted,'capture_count',n);
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION USING MESSAGE='Quote snapshot rejected: invalid input or storage conflict', ERRCODE='22023';
END $$;

CREATE OR REPLACE FUNCTION public.append_quote_acquisition_event(p_event_sha256 text, p_unsigned_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public
SET lock_timeout = '10s' AS $$
DECLARE
    raw json; doc jsonb; manifest jsonb; limits jsonb; key text; value jsonb; manifest_text text;
    attempt uuid; seq integer; instant timestamptz;
    prior public.quote_acquisition_events%ROWTYPE;
    saved public.quote_acquisition_events%ROWTYPE;
    captures jsonb; snapshot public.quote_snapshots%ROWTYPE;
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
    IF p_unsigned_json IS NULL OR octet_length(convert_to(p_unsigned_json,'UTF8')) > 65536
       OR p_event_sha256 IS NULL OR p_event_sha256 !~ '^[0-9a-f]{64}$'
       OR encode(sha256(convert_to(p_unsigned_json,'UTF8')),'hex') <> p_event_sha256 THEN
        RAISE EXCEPTION 'Invalid attempt envelope';
    END IF;
    raw := p_unsigned_json::json;
    IF NOT public.quote_storage_unique_json(raw) THEN RAISE EXCEPTION 'Duplicate attempt fields'; END IF;
    doc := p_unsigned_json::jsonb;
    IF NOT public.quote_storage_keys(doc,ARRAY[
        'version','attempt_id','sequence','previous_event_sha256','kind','occurred_at',
        'pair','instrument','window_start_ns','window_end_ns','implementation_sha256',
        'client_version','runtime_manifest_json','limits','capture_sha256','snapshot_sha256','status','reason'])
       OR doc->>'version' IS DISTINCT FROM 'quote-acquisition-event-v1'
       OR doc->>'client_version' IS DISTINCT FROM 'fxregime-quote-http-v1'
       OR NOT public.quote_storage_identity(doc)
       OR length(doc->>'window_start_ns')>21 OR length(doc->>'window_end_ns')>21
       OR jsonb_typeof(doc->'attempt_id') IS DISTINCT FROM 'string'
       OR doc->>'attempt_id' !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       OR json_typeof(raw->'sequence') IS DISTINCT FROM 'number'
       OR raw->>'sequence' !~ '^(0|[1-9][0-9]*)$'
       OR (raw->>'sequence')::numeric NOT BETWEEN 0 AND 10001
       OR doc->>'kind' NOT IN ('started','page_saved','finished')
       OR jsonb_typeof(doc->'kind') IS DISTINCT FROM 'string' THEN
        RAISE EXCEPTION 'Invalid attempt schema';
    END IF;
    FOREACH key IN ARRAY ARRAY['implementation_sha256','previous_event_sha256','capture_sha256','snapshot_sha256'] LOOP
        IF key <> 'implementation_sha256' AND doc->key='null'::jsonb THEN CONTINUE; END IF;
        IF jsonb_typeof(doc->key) IS DISTINCT FROM 'string' OR doc->>key !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'Invalid attempt hash';
        END IF;
    END LOOP;
    instant := public.quote_storage_time(doc->'occurred_at');
    IF instant > clock_timestamp() OR doc->>'occurred_at' LIKE '%.000000+00:00' THEN
        RAISE EXCEPTION 'Invalid attempt time';
    END IF;
    limits := doc->'limits';
    IF NOT public.quote_storage_keys(limits,ARRAY['max_pages','max_page_bytes','max_total_bytes','deadline_seconds','request_timeout_seconds']) THEN
        RAISE EXCEPTION 'Invalid attempt limits';
    END IF;
    FOR key,value IN SELECT * FROM jsonb_each(limits) LOOP
        IF jsonb_typeof(value) <> 'number' OR raw->'limits'->>key !~ '^[1-9][0-9]*$' THEN
            RAISE EXCEPTION 'Invalid attempt limit integer';
        END IF;
        IF (value #>> '{}')::numeric > (CASE key
            WHEN 'max_pages' THEN 10000 WHEN 'max_page_bytes' THEN 16777216
            WHEN 'max_total_bytes' THEN 268435456 WHEN 'deadline_seconds' THEN 3600
            WHEN 'request_timeout_seconds' THEN 60 END) THEN RAISE EXCEPTION 'Attempt limit out of range'; END IF;
    END LOOP;
    IF (limits->>'max_total_bytes')::integer < (limits->>'max_page_bytes')::integer THEN
        RAISE EXCEPTION 'Invalid attempt byte limits';
    END IF;
    seq := (doc->>'sequence')::integer;
    attempt := (doc->>'attempt_id')::uuid;
    IF doc->>'kind'='started' THEN
        IF seq <> 0 OR doc->'previous_event_sha256' <> 'null'::jsonb
           OR jsonb_typeof(doc->'runtime_manifest_json') IS DISTINCT FROM 'string' THEN
            RAISE EXCEPTION 'Invalid attempt start';
        END IF;
        IF encode(sha256(convert_to(doc->>'runtime_manifest_json','UTF8')),'hex') <> doc->>'implementation_sha256'
           OR NOT public.quote_storage_unique_json((doc->>'runtime_manifest_json')::json) THEN
            RAISE EXCEPTION 'Invalid runtime manifest hash';
        END IF;
        manifest := (doc->>'runtime_manifest_json')::jsonb;
        IF NOT public.quote_storage_keys(manifest,ARRAY['version','client_version','files','dependencies'])
           OR manifest->>'version' IS DISTINCT FROM 'quote-runtime-manifest-v1'
           OR manifest->>'client_version' IS DISTINCT FROM 'fxregime-quote-http-v1'
           OR NOT public.quote_storage_keys(manifest->'files',ARRAY[
                'pipeline/src/research/quote_acquisition.py','pipeline/src/research/quote_attempt.py',
                'pipeline/src/research/quote_capture.py','pipeline/src/research/quote_reference.py','pipeline/src/db/writer.py'])
           OR NOT public.quote_storage_keys(manifest->'dependencies',ARRAY['python','aiohttp']) THEN
            RAISE EXCEPTION 'Invalid runtime manifest shape';
        END IF;
        FOR value IN SELECT v FROM jsonb_each(manifest->'files') AS e(k,v) LOOP
            IF jsonb_typeof(value) <> 'string' OR value #>> '{}' !~ '^[0-9a-f]{64}$' THEN
                RAISE EXCEPTION 'Invalid runtime source hash';
            END IF;
        END LOOP;
        FOR value IN SELECT v FROM jsonb_each(manifest->'dependencies') AS e(k,v) LOOP
            IF jsonb_typeof(value) <> 'string' OR value #>> '{}' !~ '^[A-Za-z0-9._+-]{1,128}$' THEN
                RAISE EXCEPTION 'Invalid runtime dependency';
            END IF;
        END LOOP;
        SELECT '{"client_version":"fxregime-quote-http-v1","dependencies":{"aiohttp":' ||
            to_json(manifest->'dependencies'->>'aiohttp')::text || ',"python":' ||
            to_json(manifest->'dependencies'->>'python')::text || '},"files":{' ||
            string_agg(to_json(k)::text || ':' || to_json(v)::text,',' ORDER BY k COLLATE "C") ||
            '},"version":"quote-runtime-manifest-v1"}' INTO manifest_text
            FROM jsonb_each_text(manifest->'files') AS e(k,v);
        IF manifest_text<>doc->>'runtime_manifest_json' THEN RAISE EXCEPTION 'Noncanonical runtime manifest'; END IF;
    ELSIF seq=0 OR doc->'previous_event_sha256'='null'::jsonb OR doc->'runtime_manifest_json'<>'null'::jsonb THEN
        RAISE EXCEPTION 'Invalid subsequent attempt event';
    END IF;
    IF doc->>'kind'='finished' THEN
        IF doc->'capture_sha256'<>'null'::jsonb OR jsonb_typeof(doc->'reason') IS DISTINCT FROM 'string'
           OR doc->>'reason' NOT IN ('completed','request_failed','read_failed','body_limit','byte_budget','page_limit',
                'time_budget','http_status','invalid_response','capture_invalid','capture_write_failed','page_event_write_failed',
                'snapshot_write_failed','cursor_cycle','clock_invalid','implementation_changed')
           OR doc->>'status' NOT IN ('complete','failed') OR jsonb_typeof(doc->'status') IS DISTINCT FROM 'string'
           OR (doc->>'status'='complete') <> (doc->>'reason'='completed')
           OR (doc->>'status'='complete' AND doc->'snapshot_sha256'='null'::jsonb) THEN
            RAISE EXCEPTION 'Invalid terminal attempt event';
        END IF;
        IF seq>(limits->>'max_pages')::integer+1 OR (seq=1 AND doc->'snapshot_sha256'<>'null'::jsonb) THEN
            RAISE EXCEPTION 'Invalid terminal page count';
        END IF;
    ELSIF doc->>'status' IS DISTINCT FROM 'running' OR doc->'reason'<>'null'::jsonb
          OR doc->'snapshot_sha256'<>'null'::jsonb
          OR (doc->>'kind'='page_saved') <> (doc->'capture_sha256'<>'null'::jsonb) THEN
        RAISE EXCEPTION 'Invalid running attempt event';
    END IF;

    -- One writer per attempt. Hash collisions merely serialize unrelated attempts.
    PERFORM pg_advisory_xact_lock(hashtextextended(attempt::text,0));
    SELECT * INTO saved FROM public.quote_acquisition_events WHERE attempt_id=attempt AND sequence=seq;
    IF FOUND THEN
        IF saved.event_sha256<>p_event_sha256 OR saved.unsigned_json<>p_unsigned_json THEN
            RAISE EXCEPTION 'Attempt sequence conflict';
        END IF;
        RETURN jsonb_build_object('event_sha256',p_event_sha256,'attempt_id',attempt::text,'sequence',seq,'inserted',false);
    END IF;
    SELECT * INTO prior FROM public.quote_acquisition_events WHERE attempt_id=attempt ORDER BY sequence DESC LIMIT 1;
    IF FOUND THEN
        IF seq<>prior.sequence+1 OR prior.kind='finished'
           OR doc->>'previous_event_sha256' IS DISTINCT FROM prior.event_sha256
           OR instant<prior.occurred_at THEN RAISE EXCEPTION 'Invalid attempt chain'; END IF;
        FOREACH key IN ARRAY ARRAY['pair','instrument','window_start_ns','window_end_ns','implementation_sha256','client_version','limits'] LOOP
            IF doc->key IS DISTINCT FROM prior.document->key THEN RAISE EXCEPTION 'Attempt identity changed'; END IF;
        END LOOP;
    ELSIF seq<>0 THEN RAISE EXCEPTION 'Missing attempt start';
    END IF;
    IF doc->>'kind'='page_saved' THEN
        IF seq>(limits->>'max_pages')::integer OR NOT EXISTS (
            SELECT 1 FROM public.quote_captures c WHERE c.capture_sha256=doc->>'capture_sha256'
            AND c.document->>'page_index'=(seq-1)::text AND c.pair=doc->>'pair' AND c.instrument=doc->>'instrument'
            AND c.window_start_ns=(doc->>'window_start_ns')::numeric AND c.window_end_ns=(doc->>'window_end_ns')::numeric
            AND public.quote_storage_time(c.document->'requested_at')>=prior.occurred_at
            AND c.received_at<=instant
            AND (c.document->>'raw_size_bytes')::numeric<=(limits->>'max_page_bytes')::integer
            AND (c.document->>'raw_size_bytes')::numeric + (
                SELECT coalesce(sum((old_capture.document->>'raw_size_bytes')::numeric),0)
                FROM public.quote_acquisition_events old_event
                JOIN public.quote_captures old_capture ON old_capture.capture_sha256=old_event.document->>'capture_sha256'
                WHERE old_event.attempt_id=attempt AND old_event.kind='page_saved'
            )<=(limits->>'max_total_bytes')::integer
        ) THEN RAISE EXCEPTION 'Invalid attempt capture lineage'; END IF;
    ELSIF doc->>'kind'='finished' THEN
        SELECT coalesce(jsonb_agg(document->'capture_sha256' ORDER BY sequence),'[]'::jsonb)
            INTO captures FROM public.quote_acquisition_events WHERE attempt_id=attempt AND kind='page_saved';
        IF seq<>jsonb_array_length(captures)+1 THEN RAISE EXCEPTION 'Invalid terminal sequence'; END IF;
        IF doc->'snapshot_sha256'<>'null'::jsonb THEN
            SELECT * INTO snapshot FROM public.quote_snapshots WHERE snapshot_sha256=doc->>'snapshot_sha256';
            IF NOT FOUND THEN RAISE EXCEPTION 'Missing attempt snapshot'; END IF;
            IF snapshot.pair<>doc->>'pair' OR snapshot.instrument<>doc->>'instrument'
               OR snapshot.window_start_ns<>(doc->>'window_start_ns')::numeric
               OR snapshot.window_end_ns<>(doc->>'window_end_ns')::numeric
               OR snapshot.as_of>instant OR snapshot.document->>'implementation_sha256'<>doc->>'implementation_sha256'
               OR snapshot.document->>'client_version'<>doc->>'client_version'
               OR snapshot.document->'reference'->'capture_sha256'<>captures
               OR (doc->>'status'='complete' AND snapshot.document->'reference'->'acquisition_complete'<>'true'::jsonb) THEN
                RAISE EXCEPTION 'Invalid attempt snapshot lineage';
            END IF;
        END IF;
    END IF;
    INSERT INTO public.quote_acquisition_events(attempt_id,sequence,event_sha256,unsigned_json,document,kind,occurred_at)
        VALUES(attempt,seq,p_event_sha256,p_unsigned_json,doc,doc->>'kind',instant);
    RETURN jsonb_build_object('event_sha256',p_event_sha256,'attempt_id',attempt::text,'sequence',seq,'inserted',true);
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION USING MESSAGE='Quote acquisition event rejected: invalid input or storage conflict', ERRCODE='22023';
END $$;

COMMIT;
