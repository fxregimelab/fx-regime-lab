# Published-call population repair — 27 September 2026

Previously, performance readers started from evaluation rows. A published call with no evaluation disappeared from total counts, so validation failures could raise the reported scored share. This packet starts reporting from persisted calls and preserves missing outcomes.

## Implemented contract

The PostgreSQL `validation_observations` view starts from `regime_calls` and left-joins one current `published-direction-v1` evaluation by call ID. It never borrows results from another call on the same date/pair. Direction, confidence and source/model metadata come from the immutable published call. Missing evaluations have a null evaluation ID, an explicit false presence flag and null outcomes. The scoring-version field identifies the requested definition, even when no evaluation exists.

Python aggregation and public queries read that same view. They retain complete pagination and explicit source/strategy/model/scoring selection. Backend and frontend report total calls, calls with evaluations, calls without evaluations, horizon maturity, abstention, missing outcomes and scored observations separately. The view's call ID is the stable pagination identity. Public labels now describe published calls, and explain that scored share includes pending calls and abstentions in its denominator.

Snapshot identity now includes `population_version`. Existing derived snapshots keep `evaluation-records-v1`; new results use `published-calls-v1`. Both can coexist on the same date, pair, source and model. Public readers and accuracy-monitor readers require the new population version. Old snapshots cannot silently inherit new denominators; deployment must recompute snapshots after applying the migrations.

The view is read-only and uses PostgreSQL 15+ security-invoker behavior. SELECT is granted to the existing public/service roles, but underlying permissions and row-level security still apply. No write grant is introduced.

## Executed evidence

- Full pipeline regression gate passed; current collection contains 404 tests. Focused aggregate/persistence suite: 34 passed.
- Ten Node query/integration tests passed. These include complete pagination beyond 2,000 rows, exact source/model/population isolation, missing call-ID evaluations, query failure behavior and Python/frontend parity at both horizons.
- Fifteen existing frontend calculator/sharing tests passed. TypeScript passed; full Biome passed 201 files; Ruff passed; MyPy passed all 162 files; production build passed.
- Real PostgreSQL 17.11 rehearsal applied the new migration twice. Six calls yielded six observations although only four had canonical evaluations. A second call sharing date/pair with an evaluated call retained null outcomes. The actual aggregate-to-writer payload produced four replay calls, two scored observations, two missing evaluations, one immature call and one mature missing outcome. All five older snapshots remained stored under their original population semantics.
- A fixture row-level policy restricted anonymous/authenticated callers to EURUSD. The view respected it; USDJPY stayed invisible. No INSERT/UPDATE/DELETE privilege was granted, and direct deletion through the view failed. Earlier rollback/concurrency/immutability tests also passed again.
- GitNexus refreshed index and CLI impact check found 16 consumers of the shared reader and classified risk as critical. Final tracked-change scan: 35 files, 205 symbols, 28 flows, critical overall risk. MCP storage-version incompatibility and unavailable full-text search remain tooling limitations, not waived application checks.

## Limits and next work

This closes the local missing-evaluation denominator defect. It does not prove the scheduler published every expected trading session, that a stored live label is genuine, or that source inputs were available before publication. Holiday-aware entry/exit timing, source provenance, economic factor definitions, untouched research evaluation and deployed acceptance remain open.

The SQL fixture is a documented-schema rehearsal with selected actual migrations, not a full historical schema replay or production export. Browser and production acceptance have not been claimed. No original call/evaluation was rewritten, and no production write, commit, push or deployment occurred. The temporary Unix-socket PostgreSQL server was stopped after verification; no startup service was installed.
