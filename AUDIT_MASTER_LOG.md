# FX Regime Lab: Master Audit Log

This document serves as the living record of the Phase-by-Phase deep system audit. 
*Status:* **[ COMPLETED ]**

## Audit Roadmap

### 🟢 Phase 1: Data Ingestion & External Resilience (Python Fetchers)

**Status:** **[ COMPLETED ]**
*Findings:* Discovered hardcoded year in COT fetcher, missing backoff for AI rate limits, and missing non-US macro events in FRED mappings. Logged 6 issues to `BUG_REPORT.md`.

### 🟢 Phase 2: Signal Math & Logic Integrity (Python Engine)

**Status:** **[ COMPLETED ]**
*Findings:* Math is generally safe against zero-division (clipping/checks in place). Identified a date misalignment risk in `validation/backtest.py` and a logic gap in `get_primary_driver` where a zero-signal state misreports the driver. No look-ahead bias found in analog engine. Logged 3 issues to `BUG_REPORT.md`.

### 🟢 Phase 3: Database Architecture & Persistence (Supabase + Writer)

**Status:** **[ COMPLETED ]**
*Findings:* RLS `SELECT` policies are correct, but explicit `INSERT/UPDATE/DELETE` blocks for `anon` are missing. Identified a potential race condition in `ai_usage_log` limit checking. Logged 3 issues to `BUG_REPORT.md`.

### 🟢 Phase 4: Frontend State, Performance & UX Integrity (Next.js)

**Scope:** `web/src/lib/queries.ts`, `web/src/components/`, `web/src/app/`
**Focus Areas:** React component lifecycle, Query caching, Mobile responsiveness, Error boundaries.
**Status:** **[ COMPLETED ]**
*Findings:* The UI lacks root `error.tsx` boundaries, leaving the terminal vulnerable to a complete crash on any React exception. `useHistoricalData` massively over-fetches due to a global 60-second `staleTime` applied to 25k-row payloads. A "Mobile Viewport Trap" exists where a hardcoded `100vh` lock on desktop breaks native mobile scrolling. Logged 3 issues to `BUG_REPORT.md`.

### 🟢 Phase 5: Build, Security & Automation (DevOps)

**Scope:** `.github/workflows/`, `web/next.config.js`, `pipeline/pyproject.toml`, `.env`
**Focus Areas:** CI/CD resilience, Dependency vulnerabilities, Environment variable leakage.
**Status:** **[ COMPLETED ]**
*Findings:* GitHub actions correctly map secrets. The `pyproject.toml` file installs testing and development dependencies (`pytest`, `ruff`, `mypy`) into the production runner environment globally, causing CI bloat. Logged 1 issue to `BUG_REPORT.md`.

---

## Audit Execution Notes

- **Phase 4 & 5 Synthesis**: The audit is complete. The system architecture is structurally sound but suffers from optimization oversights typical of rapid iteration. The most critical issue discovered in Phase 4 is the **Data Over-Fetching** (Bug 4.3); downloading 25k rows every 60 seconds per user will rapidly exhaust Supabase bandwidth quotas. The missing Error Boundaries (Bug 4.1) represent a significant UX risk in a production institutional tool. The backend container bloat (Bug 5.1) is an easy win for faster daily pipeline runs.