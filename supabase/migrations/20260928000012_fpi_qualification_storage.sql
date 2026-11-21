-- Administrative assertions only: ACCEPT does not authorize feature consumption.
BEGIN;
CREATE SEQUENCE IF NOT EXISTS public.fpi_qualification_ordinal AS bigint MINVALUE 1;
CREATE TABLE IF NOT EXISTS public.fpi_qualification_events (
    event_id text PRIMARY KEY CHECK (event_id ~ '^[0-9a-f]{64}$'),
    command_id text UNIQUE NOT NULL CHECK (command_id ~ '^[0-9a-f]{64}$'),
    command_document_json text NOT NULL,
    event_document_json text NOT NULL,
    event_ordinal bigint UNIQUE NOT NULL CHECK (event_ordinal > 0),
    scope text NOT NULL CHECK (scope IN ('membership','value','parser','date')),
    target text NOT NULL,
    expected_prior_event_id text REFERENCES public.fpi_qualification_events(event_id),
    recorded_at timestamptz NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS fpi_qualification_successor
    ON public.fpi_qualification_events(scope,target,coalesce(expected_prior_event_id,''));
CREATE INDEX IF NOT EXISTS fpi_qualification_target_order
    ON public.fpi_qualification_events(scope,target,event_ordinal DESC);

CREATE OR REPLACE FUNCTION public.fpi_qualification_clock()
RETURNS timestamptz LANGUAGE sql VOLATILE SET search_path = pg_catalog, public AS $$
    SELECT clock_timestamp()
$$;

CREATE OR REPLACE FUNCTION public.append_fpi_qualification(p_command_id text,p_document_json text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET lock_timeout = '10s'
AS $$
DECLARE
    doc jsonb; field text; item jsonb; previous text := ''; basis text[] := ARRAY[]::text[];
    command_scope text; command_target text; predecessor text; chosen text;
    saved public.fpi_qualification_events%ROWTYPE; current_head text;
    candidate_ids text[]; witness jsonb; allowed boolean;
    ordinal bigint; recorded timestamptz; time_text text; event_text text; identity text;
BEGIN
    -- A function SET cannot arm the outer statement timer. The caller must set
    -- this before its top-level request; deployment must verify that setup.
    IF (SELECT setting::bigint FROM pg_settings WHERE name='statement_timeout') NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION 'Unbounded caller statement timeout';
    END IF;
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Unsupported transaction isolation';
    END IF;
    doc := public.fpi_parse_document(p_document_json,300000);
    IF NOT public.fpi_capture_keys(doc,ARRAY['version','scope','target','action','reason_code',
        'evidence_sha256','expected_prior_event_id','chosen_membership_id','basis_membership_ids'])
       OR doc->>'version' IS DISTINCT FROM 'fpi-qualification-command-v2'
       OR p_command_id IS NULL OR p_command_id !~ '^[0-9a-f]{64}$'
       OR public.fpi_parse_hash(p_document_json) IS DISTINCT FROM p_command_id THEN
        RAISE EXCEPTION 'Invalid command envelope';
    END IF;
    FOREACH field IN ARRAY ARRAY['scope','target','action','reason_code','evidence_sha256'] LOOP
        IF jsonb_typeof(doc->field) IS DISTINCT FROM 'string' THEN
            RAISE EXCEPTION 'Invalid command type';
        END IF;
    END LOOP;
    FOREACH field IN ARRAY ARRAY['expected_prior_event_id','chosen_membership_id'] LOOP
        IF jsonb_typeof(doc->field) IS DISTINCT FROM 'null' AND
           (jsonb_typeof(doc->field) IS DISTINCT FROM 'string' OR doc->>field !~ '^[0-9a-f]{64}$') THEN
            RAISE EXCEPTION 'Invalid optional hash';
        END IF;
    END LOOP;
    IF doc->>'reason_code' !~ '^[A-Z][A-Z0-9_]{0,63}$'
       OR doc->>'evidence_sha256' !~ '^[0-9a-f]{64}$'
       OR jsonb_typeof(doc->'basis_membership_ids') IS DISTINCT FROM 'array'
       OR jsonb_array_length(doc->'basis_membership_ids') > 4096 THEN
        RAISE EXCEPTION 'Invalid command fields';
    END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(doc->'basis_membership_ids') LOOP
        IF jsonb_typeof(item) IS DISTINCT FROM 'string' OR item #>> '{}' !~ '^[0-9a-f]{64}$'
           OR (item #>> '{}') COLLATE "C" <= previous COLLATE "C" THEN
            RAISE EXCEPTION 'Invalid basis';
        END IF;
        previous := item #>> '{}'; basis := array_append(basis,previous);
    END LOOP;
    command_scope := doc->>'scope'; command_target := doc->>'target';
    predecessor := doc->>'expected_prior_event_id'; chosen := doc->>'chosen_membership_id';
    IF command_scope = 'date' THEN
        IF command_target !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR command_target LIKE '0000-%'
           OR to_char(command_target::date,'YYYY-MM-DD') <> command_target
           OR doc->>'action' <> 'RESOLVE' OR chosen IS NULL OR cardinality(basis)=0
           OR NOT chosen=ANY(basis) THEN RAISE EXCEPTION 'Invalid date command'; END IF;
    ELSIF command_scope IN ('membership','value','parser') THEN
        IF command_target !~ '^[0-9a-f]{64}$' OR doc->>'action' NOT IN ('ACCEPT','WITHDRAW','QUARANTINE')
           OR chosen IS NOT NULL OR cardinality(basis)<>0 THEN RAISE EXCEPTION 'Invalid scope command'; END IF;
    ELSE RAISE EXCEPTION 'Invalid scope'; END IF;

    -- One transaction-held order across scopes; each following SQL statement gets
    -- a fresh READ COMMITTED snapshot after a possible wait for an earlier writer.
    PERFORM pg_advisory_xact_lock(946027,1);
    SELECT * INTO saved FROM public.fpi_qualification_events WHERE command_id=p_command_id;
    IF FOUND THEN
        IF saved.command_document_json IS DISTINCT FROM p_document_json THEN
            RAISE EXCEPTION 'Command identity conflict';
        END IF;
        RETURN jsonb_build_object('version','fpi-qualification-receipt-v2','command_id',saved.command_id,
            'event_id',saved.event_id,'event_ordinal',saved.event_ordinal,
            'recorded_at',saved.event_document_json::jsonb->>'recorded_at',
            'event_document_json',saved.event_document_json,'inserted',false);
    END IF;
    IF (command_scope='membership' AND NOT EXISTS(SELECT 1 FROM public.fpi_parsed_memberships WHERE membership_id=command_target))
       OR (command_scope='value' AND NOT EXISTS(SELECT 1 FROM public.fpi_parsed_memberships WHERE value_sha256=command_target))
       OR (command_scope='parser' AND NOT EXISTS(SELECT 1 FROM public.fpi_implementation_artifacts WHERE kind='PARSER' AND artifact_sha256=command_target)) THEN
        RAISE EXCEPTION 'Missing target';
    END IF;
    SELECT event_id INTO current_head FROM public.fpi_qualification_events
        WHERE scope=command_scope AND target=command_target ORDER BY event_ordinal DESC LIMIT 1;
    IF current_head IS DISTINCT FROM predecessor THEN RAISE EXCEPTION 'Stale predecessor'; END IF;
    IF command_scope='date' THEN
        -- Bound the candidate read before aggregation. Candidate universe, chosen
        -- metadata and all three heads share this single statement snapshot.
        WITH candidates AS MATERIALIZED (
            SELECT membership_id,value_sha256,parse_id FROM public.fpi_parsed_memberships
            WHERE reporting_date=command_target::date ORDER BY membership_id COLLATE "C" LIMIT 4097
        ), selected AS (
            SELECT c.*,p.parser_sha256 FROM candidates c JOIN public.fpi_parse_results p USING(parse_id)
            WHERE c.membership_id=chosen
        ), targets AS (
            SELECT 'membership'::text AS scope,membership_id AS target FROM selected
            UNION ALL SELECT 'value',value_sha256 FROM selected
            UNION ALL SELECT 'parser',parser_sha256 FROM selected
        ), heads AS (
            SELECT t.scope,t.target,e.event_id,e.command_document_json::jsonb->>'action' AS action
            FROM targets t LEFT JOIN LATERAL (
                SELECT event_id,command_document_json FROM public.fpi_qualification_events q
                WHERE q.scope=t.scope AND q.target=t.target ORDER BY event_ordinal DESC LIMIT 1
            ) e ON true
        )
        SELECT (SELECT array_agg(membership_id ORDER BY membership_id COLLATE "C") FROM candidates),
            jsonb_build_object('heads',jsonb_agg(jsonb_build_object('scope',scope,'target',target,
                'event_id',event_id) ORDER BY scope COLLATE "C",target COLLATE "C")),
            count(*)=3 AND bool_and(CASE WHEN scope='membership' THEN action IS NOT DISTINCT FROM 'ACCEPT'
                ELSE event_id IS NULL OR action='ACCEPT' END)
        INTO candidate_ids,witness,allowed FROM heads;
        IF cardinality(candidate_ids)>4096 OR candidate_ids IS DISTINCT FROM basis OR NOT coalesce(allowed,false) THEN
            RAISE EXCEPTION 'Invalid resolution';
        END IF;
    END IF;
    ordinal := nextval('public.fpi_qualification_ordinal');
    recorded := public.fpi_qualification_clock();
    IF recorded IS NULL OR NOT isfinite(recorded) OR extract(year FROM recorded AT TIME ZONE 'UTC') NOT BETWEEN 1 AND 9999 THEN
        RAISE EXCEPTION 'Invalid server clock';
    END IF;
    time_text := to_char(recorded AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS') ||
        CASE WHEN extract(microseconds FROM recorded)::bigint % 1000000 = 0 THEN ''
             ELSE '.' || to_char(recorded AT TIME ZONE 'UTC','US') END || '+00:00';
    event_text := public.fpi_parse_canonical(jsonb_build_object('version','fpi-qualification-event-v2',
        'command',doc,'command_id',p_command_id,'event_ordinal',ordinal,'recorded_at',time_text,'witness',witness));
    identity := public.fpi_parse_hash(event_text);
    INSERT INTO public.fpi_qualification_events(event_id,command_id,command_document_json,event_document_json,
        event_ordinal,scope,target,expected_prior_event_id,recorded_at)
    VALUES(identity,p_command_id,p_document_json,event_text,ordinal,command_scope,command_target,predecessor,recorded);
    RETURN jsonb_build_object('version','fpi-qualification-receipt-v2','command_id',p_command_id,
        'event_id',identity,'event_ordinal',ordinal,'recorded_at',time_text,
        'event_document_json',event_text,'inserted',true);
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION USING MESSAGE='FPI qualification rejected: invalid input or storage conflict',ERRCODE='22023';
END $$;

DROP TRIGGER IF EXISTS immutable_rows ON public.fpi_qualification_events;
CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON public.fpi_qualification_events
    FOR EACH ROW EXECUTE FUNCTION public.reject_fpi_capture_mutation();
DROP TRIGGER IF EXISTS immutable_truncate ON public.fpi_qualification_events;
CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON public.fpi_qualification_events
    FOR EACH STATEMENT EXECUTE FUNCTION public.reject_fpi_capture_mutation();
ALTER TABLE public.fpi_qualification_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_read ON public.fpi_qualification_events;
CREATE POLICY service_read ON public.fpi_qualification_events FOR SELECT TO service_role USING(true);
REVOKE ALL ON TABLE public.fpi_qualification_events FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON SEQUENCE public.fpi_qualification_ordinal FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.fpi_qualification_clock() FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.append_fpi_qualification(text,text) FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.fpi_qualification_events TO service_role;
GRANT EXECUTE ON FUNCTION public.append_fpi_qualification(text,text) TO service_role;
COMMIT;
