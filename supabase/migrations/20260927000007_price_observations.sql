-- Provider observations are evidence of retrieval, not certified final closes.
-- This migration never inserts into or updates historical_prices.
BEGIN;

CREATE TABLE IF NOT EXISTS public.price_observations (
    id bigserial PRIMARY KEY,
    pair text NOT NULL CHECK (pair IN ('EURUSD','USDJPY','USDINR')),
    date date NOT NULL,
    provider text NOT NULL CHECK (provider IN ('polygon','alphavantage','yahoo')),
    instrument text NOT NULL CHECK (btrim(instrument) <> ''),
    retrieved_at timestamptz NOT NULL CHECK (isfinite(retrieved_at)),
    observation jsonb NOT NULL CHECK (jsonb_typeof(observation) = 'object'),
    payload_hash text NOT NULL UNIQUE CHECK (payload_hash ~ '^[0-9a-f]{64}$')
);
COMMENT ON TABLE public.price_observations IS
    'Private immutable provider retrievals. Unknown session boundaries remain unknown; no final-close certification or historical_prices promotion.';
CREATE INDEX IF NOT EXISTS price_observations_pair_date_retrieved
    ON public.price_observations(pair,date,retrieved_at);

CREATE OR REPLACE FUNCTION public.reject_price_observation_mutation()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
    RAISE EXCEPTION 'price_observations is immutable; append a new retrieval or correction';
END $$;
DROP TRIGGER IF EXISTS price_observations_immutable ON public.price_observations;
CREATE TRIGGER price_observations_immutable BEFORE UPDATE OR DELETE ON public.price_observations
    FOR EACH ROW EXECUTE FUNCTION public.reject_price_observation_mutation();
DROP TRIGGER IF EXISTS price_observations_no_truncate ON public.price_observations;
CREATE TRIGGER price_observations_no_truncate BEFORE TRUNCATE ON public.price_observations
    FOR EACH STATEMENT EXECUTE FUNCTION public.reject_price_observation_mutation();

CREATE OR REPLACE FUNCTION public.append_price_observations(p_observations jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
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

ALTER TABLE public.price_observations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS price_observations_service_read ON public.price_observations;
CREATE POLICY price_observations_service_read ON public.price_observations
    FOR SELECT TO service_role USING (true);
REVOKE ALL ON public.price_observations FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.price_observations TO service_role;
REVOKE ALL ON SEQUENCE public.price_observations_id_seq FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.reject_price_observation_mutation() FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.append_price_observations(jsonb) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.append_price_observations(jsonb) TO service_role;
COMMIT;
