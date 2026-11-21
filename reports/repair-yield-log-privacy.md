# Yield fetcher log privacy repair

## Result

The yield adapters now record the exception class and fixed operation context when a provider or parser fails. They do not stringify the exception, traceback, response body, parsed response value, or caller-supplied source identifier. Successful async fetches still record the returned value and an approved yield identifier. Unrecognized configured identifiers receive the fixed label `<unrecognized-yield-id>`.

The change is limited to diagnostics. Return values, FRED-to-Yahoo fallback order, batch fallback values, retry ownership in `AsyncFetcher`, and cancellation behavior are unchanged.

## Reproduced baseline

Before the source edit, this command exercised the real logging paths with synthetic markers and no network access:

```text
pytest -q tests/test_yield_log_privacy.py
```

Result: **9 failed, 2 passed**. The failures reproduced leaks from sync Yahoo and FRED legs, both Yahoo batch exception paths, ECB assets, async Yahoo, malformed FRED JSON, a FRED float conversion error that echoed the response value, and a gathered leg exception.

No real API key was read. Tests set `FRED_API_KEY` to a synthetic value and replace Fred, yfinance, `AsyncFetcher`, and sessions with local fakes or mocks.

## Verification

- Leaf privacy suite: **14 passed**.
- Declared scoped gate: **49 passed** across `test_yield_log_privacy.py`, `test_ingestion_log_privacy.py`, and `test_rate_input_contract.py`; output contained `REPAIR_PYTEST_VERIFIED`.
- Unlazy `leaf-26.1:G1`: **met** with output fingerprint `680b8cbe176009253e6574c329825a47615957de9adaef97d1700d62db04fc58`.
- Ruff on the owned Python source and test: **passed**.
- MyPy on the owned Python source and test: **passed**.
- `git diff --check` on the three owned files: **passed**.

The first gate-check invocation omitted the repository base and therefore resolved `CWD: pipeline` under the ledger directory. It did not execute the check. Re-running with `--cwd D:\Projects\fxregimelab` resolved the declared directory correctly and passed G1. `leaf-26.1:G2` remains a manual parent acceptance gate.

## Review record

1. Implementation pass replaced raw exception formatting in every exception logger in `yields.py`.
2. Domain pass added checks for result preservation, sync fallback continuation, the US async FRED-to-Yahoo fallback, and both Yahoo and FRED cancellation behavior.
3. Defect hunt found two non-exception empty-result logs that still accepted a configured Yahoo identifier; those now use the same approved-identifier boundary.
4. Polish pass checked every warning and error call in the file, ran the scoped gate, Ruff, MyPy, whitespace validation, and the repository change detector.

GitNexus reported CRITICAL upstream risk for all seven inspected functions, generally 38–39 impacted nodes, 33–34 direct nodes, seven processes, and five modules. The result includes unrelated files because the current graph is collision-heavy. Direct source inspection found the real integration points in the shared ingestion buffer and scheduler. The final GitNexus change detector also saw the repository's full dirty worktree—93 files and 626 symbols—so it cannot attribute that CRITICAL aggregate to this leaf alone.

## Owned changes and limits

This leaf changed only:

- `pipeline/src/fetchers/yields.py`: bounded log arguments and an allowlist used only when displaying a successful source identifier.
- `pipeline/tests/test_yield_log_privacy.py`: synthetic regression and behavior controls.
- `reports/repair-yield-log-privacy.md`: this evidence record.

`yields.py` already contained an uncommitted deletion of the Germany and India 2Y-to-10Y proxy fallback before this leaf started. That economic-definition repair was preserved without alteration and appears in the repository diff alongside this leaf's logging changes.

This check does not cover logging inside Fred, yfinance, aiohttp, or another dependency. It does not prove that arbitrary credentials cannot reach logs elsewhere in the application. No provider, credential, database, Docker, Hermes gateway, production service, deployment, or commit was used. Full-suite and final G2 acceptance belong to the parent repair task.
