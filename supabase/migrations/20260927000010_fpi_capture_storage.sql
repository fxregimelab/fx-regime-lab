-- Private byte-exact evidence for fixed NSDL FPI report responses.
-- This archive does not establish publication time, observation eligibility or signal activation.
BEGIN;

CREATE TABLE IF NOT EXISTS public.fpi_captures (
    capture_sha256 text PRIMARY KEY CHECK (capture_sha256 ~ '^[0-9a-f]{64}$'),
    document_json text NOT NULL,
    document jsonb NOT NULL,
    source_url text NOT NULL CHECK (source_url IN (
        'https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx',
        'https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx'
    )),
    requested_at timestamptz NOT NULL,
    retrieved_at timestamptz NOT NULL CHECK (requested_at <= retrieved_at),
    raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    body_size integer NOT NULL CHECK (body_size BETWEEN 0 AND 5000000),
    http_status integer NOT NULL CHECK (http_status BETWEEN 100 AND 599),
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK (stored_at >= retrieved_at)
);

CREATE INDEX IF NOT EXISTS fpi_captures_source_retrieved
    ON public.fpi_captures(source_url, retrieved_at);
CREATE INDEX IF NOT EXISTS fpi_captures_raw_sha256
    ON public.fpi_captures(raw_sha256);

COMMENT ON TABLE public.fpi_captures IS
    'Private immutable HTTP response evidence. Storage is not source release time, observation acceptance or feature eligibility.';
COMMENT ON COLUMN public.fpi_captures.document_json IS
    'Authoritative exact UTF-8 JSON text whose SHA-256 is capture_sha256.';

CREATE OR REPLACE FUNCTION public.reject_fpi_capture_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION 'FPI capture storage is immutable; append new evidence';
END
$$;

-- Check JSON syntax before conversion to JSONB, because JSONB discards duplicate keys.
CREATE OR REPLACE FUNCTION public.fpi_capture_unique_json(value json)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
SET search_path = pg_catalog, public
AS $$
DECLARE
    child json;
BEGIN
    IF json_typeof(value) = 'object' THEN
        IF EXISTS (SELECT 1 FROM json_each(value) GROUP BY key HAVING count(*) > 1) THEN
            RETURN false;
        END IF;
        FOR child IN SELECT item_value FROM json_each(value) AS item(item_key, item_value) LOOP
            IF NOT public.fpi_capture_unique_json(child) THEN
                RETURN false;
            END IF;
        END LOOP;
    ELSIF json_typeof(value) = 'array' THEN
        FOR child IN SELECT item_value FROM json_array_elements(value) AS item(item_value) LOOP
            IF NOT public.fpi_capture_unique_json(child) THEN
                RETURN false;
            END IF;
        END LOOP;
    END IF;
    RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.fpi_capture_keys(value jsonb, expected text[])
RETURNS boolean
LANGUAGE sql
IMMUTABLE
SET search_path = pg_catalog, public
AS $$
    SELECT CASE
        WHEN jsonb_typeof(value) = 'object' THEN
            (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(value) AS item(key))
            IS NOT DISTINCT FROM
            (SELECT array_agg(key ORDER BY key) FROM unnest(expected) AS item(key))
        ELSE false
    END
$$;

CREATE OR REPLACE FUNCTION public.fpi_capture_time(value jsonb)
RETURNS timestamptz
LANGUAGE plpgsql
IMMUTABLE
SET search_path = pg_catalog, public
SET timezone = 'UTC'
AS $$
DECLARE
    source text := value #>> '{}';
    result timestamptz;
BEGIN
    IF jsonb_typeof(value) IS DISTINCT FROM 'string'
       OR source !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{6})?\+00:00$'
       OR source LIKE '0000-%' THEN
        RAISE EXCEPTION 'Invalid FPI capture timestamp';
    END IF;
    result := source::timestamptz;
    IF NOT isfinite(result) THEN
        RAISE EXCEPTION 'Invalid FPI capture timestamp';
    END IF;
    RETURN result;
END
$$;

CREATE OR REPLACE FUNCTION public.append_fpi_capture(
    p_capture_sha256 text,
    p_document_json text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
SET timezone = 'UTC'
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

DROP TRIGGER IF EXISTS fpi_captures_immutable_rows ON public.fpi_captures;
CREATE TRIGGER fpi_captures_immutable_rows
BEFORE UPDATE OR DELETE ON public.fpi_captures
FOR EACH ROW EXECUTE FUNCTION public.reject_fpi_capture_mutation();

DROP TRIGGER IF EXISTS fpi_captures_immutable_truncate ON public.fpi_captures;
CREATE TRIGGER fpi_captures_immutable_truncate
BEFORE TRUNCATE ON public.fpi_captures
FOR EACH STATEMENT EXECUTE FUNCTION public.reject_fpi_capture_mutation();

ALTER TABLE public.fpi_captures ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS fpi_captures_service_read ON public.fpi_captures;
CREATE POLICY fpi_captures_service_read
ON public.fpi_captures
FOR SELECT
TO service_role
USING (true);

REVOKE ALL ON TABLE public.fpi_captures FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.fpi_captures TO service_role;

REVOKE ALL ON FUNCTION public.reject_fpi_capture_mutation() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.fpi_capture_unique_json(json) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.fpi_capture_keys(jsonb, text[]) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.fpi_capture_time(jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.append_fpi_capture(text, text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.append_fpi_capture(text, text) TO service_role;

COMMIT;
