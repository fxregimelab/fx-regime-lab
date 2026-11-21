-- Bound private FPI storage requests without changing retained evidence or receipts.
-- statement_timeout must be inherited; a function SET does not arm the outer timer.
BEGIN;

CREATE OR REPLACE FUNCTION public.append_fpi_capture(
    p_capture_sha256 text,
    p_document_json text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
SET timezone = 'UTC'
SET lock_timeout = '10s'
AS $$
DECLARE
    raw_doc json;
    doc jsonb;
    decoded_body bytea;
    requested timestamptz;
    retrieved timestamptz;
    receipt timestamptz;
    inserted boolean;
    saved_text text;
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION 'FPI storage requires an inherited bounded statement timeout';
    END IF;
    IF p_document_json IS NULL
       OR octet_length(convert_to(p_document_json, 'UTF8')) > 7000000
       OR p_capture_sha256 IS NULL
       OR p_capture_sha256 !~ '^[0-9a-f]{64}$'
       OR encode(sha256(convert_to(p_document_json, 'UTF8')), 'hex') <> p_capture_sha256 THEN
        RAISE EXCEPTION 'Invalid FPI capture envelope';
    END IF;

    raw_doc := p_document_json::json;
    IF NOT public.fpi_capture_unique_json(raw_doc) THEN
        RAISE EXCEPTION 'Invalid FPI capture envelope';
    END IF;
    doc := p_document_json::jsonb;

    IF NOT public.fpi_capture_keys(doc, ARRAY[
        'version', 'source_url', 'requested_at', 'retrieved_at',
        'http_status', 'body_base64', 'body_size', 'raw_sha256'
    ])
       OR jsonb_typeof(doc->'version') IS DISTINCT FROM 'string'
       OR doc->>'version' IS DISTINCT FROM 'fpi-http-capture-v1'
       OR jsonb_typeof(doc->'source_url') IS DISTINCT FROM 'string'
       OR doc->>'source_url' NOT IN (
           'https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx',
           'https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx'
       ) THEN
        RAISE EXCEPTION 'Invalid FPI capture schema';
    END IF;

    -- Read integer lexemes from JSON, not JSONB: JSONB normalizes 2e2 and 200.0.
    IF json_typeof(raw_doc->'http_status') IS DISTINCT FROM 'number'
       OR raw_doc->>'http_status' !~ '^(0|[1-9][0-9]*)$'
       OR (doc->>'http_status')::numeric NOT BETWEEN 100 AND 599
       OR json_typeof(raw_doc->'body_size') IS DISTINCT FROM 'number'
       OR raw_doc->>'body_size' !~ '^(0|[1-9][0-9]*)$'
       OR (doc->>'body_size')::numeric > 5000000 THEN
        RAISE EXCEPTION 'Invalid FPI capture integer';
    END IF;

    requested := public.fpi_capture_time(doc->'requested_at');
    retrieved := public.fpi_capture_time(doc->'retrieved_at');
    IF requested > retrieved OR retrieved > clock_timestamp() THEN
        RAISE EXCEPTION 'Invalid FPI capture time order';
    END IF;

    IF jsonb_typeof(doc->'raw_sha256') IS DISTINCT FROM 'string'
       OR doc->>'raw_sha256' !~ '^[0-9a-f]{64}$'
       OR jsonb_typeof(doc->'body_base64') IS DISTINCT FROM 'string'
       OR doc->>'body_base64' !~ '^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$' THEN
        RAISE EXCEPTION 'Invalid FPI capture body';
    END IF;

    decoded_body := decode(doc->>'body_base64', 'base64');
    IF replace(encode(decoded_body, 'base64'), E'\n', '') IS DISTINCT FROM doc->>'body_base64'
       OR octet_length(decoded_body) <> (doc->>'body_size')::integer
       OR octet_length(decoded_body) > 5000000
       OR encode(sha256(decoded_body), 'hex') IS DISTINCT FROM doc->>'raw_sha256' THEN
        RAISE EXCEPTION 'Invalid FPI capture body';
    END IF;

    receipt := clock_timestamp();
    INSERT INTO public.fpi_captures(
        capture_sha256, document_json, document, source_url, requested_at,
        retrieved_at, raw_sha256, body_size, http_status, stored_at
    ) VALUES (
        p_capture_sha256, p_document_json, doc, doc->>'source_url', requested,
        retrieved, doc->>'raw_sha256', (doc->>'body_size')::integer,
        (doc->>'http_status')::integer, receipt
    )
    ON CONFLICT (capture_sha256) DO NOTHING;
    inserted := FOUND;

    SELECT document_json, stored_at
      INTO saved_text, receipt
      FROM public.fpi_captures
     WHERE capture_sha256 = p_capture_sha256;
    IF saved_text IS DISTINCT FROM p_document_json THEN
        RAISE EXCEPTION 'FPI capture fingerprint conflict';
    END IF;

    RETURN jsonb_build_object(
        'capture_sha256', p_capture_sha256,
        'inserted', inserted,
        'stored_at', receipt
    );
EXCEPTION WHEN OTHERS THEN
    -- Never echo submitted JSON, decoded bytes, source content or provider diagnostics.
    RAISE EXCEPTION USING
        MESSAGE = 'FPI capture rejected: invalid input or storage conflict',
        ERRCODE = '22023';
END
$$;

CREATE OR REPLACE FUNCTION public.append_fpi_artifact(p_artifact_sha256 text,p_document_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET timezone = 'UTC'
SET lock_timeout = '10s' AS $$
DECLARE doc jsonb; body bytea; saved text; receipt timestamptz; inserted boolean;
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION 'FPI storage requires an inherited bounded statement timeout';
    END IF;
    doc := public.fpi_parse_document(p_document_json,7000000);
    IF NOT public.fpi_capture_keys(doc,ARRAY['version','kind','artifact_sha256','body_size','body_base64'])
       OR doc->>'version' IS DISTINCT FROM 'fpi-implementation-artifact-v1'
       OR jsonb_typeof(doc->'kind') IS DISTINCT FROM 'string' OR doc->>'kind' NOT IN ('PARSER','SELECTOR')
       OR p_artifact_sha256 IS NULL OR p_artifact_sha256 !~ '^[0-9a-f]{64}$'
       OR jsonb_typeof(doc->'artifact_sha256') IS DISTINCT FROM 'string'
       OR doc->>'artifact_sha256' IS DISTINCT FROM p_artifact_sha256
       OR jsonb_typeof(doc->'body_size') IS DISTINCT FROM 'number'
       OR p_document_json::json->>'body_size' !~ '^[1-9][0-9]*$'
       OR (doc->>'body_size')::numeric NOT BETWEEN 1 AND 5000000
       OR jsonb_typeof(doc->'body_base64') IS DISTINCT FROM 'string'
       OR doc->>'body_base64' !~ '^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$' THEN
        RAISE EXCEPTION 'Invalid artifact';
    END IF;
    body := decode(doc->>'body_base64','base64');
    IF replace(encode(body,'base64'),E'\n','') IS DISTINCT FROM doc->>'body_base64'
       OR octet_length(body) <> (doc->>'body_size')::integer
       OR encode(sha256(body),'hex') <> p_artifact_sha256 THEN RAISE EXCEPTION 'Invalid artifact bytes'; END IF;
    INSERT INTO public.fpi_implementation_artifacts(kind,artifact_sha256,document_json,body_size)
    VALUES(doc->>'kind',p_artifact_sha256,p_document_json,octet_length(body)) ON CONFLICT DO NOTHING;
    inserted := FOUND;
    SELECT document_json,stored_at INTO saved,receipt FROM public.fpi_implementation_artifacts
      WHERE kind=doc->>'kind' AND artifact_sha256=p_artifact_sha256;
    IF saved IS DISTINCT FROM p_document_json THEN RAISE EXCEPTION 'Artifact conflict'; END IF;
    RETURN jsonb_build_object('artifact_sha256',p_artifact_sha256,'kind',doc->>'kind',
        'inserted',inserted,'stored_at',receipt);
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION USING MESSAGE='FPI artifact rejected: invalid input or storage conflict',ERRCODE='22023';
END $$;

CREATE OR REPLACE FUNCTION public.append_fpi_parse_result(p_parse_id text,p_record_sha256 text,p_document_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET timezone = 'UTC'
SET lock_timeout = '10s' AS $$
DECLARE
    doc jsonb; member jsonb; content_days jsonb := '[]'; members jsonb := '[]';
    field text; recorded timestamptz; retrieved timestamptz; http integer;
    previous_day text := ''; saved text; receipt timestamptz; inserted boolean; computed text;
BEGIN
    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION 'FPI storage requires an inherited bounded statement timeout';
    END IF;
    doc := public.fpi_parse_document(p_document_json,4000000);
    IF NOT public.fpi_capture_keys(doc,ARRAY['version','parse_id','content_sha256','capture_sha256',
        'parser_sha256','definition_version','recorded_at','failure_reason','days'])
       OR doc->>'version' IS DISTINCT FROM 'fpi-parse-record-v1'
       OR doc->>'definition_version' IS DISTINCT FROM 'fpi-inr-observation-v1'
       OR p_parse_id IS NULL OR doc->>'parse_id' IS DISTINCT FROM p_parse_id
       OR p_record_sha256 IS NULL OR public.fpi_parse_hash(p_document_json) IS DISTINCT FROM p_record_sha256
       OR jsonb_typeof(doc->'days') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Invalid parse envelope'; END IF;
    FOREACH field IN ARRAY ARRAY['parse_id','content_sha256','capture_sha256','parser_sha256'] LOOP
        IF jsonb_typeof(doc->field) IS DISTINCT FROM 'string' OR doc->>field !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'Invalid parse hash';
        END IF;
    END LOOP;
    computed := public.fpi_parse_hash(public.fpi_parse_canonical(jsonb_build_array(
        doc->>'capture_sha256',doc->>'parser_sha256',doc->>'definition_version')));
    IF computed <> p_parse_id THEN RAISE EXCEPTION 'Invalid parse identity'; END IF;
    recorded := public.fpi_capture_time(doc->'recorded_at');
    -- datetime.isoformat() omits the fraction when microseconds are zero.
    -- Accepting .000000 would create an envelope the Python restore rejects.
    IF doc->>'recorded_at' LIKE '%.000000+00:00' THEN RAISE EXCEPTION 'Noncanonical parse time'; END IF;
    SELECT retrieved_at,http_status INTO retrieved,http FROM public.fpi_captures
        WHERE capture_sha256=doc->>'capture_sha256';
    IF NOT FOUND OR recorded < retrieved OR recorded > clock_timestamp() THEN RAISE EXCEPTION 'Invalid parse time'; END IF;
    IF jsonb_typeof(doc->'failure_reason') = 'null' THEN
        IF jsonb_array_length(doc->'days') NOT BETWEEN 1 AND 31 OR http <> 200 THEN
            RAISE EXCEPTION 'Invalid successful parse';
        END IF;
    ELSIF jsonb_typeof(doc->'failure_reason') IS DISTINCT FROM 'string'
       OR doc->>'failure_reason' !~ '^[A-Z][A-Z0-9_]{0,63}$' OR jsonb_array_length(doc->'days') <> 0 THEN
        RAISE EXCEPTION 'Invalid failed parse';
    END IF;
    FOR member IN SELECT value FROM jsonb_array_elements(doc->'days') LOOP
        IF NOT public.fpi_capture_keys(member,ARRAY['reporting_date','value_sha256','membership_id','document_json',
            'source_evidence_sha256','source_evidence_document_json']) THEN RAISE EXCEPTION 'Invalid member'; END IF;
        FOREACH field IN ARRAY ARRAY['reporting_date','value_sha256','membership_id','document_json',
            'source_evidence_sha256','source_evidence_document_json'] LOOP
            IF jsonb_typeof(member->field) IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'Invalid member type'; END IF;
        END LOOP;
        IF member->>'reporting_date' <= previous_day
           OR (member->>'reporting_date')::date > (retrieved AT TIME ZONE 'Asia/Kolkata')::date
           OR public.fpi_parse_hash(member->>'document_json') IS DISTINCT FROM member->>'value_sha256'
           OR public.fpi_parse_hash(member->>'source_evidence_document_json') IS DISTINCT FROM member->>'source_evidence_sha256'
           OR public.fpi_parse_hash(public.fpi_parse_canonical(jsonb_build_array(p_parse_id,
               member->>'value_sha256',member->>'source_evidence_sha256'))) IS DISTINCT FROM member->>'membership_id' THEN
            RAISE EXCEPTION 'Invalid member identity or date';
        END IF;
        PERFORM public.fpi_parse_day(member->>'document_json',member->>'source_evidence_document_json',member->>'reporting_date');
        previous_day := member->>'reporting_date';
        members := members || jsonb_build_array(member->>'membership_id');
        content_days := content_days || jsonb_build_array(jsonb_build_object('document_json',member->>'document_json',
            'source_evidence_sha256',member->>'source_evidence_sha256'));
    END LOOP;
    computed := public.fpi_parse_hash(public.fpi_parse_canonical(jsonb_build_object('parse_id',p_parse_id,
        'recorded_at',doc->>'recorded_at','days',content_days,'failure_reason',doc->'failure_reason')));
    IF computed IS DISTINCT FROM doc->>'content_sha256' THEN RAISE EXCEPTION 'Invalid content identity'; END IF;
    INSERT INTO public.fpi_parse_results(parse_id,record_sha256,content_sha256,document_json,capture_sha256,
        parser_sha256,definition_version,recorded_at,failure_reason)
    VALUES(p_parse_id,p_record_sha256,computed,p_document_json,doc->>'capture_sha256',doc->>'parser_sha256',
        doc->>'definition_version',recorded,doc->>'failure_reason') ON CONFLICT (parse_id) DO NOTHING;
    inserted := FOUND;
    SELECT document_json,stored_at INTO saved,receipt FROM public.fpi_parse_results WHERE parse_id=p_parse_id;
    IF saved IS DISTINCT FROM p_document_json THEN RAISE EXCEPTION 'Parse identity conflict'; END IF;
    IF inserted THEN
        INSERT INTO public.fpi_parsed_memberships(membership_id,parse_id,reporting_date,value_sha256,
            document_json,source_evidence_sha256,source_evidence_document_json)
        SELECT item->>'membership_id',p_parse_id,(item->>'reporting_date')::date,item->>'value_sha256',
            item->>'document_json',item->>'source_evidence_sha256',item->>'source_evidence_document_json'
        FROM jsonb_array_elements(doc->'days') AS entries(item);
    END IF;
    RETURN jsonb_build_object('parse_id',p_parse_id,'record_sha256',p_record_sha256,'content_sha256',computed,
        'membership_ids',members,'inserted',inserted,'stored_at',receipt);
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION USING MESSAGE='FPI parse rejected: invalid input or storage conflict',ERRCODE='22023';
END $$;

COMMIT;
