-- Public explanations may read bound signal inputs, never private rationale.
BEGIN;
CREATE OR REPLACE VIEW public.live_publication_signals
WITH (security_barrier = true, security_invoker = false) AS
SELECT c.id AS call_id, c.pair, c.date, e.signal_payload
FROM public.regime_calls c
JOIN public.publication_evidence e ON e.call_id = c.id
WHERE c.data_source = 'live'
  AND c.strategy_version = 'v2'
  AND c.pair IN ('EURUSD', 'USDJPY', 'USDINR')
  AND c.date <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date;
COMMENT ON VIEW public.live_publication_signals IS
  'Public immutable inputs by call ID. Owner-rights view intentionally exposes only live v2 signal snapshots, not private evidence metadata or rationale. Missing legacy evidence is unavailable, not the current signal projection.';
REVOKE ALL ON public.live_publication_signals FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.live_publication_signals TO anon, authenticated, service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;
