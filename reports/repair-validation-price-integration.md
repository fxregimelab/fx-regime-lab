# Validation price integration — packet 11

The four validation paths now share `publication-snapshot-v2`. Each entry belongs to the exact immutable publication; endpoints use exact dated stored closes, and each completed horizon retains its price evidence. The new database contract verifies the reported metrics against those prices. Earlier v1 records remain intact and excluded from current v2 reports.

The parent added a strict historical price reader with no nearest-session fallback, switched public cohort selection and labels to v2, and explained the measurement on the public performance pages. Missing original entry or endpoint evidence remains unavailable. Source errors propagate. The three-pair restriction remains in force.

Independent parent verification passed:

- 63 shared evaluator/live/replay tests; 88 staged tests; 49 writer/cohort/reader tests.
- 19 public query and metric tests, including exclusion of `published-direction-v1` from current cohorts.
- Seven grouped PostgreSQL price-evidence checks, including actual evaluator-to-writer serialization, concurrent writes, immutable completion, rollback and role restrictions; the historical v1 verifier also passed.
- Full pipeline regression gate, with 581 tests collected; full Ruff and MyPy (175 files).
- Full frontend TypeScript, Biome (202 files) and production build. The existing metadataBase warning remains open.

The full type check found 24 errors in new test fixtures that narrower source-only checks missed. The worker corrected live/replay fixtures; the parent corrected staged narrowing and mapping fixtures. The relevant leaf gates and full type check then passed. No type suppression was used to hide those errors.

GitNexus marked shared entry points and public readers CRITICAL, but included unrelated cross-language paths. Exact caller review and regression checks supplied the practical impact evidence. Newly added symbols were not indexed. Parent review also corrected timestamp truncation, exception swallowing, inconsistent ID handling and fake-version filtering before accepting the leaves.

The same-date divergent-entry fixture is a regression test with a forbidden mutable-reader trap, not a claim that original source was executed. Local database fixtures do not prove the complete historical migration chain or deployed behavior. No production write, provider call, notification, commit or deployment was made. The task-local PostgreSQL server was stopped and `pg_ctl status` confirmed no server running. Docker and heavier Hermes services were unnecessary; Hermes MCP was unchanged.

## Next dependency

Current daily ingestion does not yet guarantee archival of completed historical closes. `fetch_max_history` is a separate one-time helper. The corrected evaluator therefore leaves missing endpoints unscored, rather than reconstructing them from mutable signal rows. Next work must preserve bar source, session boundaries and availability, archive completed observations in both scheduled paths, and report unavailable mature outcomes in operational health. Current `SpotBar` discards provider/timestamp details, and Polygon date parsing uses host-local date conversion; these belong to the timing repair. No current or future partial bar may silently become a completed endpoint.

Provider provenance, publication-time tradability, holidays, live observation windows, inference model version release and forecasting skill remain open. The complete goal is still active.
