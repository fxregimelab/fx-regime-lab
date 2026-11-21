-- Retain implementation bytes and whole parsed results. This is not qualification
-- or proof that a result was visible to a historical decision.
BEGIN;

CREATE TABLE IF NOT EXISTS public.fpi_implementation_artifacts (
    kind text NOT NULL CHECK (kind IN ('PARSER','SELECTOR')),
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    document_json text NOT NULL,
    body_size integer NOT NULL CHECK (body_size BETWEEN 1 AND 5000000),
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (kind, artifact_sha256)
);
CREATE TABLE IF NOT EXISTS public.fpi_parse_results (
    parse_id text PRIMARY KEY CHECK (parse_id ~ '^[0-9a-f]{64}$'),
    record_sha256 text NOT NULL CHECK (record_sha256 ~ '^[0-9a-f]{64}$'),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    document_json text NOT NULL,
    capture_sha256 text NOT NULL REFERENCES public.fpi_captures(capture_sha256),
    parser_kind text NOT NULL DEFAULT 'PARSER' CHECK (parser_kind = 'PARSER'),
    parser_sha256 text NOT NULL,
    definition_version text NOT NULL CHECK (definition_version = 'fpi-inr-observation-v1'),
    recorded_at timestamptz NOT NULL,
    failure_reason text CHECK (failure_reason ~ '^[A-Z][A-Z0-9_]{0,63}$'),
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK (stored_at >= recorded_at),
    FOREIGN KEY (parser_kind, parser_sha256)
        REFERENCES public.fpi_implementation_artifacts(kind, artifact_sha256)
);
CREATE TABLE IF NOT EXISTS public.fpi_parsed_memberships (
    membership_id text PRIMARY KEY CHECK (membership_id ~ '^[0-9a-f]{64}$'),
    parse_id text NOT NULL REFERENCES public.fpi_parse_results(parse_id),
    reporting_date date NOT NULL,
    value_sha256 text NOT NULL CHECK (value_sha256 ~ '^[0-9a-f]{64}$'),
    document_json text NOT NULL,
    source_evidence_sha256 text NOT NULL CHECK (source_evidence_sha256 ~ '^[0-9a-f]{64}$'),
    source_evidence_document_json text NOT NULL,
    UNIQUE (parse_id, reporting_date)
);
CREATE INDEX IF NOT EXISTS fpi_parse_capture_parser ON public.fpi_parse_results(capture_sha256, parser_sha256);
CREATE INDEX IF NOT EXISTS fpi_membership_date ON public.fpi_parsed_memberships(reporting_date);
CREATE INDEX IF NOT EXISTS fpi_membership_value ON public.fpi_parsed_memberships(value_sha256);

-- Permitted schemas contain ASCII strings only. Retain Python's sorted compact
-- representation, including escaping inside embedded document strings.
CREATE OR REPLACE FUNCTION public.fpi_parse_canonical(value jsonb, depth integer DEFAULT 0)
RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, public AS $$
DECLARE result text;
BEGIN
    IF depth > 16 THEN RAISE EXCEPTION 'JSON nesting limit'; END IF;
    CASE jsonb_typeof(value)
    WHEN 'object' THEN
        SELECT '{' || coalesce(string_agg(to_json(key)::text || ':' ||
            public.fpi_parse_canonical(item, depth+1), ',' ORDER BY key COLLATE "C"),'') || '}'
        INTO result FROM jsonb_each(value) AS entries(key,item);
    WHEN 'array' THEN
        SELECT '[' || coalesce(string_agg(public.fpi_parse_canonical(item,depth+1),',' ORDER BY n),'') || ']'
        INTO result FROM jsonb_array_elements(value) WITH ORDINALITY AS entries(item,n);
    ELSE result := value::text;
    END CASE;
    IF result IS NULL OR octet_length(result) <> length(result) THEN
        RAISE EXCEPTION 'Non-ASCII JSON';
    END IF;
    RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_parse_document(value text, max_size integer)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, public AS $$
DECLARE doc jsonb;
BEGIN
    IF value IS NULL OR octet_length(value) > max_size OR octet_length(value) <> length(value) THEN
        RAISE EXCEPTION 'Invalid document size';
    END IF;
    IF NOT public.fpi_capture_unique_json(value::json) THEN
        RAISE EXCEPTION 'Duplicate document keys';
    END IF;
    -- JSONB conversion rejects NUL and invalid surrogate escapes. Exact canonical
    -- comparison also rejects whitespace and alternate escapes.
    doc := value::jsonb;
    IF public.fpi_parse_canonical(doc) IS DISTINCT FROM value THEN
        RAISE EXCEPTION 'Noncanonical document';
    END IF;
    RETURN doc;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_parse_hash(value text)
