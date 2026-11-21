-- Private evidence only. No accepted-price, evaluation or historical-table writes.
BEGIN;

CREATE TABLE IF NOT EXISTS public.quote_captures (
    capture_sha256 text PRIMARY KEY CHECK (capture_sha256 ~ '^[0-9a-f]{64}$'),
    unsigned_json text NOT NULL,
    document jsonb NOT NULL,
    pair text NOT NULL CHECK (pair IN ('EURUSD','USDJPY','USDINR')),
    instrument text NOT NULL,
    window_start_ns numeric NOT NULL,
    window_end_ns numeric NOT NULL,
    received_at timestamptz NOT NULL,
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS public.quote_snapshots (
    snapshot_sha256 text PRIMARY KEY CHECK (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    unsigned_json text NOT NULL,
    document jsonb NOT NULL,
    pair text NOT NULL CHECK (pair IN ('EURUSD','USDJPY','USDINR')),
    instrument text NOT NULL,
    window_start_ns numeric NOT NULL,
    window_end_ns numeric NOT NULL,
    as_of timestamptz NOT NULL,
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS public.quote_snapshot_pages (
    snapshot_sha256 text NOT NULL REFERENCES public.quote_snapshots(snapshot_sha256),
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    capture_sha256 text NOT NULL REFERENCES public.quote_captures(capture_sha256),
    PRIMARY KEY (snapshot_sha256, ordinal)
);
CREATE INDEX IF NOT EXISTS quote_captures_pair_window_receipt
    ON public.quote_captures(pair,window_start_ns,received_at);
CREATE INDEX IF NOT EXISTS quote_snapshots_pair_window_as_of
    ON public.quote_snapshots(pair,window_start_ns,as_of);
CREATE INDEX IF NOT EXISTS quote_snapshot_pages_capture
    ON public.quote_snapshot_pages(capture_sha256);
COMMENT ON TABLE public.quote_captures IS
    'Private immutable redacted captures; unsigned_json is authoritative UTF-8 hash input. Not provider authentication.';
COMMENT ON TABLE public.quote_snapshots IS
    'Private provisional constructor output, never validation eligible. Storage does not independently prove midpoint arithmetic or implementation provenance.';

CREATE OR REPLACE FUNCTION public.reject_quote_storage_mutation()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
    RAISE EXCEPTION 'Quote storage is immutable; append new evidence';
END $$;

-- Use JSON (not JSONB) while checking syntax and duplicate keys: source numbers
-- can exceed PostgreSQL numeric's exponent range and remain legitimate evidence.
CREATE OR REPLACE FUNCTION public.quote_storage_unique_json(value json)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE child json;
BEGIN
    IF json_typeof(value) = 'object' THEN
        IF EXISTS (SELECT 1 FROM json_each(value) GROUP BY key HAVING count(*) > 1) THEN
            RETURN false;
        END IF;
        FOR child IN SELECT v FROM json_each(value) AS e(k,v) LOOP
            IF NOT public.quote_storage_unique_json(child) THEN RETURN false; END IF;
        END LOOP;
    ELSIF json_typeof(value) = 'array' THEN
        FOR child IN SELECT v FROM json_array_elements(value) AS e(v) LOOP
            IF NOT public.quote_storage_unique_json(child) THEN RETURN false; END IF;
        END LOOP;
    END IF;
    RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.quote_storage_keys(value jsonb, expected text[])
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,public AS $$
    SELECT CASE WHEN jsonb_typeof(value) = 'object' THEN
        (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(value) AS e(key))
        IS NOT DISTINCT FROM (SELECT array_agg(key ORDER BY key) FROM unnest(expected) AS e(key))
    ELSE false END
$$;

CREATE OR REPLACE FUNCTION public.quote_storage_time(value jsonb)
RETURNS timestamptz LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE result timestamptz; source text := value #>> '{}';
BEGIN
    IF jsonb_typeof(value) IS DISTINCT FROM 'string' OR source !~
       '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{6})?\+00:00$'
       OR source LIKE '0000-%' THEN
        RAISE EXCEPTION 'Invalid quote timestamp';
    END IF;
    result := source::timestamptz;
    IF NOT isfinite(result) THEN RAISE EXCEPTION 'Invalid quote timestamp'; END IF;
    RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.quote_storage_identity(value jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE key text; first_ns numeric; last_ns numeric;
BEGIN
    FOREACH key IN ARRAY ARRAY['pair','instrument','window_start_ns','window_end_ns'] LOOP
        IF jsonb_typeof(value->key) IS DISTINCT FROM 'string' THEN RETURN false; END IF;
    END LOOP;
    IF (value->>'pair',value->>'instrument') NOT IN
       (('EURUSD','C:EUR-USD'),('USDJPY','C:USD-JPY'),('USDINR','C:USD-INR')) THEN RETURN false; END IF;
    IF value->>'window_start_ns' !~ '^(0|[1-9][0-9]*)$' OR
       value->>'window_end_ns' !~ '^(0|[1-9][0-9]*)$' THEN RETURN false; END IF;
    first_ns := (value->>'window_start_ns')::numeric;
    last_ns := (value->>'window_end_ns')::numeric;
    RETURN last_ns-first_ns = 86400000000000 AND mod(first_ns,86400000000000) = 0;
END $$;

CREATE OR REPLACE FUNCTION public.append_quote_capture(p_capture_sha256 text, p_unsigned_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
    doc jsonb; body json; body_valid boolean := true; key text; val jsonb;
    first_request boolean; receipt timestamptz; requested timestamptz;
    inserted boolean; saved text; issue_order integer := 0; issue_index integer;
    next_url text;
BEGIN
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
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
    doc jsonb; ref jsonb; val jsonb; key text; capture_hash text;
    instant timestamptz; n integer; inserted boolean; saved text; input_text text;
BEGIN
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

DO $$ DECLARE tab text; BEGIN
    FOREACH tab IN ARRAY ARRAY['quote_captures','quote_snapshots','quote_snapshot_pages'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS quote_immutable ON public.%I',tab);
        EXECUTE format('CREATE TRIGGER quote_immutable BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.reject_quote_storage_mutation()',tab);
        EXECUTE format('DROP TRIGGER IF EXISTS quote_no_truncate ON public.%I',tab);
        EXECUTE format('CREATE TRIGGER quote_no_truncate BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.reject_quote_storage_mutation()',tab);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tab);
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,service_role',tab);
        EXECUTE format('GRANT SELECT ON public.%I TO service_role',tab);
        EXECUTE format('DROP POLICY IF EXISTS quote_service_read ON public.%I',tab);
        EXECUTE format('CREATE POLICY quote_service_read ON public.%I FOR SELECT TO service_role USING (true)',tab);
    END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.reject_quote_storage_mutation(),
    public.quote_storage_unique_json(json),public.quote_storage_keys(jsonb,text[]),
    public.quote_storage_time(jsonb),public.quote_storage_identity(jsonb),
    public.append_quote_capture(text,text),public.append_quote_snapshot(text,text)
    FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.append_quote_capture(text,text),public.append_quote_snapshot(text,text) TO service_role;
COMMIT;
