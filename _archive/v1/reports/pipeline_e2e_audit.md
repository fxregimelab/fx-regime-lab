# FX Regime Lab — end-to-end pipeline audit

**Generated:** 2026-04-17 (repo analysis + doc reconciliation)  
**Canonical orchestrator:** [`run.py`](../run.py) `STEPS` — do not rely on older prose that omits Layer 3 or publish steps.

---

## 1. Contract matrix (run.py steps)

| Step | Script | Primary inputs | Primary outputs | `run.py` treats failure as | Error visibility |
|------|--------|----------------|-----------------|---------------------------|------------------|
| `fx` | `pipeline.py` | FRED, yfinance (FX, commodities, VIX proxy paths) | `data/latest.csv`, master build path toward `data/latest_with_cot.csv` | **Blocking** | `sys.exit(1)` if FX or yields empty |
| `cot` | `cot_pipeline.py` | CFTC feeds | `data/cot_latest.csv`, merges into `latest_with_cot` | **Blocking** | `sys.exit(1)` if COT fetch empty |
| `inr` | `inr_pipeline.py` | USD/INR, IN yields, FPI | INR columns in master / `data/inr_latest.csv` | **Blocking** | `sys.exit(1)` if USD/INR price empty |
| `vol` | `vol_pipeline.py` | CBOE tickers via yfinance | `data/vol_latest.csv`, Supabase `signals` IV column | **Blocking** | Default: **always** `sys.exit(0)`; with **`LAYER3_STRICT=1`** (CI) exits **1** if any expected pair missing |
| `oi` | `oi_pipeline.py` | CME OI scrape + prices | `data/oi_*.csv`, sidecar for merge | **Blocking** | Default: **always** `sys.exit(0)`; **`LAYER3_STRICT=1`** exits **1** on empty report / no products |
| `rr` | `rr_pipeline.py` | yfinance FXE options | `data/rr_latest.csv` (or empty), Supabase | **Blocking** | Default: **always** `sys.exit(0)`; **`LAYER3_STRICT=1`** exits **1** on skip paths |
| `merge` | `scripts/pipeline_merge.py` → `pipeline.merge_main` | `data/latest_with_cot.csv`, `vol/oi/rr` sidecars | Updated master CSV, `sync_signals_from_master_csv` | **Blocking** | `merge_main` returns `bool`; wrapper exits **1** if `False` or exception |
| `text` | `morning_brief.py` | `data/latest_with_cot.csv` | `briefs/brief_YYYYMMDD.txt` | **Blocking** | `sys.exit(1)` if master missing |
| `macro` | `macro_pipeline.py` | ForexFactory XML + `cb_events.json` | `data/macro_cal.json` | **Non-blocking** | No `sys.exit`; failures degrade to empty/minimal JSON path inside fetch logic |
| `ai` | `ai_brief.py` | Master CSV, optional Anthropic | `data/ai_article.json`, `data/ai_regime_read.json` | **Non-blocking** | Missing CSV → early `return` (exit 0); Claude errors → template fallback |
| `substack` | `scripts/substack_publish.py` | `data/ai_article.json`, Substack secrets | Substack draft (if creds) | **Non-blocking** | `main()` returns 1 on failure → `sys.exit(1)` |
| `html` | `create_html_brief.py` | Prior brief or `index.html`, master, charts builders | `briefs/brief_*.html`, `charts/*.html` | **Blocking** | `sys.exit(1)` if no template brief |
| `validate` | `validation_regime.py` | Supabase `regime_calls`, yfinance, master CSV | `validation_log` upserts | **Non-blocking** | No Supabase → skip (`return`); `__main__` forces `sys.exit(0)` |
| `deploy` | `deploy.py` | `briefs/brief_{DATE_SLUG}.html` from `config`; stale fallback local-only unless `DEPLOY_ALLOW_STALE_BRIEF=1` on CI | `index.html`, git push | **Blocking** | Fatal paths use `sys.exit(1)`; CI disallows stale fallback by default |

