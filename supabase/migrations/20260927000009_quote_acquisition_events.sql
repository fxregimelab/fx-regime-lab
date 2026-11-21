-- Private attempt evidence. Retrieval completion never qualifies a market price.
BEGIN;

CREATE TABLE IF NOT EXISTS public.quote_acquisition_events (
    attempt_id uuid NOT NULL,
    sequence integer NOT NULL CHECK (sequence BETWEEN 0 AND 10001),
    event_sha256 text NOT NULL UNIQUE CHECK (event_sha256 ~ '^[0-9a-f]{64}$'),
    unsigned_json text NOT NULL,
    document jsonb NOT NULL,
    kind text NOT NULL CHECK (kind IN ('started','page_saved','finished')),
    occurred_at timestamptz NOT NULL,
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (attempt_id,sequence)
);
COMMENT ON TABLE public.quote_acquisition_events IS
    'Private append-only acquisition attempts, including zero-response failures. Exact unsigned UTF-8 text is authoritative; no qualification permission.';

CREATE OR REPLACE FUNCTION public.append_quote_acquisition_event(p_event_sha256 text, p_unsigned_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
    raw json; doc jsonb; manifest jsonb; limits jsonb; key text; value jsonb; manifest_text text;
    attempt uuid; seq integer; instant timestamptz;
    prior public.quote_acquisition_events%ROWTYPE;
    saved public.quote_acquisition_events%ROWTYPE;
    captures jsonb; snapshot public.quote_snapshots%ROWTYPE;
BEGIN
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

DROP TRIGGER IF EXISTS quote_immutable ON public.quote_acquisition_events;
CREATE TRIGGER quote_immutable BEFORE UPDATE OR DELETE ON public.quote_acquisition_events
    FOR EACH ROW EXECUTE FUNCTION public.reject_quote_storage_mutation();
DROP TRIGGER IF EXISTS quote_no_truncate ON public.quote_acquisition_events;
CREATE TRIGGER quote_no_truncate BEFORE TRUNCATE ON public.quote_acquisition_events
    FOR EACH STATEMENT EXECUTE FUNCTION public.reject_quote_storage_mutation();
ALTER TABLE public.quote_acquisition_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.quote_acquisition_events FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.quote_acquisition_events TO service_role;
DROP POLICY IF EXISTS quote_service_read ON public.quote_acquisition_events;
CREATE POLICY quote_service_read ON public.quote_acquisition_events FOR SELECT TO service_role USING (true);
REVOKE ALL ON FUNCTION public.append_quote_acquisition_event(text,text) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.append_quote_acquisition_event(text,text) TO service_role;
COMMIT;
