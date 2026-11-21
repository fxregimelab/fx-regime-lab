-- Atomic publication repair. Existing rows are never rewritten or deleted.
BEGIN;

-- The May 5 constraint used title case; current producers use uppercase.
-- Preserve historical values and accept the canonical producer spelling.
ALTER TABLE public.regime_calls DROP CONSTRAINT IF EXISTS regime_calls_directional_bias_values;
ALTER TABLE public.regime_calls ADD CONSTRAINT regime_calls_directional_bias_values
  CHECK (directional_bias IS NULL OR directional_bias IN ('Long','Short','Neutral','LONG','SHORT','NEUTRAL'));

-- Remove only old uniqueness whose complete key is pair/date. Other indexes stay.
DO $$
DECLARE item record;
BEGIN
  FOR item IN
    SELECT c.conname FROM pg_catalog.pg_constraint c
    WHERE c.conrelid='public.regime_calls'::regclass AND c.contype='u'
      AND (SELECT array_agg(a.attname::text ORDER BY a.attname)
           FROM unnest(c.conkey) k JOIN pg_catalog.pg_attribute a
             ON a.attrelid=c.conrelid AND a.attnum=k) = ARRAY['date','pair']
  LOOP
    EXECUTE format('ALTER TABLE public.regime_calls DROP CONSTRAINT %I',item.conname);
  END LOOP;
  FOR item IN
    SELECT i.indexrelid::regclass AS index_name FROM pg_catalog.pg_index i
    WHERE i.indrelid='public.regime_calls'::regclass AND i.indisunique
      AND NOT i.indisprimary AND i.indexprs IS NULL
      AND (SELECT array_agg(a.attname::text ORDER BY a.attname)
           FROM unnest(i.indkey) WITH ORDINALITY k(attnum,n)
           JOIN pg_catalog.pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
           WHERE k.n <= i.indnkeyatts) = ARRAY['date','pair']
  LOOP
    EXECUTE format('DROP INDEX %s',item.index_name);
  END LOOP;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS regime_calls_publication_identity
  ON public.regime_calls(pair,date,data_source,strategy_version,model_version) NULLS NOT DISTINCT;

CREATE TABLE IF NOT EXISTS public.publication_evidence (
  call_id integer PRIMARY KEY REFERENCES public.regime_calls(id) ON DELETE RESTRICT,
  call_payload jsonb NOT NULL,
  signal_payload jsonb NOT NULL,
  rationale_payload jsonb,
  payload_hash text NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
  supersedes_call_id integer REFERENCES public.regime_calls(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.signal_projection_history (
  id bigserial PRIMARY KEY,
  pair text NOT NULL,
  date date NOT NULL,
  signal_payload jsonb NOT NULL,
  operation text NOT NULL CHECK (operation IN ('UPDATE','DELETE')),
  archived_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.signal_projection_history IS
  'Prior current projections, not reconstructed original evidence for legacy calls.';

CREATE OR REPLACE FUNCTION public.reject_publication_mutation()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  RAISE EXCEPTION '% is immutable; append an explicit new version',TG_TABLE_NAME;
END $$;
DO $$
DECLARE table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['regime_calls','publication_evidence','call_rationale','signal_projection_history'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS publication_immutable ON public.%I',table_name);
    EXECUTE format('CREATE TRIGGER publication_immutable BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.reject_publication_mutation()',table_name);
  END LOOP;
END $$;
CREATE OR REPLACE FUNCTION public.archive_signal_projection()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
  INSERT INTO public.signal_projection_history(pair,date,signal_payload,operation)
    VALUES (OLD.pair,OLD.date,to_jsonb(OLD),TG_OP);
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS archive_signal_projection ON public.signals;
CREATE TRIGGER archive_signal_projection BEFORE UPDATE OR DELETE ON public.signals
  FOR EACH ROW EXECUTE FUNCTION public.archive_signal_projection();

-- JSON numbers with different formatting (1 and 1.0) have the same fingerprint.
CREATE OR REPLACE FUNCTION public.publication_canonical_json(value jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE result jsonb;
BEGIN
  CASE jsonb_typeof(value)
    WHEN 'number' THEN RETURN to_jsonb(trim_scale(value::text::numeric));
    WHEN 'array' THEN
      SELECT coalesce(jsonb_agg(public.publication_canonical_json(v) ORDER BY n),'[]'::jsonb)
        INTO result FROM jsonb_array_elements(value) WITH ORDINALITY x(v,n);
      RETURN result;
    WHEN 'object' THEN
      SELECT coalesce(jsonb_object_agg(k,public.publication_canonical_json(v)),'{}'::jsonb)
        INTO result FROM jsonb_each(value) x(k,v);
      RETURN result;
    ELSE RETURN value;
  END CASE;
END $$;

CREATE OR REPLACE FUNCTION public.append_regime_publication(
  p_call jsonb, p_signal jsonb, p_rationale jsonb,
  p_supersedes_call_id integer DEFAULT NULL
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
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

REVOKE ALL ON FUNCTION public.append_regime_publication(jsonb,jsonb,jsonb,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.append_regime_publication(jsonb,jsonb,jsonb,integer) TO service_role;
REVOKE ALL ON FUNCTION public.archive_signal_projection() FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.reject_publication_mutation() FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.publication_canonical_json(jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON public.regime_calls,public.publication_evidence,public.signal_projection_history FROM PUBLIC,anon,authenticated,service_role;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON public.call_rationale FROM PUBLIC,anon,authenticated;
REVOKE UPDATE,DELETE,TRUNCATE ON public.call_rationale FROM service_role;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON public.signals FROM PUBLIC,anon,authenticated;
ALTER TABLE public.publication_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_projection_history ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON public.publication_evidence,public.signal_projection_history TO service_role;
DROP POLICY IF EXISTS publication_service_read ON public.publication_evidence;
CREATE POLICY publication_service_read ON public.publication_evidence FOR SELECT TO service_role USING (true);
DROP POLICY IF EXISTS projection_history_service_read ON public.signal_projection_history;
CREATE POLICY projection_history_service_read ON public.signal_projection_history FOR SELECT TO service_role USING (true);
COMMIT;
