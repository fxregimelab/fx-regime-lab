# Packet 16.2 — bounded quote HTTP acquisition

## Result

`pipeline/src/research/quote_acquisition.py` now implements the frozen packet-16 HTTP
orchestration contract. It acquires one closed UTC day for EUR/USD, USD/JPY or USD/INR,
using the fixed Massive quote endpoint and durable attempt evidence.

The normal result is a provisional snapshot. It is not a qualified market price and does
not permit evaluation or publication.

## Durable ordering

The worker records a newly inserted `started` event before opening a connection. A duplicate
start receipt stops without a provider request, so an unfinished attempt is not restarted
implicitly.

Each full response follows this order:

1. receive the complete bounded body and record its receipt time;
2. close the response;
3. build and persist the sanitized capture;
4. verify the capture receipt;
5. persist and verify the linked `page_saved` event;
6. only then request another page.

Only pages with verified capture and page-event receipts enter the terminal snapshot. The
snapshot receipt must match the exact hash of the constructor envelope produced from those
pages. A complete terminal event is attempted only for a snapshot whose constructor says
`acquisition_complete=true`. The runtime source manifest is hashed again after snapshot
persistence and before a complete terminal event is built.

If a page-event write has an uncertain result, the worker raises a generic error and leaves
the last verified event as unfinished evidence. It does not guess a terminal sequence. A
terminal-event write failure also raises a generic error from no exception cause.

## Network and privacy boundaries

- The default adapter uses TLS verification, disables redirects, ambient proxy/netrc state,
  cookies and aiohttp's automatic persistent-connection retry.
- Returned `next_url` values are never followed. The original cursor is validated and hashed,
  then sent only to the same fixed Massive endpoint.
- Each open and chunk read is bounded by the smaller of the request timeout and remaining
  overall network budget.
- Page, total-byte, page-count and elapsed-time budgets stop traversal with fixed reason codes.
- Partial bodies are never archived as complete captures.
- Provider, parser and persistence exceptions are reduced to fixed codes or generic errors.
  API keys, cursors, URLs and raw exception text do not enter attempt events.
- Cancellation makes a bounded close attempt for the current response and an owned default
  session, preserves already acknowledged progress, and propagates `CancelledError` without a
  fabricated terminal event even if cleanup fails or hangs.

## Verification

The focused synthetic suite makes no provider request and no production write. It covers:

- two-page ordering, exact fixed-host traversal and credential/cursor redaction;
- hostile URLs, cursor cycles, non-200 responses and malformed JSON/schema;
- empty and mixed-invalid results as provisional completed retrievals;
- page, body, total-byte, request, read and overall deadline limits;
- actual blocked open/read timeouts and an interrupted partial stream;
- invalid days, pairs, UUIDs, limits and clocks before persistence or network work;
- capture, page-event, snapshot, start and terminal receipt failures;
- source changes during snapshot persistence;
- receipt time before delayed cleanup, cancellation through failed/hanging cleanup, bounded
  hanging cleanup, and one-off invalid/regressing cleanup-clock samples followed by recovery;
- the default aiohttp adapter settings, including disabled automatic retry.

Observed checks on 27 September 2026:

- `node ../scripts/repair/verify-pytest.mjs tests/test_quote_acquisition.py` — 39 passed,
  `REPAIR_PYTEST_VERIFIED`.
- `python -m ruff check src/research/quote_acquisition.py tests/test_quote_acquisition.py`
  — passed.
- `python -m mypy .` — passed with no issues across 195 source files.

## Limits

Synchronous archive callbacks use their database client's own timeout and are not cancelled to
manufacture a hard end-to-end deadline. The worker checks the monotonic budget immediately
after those calls return.

Response and owned-session cleanup use the remaining network budget, capped by the configured
request timeout. Once that budget is exhausted, the worker grants one millisecond for
best-effort cleanup so a hostile close await cannot hang the task. An injected transport stays
owned by its caller; only its current response is closed.

No actual provider run, PostgreSQL proof, schedule, price qualification, revision policy,
evaluation integration or forecasting-skill claim is established by this packet.

The repository-wide GitNexus change scan reported CRITICAL risk across 73 shared-worktree files
and 293 processes. That aggregate includes the parent repair wave and many files outside this
leaf's ownership. This leaf changed only the acquisition module, its focused test, and this
report; the parent must run the final scoped/integration review before committing.

## Independent parent acceptance

The parent reviewed the final integrated source and independently re-executed the leaf gate. The final PostgreSQL bridge and all six groups passed with 174 rejection cases. The final transport gate passed 39 tests; the full pipeline gate passed with 1003 tests collected, and full Ruff/MyPy195 passed. PostgreSQL was stopped after zero scratch databases and other client sessions were confirmed. Source-only worker checks were not treated as full integration acceptance. No production/research acceptance is implied.

Final integrated acquisition source SHA-256: `a94813e6e6ea80f974ec4b046ac393a0a2cb4538430e0203856543e548b707c2`.
