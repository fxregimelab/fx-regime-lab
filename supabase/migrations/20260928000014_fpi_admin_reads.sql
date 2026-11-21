-- Retained administrative reads never authorize execution or feature consumption.
-- Evidence discovery and retention share the one statement below, at READ COMMITTED.
BEGIN;
CREATE TABLE IF NOT EXISTS public.fpi_admin_read_policies (
 policy_sha256 text PRIMARY KEY CHECK(policy_sha256 ~ '^[0-9a-f]{64}$'),
 document_json text NOT NULL,
 selector_kind text NOT NULL DEFAULT 'SELECTOR' CHECK(selector_kind='SELECTOR'),
 selector_sha256 text NOT NULL,
 UNIQUE(policy_sha256,selector_sha256),
 FOREIGN KEY(selector_kind,selector_sha256) REFERENCES public.fpi_implementation_artifacts(kind,artifact_sha256)
);
CREATE TABLE IF NOT EXISTS public.fpi_admin_reads (
 read_id text PRIMARY KEY CHECK(read_id ~ '^[0-9a-f]{64}$'),
 decision_id uuid UNIQUE NOT NULL,
 request_sha256 text UNIQUE NOT NULL CHECK(read_id=request_sha256),
 request_document_json text NOT NULL,
 policy_sha256 text NOT NULL REFERENCES public.fpi_admin_read_policies(policy_sha256),
 read_sha256 text NOT NULL CHECK(read_sha256 ~ '^[0-9a-f]{64}$'),
 manifest_document_json text NOT NULL,
 read_at timestamptz NOT NULL,
 status text NOT NULL CHECK(status IN ('COMPLETE','CLOCK_INCONSISTENT','READ_SCOPE_EXCEEDED'))
);
CREATE INDEX IF NOT EXISTS fpi_admin_membership_date_id ON public.fpi_parsed_memberships(reporting_date,membership_id);
CREATE INDEX IF NOT EXISTS fpi_admin_failure_time_id ON public.fpi_parse_results(stored_at,parse_id) WHERE failure_reason IS NOT NULL;
CREATE INDEX IF NOT EXISTS fpi_admin_failure_capture_id ON public.fpi_parse_results(capture_sha256,parse_id) WHERE failure_reason IS NOT NULL;

CREATE OR REPLACE FUNCTION public.fpi_admin_clock() RETURNS timestamptz
LANGUAGE sql VOLATILE SET search_path=pg_catalog,public AS $$ SELECT clock_timestamp() $$;

CREATE OR REPLACE FUNCTION public.fpi_admin_assert(ok boolean) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
BEGIN
 IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'READ_INTEGRITY_ERROR'; END IF;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_admin_time(t timestamptz) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
BEGIN
 IF t IS NULL OR NOT isfinite(t) OR extract(year FROM t AT TIME ZONE 'UTC') NOT BETWEEN 1 AND 9999
 THEN RAISE EXCEPTION 'READ_CLOCK_RANGE'; END IF;
 RETURN to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS') ||
 CASE WHEN extract(microseconds FROM t AT TIME ZONE 'UTC')::bigint % 1000000=0 THEN ''
 ELSE '.'||to_char(t AT TIME ZONE 'UTC','US') END || '+00:00';
END $$;

CREATE OR REPLACE FUNCTION public.fpi_admin_document(value text,cap integer) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE n integer:=0; i integer; quoted boolean:=false; escaped boolean:=false; ch integer; bytes bytea;
BEGIN
 PERFORM public.fpi_admin_assert(value IS NOT NULL AND octet_length(value)<=cap AND octet_length(value)=length(value));
 -- Bound nesting before either recursive JSON uniqueness or canonical decoding.
 bytes:=convert_to(value,'UTF8');
 FOR i IN 0..octet_length(bytes)-1 LOOP
  ch:=get_byte(bytes,i);
  IF quoted THEN
   IF escaped THEN escaped:=false;
   ELSIF ch=92 THEN escaped:=true;
   ELSIF ch=34 THEN quoted:=false; END IF;
  ELSIF ch=34 THEN quoted:=true;
  ELSIF ch IN (123,91) THEN n:=n+1; PERFORM public.fpi_admin_assert(n<=32);
  ELSIF ch IN (125,93) THEN n:=n-1; END IF;
 END LOOP;
 RETURN public.fpi_parse_document(value,cap);
END $$;

