# AD build checkpoint — AD-T00 baseline freeze

**Date:** 2026-10-18 (local). **Branch:** `fx-live-personal`. **Status: PASS.**
No daemon, broker order, production pipeline run, or provider call was performed.

## 1. Repository state

- HEAD before freeze: `1f03826` (framework v1.0). Pre-existing uncommitted work was
  found and **preserved, not discarded**: the 2026-10-18 audit remediation (code+tests+
  audit doc) and the autonomous-desk specification pack (docs only).
- Disposition — committed in two reviewed commits:
  - `07e9d4b` — desk audit 2026-10-18: harden eligibility/inputs; add `admission.py`,
    `operator_score.py`, `evidence.py` (17 files, +1098/−49).
  - `2346e96` — autonomous demo desk specification pack (10 files, +2309).
- Pushed: `origin/fx-live-personal` `1f03826..2346e96`. This receipt is the only file
  added afterwards, in its own commit.
- No other modified, deleted, or untracked paths existed at freeze time.

## 2. Gate commands and observed results

| Command (from `pipeline/`) | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | **478 passed** in 99.54s |
| `.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.venv\Scripts\python.exe -m mypy .` | Success: no issues in 230 files |
| `web/`: `npm run lint` (biome) | 206 files checked, no fixes applied |
| `web/`: `npm run build` | **NOT RUN at this checkpoint** (no web files changed since the audit build pass). Not recorded as a pass. |

Tool versions (this machine/venv): Python 3.14.5, pytest 9.1.1, ruff 0.15.18,
mypy 2.1.0 (compiled), Node 24.19.0, npm 12.2.0. OS: Windows (win32).

## 3. Code-intelligence status (impact analysis)

- GitNexus MCP: `list_repos` works; **graph queries fail** — LadybugDB storage version
  mismatch (database file 42 vs runtime 40). The index is also stale (indexed 2026-09-26,
  last commit `9fa1505`) and points at `D:\Projects\fxregimelab` (path differs from this
  working copy).
- Consequence: per spec 05 universal contract, impact tooling is **UNKNOWN** for all
  tasks. Each task changing existing symbols must list direct callers manually
  (grep/references) for reviewer disposition. New-file tasks (AD-T01/T02) are unaffected.
  High-care manual inspection required for shared-file edits (`db/writer.py` AD-T03,
  `ai/providers/chain.py` AD-T12).

## 4. Observed baseline vs proposed work

Observed local modules: `paper/{store,prices,levels,checklist,admission,operator_score,evidence,config}.py`
plus the 478-test suite. Proposed (not yet present): `contracts.py`, `policy.py`,
`snapshots.py`, `spec_bundle.py`, `broker*.py`, `clock.py`, `news.py`, `calendar.py`,
`features.py`, `strategies.py`, `reasoning.py`, `sizing.py`, `readiness.py`,
`reservations.py`, `executor.py`, `permits.py`, `reconcile.py`, `manage.py`,
`watchdog.py`, `settlement.py`, `replay.py`, `opportunities.py`, `benchmarks.py`,
`experiments.py`, `evaluation.py`, `reasoning_eval.py`, `certificates.py`,
`activation.py`, `evolution.py`, `memory.py`, `supervisor.py`, `flow.py`, `graduation.py`
and their `test_ad_*` suites (task packets AD-T01…AD-T32).

## 5. External dependencies kept as blockers (for later gates)

Read-only terminal verification (G1), authoritative calendar/news entitlement (G1),
broker symbol/stop/freeze rule confirmation (G2/G3), continuous host availability (G3),
provider budget provisioning (G1). None block the local build chain; each remains
BLOCKED until real evidence exists — no guessed substitutes.

## 6. Next

**AD-T01** (strict transport contracts) is eligible now. AD-T02 is blocked on T01.
Baseline for every task: current HEAD after this receipt, all 478 tests green.
