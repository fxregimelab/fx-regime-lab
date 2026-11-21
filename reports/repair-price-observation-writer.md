# Price observation writer repair

The parsers now retain provider identity, retrieval time, raw timestamp or date label, selected response metadata, and the separate source of a substituted futures-volume series. Polygon epochs are decoded in UTC. Unknown daily-window boundaries remain null.

The pure preparation function returns detached observation payloads with separate counts for missing metadata, invalid rows, future dates and unknown sessions. It does not invent old retrieval times. Repeated dates and revisions remain separate evidence. The database writer uses one atomic append RPC, validates positive IDs and consistent inserted/existing counts, and propagates failures without a fallback upsert.

Parent verification: 46 focused tests passed through the repair wrapper; scoped Ruff passed; full MyPy passed with 179 source files before the final test-only addition. Real PostgreSQL accepted the complete SpotBar preparation to writer to RPC path, including retries and corrections. The integration report records the database proof. Full pipeline checks follow scheduled-flow integration.

GitNexus classified the SpotBar and parser changes CRITICAL, including 46 direct SpotBar dependants. Existing numerical fields remain compatible. New metadata is optional for old fixtures; absent evidence is counted rather than fabricated. The graph includes noisy cross-language matches, so actual source paths and tests were also inspected.

The first existing fallback test assumed every requested ticker could receive the EURUSD response. Strict response identity exposed that fixture defect; it now returns the requested ticker. The no-key fixture explicitly removes the Polygon key, and provider throttle sleeps are mocked. An initial async test used an unavailable pytest plugin; it was converted to asyncio.run and passed.

This is a provider observation archive, not completed-close acquisition. It does not promote observations to historical_prices, replace v2 evaluation evidence, retain full raw HTTP envelopes, or prove historical availability. Full request/response capture, canonical session construction, mature validation coverage and release evidence remain open. Changes are local and uncommitted.