CREATE OR REPLACE FUNCTION public.fpi_admin_policy(value text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE d jsonb:=public.fpi_admin_document(value,32768); k text; v jsonb; prior text:='';
BEGIN
 PERFORM public.fpi_admin_assert(public.fpi_capture_keys(d,ARRAY['version','scope_version','guardrail_version',
 'trust_mode','selector_version','selector_sha256','parser_allowlist','definition_allowlist','max_current_age_days',
 'max_history_age_days','minimum_history','history_window','diagnostic_window_days','feature_version','model_version',
 'prediction_horizon','source_rule','source_rationale','allow_withdrawal_fallback','age_timezone','missingness']));
 PERFORM public.fpi_admin_assert(d->>'version'='fpi-admin-read-policy-v1' AND d->>'scope_version'='fpi-admin-scope-v1'
 AND d->>'guardrail_version'='fpi-admin-read-limits-v1' AND d->>'trust_mode'='ADMINISTRATIVE_UNVERIFIED'
 AND d->>'selector_version'='NOT_EXECUTED' AND jsonb_typeof(d->'selector_sha256')='string'
 AND d->>'selector_sha256' ~ '^[0-9a-f]{64}$'
 AND d->'definition_allowlist'='["fpi-inr-observation-v1"]'::jsonb AND d->>'age_timezone'='Asia/Kolkata'
 AND d->>'missingness'='MISSING' AND d->>'source_rule' IN ('AGREEMENT','LATEST','MONTHLY')
 AND jsonb_typeof(d->'source_rationale')='string' AND d->>'source_rationale' ~ '^[ -~]+$'
 AND length(d->>'source_rationale') BETWEEN 1 AND 1024
 AND jsonb_typeof(d->'allow_withdrawal_fallback')='boolean');
 FOREACH k IN ARRAY ARRAY['max_current_age_days','max_history_age_days','minimum_history','history_window','diagnostic_window_days'] LOOP
  PERFORM public.fpi_admin_assert(jsonb_typeof(d->k)='number' AND d->>k ~ '^(0|[1-9][0-9]{0,5})$');
 END LOOP;
 PERFORM public.fpi_admin_assert((d->>'max_current_age_days')::integer BETWEEN 0 AND 100000
 AND (d->>'max_history_age_days')::integer BETWEEN (d->>'max_current_age_days')::integer AND 100000
 AND (d->>'minimum_history')::integer BETWEEN 10 AND (d->>'history_window')::integer
 AND (d->>'history_window')::integer<=2520 AND (d->>'diagnostic_window_days')::integer=7);
 FOREACH k IN ARRAY ARRAY['feature_version','model_version','prediction_horizon'] LOOP
  PERFORM public.fpi_admin_assert(jsonb_typeof(d->k)='string' AND d->>k ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$');
 END LOOP;
 PERFORM public.fpi_admin_assert(jsonb_typeof(d->'parser_allowlist')='array' AND jsonb_array_length(d->'parser_allowlist') BETWEEN 1 AND 64);
 FOR v IN SELECT item FROM jsonb_array_elements(d->'parser_allowlist') AS entries(item) LOOP
  PERFORM public.fpi_admin_assert(jsonb_typeof(v)='string' AND v#>>'{}' ~ '^[0-9a-f]{64}$' AND (v#>>'{}') COLLATE "C">prior COLLATE "C");
  prior:=v#>>'{}';
 END LOOP;
 RETURN d;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_admin_overflow(d text,l bigint,n numeric,m text DEFAULT 'AT_LEAST') RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,public AS $$
 SELECT jsonb_build_object('code','READ_SCOPE_EXCEEDED','dimension',d,'limit',l,'observed',n,'measurement',m,'witness',NULL)
$$;
CREATE OR REPLACE FUNCTION public.fpi_admin_clock_failure(d text,k text,i text,f text,v text) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,public AS $$
 SELECT jsonb_build_object('code','CLOCK_INCONSISTENT','dimension',d,'limit',NULL,'observed',NULL,'measurement',NULL,
 'witness',jsonb_build_object('kind',k,'id',i,'field',f,'value',v))
$$;

CREATE OR REPLACE FUNCTION public.fpi_admin_original(k text,i text,value text,cap integer) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE d jsonb:=public.fpi_admin_document(value,cap); body bytea; row_doc jsonb; days jsonb:='[]'; previous text:='';
BEGIN
 IF k IN ('PARSER','SELECTOR') THEN
  PERFORM public.fpi_admin_assert(public.fpi_capture_keys(d,ARRAY['version','kind','artifact_sha256','body_size','body_base64'])
  AND d->>'version'='fpi-implementation-artifact-v1' AND d->>'kind'=k AND d->>'artifact_sha256'=i
  AND jsonb_typeof(d->'body_size')='number' AND d->>'body_size' ~ '^[1-9][0-9]*$'
  AND jsonb_typeof(d->'body_base64')='string');
  body:=decode(d->>'body_base64','base64');
  PERFORM public.fpi_admin_assert(octet_length(body) BETWEEN 1 AND 5000000 AND octet_length(body)=(d->>'body_size')::integer
   AND replace(encode(body,'base64'),E'\n','')=d->>'body_base64' AND encode(sha256(body),'hex')=i);
 ELSE
  PERFORM public.fpi_admin_assert(public.fpi_parse_hash(value)=i);
  IF k='CAPTURE' THEN
   PERFORM public.fpi_admin_assert(public.fpi_capture_keys(d,ARRAY['version','source_url','requested_at','retrieved_at','http_status','body_base64','body_size','raw_sha256'])
    AND d->>'version'='fpi-http-capture-v1'
    AND d->>'source_url' IN ('https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx','https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx')
    AND jsonb_typeof(d->'http_status')='number' AND d->>'http_status' ~ '^[1-5][0-9]{2}$'
    AND jsonb_typeof(d->'body_size')='number' AND d->>'body_size' ~ '^(0|[1-9][0-9]*)$'
    AND jsonb_typeof(d->'body_base64')='string' AND d->>'raw_sha256' ~ '^[0-9a-f]{64}$');
   PERFORM public.fpi_admin_assert(public.fpi_capture_time(d->'requested_at')<=public.fpi_capture_time(d->'retrieved_at'));
   body:=decode(d->>'body_base64','base64');
   PERFORM public.fpi_admin_assert(octet_length(body) BETWEEN 0 AND 5000000 AND octet_length(body)=(d->>'body_size')::integer
    AND replace(encode(body,'base64'),E'\n','')=d->>'body_base64' AND encode(sha256(body),'hex')=d->>'raw_sha256');
  ELSIF k='PARSE' THEN
   PERFORM public.fpi_admin_assert(public.fpi_capture_keys(d,ARRAY['version','parse_id','content_sha256','capture_sha256','parser_sha256','definition_version','recorded_at','failure_reason','days'])
    AND d->>'version'='fpi-parse-record-v1' AND d->>'definition_version'='fpi-inr-observation-v1'
    AND d->>'parse_id'=public.fpi_parse_hash(public.fpi_parse_canonical(jsonb_build_array(d->>'capture_sha256',d->>'parser_sha256',d->>'definition_version'))));
   PERFORM public.fpi_admin_assert(jsonb_typeof(d->'days')='array' AND jsonb_array_length(d->'days') BETWEEN 0 AND 31);
   FOR row_doc IN SELECT item FROM jsonb_array_elements(d->'days') entries(item) LOOP
    PERFORM public.fpi_admin_assert(public.fpi_capture_keys(row_doc,ARRAY['membership_id','reporting_date','value_sha256','document_json','source_evidence_sha256','source_evidence_document_json'])
     AND row_doc->>'reporting_date'>previous AND row_doc->>'value_sha256'=public.fpi_parse_hash(row_doc->>'document_json')
     AND row_doc->>'source_evidence_sha256'=public.fpi_parse_hash(row_doc->>'source_evidence_document_json')
     AND row_doc->>'membership_id'=public.fpi_parse_hash(public.fpi_parse_canonical(jsonb_build_array(d->>'parse_id',row_doc->>'value_sha256',row_doc->>'source_evidence_sha256'))));
    PERFORM public.fpi_parse_day(row_doc->>'document_json',row_doc->>'source_evidence_document_json',row_doc->>'reporting_date');
    previous:=row_doc->>'reporting_date';
    days:=days||jsonb_build_array(jsonb_build_object('document_json',row_doc->>'document_json','source_evidence_sha256',row_doc->>'source_evidence_sha256'));
   END LOOP;
   PERFORM public.fpi_admin_assert((d->>'failure_reason' IS NULL AND jsonb_array_length(days)>0)
    OR (d->>'failure_reason' ~ '^[A-Z][A-Z0-9_]{0,63}$' AND jsonb_array_length(days)=0));
   PERFORM public.fpi_admin_assert(d->>'content_sha256'=public.fpi_parse_hash(public.fpi_parse_canonical(jsonb_build_object(
    'parse_id',d->>'parse_id','recorded_at',d->>'recorded_at','failure_reason',d->'failure_reason','days',days))));
  ELSIF k='EVENT' THEN
   PERFORM public.fpi_admin_assert(public.fpi_capture_keys(d,ARRAY['version','command','command_id','event_ordinal','recorded_at','witness'])
    AND d->>'version'='fpi-qualification-event-v2' AND d->>'event_ordinal' ~ '^[1-9][0-9]*$'
    AND d->>'command_id'=public.fpi_parse_hash(public.fpi_parse_canonical(d->'command'))
    AND public.fpi_capture_keys(d->'command',ARRAY['version','scope','target','action','reason_code','evidence_sha256','expected_prior_event_id','chosen_membership_id','basis_membership_ids'])
    AND d->'command'->>'version'='fpi-qualification-command-v2');
  END IF;
 END IF;
 RETURN d;
END $$;

CREATE OR REPLACE FUNCTION public.fpi_admin_receipt(r public.fpi_admin_reads,inserted boolean) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,public AS $$
 SELECT jsonb_build_object('version','fpi-admin-read-receipt-v1','decision_id',r.decision_id::text,
 'request_sha256',r.request_sha256,'read_id',r.read_id,'read_sha256',r.read_sha256,'read_at',public.fpi_admin_time(r.read_at),
 'status',r.status,'execution_state','UNVERIFIED','acquisition_state','UNVERIFIED','eligible',false,'inserted',inserted)
$$;

CREATE OR REPLACE FUNCTION public.append_fpi_admin_read_policy(p_policy_sha256 text,p_document_json text) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,public SET lock_timeout='10s' AS $$
DECLARE d jsonb; a record; saved text; inserted boolean;
BEGIN
 IF (SELECT setting::bigint FROM pg_settings WHERE name='statement_timeout') NOT BETWEEN 1 AND 30000
 OR current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'READ_REQUEST_INVALID'; END IF;
 d:=public.fpi_admin_policy(p_document_json);
 PERFORM public.fpi_admin_assert(p_policy_sha256 ~ '^[0-9a-f]{64}$' AND public.fpi_parse_hash(p_document_json)=p_policy_sha256);
 FOR a IN SELECT 'PARSER'::text kind,value#>>'{}' identity FROM jsonb_array_elements(d->'parser_allowlist')
 UNION ALL SELECT 'SELECTOR',d->>'selector_sha256' LOOP
  SELECT document_json INTO saved FROM public.fpi_implementation_artifacts WHERE kind=a.kind AND artifact_sha256=a.identity;
  IF NOT FOUND THEN RAISE EXCEPTION 'READ_DEPENDENCY_MISSING'; END IF;
  PERFORM public.fpi_admin_original(a.kind,a.identity,saved,7000000);
 END LOOP;
 INSERT INTO public.fpi_admin_read_policies(policy_sha256,document_json,selector_sha256)
 VALUES(p_policy_sha256,p_document_json,d->>'selector_sha256') ON CONFLICT DO NOTHING;
 inserted:=FOUND;
 SELECT document_json INTO saved FROM public.fpi_admin_read_policies WHERE policy_sha256=p_policy_sha256;
 PERFORM public.fpi_admin_assert(saved=p_document_json);
 RETURN jsonb_build_object('version','fpi-admin-read-policy-receipt-v1','policy_sha256',p_policy_sha256,'inserted',inserted);
EXCEPTION WHEN OTHERS THEN
 IF SQLERRM='READ_DEPENDENCY_MISSING' THEN RAISE EXCEPTION USING MESSAGE='READ_DEPENDENCY_MISSING',ERRCODE='22023'; END IF;
 RAISE EXCEPTION USING MESSAGE='READ_REQUEST_INVALID',ERRCODE='22023';
END $$;

CREATE OR REPLACE FUNCTION public.capture_fpi_admin_read(p_request_sha256 text,p_document_json text) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,public SET lock_timeout='10s' AS $$
DECLARE req jsonb; k text; saved public.fpi_admin_reads%ROWTYPE;
BEGIN
 IF (SELECT setting::bigint FROM pg_settings WHERE name='statement_timeout') NOT BETWEEN 1 AND 30000
 OR current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'READ_REQUEST_INVALID'; END IF;
 req:=public.fpi_admin_document(p_document_json,4096);
 PERFORM public.fpi_admin_assert(public.fpi_capture_keys(req,ARRAY['version','decision_id','run_id','prediction_id','model_sha256','pair','mode','policy_sha256'])
 AND req->>'version'='fpi-admin-read-request-v1' AND req->>'pair'='USDINR' AND req->>'mode'='ADMIN_EVIDENCE_READ'
 AND public.fpi_parse_hash(p_document_json)=p_request_sha256);
 FOREACH k IN ARRAY ARRAY['decision_id','run_id'] LOOP
  PERFORM public.fpi_admin_assert(jsonb_typeof(req->k)='string' AND req->>k ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$');
 END LOOP;
 FOREACH k IN ARRAY ARRAY['prediction_id','model_sha256','policy_sha256'] LOOP
  PERFORM public.fpi_admin_assert(jsonb_typeof(req->k)='string' AND req->>k ~ '^[0-9a-f]{64}$');
 END LOOP;
 PERFORM pg_advisory_xact_lock(946029,('x'||substr(public.fpi_parse_hash(req->>'decision_id'),1,8))::bit(32)::integer);
 SELECT * INTO saved FROM public.fpi_admin_reads WHERE decision_id=(req->>'decision_id')::uuid;
 IF FOUND THEN
  IF saved.request_sha256 IS DISTINCT FROM p_request_sha256 OR saved.request_document_json IS DISTINCT FROM p_document_json
  THEN RAISE EXCEPTION 'READ_REQUEST_CONFLICT'; END IF;
  RETURN public.fpi_admin_receipt(saved,false);
 END IF;

 WITH
 policy AS MATERIALIZED (
  SELECT public.fpi_admin_policy(document_json) d FROM public.fpi_admin_read_policies
  WHERE policy_sha256=req->>'policy_sha256' AND public.fpi_admin_assert(public.fpi_parse_hash(document_json)=policy_sha256)
 ), clock_sample AS MATERIALIZED (SELECT public.fpi_admin_clock() t),
 clock_checked AS MATERIALIZED (
  SELECT t,public.fpi_admin_time(t) time_text,
  CASE WHEN extract(year FROM (t AT TIME ZONE 'UTC')+interval '5 hours 30 minutes') BETWEEN 1 AND 9999
  THEN ((t AT TIME ZONE 'UTC')+interval '5 hours 30 minutes')::date
  ELSE public.fpi_admin_time(t+interval '10000 years')::date END today FROM clock_sample
 ), scope_base AS MATERIALIZED (
  SELECT c.*,p.d,
  greatest('0001-01-01'::date,c.today-least(c.today-'0001-01-01'::date,(p.d->>'max_history_age_days')::integer)) first_day,
  c.today-'0001-01-01'::date < (p.d->>'max_history_age_days')::integer history_clamped,
  CASE WHEN c.t<'0001-01-08 00:00:00+00'::timestamptz THEN '0001-01-01 00:00:00+00'::timestamptz ELSE c.t-interval '168 hours' END diagnostic_start,
  c.t<'0001-01-08 00:00:00+00'::timestamptz diagnostic_clamped,
  (SELECT reporting_date FROM public.fpi_parsed_memberships ORDER BY reporting_date DESC LIMIT 1) newest
  FROM clock_checked c CROSS JOIN policy p
 ), scope AS MATERIALIZED (
  SELECT *,jsonb_build_object('version','fpi-admin-scope-v1','india_date',to_char(today,'YYYY-MM-DD'),
  'history_start_date',to_char(first_day,'YYYY-MM-DD'),'history_start_clamped',history_clamped,
  'diagnostic_start_at',public.fpi_admin_time(diagnostic_start),'diagnostic_start_clamped',diagnostic_clamped,
  'newest_reporting_date',to_char(newest,'YYYY-MM-DD')) doc FROM scope_base
  WHERE public.fpi_admin_assert(newest IS NULL OR (isfinite(newest) AND extract(year FROM newest) BETWEEN 1 AND 9999))
 ), newest_guard AS MATERIALIZED (
  SELECT CASE WHEN newest>today THEN public.fpi_admin_clock_failure('NEWEST_DATE','MEMBERSHIP_DATE',NULL,'reporting_date',to_char(newest,'YYYY-MM-DD')) END failure FROM scope
 ), future_failure AS MATERIALIZED (
  SELECT p.parse_id,p.stored_at FROM scope s CROSS JOIN newest_guard g CROSS JOIN LATERAL (
   SELECT parse_id,stored_at FROM public.fpi_parse_results WHERE failure_reason IS NOT NULL AND stored_at>s.t
   ORDER BY stored_at DESC,parse_id DESC LIMIT 1
  ) p WHERE g.failure IS NULL AND public.fpi_admin_assert(isfinite(p.stored_at)
   AND extract(year FROM p.stored_at AT TIME ZONE 'UTC') BETWEEN 1 AND 9999)
 ), clock_guard AS MATERIALIZED (
  SELECT coalesce(g.failure,(SELECT public.fpi_admin_clock_failure('FUTURE_FAILURE_STORAGE','PARSE',parse_id,'stored_at',public.fpi_admin_time(stored_at)) FROM future_failure)) failure FROM newest_guard g
 ), candidates AS MATERIALIZED (
  SELECT m.membership_id,m.parse_id,m.reporting_date,m.value_sha256,m.source_evidence_sha256
  FROM scope s CROSS JOIN clock_guard g CROSS JOIN LATERAL (
   (SELECT membership_id,parse_id,reporting_date,value_sha256,source_evidence_sha256 FROM public.fpi_parsed_memberships
    WHERE reporting_date BETWEEN s.first_day AND s.today LIMIT 20001)
   UNION ALL
   (SELECT membership_id,parse_id,reporting_date,value_sha256,source_evidence_sha256 FROM public.fpi_parsed_memberships
    WHERE reporting_date=s.newest AND s.newest<s.first_day LIMIT 20001)
   LIMIT 20001
  ) m WHERE g.failure IS NULL
 ), candidate_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM clock_guard),CASE WHEN count(*)>20000 THEN public.fpi_admin_overflow('CANDIDATES',20000,count(*)) END) failure FROM candidates
 ), candidate_parses AS MATERIALIZED (
  SELECT DISTINCT c.parse_id FROM candidates c CROSS JOIN candidate_guard g WHERE g.failure IS NULL LIMIT 2049
 ), candidate_parse_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM candidate_guard),CASE WHEN count(*)>2048 THEN public.fpi_admin_overflow('PARSES',2048,count(*)) END) failure FROM candidate_parses
 ), candidate_captures AS MATERIALIZED (
  SELECT DISTINCT p.capture_sha256 FROM candidate_parses c JOIN public.fpi_parse_results p USING(parse_id)
  CROSS JOIN candidate_parse_guard g WHERE g.failure IS NULL
 ), time_failures AS MATERIALIZED (
  SELECT p.parse_id FROM scope s CROSS JOIN candidate_parse_guard g CROSS JOIN LATERAL (
   SELECT parse_id FROM public.fpi_parse_results WHERE failure_reason IS NOT NULL AND stored_at BETWEEN s.diagnostic_start AND s.t LIMIT 2049
  ) p WHERE g.failure IS NULL
 ), time_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM candidate_parse_guard),CASE WHEN count(*)>2048 THEN public.fpi_admin_overflow('PARSES',2048,count(*)) END) failure FROM time_failures
 ), capture_failures AS MATERIALIZED (
  SELECT p.parse_id FROM candidate_captures c JOIN public.fpi_parse_results p USING(capture_sha256)
  CROSS JOIN time_guard g WHERE g.failure IS NULL AND p.failure_reason IS NOT NULL LIMIT 2049
 ), capture_failure_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM time_guard),CASE WHEN count(*)>2048 THEN public.fpi_admin_overflow('PARSES',2048,count(*)) END) failure FROM capture_failures
 ), parse_ids AS MATERIALIZED (
  SELECT parse_id FROM (SELECT parse_id FROM candidate_parses UNION SELECT parse_id FROM time_failures UNION SELECT parse_id FROM capture_failures) u
  CROSS JOIN capture_failure_guard g WHERE g.failure IS NULL
 ), parse_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM capture_failure_guard),CASE WHEN count(*)>2048 THEN public.fpi_admin_overflow('PARSES',2048,count(*),'EXACT') END) failure FROM parse_ids
 ), parses AS MATERIALIZED (
  SELECT p.parse_id,p.record_sha256,p.content_sha256,p.capture_sha256,p.parser_sha256,p.definition_version,p.recorded_at,p.failure_reason,p.stored_at,
  octet_length(p.document_json) document_size FROM parse_ids i JOIN public.fpi_parse_results p USING(parse_id) CROSS JOIN parse_guard g WHERE g.failure IS NULL
 ), capture_ids AS MATERIALIZED (SELECT DISTINCT capture_sha256 FROM parses LIMIT 2049),
 capture_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM parse_guard),CASE WHEN count(*)>2048 THEN public.fpi_admin_overflow('CAPTURES',2048,count(*)) END) failure FROM capture_ids
 ), captures AS MATERIALIZED (
  SELECT c.capture_sha256,c.source_url,c.requested_at,c.retrieved_at,c.raw_sha256,c.body_size,c.http_status,c.stored_at,
  octet_length(c.document_json) document_size FROM capture_ids i JOIN public.fpi_captures c USING(capture_sha256) CROSS JOIN capture_guard g WHERE g.failure IS NULL
 ), support AS MATERIALIZED (
  SELECT m.membership_id,m.parse_id,m.reporting_date,m.value_sha256,m.source_evidence_sha256 FROM parses p
  JOIN public.fpi_parsed_memberships m USING(parse_id) CROSS JOIN capture_guard g WHERE g.failure IS NULL LIMIT 20001
 ), support_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM capture_guard),CASE WHEN count(*)>20000 THEN public.fpi_admin_overflow('SUPPORT_MEMBERSHIPS',20000,count(*)) END) failure FROM support
 ), artifact_ids AS MATERIALIZED (
  SELECT kind,identity FROM (
   SELECT 'PARSER'::text kind,parser_sha256 identity FROM parses
   UNION SELECT 'PARSER',value#>>'{}' FROM policy p,jsonb_array_elements(p.d->'parser_allowlist')
   UNION SELECT 'SELECTOR',d->>'selector_sha256' FROM policy
  ) u CROSS JOIN support_guard g WHERE g.failure IS NULL LIMIT 2114
 ), artifact_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM support_guard),CASE WHEN count(*)>2113 THEN public.fpi_admin_overflow('ARTIFACTS',2113,count(*)) END) failure FROM artifact_ids
 ), artifacts AS MATERIALIZED (
  SELECT i.kind,i.identity artifact_sha256,a.body_size,a.stored_at,octet_length(a.document_json) document_size
  FROM artifact_ids i LEFT JOIN public.fpi_implementation_artifacts a ON a.kind=i.kind AND a.artifact_sha256=i.identity
  CROSS JOIN artifact_guard g WHERE g.failure IS NULL AND public.fpi_admin_assert(a.artifact_sha256 IS NOT NULL)
 ), members AS MATERIALIZED (
  SELECT c.*,p.parser_sha256,public.fpi_parse_canonical(jsonb_build_object('membership_id',c.membership_id,'value_sha256',c.value_sha256,
  'parser_sha256',p.parser_sha256,'reporting_date',to_char(c.reporting_date,'YYYY-MM-DD'))) fragment
  FROM candidates c JOIN parses p USING(parse_id) CROSS JOIN artifact_guard g WHERE g.failure IS NULL
 ), targets AS MATERIALIZED (
  SELECT scope,target FROM (
   SELECT 'membership'::text scope,membership_id target FROM members
   UNION SELECT 'value',value_sha256 FROM members UNION SELECT 'parser',parser_sha256 FROM members
   UNION SELECT 'date',to_char(reporting_date,'YYYY-MM-DD') FROM members
  ) u LIMIT 100001
 ), head_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM artifact_guard),CASE WHEN count(*)>100000 THEN public.fpi_admin_overflow('HEADS',100000,count(*)) END) failure FROM targets
 ), heads AS MATERIALIZED (
  SELECT t.*,e.event_id,e.document_size,public.fpi_parse_canonical(jsonb_build_object('scope',t.scope,'target',t.target,'event_id',e.event_id)) fragment
  FROM targets t CROSS JOIN head_guard g LEFT JOIN LATERAL (
   SELECT q.event_id,octet_length(q.event_document_json) document_size FROM public.fpi_qualification_events q
   WHERE q.scope=t.scope AND q.target=t.target ORDER BY event_ordinal DESC LIMIT 1
  ) e ON true WHERE g.failure IS NULL
 ), preliminary_size AS MATERIALIZED (
  SELECT 75::bigint+coalesce((SELECT sum(length(fragment))+greatest(count(*)-1,0) FROM members),0)
  +coalesce((SELECT sum(length(fragment))+greatest(count(*)-1,0) FROM heads),0)
  +coalesce((SELECT sum(document_size)+greatest(count(*)-1,0) FROM heads WHERE scope='date' AND event_id IS NOT NULL),0) n
 ), preliminary_guard AS MATERIALIZED (
  SELECT coalesce(g.failure,CASE WHEN n>16000000 THEN public.fpi_admin_overflow('QUALIFICATION_BYTES',16000000,n) END) failure
  FROM head_guard g CROSS JOIN preliminary_size
 ), date_events_input AS MATERIALIZED (
  SELECT q.event_id,q.event_document_json FROM heads h JOIN public.fpi_qualification_events q USING(event_id)
  CROSS JOIN preliminary_guard g WHERE g.failure IS NULL AND h.scope='date'
  AND public.fpi_admin_assert(h.event_id IS NULL OR h.document_size BETWEEN 1 AND 400000)
 ), date_events AS MATERIALIZED (
  SELECT event_id,public.fpi_admin_original('EVENT',event_id,event_document_json,400000) d FROM date_events_input
 ), event_ids AS MATERIALIZED (
  SELECT event_id FROM (
   SELECT event_id FROM heads WHERE event_id IS NOT NULL
   UNION SELECT w->>'event_id' FROM date_events d,jsonb_array_elements(d.d->'witness'->'heads') w WHERE w->>'event_id' IS NOT NULL
  ) u CROSS JOIN preliminary_guard g WHERE g.failure IS NULL LIMIT 100001
 ), event_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM preliminary_guard),CASE WHEN count(*)>100000 THEN public.fpi_admin_overflow('EVENTS',100000,count(*)) END) failure FROM event_ids
 ), events AS MATERIALIZED (
  SELECT i.event_id,q.recorded_at,octet_length(q.event_document_json) document_size FROM event_ids i
  LEFT JOIN public.fpi_qualification_events q USING(event_id) CROSS JOIN event_guard g
  WHERE g.failure IS NULL AND public.fpi_admin_assert(q.event_id IS NOT NULL)
 ), time_rows AS MATERIALIZED (
  SELECT 'CAPTURE'::text kind,capture_sha256 id,v.field,v.t FROM captures CROSS JOIN LATERAL
   (VALUES('requested_at',requested_at),('retrieved_at',retrieved_at),('stored_at',stored_at)) v(field,t)
  UNION ALL SELECT 'PARSE',parse_id,v.field,v.t FROM parses CROSS JOIN LATERAL (VALUES('recorded_at',recorded_at),('stored_at',stored_at)) v(field,t)
  UNION ALL SELECT 'ARTIFACT',artifact_sha256,'stored_at',stored_at FROM artifacts
  UNION ALL SELECT 'EVENT',event_id,'recorded_at',recorded_at FROM events
 ), time_rows_guarded AS MATERIALIZED (SELECT r.* FROM time_rows r CROSS JOIN event_guard g WHERE g.failure IS NULL),
 bounded_times AS MATERIALIZED (
  SELECT * FROM time_rows_guarded WHERE public.fpi_admin_assert(isfinite(t)
   AND extract(year FROM t AT TIME ZONE 'UTC') BETWEEN 1 AND 9999)
 ),
 india_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM event_guard),(SELECT public.fpi_admin_clock_failure('INDIA_TIME_RANGE',kind,id,field,public.fpi_admin_time(t))
   FROM bounded_times WHERE ((kind='CAPTURE' AND field='retrieved_at') OR (kind='PARSE' AND field='recorded_at'))
   AND extract(year FROM (t AT TIME ZONE 'UTC')+interval '5 hours 30 minutes') NOT BETWEEN 1 AND 9999
   ORDER BY kind COLLATE "C",id COLLATE "C",field COLLATE "C" LIMIT 1)) failure
 ), referenced_guard AS MATERIALIZED (
  SELECT coalesce((SELECT failure FROM india_guard),(SELECT public.fpi_admin_clock_failure('REFERENCED_TIME',kind,id,field,public.fpi_admin_time(b.t))
   FROM bounded_times b CROSS JOIN scope s CROSS JOIN india_guard g WHERE g.failure IS NULL AND b.t>s.t
   ORDER BY kind COLLATE "C",id COLLATE "C",field COLLATE "C" LIMIT 1)) failure
 ), original_size AS MATERIALIZED (
  SELECT coalesce(sum(n),0) n FROM (
   SELECT document_size::bigint n,7000000 cap FROM captures UNION ALL SELECT document_size,4000000 FROM parses
   UNION ALL SELECT document_size,7000000 FROM artifacts
  ) u CROSS JOIN referenced_guard g WHERE g.failure IS NULL AND public.fpi_admin_assert(n BETWEEN 1 AND cap)
 ), original_guard AS MATERIALIZED (
  SELECT coalesce(g.failure,CASE WHEN n>64000000 THEN public.fpi_admin_overflow('ORIGINAL_BYTES',64000000,n,'EXACT') END) failure
  FROM referenced_guard g CROSS JOIN original_size
 ), capture_documents_input AS MATERIALIZED (
  SELECT c.*,raw.document_json FROM captures c JOIN public.fpi_captures raw USING(capture_sha256)
  CROSS JOIN original_guard g WHERE g.failure IS NULL
 ), capture_documents AS MATERIALIZED (
  SELECT c.*,public.fpi_admin_original('CAPTURE',capture_sha256,document_json,7000000) d FROM capture_documents_input c
 ), parse_documents_input AS MATERIALIZED (
  SELECT p.*,raw.document_json FROM parses p JOIN public.fpi_parse_results raw USING(parse_id) CROSS JOIN original_guard g WHERE g.failure IS NULL
 ), parse_documents AS MATERIALIZED (
  SELECT p.*,public.fpi_admin_original('PARSE',record_sha256,document_json,4000000) d FROM parse_documents_input p
 ), artifact_documents_input AS MATERIALIZED (
  SELECT a.*,raw.document_json FROM artifacts a JOIN public.fpi_implementation_artifacts raw USING(kind,artifact_sha256)
  CROSS JOIN original_guard g WHERE g.failure IS NULL
 ), artifact_documents AS MATERIALIZED (
  SELECT a.*,public.fpi_admin_original(kind,artifact_sha256,document_json,7000000) d FROM artifact_documents_input a
 ), capture_fragments AS MATERIALIZED (
  SELECT capture_sha256,public.fpi_parse_canonical(jsonb_build_object('capture_sha256',capture_sha256,'document_size',document_size,
  'source_url',source_url,'requested_at',public.fpi_admin_time(requested_at),'retrieved_at',public.fpi_admin_time(retrieved_at),
  'http_status',http_status,'body_size',body_size,'raw_sha256',raw_sha256)) fragment
  FROM capture_documents WHERE public.fpi_admin_assert(d->>'source_url'=source_url AND d->>'requested_at'=public.fpi_admin_time(requested_at)
   AND d->>'retrieved_at'=public.fpi_admin_time(retrieved_at) AND d->>'raw_sha256'=raw_sha256 AND (d->>'body_size')::integer=body_size
   AND (d->>'http_status')::integer=http_status AND stored_at>=retrieved_at AND retrieved_at>=requested_at)
 ), support_fragments AS MATERIALIZED (
  SELECT parse_id,reporting_date,public.fpi_parse_canonical(jsonb_build_object('membership_id',membership_id,'reporting_date',to_char(reporting_date,'YYYY-MM-DD'),
  'value_sha256',value_sha256,'source_evidence_sha256',source_evidence_sha256)) fragment FROM support CROSS JOIN original_guard g WHERE g.failure IS NULL
 ), support_documents AS MATERIALIZED (
  SELECT m.* FROM support s JOIN public.fpi_parsed_memberships m USING(membership_id) CROSS JOIN original_guard g
  WHERE g.failure IS NULL AND public.fpi_admin_assert(octet_length(m.document_json) BETWEEN 1 AND 32768
   AND octet_length(m.source_evidence_document_json) BETWEEN 1 AND 32768)
 ), parse_fragments AS MATERIALIZED (
  SELECT p.parse_id,public.fpi_parse_canonical(jsonb_build_object('parse_id',p.parse_id,'record_sha256',p.record_sha256,'document_size',p.document_size,
   'content_sha256',p.content_sha256,'capture_sha256',p.capture_sha256,'parser_sha256',p.parser_sha256,'definition_version',p.definition_version,
   'recorded_at',public.fpi_admin_time(p.recorded_at),'failure_reason',p.failure_reason))::jsonb pdoc,
   coalesce((SELECT string_agg(fragment,',' ORDER BY reporting_date) FROM support_fragments m WHERE m.parse_id=p.parse_id),'') membership_text
  FROM parse_documents p JOIN captures c USING(capture_sha256)
  WHERE public.fpi_admin_assert(p.d->>'parse_id'=p.parse_id AND p.d->>'content_sha256'=p.content_sha256 AND p.d->>'capture_sha256'=p.capture_sha256
   AND p.d->>'parser_sha256'=p.parser_sha256 AND p.d->>'definition_version'=p.definition_version AND p.d->>'recorded_at'=public.fpi_admin_time(p.recorded_at)
   AND (p.d->>'failure_reason') IS NOT DISTINCT FROM p.failure_reason AND p.stored_at>=p.recorded_at AND p.recorded_at>=c.retrieved_at
   AND (p.failure_reason IS NOT NULL OR c.http_status=200)
   AND jsonb_array_length(p.d->'days')=(SELECT count(*) FROM support m WHERE m.parse_id=p.parse_id)
   AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(p.d->'days') item WHERE NOT EXISTS(
    SELECT 1 FROM support_documents m WHERE m.parse_id=p.parse_id AND m.membership_id=item->>'membership_id'
    AND to_char(m.reporting_date,'YYYY-MM-DD')=item->>'reporting_date' AND m.value_sha256=item->>'value_sha256'
    AND m.source_evidence_sha256=item->>'source_evidence_sha256' AND m.document_json=item->>'document_json'
    AND m.source_evidence_document_json=item->>'source_evidence_document_json'))
   AND NOT EXISTS(SELECT 1 FROM support m WHERE m.parse_id=p.parse_id AND m.reporting_date>((c.retrieved_at AT TIME ZONE 'UTC')+interval '5 hours 30 minutes')::date))
 ), reference_parse_fragments AS MATERIALIZED (
  SELECT parse_id,public.fpi_parse_canonical(pdoc||jsonb_build_object('memberships',('['||membership_text||']')::jsonb)) fragment FROM parse_fragments
 ), reference_size AS MATERIALIZED (
  SELECT 62::bigint+coalesce((SELECT sum(length(fragment))+greatest(count(*)-1,0) FROM capture_fragments),0)
   +coalesce((SELECT sum(length(fragment))+greatest(count(*)-1,0) FROM reference_parse_fragments),0) n
 ), reference_guard AS MATERIALIZED (
  SELECT coalesce(g.failure,CASE WHEN n>16000000 THEN public.fpi_admin_overflow('REFERENCE_BYTES',16000000,n,'EXACT') END) failure FROM original_guard g CROSS JOIN reference_size
 ), qualification_size AS MATERIALIZED (
  SELECT 75::bigint+coalesce((SELECT sum(length(fragment))+greatest(count(*)-1,0) FROM members),0)
   +coalesce((SELECT sum(length(fragment))+greatest(count(*)-1,0) FROM heads),0)
   +coalesce((SELECT sum(document_size)+greatest(count(*)-1,0) FROM events WHERE public.fpi_admin_assert(document_size BETWEEN 1 AND 400000)),0) n
 ), qualification_guard AS MATERIALIZED (
  SELECT coalesce(g.failure,CASE WHEN n>16000000 THEN public.fpi_admin_overflow('QUALIFICATION_BYTES',16000000,n,'EXACT') END) failure
  FROM reference_guard g CROSS JOIN qualification_size
 ), event_documents_input AS MATERIALIZED (
  SELECT e.event_id,raw.event_document_json,raw.command_document_json,raw.command_id,raw.scope,raw.target,raw.event_ordinal,raw.recorded_at,raw.expected_prior_event_id
  FROM events e JOIN public.fpi_qualification_events raw USING(event_id)
  CROSS JOIN qualification_guard g WHERE g.failure IS NULL
 ), event_documents AS MATERIALIZED (
  SELECT event_id,d,event_document_json fragment FROM (
   SELECT *,public.fpi_admin_original('EVENT',event_id,event_document_json,400000) d FROM event_documents_input OFFSET 0
  ) validated WHERE public.fpi_admin_assert(d->>'command_id'=command_id AND public.fpi_parse_canonical(d->'command')=command_document_json
   AND d->'command'->>'scope'=scope AND d->'command'->>'target'=target AND (d->>'event_ordinal')::bigint=event_ordinal
   AND d->>'recorded_at'=public.fpi_admin_time(recorded_at)
   AND (d->'command'->>'expected_prior_event_id') IS NOT DISTINCT FROM expected_prior_event_id)
 ), references_input AS MATERIALIZED (
  SELECT 'capture'::text kind,capture_sha256 id,fragment FROM capture_fragments CROSS JOIN qualification_guard g WHERE g.failure IS NULL
  UNION ALL SELECT 'parse',parse_id,fragment FROM reference_parse_fragments CROSS JOIN qualification_guard g WHERE g.failure IS NULL
 ), references_doc AS MATERIALIZED (
  SELECT '{"captures":['||coalesce(string_agg(fragment,',' ORDER BY id COLLATE "C") FILTER(WHERE kind='capture'),'')
   ||'],"parses":['||coalesce(string_agg(fragment,',' ORDER BY id COLLATE "C") FILTER(WHERE kind='parse'),'')||'],"version":"fpi-read-references-v1"}' doc
  FROM references_input
 ), qualification_input AS MATERIALIZED (
  SELECT 'member'::text kind,membership_id id,fragment FROM members CROSS JOIN qualification_guard g WHERE g.failure IS NULL
  UNION ALL SELECT 'head',scope||':'||target,fragment FROM heads CROSS JOIN qualification_guard g WHERE g.failure IS NULL
  UNION ALL SELECT 'event',event_id,fragment FROM event_documents WHERE public.fpi_admin_assert(d->>'version'='fpi-qualification-event-v2')
 ), qualification_doc AS MATERIALIZED (
  SELECT '{"events":['||coalesce(string_agg(fragment,',' ORDER BY id COLLATE "C") FILTER(WHERE kind='event'),'')
  ||'],"heads":['||coalesce(string_agg(fragment,',' ORDER BY id COLLATE "C") FILTER(WHERE kind='head'),'')
  ||'],"members":['||coalesce(string_agg(fragment,',' ORDER BY id COLLATE "C") FILTER(WHERE kind='member'),'')||'],"version":"fpi-qualification-view-v2"}' doc
  FROM qualification_input
 ), artifact_fragments AS MATERIALIZED (
  SELECT a.kind,a.artifact_sha256,jsonb_build_object('kind',a.kind,'artifact_sha256',a.artifact_sha256,'document_size',a.document_size,
   'body_size',a.body_size,'stored_at',public.fpi_admin_time(a.stored_at)) d FROM artifact_documents a CROSS JOIN qualification_guard g
  WHERE g.failure IS NULL AND public.fpi_admin_assert((a.d->>'body_size')::integer=a.body_size)
 ), metadata_doc AS MATERIALIZED (
  SELECT jsonb_build_object('candidate_membership_ids',coalesce((SELECT jsonb_agg(membership_id ORDER BY membership_id COLLATE "C") FROM candidates),'[]'),
  'candidate_dates',coalesce((SELECT jsonb_agg(day_text ORDER BY day_text COLLATE "C") FROM (SELECT DISTINCT to_char(reporting_date,'YYYY-MM-DD') day_text FROM candidates) u),'[]'),
  'diagnostic_parse_ids',coalesce((SELECT jsonb_agg(parse_id ORDER BY parse_id COLLATE "C") FROM parses WHERE failure_reason IS NOT NULL),'[]'),
  'reference_sha256',public.fpi_parse_hash(r.doc),'qualification_sha256',public.fpi_parse_hash(q.doc),
  'artifacts',coalesce((SELECT jsonb_agg(d ORDER BY kind COLLATE "C",artifact_sha256 COLLATE "C") FROM artifact_fragments),'[]'),
  'storage_times',jsonb_build_object('captures',coalesce((SELECT jsonb_agg(jsonb_build_object('capture_sha256',capture_sha256,'stored_at',public.fpi_admin_time(stored_at)) ORDER BY capture_sha256 COLLATE "C") FROM captures),'[]'),
  'parses',coalesce((SELECT jsonb_agg(jsonb_build_object('parse_id',parse_id,'stored_at',public.fpi_admin_time(stored_at)) ORDER BY parse_id COLLATE "C") FROM parses),'[]'))) d
  FROM references_doc r CROSS JOIN qualification_doc q CROSS JOIN qualification_guard g WHERE g.failure IS NULL
 ), envelope AS MATERIALIZED (
  SELECT jsonb_build_object('version','fpi-admin-read-v1','read_id',p_request_sha256,'request_sha256',p_request_sha256,'request',req,
   'policy_sha256',req->>'policy_sha256','policy',s.d,'read_at',s.time_text,'scope',s.doc,'execution_state','UNVERIFIED',
   'acquisition_state','UNVERIFIED','eligible',false,'feature',NULL) d,s.t FROM scope s
 ), manifest_size AS MATERIALIZED (
  SELECT length(public.fpi_parse_canonical(e.d))+length(public.fpi_parse_canonical(d.d))+length(r.doc)+length(q.doc)
   +length(',"references":,"qualification":')+length(',"data":,"failure":null,"status":"COMPLETE"') n
  FROM envelope e CROSS JOIN metadata_doc d CROSS JOIN references_doc r CROSS JOIN qualification_doc q
 ), final_guard AS MATERIALIZED (
  SELECT coalesce(g.failure,(SELECT public.fpi_admin_overflow('MANIFEST_BYTES',16000000,n,'EXACT') FROM manifest_size WHERE n>16000000)) failure FROM qualification_guard g
 ), data_input AS MATERIALIZED (
  SELECT m.d,r.doc rdoc,q.doc qdoc FROM metadata_doc m CROSS JOIN references_doc r CROSS JOIN qualification_doc q CROSS JOIN final_guard g WHERE g.failure IS NULL
 ), data_doc AS MATERIALIZED (
  SELECT d||jsonb_build_object('references',rdoc::jsonb,'qualification',qdoc::jsonb) d FROM data_input
 ), manifest AS MATERIALIZED (
  SELECT e.t,CASE WHEN g.failure IS NULL THEN 'COMPLETE' ELSE g.failure->>'code' END status,
   public.fpi_parse_canonical(e.d||jsonb_build_object('status',CASE WHEN g.failure IS NULL THEN 'COMPLETE' ELSE g.failure->>'code' END,
   'failure',g.failure,'data',CASE WHEN g.failure IS NULL THEN (SELECT d FROM data_doc) ELSE NULL END)) doc
  FROM envelope e CROSS JOIN final_guard g
 )
 INSERT INTO public.fpi_admin_reads(read_id,decision_id,request_sha256,request_document_json,policy_sha256,read_sha256,manifest_document_json,read_at,status)
 SELECT p_request_sha256,(req->>'decision_id')::uuid,p_request_sha256,p_document_json,req->>'policy_sha256',public.fpi_parse_hash(doc),doc,t,status
 FROM manifest WHERE public.fpi_admin_assert(length(doc)<=CASE WHEN status='COMPLETE' THEN 16000000 ELSE 65536 END)
 RETURNING * INTO saved;
 IF NOT FOUND THEN RAISE EXCEPTION 'READ_DEPENDENCY_MISSING'; END IF;
 RETURN public.fpi_admin_receipt(saved,true);
