# Test network isolation repair

## Outcome

The pipeline pytest suite now installs a default Python-process network guard for each test. It blocks non-loopback DNS lookups, TCP connections and unconnected UDP sends. Blocked attempts are recorded across threads, and the test fails during teardown even when application code catches the immediate exception.

Numeric IPv4 and IPv6 loopback addresses are allowed. `localhost` is allowed only after every address returned by the active resolver is confirmed as loopback. A real aiohttp request to a local HTTP server verifies that local transport still works.

The guard covers Python calls through `socket.getaddrinfo`, `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr`, `socket.connect`, `connect_ex`, `sendto`, and `sendmsg` where the platform provides it. It is not an operating-system sandbox. A subprocess or native library that bypasses Python's `socket` module needs a separate audit. Collection-time imports and higher-scope fixture setup happen outside the function-scoped guard. A worker thread is covered while its test is active; a test must still join its workers because work that deliberately outlives fixture teardown is outside this boundary. The suite passed with no known call in those uncovered phases, but this does not prove a future import, higher-scope fixture or orphaned worker cannot make one.

## Negative controls

The isolation tests replace the underlying resolver and connector with functions that fail if reached. Foreign hostnames, documentation-only literal IP addresses, reverse DNS and UDP destinations are rejected by the guard before those functions run. Another control catches the immediate block in a worker thread and verifies that guard exit still raises an assertion. Cleanup tests verify that the socket functions are restored after the control context exits.

The prior FPI smoke test called a public URL and accepted `None` after a network failure. It has been replaced with the frozen retired-source contract: both FPI fetch APIs must raise `RuntimeError` containing `Unqualified FPI source is retired` before any request. A global `requests.Session.request` fail-if-called control verifies zero request attempts. Parser coverage also rejects non-finite numbers, impossible calendar dates and trailing date text.

## Verification

- `python -m pytest tests/test_network_isolation.py -q`: 5 passed.
- `python -m pytest tests/test_network_isolation.py tests/test_fpi_india.py -q`: 8 passed after the separately owned production FPI retirement landed.
- `ruff check tests/conftest.py tests/network_guard.py tests/test_network_isolation.py tests/test_fpi_india.py`: passed.
- `mypy tests/conftest.py tests/network_guard.py tests/test_network_isolation.py tests/test_fpi_india.py`: passed with no issues.
- An earlier full-suite discovery run, before the final retired-FPI contract was added, collected and passed 1,200 tests under the initial guard in 41.88 seconds. It found no other runtime outbound attempt. This historical run is not final evidence for the later FPI contract or the extended DNS and UDP coverage.

The focused contract is complete. The parent repair task owns the final full-suite integration run after its remaining consumer changes.

## GitNexus limitation

Pre-edit impact checks reported CRITICAL reach for `fetch_fpi_flows`, `fetch_fpi_history`, and even the legacy test-only smoke function. The results included unrelated UI symbols and processes. New guard symbols were not indexed. The final change scan reported the shared checkout's 91 files and 600 symbols as CRITICAL, so it could not isolate this leaf. Direct inspection confirmed the production FPI callers in the scheduler and history helper; this leaf does not edit production code.
