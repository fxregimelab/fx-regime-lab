# TASK.md — THE COUNCIL REBUILD

> **Read `HANDOVER.md` first** before any work on this file. It contains the operator identity, locked decisions, career strategy, and session operating rules that govern all task prioritization.

**Status:** P0 Emergency Triage Complete. 198/198 tests pass. ruff + mypy clean on all new code.

## Active Rounds (The Dual-Mandate Roadmap)

### Round 1: The Foundation (Data & Schema Audit) [COMPLETE]
- [x] Phase 1: Audit `signals` and `regime_calls` tables.
- [x] Phase 2: Implement strict immutable constraints.
- [x] Phase 3: Establish the `validation_log` schema.

### Round 2: The Core Logic (Pipeline Refactoring) [COMPLETE]
- [x] Phase 1 (Layer 1): Refactor Regime Gate logic.
- [x] Phase 2 (Layer 2): Refactor Directional Signal logic.
- [x] Phase 3 (Layer 3): Implement Timing & Entry logic.
- [x] Verification: 100% Logic Test Pass (121/121 pytest cases).

### Round 3: The Validation Engine (The Immutable Ledger) [COMPLETE]
- [x] Phase 1: Implement Daily validation script (T+5, T+20) with log returns, 5bps Marcus dead-band, Brier scores.
- [x] Phase 2: Aggregate stats module (`validation_stats` table) with Brier Skill, Win Rates, Sharpe-like ratios, calibration buckets, max drawdown.
- [x] Phase 3: Automate Supabase logging — `run_daily.sh` now runs `python -m src.validation.engine` followed by `python -m src.validation.aggregate`.

### Round 4: The Research Construction (Historical Backtest) [COMPLETE]
- [x] Phase 1: Historical data backfill infrastructure (`src/backfill/historical_fetcher.py`) via yfinance.
- [x] Phase 2: Historical pipeline execution engine (`src/backfill/orchestrator.py`) with date-range replay.
- [x] Phase 3: Research artifact generator (`src/research/artifacts.py`) — markdown track-record reports from validation_stats.

### P0: Emergency Triage (Credibility Kill Shots) [COMPLETE — 2026-05-08]
- [x] **P0-T1:** Wire Round 3 validation engine into production (`run_validation` now called by orchestrator; T+5/T+20 stored separately; Brier scores computed).
- [x] **P0-T2:** Enforce immutable ledger (`write_regime_call` uses insert-or-ignore; `delete_pipeline_data_for_date` gated behind `force=True`; `audit_log` table + triggers in migration; `call_id` FK preserved).
- [x] **P0-T3:** Pipeline failure alerting (`monitoring/alerts.py` with Slack + Resend email; success heartbeat + DQS alert wired into `orchestrator.py`; `.env.example` updated).
- [x] Integration tests: `tests/integration/test_p0_validation_immutability.py` (3 cases).
- [x] Alert tests: `tests/test_alerts.py` (9 cases).

### Round 5: The Research Terminal (Institutional UI) [IN PROGRESS — delegated to Cursor Agent]
- [x] Phase 1: Scaffold Next.js App Router with Tailwind v4, Supabase SSR, design tokens.
- [x] Phase 2: Methodology page shell with KaTeX support.
- [x] Phase 3: Validation stats display components.
- [ ] Final polish: Terminal pair desks, mobile layouts, error states (agent building).

---

## Test & Quality Summary

| Metric | Value |
|--------|-------|
| Total pytest cases | 198 |
| Pass rate | 198/198 (100%) |
| Pre-existing bug fixed | `test_cot_percentile_three_year_window_uses_last_156` date overflow |
| New modules | `validation/aggregate`, `validation/engine`, `backfill/orchestrator`, `backfill/historical_fetcher`, `research/artifacts`, `monitoring/alerts`, `scheduler/run_pipeline` |
| New migrations | `20260505000001_round3_validation_engine.sql`, `20260505000002_validation_stats.sql`, `20260508000001_p0_validation_immutability.sql` |
| ruff status | Clean on all new + modified files |
| mypy status | Clean on all new modules |

## The Council Checklist (The OMEGA Loop)

Every task MUST be checked by the chambers for **Dual-Alignment**:
1.  **Chamber 1 (Strategy):** Is the logic macro-economically sound? (MFE Level)
2.  **Chamber 2 (Engineering):** Is the data pipeline "Zero-Failure"? (Production Level)
3.  **Chamber 3 (Perception):** Is the output "Institutional Research" grade? (Admissions/HF Level)
4.  **Delegated Execution:** Delegate implementation to the Cursor Agent CLI (`agent --print "..."`).

## Notes

- **Cloaked Professionalism:** Strictly NO student/admissions language in public files.
- **Agentic Power:** The Cursor Agent is authenticated as `tech@fintreeindia.com`. Use it for implementation.
- Always update documentation after iterating.