EXCEPTION WHEN OTHERS THEN
 IF SQLERRM IN ('READ_REQUEST_CONFLICT','READ_CLOCK_RANGE','READ_DEPENDENCY_MISSING','READ_REQUEST_INVALID')
 THEN RAISE EXCEPTION USING MESSAGE=SQLERRM,ERRCODE='22023'; END IF;
 RAISE EXCEPTION USING MESSAGE='READ_INTEGRITY_ERROR',ERRCODE='22023';
END $$;

DO $$ DECLARE t text; f record; BEGIN
 FOREACH t IN ARRAY ARRAY['fpi_admin_read_policies','fpi_admin_reads'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS immutable_rows ON public.%I',t);
  EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.reject_fpi_capture_mutation()',t);
  EXECUTE format('DROP TRIGGER IF EXISTS immutable_truncate ON public.%I',t);
  EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.reject_fpi_capture_mutation()',t);
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('DROP POLICY IF EXISTS service_read ON public.%I',t);
  EXECUTE format('CREATE POLICY service_read ON public.%I FOR SELECT TO service_role USING(true)',t);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,service_role',t);
  EXECUTE format('GRANT SELECT ON public.%I TO service_role',t);
 END LOOP;
 FOR f IN SELECT oid::regprocedure signature FROM pg_proc WHERE pronamespace='public'::regnamespace
 AND (proname LIKE 'fpi_admin_%' OR proname IN ('append_fpi_admin_read_policy','capture_fpi_admin_read')) LOOP
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,anon,authenticated,service_role',f.signature);
 END LOOP;
END $$;
GRANT EXECUTE ON FUNCTION public.append_fpi_admin_read_policy(text,text),public.capture_fpi_admin_read(text,text) TO service_role;
COMMIT;
