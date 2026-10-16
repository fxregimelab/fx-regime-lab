# REPAIR CHECKPOINT — fx-live-personal (background branch only)

> Main stays archived at `v2.1-archive`. Never push to main. Never move the tag.
> Ledger `regime_calls` + `validation_log` append-only. No UPDATE/DELETE.
> Footer stays honest (DEGRADED until truly green).

## Packet 1 — Triage baseline (2026-10-17, branch fx-live-personal @ bb089f3)

- pytest: **379/379 passed** (baseline confirmed; collect-only 379, full run 71s)
- web `tsc --noEmit`: **0 errors**
- web `biome check .`: **clean (206 files)**
- web `npm run build`: **pass (exit 0, Windows EISDIR not hit)**
- Supabase migrations on disk: **59 files** (58 real + 1 zero-byte `.tmp_schema_check.sql`);
  `docs/DB_STATUS.md` documents 49 (stale — needs refresh before live proof)
- Prefect: single deployment `Daily_FX_Regime_Engine`, cron `0 9 * * *`,
  `prefect.yaml` pull branch = `main` → background runs need manual trigger or
  branch override (no auto-run from fx-live-personal yet)
- Vercel: root `vercel.json` minimal; preview needs Root Directory = `web` +
  `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Fetchers: FRED / CFTC / Yahoo-Polygon-AlphaVantage / SEBI-FPI live.
  **MOF + ECB-SDW have no live fetchers** (proxies only: intervention proximity
  synthetic, ECB via FRED) — scoped as known-deferred for this slice.
- Eval/scorecard: none existed; local JSON+MD under `reports/` is canonical.
- Footer: **DEGRADED kept** (pipeline code green, live freshness + ledger proof
  + branch preview still pending).
- Ledger proof: **no DB writes performed in this packet** (shell has no
  SUPABASE/AI keys loaded; `.env.local` keys present for operator manual runs
  only, values never printed). History delta = zero by construction.
  Live counts+hashes must be captured by operator with creds before any PR.

## Packet 2 — First AI + eval slice (2026-10-17, branch fx-live-personal)

New files only (no existing symbol edited; GitNexus index unavailable —
DB version mismatch — manual grep impact: AIClient callers =
`orchestrator.py:771/791` via `generate_brief`; new code paths isolated):

- `pipeline/src/ai/renderers/analyst_note.py`
  SHA256 `78773CC1051A8D300014683D5BEDD847AADE02A8EB8EB65C97DABE4E90093A44`
- `pipeline/src/ai/analyst_reader.py`
  SHA256 `25A1114C2E415444DB4702F7B06B72D19B02F4BEAF8057AA7ED7E22CDC0611A7`
- `pipeline/src/eval/__init__.py` + `pipeline/src/eval/llm_reader_eval.py`
  SHA256 `EC3291A55884EE30C6B69F35BE358C13DBF91F721631752B658EB9DEC0CA326B`
- `pipeline/tests/test_analyst_reader.py` (8 tests) +
  `pipeline/tests/test_llm_reader_eval.py` (4 tests)

Guards: one LLM reader only; frozen call + brief in; 5-line note with cited
inputs out; no new signals; no new pairs; 3-pair lock enforced in code;
AI only via `pipeline/src/ai/client.py` (`AIClient.render`/`render_async`);
rate limiter untouched (chain-enforced 180/day); deterministic offline
fallback; no secrets in logs; no prod writes from tests.

- pytest: **391/391 passed** (379 baseline + 12 new), ruff clean on new files
- Eval baseline `reports/llm_reader_eval_v1.json/.md`:
  faithfulness **1.000**, number accuracy **1.000** (deterministic fallback,
  3 synthetic frozen rows), Brier **n=0 / skipped=3** (no outcomes claimed —
  no product claims, no accuracy marketing).
- Ledger proof: **zero writes** (unit tests mocked; eval offline; no UPDATE or
  DELETE on `regime_calls`/`validation_log` anywhere in new code — grep-verified).
- Footer: **DEGRADED kept** (honest: live calls + branch preview not yet verified).

## Packet 3 — Live run attempt: DQS abort is correct behavior (2026-10-16 ~20:31+ UTC)

Two E2E runs of the production path (`python scripts/run_live_personal.py` →
`src/scheduler/run_pipeline.py:run_pipeline` → `run_daily`) aborted at the
DQS gate: **DQS 0.2000 < 0.50 CRITICAL — refusing to publish**
(`pipeline/src/scheduler/orchestrator.py:959-964`). No calls published.

Root cause (proven with read-only replica of buffer+DQS, temp script outside repo):
- Run wall-time ~20:31/20:34 UTC Friday, pre-US-close: Friday bars not yet
  published anywhere → spot_obs stuck at Thu 2026-10-15 for all 3 pairs.
- `date.today()` uses local IST = Sat 2026-10-17 → business-day age
  Thu→Sat = 48h (`_calendar_age_hours`, `ingestion_buffer.py:80-98`).
- Buckets: rates 0.667, **spots 0.0**, cot 1.0, comm 0.667, x-assset 0.0 →
  raw 0.4444 × critical penalty 0.45 = **0.2000 exactly**. Gate worked as designed.
- Yahoo `^JG10Y/^IN10Y/^TGD10Y` 404s are noise: `fetch_legacy_10y_legs`
  (`yields.py:139-144`) already falls back to FRED series. No fix needed.
- All 4 universe yield legs verified live via FRED: DGS2 4.77, ECBDFR 2.5,
  INDIRLTLT01STM 7.06, IRLTLT01JPM156N 3.05.

Ledger proof (full paginated snapshots — earlier 1000-row views were truncated
by Supabase default limit; `ledger_snapshot.py` now paginates + exact counts):
- `reports/ledger_snapshot_full.json`: regime_calls **19,503**, validation_log
  (non-superseded) **19,485** — all 3 pairs live through 2026-10-15.
- After abort1: counts + SHA-256 identical. After abort2: identical again.
  **History delta zero, new rows zero — abort path writes nothing.**
- Prod 9 UTC daily run unaffected (runs 14:30 IST with complete bars).
- Slack/Resend keys absent locally → no alert noise from background runs.

Next: single re-run after Friday bars publish (~22:00 UTC) for the green
branch E2E + latest-calls refresh, then AFTER-proof and draft PR.

## Packet 4 — Vercel branch preview builds green (2026-10-16 ~20:45 UTC)

- `fx-live-personal @ 59d4dae` (Packet 3 receipts): **READY**
  `fx-regime-b6xojnnrg-…` + second project building at check time.
- `fx-live-personal @ 5e463ef` (reader/eval + docs): **READY ×2**.
- `main @ bb089f3` archive: **READY** (untouched). Tag commit `b0d33cd`: READY.
- "Site builds from branch preview" receipt: **PASS** (Vercel Linux builds).
- Preview URLs sit behind Vercel SSO login → page-content check (DEGRADED
  footer, fresh calls) is operator-side after login.
- Immediate pipeline retry deferred on evidence: spot re-check 20:40 UTC
  shows Friday bars still missing (last=2026-10-15 all pairs); retry now
  would abort identically. Single delayed run armed for 22:05 UTC.

## Packet 5 — DB_STATUS refresh + live-LLM eval attempt (2026-10-16 ~20:47 UTC)

- `docs/DB_STATUS.md`: removed duplicated rows 41–49, appended rows 50–58
  (z_blended, site_content, page_views, regime_category, structured_summary,
  site_settings, v2_schema, v2_1_honest_metrics, call_rationale constraint).
  Remote effects probed read-only: 11/11 present (`page_views` table present,
  0 rows). Total corrected 49 → 58 (+ zero-byte tmp file noted).
- Live-LLM eval on real frozen 2026-10-15 calls (3 pairs + briefs):
  **all providers unreachable on free tier** — Groq primary + fallbacks
  404/decommissioned, Gemini 429 (quota, retry ~3h), NIM 410 (EOL Aug 2026),
  OpenRouter `:free` slugs 404 (paid only). Per "no paid evals" guard: no paid
  calls made; reader used deterministic fallback (by design).
  `reports/llm_reader_eval_v2_live.*`: faithfulness 1.000, number accuracy
  1.000 (fallback notes), Brier n=0 (10-15 outcomes not yet matured).
- Known issue (deferred, needs human model-pinning decision):
  `pipeline/src/ai/providers/groq.py` model IDs stale; chain teardown logs
  `Event loop is closed` noise (pre-existing, also in `backfill.log`).
  No code changed — blast radius zero.
- Delayed branch E2E re-run still armed for 22:05 UTC (Friday bars).

## Open gates (6 root gates still open until evidence closes each)

1. Deploy blocker: Vercel branch preview from fx-live-personal (Root Directory
   `web` + env) — not yet built.
2. Pipeline crasher: end-to-end `run_daily` on background branch with operator
   creds — not yet run (offline-safe session; manual trigger required).
3. Data gaps: MOF/ECB-SDW fetchers deferred; latest-calls freshness unverified.
4. Ledger proof: live counts+hashes before/after with creds — pending operator run.
5. Accuracy: rolling 90-day EUR/USD ≥ 55% gate — unchanged, still the expansion bar.
6. Release: no VERIFIED RELEASE without live observation + release receipts.

## Base SHAs

- Branch base: `bb089f3` (main HEAD, includes `v2.1-archive` tag at `b0d33cd`)
- Branch: `fx-live-personal` (background only; no merge to main without human PR)