RETURNS text LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, public AS $$
    SELECT encode(sha256(convert_to(value,'UTF8')),'hex')
$$;

CREATE OR REPLACE FUNCTION public.fpi_parse_money(value jsonb)
RETURNS numeric LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, public AS $$
DECLARE source text := value #>> '{}';
BEGIN
    IF jsonb_typeof(value) IS DISTINCT FROM 'string'
       OR source !~ '^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$' OR source = '-0.00' THEN
        RAISE EXCEPTION 'Invalid money';
    END IF;
    RETURN source::numeric * 100;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_parse_amounts(value jsonb)
RETURNS numeric[] LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, public AS $$
DECLARE amounts numeric[];
BEGIN
    IF NOT public.fpi_capture_keys(value,ARRAY['purchases_cr','sales_cr','net_cr']) THEN
        RAISE EXCEPTION 'Invalid amounts';
    END IF;
    amounts := ARRAY[public.fpi_parse_money(value->'purchases_cr'),
        public.fpi_parse_money(value->'sales_cr'),public.fpi_parse_money(value->'net_cr')];
    IF amounts[1] < 0 OR amounts[2] < 0 OR 2*abs(amounts[1]-amounts[2]-amounts[3]) > 3 THEN
        RAISE EXCEPTION 'Invalid gross/net reconciliation';
    END IF;
    RETURN amounts;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_parse_day(inr_text text, source_text text, day_text text)
RETURNS void LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, public AS $$
DECLARE
    doc jsonb := public.fpi_parse_document(inr_text,32768);
    source jsonb := public.fpi_parse_document(source_text,32768);
    categories text[] := ARRAY['Equity','Debt-General Limit','Debt-VRR','Debt-FAR','Hybrid','Mutual Funds','AIFs'];
    category text; route text; routes text[]; group_doc jsonb; group_source jsonb;
    amounts numeric[]; subtotal numeric[]; totals numeric[] := ARRAY[0,0,0]::numeric[];
    sums numeric[]; usd_sum numeric; usd_subtotal numeric; usd_total numeric := 0;
    n integer;
