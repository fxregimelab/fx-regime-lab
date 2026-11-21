# Python publication reader repair

## Scope

Leaf 10.1 repairs Python current-publication reads without changing the complete
historical call-ID population used by validation. No runtime, database, network,
AI provider, notification, deployment, commit or production action was used.

## Implemented behavior

- Current reads accept only EURUSD, USDJPY and USDINR publications with
  `data_source=live` and `strategy_version=v2`.
- Current history orders by session date descending and durable integer call ID
  descending. It paginates raw rows before selecting one latest revision per
  session, so a heavily revised session cannot hide older sessions.
- Every Python current read has an explicit calendar cutoff. Prior-state reads
  use sessions strictly before the decision session and publications created
  before 00:00 UTC on that decision date. Unknown `created_at` values are
  excluded from this causal path. Naive timestamps and malformed dates fail
  before database I/O.
- Regime age starts with the current decision as day one, then extends its
  streak only through causally available prior sessions. Markov input uses the
  same prior-state boundary.
- Daily and weekly summaries, event-risk context and shadow comparison use the
  deterministic live-v2 current/history readers with inclusive descriptive
  cutoffs.
- Pair briefs and desk-card prompts retrieve signal inputs from
  `publication_evidence` by the selected durable call ID. Missing legacy
  evidence produces an explicit unavailable state and does not read the mutable
  `signals` projection. Pair/date mismatches fail instead of relabeling evidence.
- `get_historical_regime_calls` is unchanged. Validation and staged historical
  adapters therefore retain the complete immutable call-ID population.
- The legacy `get_latest_regime_call(pair)` name remains only as a descriptive
  compatibility wrapper for `pipeline/seed_history.py`; it delegates to the
  live-v2 reader with today's UTC date. All decision-state callers use explicit
  cutoffs.

## Dependency review

GitNexus reported CRITICAL blast radius for the existing reader, scheduler and
desk-card symbols (38 to 73 impacted symbols across seven indexed flows). The
index over-attributed many callers, so exact source searches were also used.
Those searches found the owned scheduler consumers plus the one descriptive
seed-history wrapper caller described above. The high-risk response was to add
separate current-live APIs, leave the validation history API intact, and cover
each owned consumer with scoped regression tests.

## Verification

- Scoped repair gate:
  `node ../scripts/repair/verify-pytest.mjs tests/test_publication_readers.py tests/test_daily_run_contract.py tests/test_scheduler_health_contract.py tests/test_run_pipeline_flags.py`
  — `64 passed`, `REPAIR_PYTEST_VERIFIED`.
- Ruff on the four changed source files and four owned test files — passed.
- Full pipeline MyPy check — passed with no issues across 173 source files.
- Additional all-history reader regression remains in the scoped reader test:
  backtest and v1 rows remain visible through `get_historical_regime_calls`.

## Remaining boundaries

- These are local mock-backed reader checks. They do not prove deployed
  Supabase behavior, production data reconciliation or scheduler observation.
- This packet preserves validation's complete call-ID population and leaves its
  historical API unchanged. It does not establish end-to-end validation
  correctness: `run_validation` still reads entry and horizon prices from the
  mutable signals projection, recorded separately as the next V08/P01 repair.
- Public web readers, the SQL public view and PostgreSQL role/immutability checks
  belong to their separate leaves.
- New inference model identifiers, broader source point-in-time repair and
  release acceptance remain open requirements.