**CI after `run.py --skip deploy`** ([`.github/workflows/daily_brief.yml`](../.github/workflows/daily_brief.yml)):

| Step | Behavior | Notes |
|------|----------|-------|
| `run.py --skip deploy` | Retry once after 60s on failure | First-attempt flag not exported on double-failure |
| Verify `briefs/brief_$(date -u +%Y%m%d).html` | Hard fail if missing | UTC date slug must match generator’s date convention |
| `publish_brief_for_site.py` | Exit 1 if no non-empty `briefs/brief_*.html` | Syncs charts/static; copies `data/*` slices to `site/data/` with WARNs if missing |
| `deploy.py` | Git add/commit/push | Fails with exit **1** on missing/corrupt brief (see §6) |
| `npx wrangler deploy` | Worker + site assets | Independent of GitHub Pages push |

---

## 2. Runtime / CI observations (from workflow + code)

- **Concurrency:** `concurrency: group: daily-brief; cancel-in-progress: true` — overlapping manual + scheduled runs can cancel a mid-flight job; acceptable if documented; risk if cancel happens between brief write and deploy.
- **Retry semantics:** Second `run.py` attempt does not distinguish “flaky network” vs “logic bug”; consider logging both exit codes to Actions summary.
- **Date alignment:** Verify step uses `date -u +%Y%m%d` (UTC). Brief slug must match [`create_html_brief.py`](../create_html_brief.py) / `config` date source for the same calendar notion of “today” in CI.
- **Local run:** Full `python run.py` requires `.env` (at least `FRED_API_KEY`) and network. Use `runs/<YYYY-MM-DD>/pipeline.log` for post-mortems. Workspace policy: do not commit or rely on reading `data/` in automation without explicit approval; operators validate CSVs locally.
- **Local smoke (audit session):** `python -c "from run import STEPS, NON_BLOCKING_STEPS; ..."` and `python -m py_compile run.py deploy.py scripts/pipeline_merge.py validation_regime.py` succeeded. **GitHub Actions:** review last *N* workflow runs in the Actions UI for retry/concurrency/deploy outcomes (not executed from this environment).

---

## 3. Silent failure and exit-code catalog

| Location | Severity | Behavior |
|----------|----------|----------|
| `vol_pipeline.py` / `oi_pipeline.py` / `rr_pipeline.py` | **P1** | Outer `try/except` then **`sys.exit(0)` always** — `run.py` records OK even when Layer 3 is empty or errored. |
| `scripts/pipeline_merge.py` | **P1** | **`sys.exit(0)` unconditionally**; exceptions logged but success from orchestrator’s view. |
| `pipeline.merge_main` | **P1** | By design **never raises**; missing master → print + `return`; write/sync failures → log + `return`. Downstream may still run with stale master. |
| `deploy.py` | **P0** | “No brief found” and “corrupted HTML” paths use **`return`** → Python exits **0**; CI can show green without Pages update. |
| `deploy.py` | **P2** | Fallback to **most recent** `briefs/*.html` if today’s file missing — can publish **wrong calendar day** without failing. |
| `ai_brief.py` | **P3** (accepted) | Missing/empty master → skip with exit 0; intentional because step is non-blocking. |
| `validation_regime.py` | **P3** (accepted) | No Supabase client → skip; step non-blocking. |
| `log_pipeline_error` | **Mitigated** | No client: append **`runs/{date}/pipeline_errors_local.jsonl`**; insert failure also appends locally. |
| `macro_pipeline.py` | **P3** | Always exits 0; may write minimal calendar — acceptable for non-blocking macro. |

---

## 4. Data triple-check procedure (CSV ↔ Supabase ↔ brief)

*Per workspace rules, automated agents do not read `data/` as bulk output; operators or approved scripts run these checks locally/CI.*

