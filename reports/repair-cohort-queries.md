# Cohort query and storage repair — 27 September 2026

The queries now select one exact source, strategy, model and scoring version. Aggregate snapshots also select a window. Metrics read every matching page; date heuristics and broad error fallbacks have been removed. The default live model is the actual current publisher label, `2.0-live`, rather than the old backtest catalog alias `v2`.

Original calls and evaluations remain unchanged. The new snapshot migration labels old derived results as unknown/legacy and changes uniqueness to include all group dimensions. The evaluation RPC copies model identity from the published call and rejects mismatched metadata. The aggregate reader anchors its window to the requested as-of date. The writer rejects missing group metadata and invalid windows before database I/O.

Public homepage accuracy now uses the exact-group snapshot and the proper directional denominator. Recent display rows no longer define headline accuracy. The desk retrieves the complete matching evaluation ledger. The legacy row table distinguishes abstention and unavailable outcomes and preserves missing market returns instead of inventing zeroes or losses.

## Verified evidence

- Nine Node query/integration tests pass, including 2,201 rows across three pages, mixed sources/versions, requested replay models, query errors, snapshot denominators, actual replay metadata, Python/frontend parity on both horizons, and server-rendered abstention/unavailable labels.
- All seven initial query regressions failed against base revision `9fa1505`; see `reports/repair-query-negative-control.txt`. The two later integration tests were not part of that negative-control run.
- Real PostgreSQL 17.11 rehearsal passed with repeat migration, distinct source/model/window snapshots on one date/pair, immutable legacy preservation, and the actual aggregate-to-writer payload inserted into SQL. This exposed missing rolling-90-day columns in checked-in migrations; the forward migration now creates them.
- Existing atomic evaluation checks passed again: concurrent horizon completion, rollback, idempotency, full earlier-horizon retention and anonymous/authenticated denial.
- Full pipeline regression gate passed (402 tests collected). Ruff passed; MyPy passed all 162 files; TypeScript passed; Biome passed 201 files; production build passed before the final display-only coverage wording correction.

## Acceptance limits

The database fixture represents the documented post-cleanup schema plus actual aggregate/honest-metrics migrations. It is not a full replay of every historical migration or a production schema export. No production data or credentials were used. The temporary WSL PostgreSQL server was stopped after verification; no automatic service was installed.

The parity fixture verifies shared counts, gross payoff, Brier and net denominators, not publication-time tradability, holiday calendars, genuine probabilities, or predictive skill. Evaluation records omit published calls with no evaluation row; full published-call coverage still needs a complete call-ID join. Stored live labels still require provenance audit. Model version must be bumped for changed inference before release. No browser, production, release or historical-reconciliation acceptance is claimed.

GitNexus CLI change analysis completed: 35 files, 179 symbols, 26 affected flows, critical overall risk. The MCP runtime cannot read the newer index (storage 40 versus 42), so CLI analysis and direct dependency inspection were used. No commit or deployment was made.
