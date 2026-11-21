# Shared ingestion log privacy

The shared HTTP helper now logs only the HTTP(S) scheme and host. Userinfo, paths, query parameters and fragments are omitted because each can contain credentials. Malformed or unsupported URLs receive a fixed label rather than being echoed. Retry errors and the six master-buffer failure branches log the exception class without its message.

This fixes a concrete exposure: the old sanitizer recognized only lowercase `api_key`, and a subsequent exception log could still reproduce the complete URL. The change does not modify outgoing requests, the retry count, backoff, response data or cancellation semantics. The tests use synthetic secret markers, not actual credentials.

Before the change, eleven privacy regressions failed and the cancellation control passed. Afterward, the declared 47-test gate passed, covering successful HTTP responses, non-success statuses, exceptions, retry/backoff counts, cancellation and all six fan-out failures. Scoped Ruff and MyPy passed after correcting two line-length violations. GitNexus classified the affected shared helpers as CRITICAL; actual callers and adjacent staged-adapter/snapshot tests were reviewed.

This acceptance covers `async_engine.py` and the separately verified price adapter. Other fetchers, library-internal logs, deployment log retention and any historical secret exposure are not certified by these tests and remain within A03. No actual credential was read, no request reached an external provider, and no runtime or production configuration was changed.