1. **Pick anchor date** `D` = latest business date in `data/latest_with_cot.csv` index (last row).
2. **CSV / merge:** Confirm latest row for each pair has expected Layer 1 + Layer 2 columns; confirm `implied_vol_30d` / OI / RR columns present or explicitly NaN after merge (see `merge_main` join logic in [`pipeline.py`](../pipeline.py)).
3. **Supabase:** For `(date=D, pair ∈ {EURUSD, USDJPY, USDINR})`, compare `signals` row to the same row in CSV (numeric tolerance). Query `pipeline_errors` for `date=D` grouped by `source`.
4. **Brief:** Open `briefs/brief_YYYYMMDD.html` for the same run; spot-check regime labels vs composite columns. Optionally run [`scripts/dev/stress_test.py`](../scripts/dev/stress_test.py) / `verify_html.py` from repo root per [`AGENTS.md`](../AGENTS.md).

---

## 5. Security / ops (checklist)

- Secrets only via GitHub Actions → `.env` step; never commit `.env`.
- `SUPABASE_SERVICE_ROLE_KEY` only in server/CI contexts; anon key for browser.
- `deploy.py` rebase/merge: on repeated conflicts, human intervention may still be required.

---

## 6. Remediation backlog (implementation status)

| Priority | Item | Status |
|----------|------|--------|
| **P0** | `deploy.py` fatal paths exit non-zero | **Done** — `sys.exit(1)` for no deployable brief, corrupted HTML; brief path uses `config.DATE_SLUG`. |
| **P1** | Merge visible to `run.py` | **Done** — `merge_main()` returns `bool`; [`scripts/pipeline_merge.py`](../scripts/pipeline_merge.py) exits **1** on `False` or exception. |
| **P1** | Layer 3 strict mode | **Done** — `LAYER3_STRICT=1` in [`vol_pipeline.py`](../vol_pipeline.py), [`oi_pipeline.py`](../oi_pipeline.py), [`rr_pipeline.py`](../rr_pipeline.py) exits **1** on empty/skip paths; [`.github/workflows/daily_brief.yml`](../.github/workflows/daily_brief.yml) sets job `env.LAYER3_STRICT`. |
| **P2** | Deploy stale-brief fallback | **Done** — On **GitHub Actions**, newest-brief fallback is **disabled** unless `DEPLOY_ALLOW_STALE_BRIEF=1`. Local still allows fallback with **WARN**. |
| **P2** | `pipeline_errors` without Supabase | **Done** — [`core/signal_write.py`](../core/signal_write.py) appends to `runs/{TODAY}/pipeline_errors_local.jsonl` when client is missing; also on failed insert. |
| **P3** | Docs / PLAN / CONTEXT | **Reconciled earlier** — single canonical `run.py` sequence in CONTEXT / AGENTS / PLAN. |

**CI observability:** [`.github/workflows/daily_brief.yml`](../.github/workflows/daily_brief.yml) logs attempt 1 and attempt 2 exit codes to `$GITHUB_STEP_SUMMARY`.

**Operator helper:** [`scripts/dev/verify_data_supabase_brief.py`](../scripts/dev/verify_data_supabase_brief.py) — optional CSV + Supabase spot-check (run from repo root).

---

## 7. Success criteria (from audit plan)

- [x] Contract matrix for all `run.py` steps + CI steps documented.
- [x] Silent success paths listed with severity and product implications.
- [x] Triple-check procedure documented (operator-executed; no `data/` read in agent path).
- [x] Documentation reconciled to `run.py` in CONTEXT / AGENTS / PLAN (this commit).
- [x] Remediations P0–P2 implemented (see §6); optional dev verify script added.

---

## References

- Orchestrator: [`run.py`](../run.py)  
- Human-facing ops summary: [`docs/PIPELINE_AUDIT_AND_OPERATIONS.md`](../docs/PIPELINE_AUDIT_AND_OPERATIONS.md)  
- Docs index: [`docs/README.md`](../docs/README.md)  
- Merge entry: [`scripts/pipeline_merge.py`](../scripts/pipeline_merge.py), [`pipeline.py`](../pipeline.py) `merge_main`  
- Status JSON: [`core/pipeline_status.py`](../core/pipeline_status.py)  
- Supabase logging: [`core/signal_write.py`](../core/signal_write.py)  