BEGIN
    IF day_text IS NULL OR day_text !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
       OR to_char(day_text::date,'YYYY-MM-DD') <> day_text OR day_text LIKE '0000-%'
       OR NOT public.fpi_capture_keys(doc,ARRAY['version','series_id','units','date_basis','reporting_date','categories','total'])
       OR doc->>'version' IS DISTINCT FROM 'fpi-inr-observation-v1'
       OR doc->>'series_id' IS DISTINCT FROM 'NSDL_FPI_CONFIRMED_REPORTED_ALL7_INR_CRORE_DAILY_V1'
       OR doc->>'units' IS DISTINCT FROM 'INR_CRORE'
       OR doc->>'date_basis' IS DISTINCT FROM 'reporting_date'
       OR doc->>'reporting_date' IS DISTINCT FROM day_text
       OR NOT public.fpi_capture_keys(doc->'categories',categories)
       OR NOT public.fpi_capture_keys(source,ARRAY['version','reporting_date','usd_units','conversion_rate_units',
           'conversion_rate_inr_per_usd','categories','total_net_usd_million'])
       OR source->>'version' IS DISTINCT FROM 'nsdl-fpi-source-evidence-v1'
       OR source->>'reporting_date' IS DISTINCT FROM day_text
       OR source->>'usd_units' IS DISTINCT FROM 'USD_MILLION'
       OR source->>'conversion_rate_units' IS DISTINCT FROM 'INR_PER_USD'
       OR NOT public.fpi_capture_keys(source->'categories',categories)
       OR jsonb_typeof(source->'conversion_rate_inr_per_usd') IS DISTINCT FROM 'string'
       OR source->>'conversion_rate_inr_per_usd' !~ '^(0|[1-9][0-9]{0,5})\.[0-9]{4}$'
       OR (source->>'conversion_rate_inr_per_usd')::numeric <= 0 THEN
        RAISE EXCEPTION 'Invalid dated evidence';
    END IF;
    FOREACH category IN ARRAY categories LOOP
        routes := CASE WHEN category='Mutual Funds' THEN ARRAY['Equity schemes','Debt schemes','Hybrid schemes',
            'Solution oriented schemes','Other schemes'] ELSE ARRAY['Stock Exchange','Primary market & others'] END;
        group_doc := doc->'categories'->category;
        group_source := source->'categories'->category;
        IF NOT public.fpi_capture_keys(group_doc,ARRAY['routes','subtotal'])
           OR NOT public.fpi_capture_keys(group_doc->'routes',routes)
           OR NOT public.fpi_capture_keys(group_source,ARRAY['routes_net_usd_million','subtotal_net_usd_million'])
           OR NOT public.fpi_capture_keys(group_source->'routes_net_usd_million',routes) THEN
            RAISE EXCEPTION 'Invalid category routes';
        END IF;
        sums := ARRAY[0,0,0]::numeric[]; usd_sum := 0;
        FOREACH route IN ARRAY routes LOOP
            amounts := public.fpi_parse_amounts(group_doc->'routes'->route);
            FOR n IN 1..3 LOOP sums[n] := sums[n]+amounts[n]; END LOOP;
            usd_sum := usd_sum+public.fpi_parse_money(group_source->'routes_net_usd_million'->route);
        END LOOP;
        subtotal := public.fpi_parse_amounts(group_doc->'subtotal');
        usd_subtotal := public.fpi_parse_money(group_source->'subtotal_net_usd_million');
        IF 2*abs(usd_sum-usd_subtotal) > cardinality(routes)+1 THEN
            RAISE EXCEPTION 'Invalid USD subtotal';
        END IF;
        usd_total := usd_total+usd_subtotal;
        FOR n IN 1..3 LOOP
            IF 2*abs(sums[n]-subtotal[n]) > cardinality(routes)+1 THEN
                RAISE EXCEPTION 'Invalid INR subtotal';
            END IF;
            totals[n] := totals[n]+subtotal[n];
        END LOOP;
    END LOOP;
    amounts := public.fpi_parse_amounts(doc->'total');
    FOR n IN 1..3 LOOP
        IF 2*abs(totals[n]-amounts[n]) > 8 THEN RAISE EXCEPTION 'Invalid INR total'; END IF;
    END LOOP;
    IF 2*abs(usd_total-public.fpi_parse_money(source->'total_net_usd_million')) > 8 THEN
        RAISE EXCEPTION 'Invalid USD total';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.append_fpi_artifact(p_artifact_sha256 text,p_document_json text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET timezone = 'UTC' AS $$
DECLARE doc jsonb; body bytea; saved text; receipt timestamptz; inserted boolean;
BEGIN
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
SET search_path = pg_catalog, public SET timezone = 'UTC' AS $$
DECLARE
    doc jsonb; member jsonb; content_days jsonb := '[]'; members jsonb := '[]';
    field text; recorded timestamptz; retrieved timestamptz; http integer;
    previous_day text := ''; saved text; receipt timestamptz; inserted boolean; computed text;
BEGIN
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

-- Touch only these tables/functions; unrelated grants and capture helper ACLs stay intact.
DO $$
DECLARE table_name text; signature text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['fpi_implementation_artifacts','fpi_parse_results','fpi_parsed_memberships'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS immutable_rows ON public.%I',table_name);
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.reject_fpi_capture_mutation()',table_name);
        EXECUTE format('DROP TRIGGER IF EXISTS immutable_truncate ON public.%I',table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.reject_fpi_capture_mutation()',table_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',table_name);
        EXECUTE format('DROP POLICY IF EXISTS service_read ON public.%I',table_name);
        EXECUTE format('CREATE POLICY service_read ON public.%I FOR SELECT TO service_role USING (true)',table_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC,anon,authenticated,service_role',table_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role',table_name);
    END LOOP;
    FOREACH signature IN ARRAY ARRAY['fpi_parse_canonical(jsonb,integer)','fpi_parse_document(text,integer)',
        'fpi_parse_hash(text)','fpi_parse_money(jsonb)','fpi_parse_amounts(jsonb)','fpi_parse_day(text,text,text)',
        'append_fpi_artifact(text,text)','append_fpi_parse_result(text,text,text)'] LOOP
        EXECUTE 'REVOKE ALL ON FUNCTION public.' || signature || ' FROM PUBLIC,anon,authenticated,service_role';
    END LOOP;
END $$;
GRANT EXECUTE ON FUNCTION public.append_fpi_artifact(text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.append_fpi_parse_result(text,text,text) TO service_role;
COMMIT;
