# Brief — T12: AI telemetry, atomic attempt budgets, production isolation

**Status:** queued (next desk packet after T06 lands)
**Kind:** implementer (desk packet AD-T12)
**Spec:** `docs/specs/autonomous-desk/05-implementation-tasks.md` AD-T12 (L211–227);
budgets in `06-agent-prompts-and-runbook.md` §10 (L183–201).

**Files:** modify `pipeline/src/ai/providers/chain.py`; create `pipeline/src/ai/telemetry.py`,
`pipeline/tests/test_ad_ai_budget.py`, `pipeline/tests/test_ad_ai_isolation.py`.
(Do not add writer.py facades — keep to these 4 files; a writer facade would be a lettered
subtask and must not be taken.)

## Current state (verified)

- `FallbackProviderChain.call_async` loops providers Groq → Gemini → NIM → OpenRouter; each
  attempt calls `rate_limiter.check_limit(date_str)` inside the provider `try` block and
  `writer.write_ai_request(date_str, purpose, model)` after success only.
- `check_limit` raises `RuntimeError` when the daily cap is hit — currently caught by the
  per-provider `except Exception` and treated as a provider failure → the chain keeps trying
  (cap exception retried; telemetry/read-limit RPC hit repeatedly).
- `AIClient.__init__(self, chain: FallbackProviderChain | None = None)` is the existing
  injection point the desk uses.

## Required behavior

1. **`telemetry.py`** (new, no DB writes, stdlib only):
   - Value types: `AttemptContext` (date_str, purpose, provider, model, max_tokens, attempt_no),
     `Reservation` (opaque id + reserved amount), `Usage` (input_tokens/output_tokens optional),
     `Outcome` enum (`success`/`failed`/`canceled`).
   - `AttemptBudgetPolicy` protocol: `reserve(ctx) -> Reservation` (must raise before send when
     no budget), `settle(reservation, usage, outcome) -> None` (exactly once per reservation).
   - `NonRetryableAttemptError(Exception)` — raised for budget/permission/schema/policy failures.
   - `DefaultProductionPolicy`: preserves today's production behavior — `reserve` calls
     `rate_limiter.check_limit(date_str)` (cap breach → `NonRetryableAttemptError`), `settle` on
     success calls `writer.write_ai_request(date_str, purpose, model)`. No other side effects.
   - Conservative estimator helper (e.g. `estimate_input_tokens(messages)`): unknown usage must
     settle at the conservative maximum, never zero. Money amounts default to 0 for verified-free
     models; unknown price ⇒ deny paid send or conservative max reservation.
2. **`chain.py`**:
   - `FallbackProviderChain.__init__(self, budget_policy: AttemptBudgetPolicy | None = None)`
     defaulting to `DefaultProductionPolicy` (behavior preserved for all existing callers).
   - **Every actual attempt** (including fallbacks and OpenRouter retries) reserves before the
     provider request and settles exactly once afterwards with actual usage when the response
     exposes it, otherwise conservative.
   - Provider failures settle `failed` (cost ≤ reserved, effectively free) and continue the chain.
   - `NonRetryableAttemptError` (and budget/permission/schema/policy errors) must propagate
     immediately — never converted into a provider failure, never retried, never fall through to
     the next provider.
   - Telemetry identity: the policy receives provider + model + attempt number for each attempt
     (fallback identity is never concealed). Settlement on success includes provider/model.
3. **Tests — no network/provider calls.** Monkeypatch provider availability + clients with fakes.
   - `test_ad_ai_budget.py`: reserve-before-send ordering per attempt; settle-exactly-once;
     failed attempt costs nothing; missing usage → conservative settlement; cap/budget exception
     propagates after exactly one reserve (not caught as provider failure, no retry); concurrent
     `call_async` invocations against a lock-protected tiny budget never overspend; fallback
     identity recorded in settlements.
   - `test_ad_ai_isolation.py`: with a **desk-style policy injected**, no production telemetry
     RPC occurs — monkeypatch `writer.write_ai_request` / `writer.get_ai_request_count_today` to
     raise and assert the chain never touches them across success, fallback, retry, and failure
     paths; with the default policy, both are still used exactly as before (success-only write).

## Fail-first list (must all fail before the fix, pass after)

- fallback/retry touches production telemetry/read-limit RPC when a desk policy is injected;
- failed attempt costs nothing (settle records ≤0 cost / failed outcome);
- cap exception caught as provider failure and retried;
- concurrent attempts overspend;
- missing usage counted as zero;
- fallback identity concealed.

## Constraints

- No DB writes anywhere in this task; tests must not require API keys, network, or the DB.
- Do not edit files outside the 4 listed. No commits/push.
- Concurrency note: other agents may run suites mid-edit; re-run once if a failure is clearly
  outside your files.

## Verify (from `pipeline\`)

Focused `-m pytest tests/test_ad_ai_budget.py tests/test_ad_ai_isolation.py -q`;
full `-m pytest -q`; `-m ruff check .`; `-m mypy .`.
