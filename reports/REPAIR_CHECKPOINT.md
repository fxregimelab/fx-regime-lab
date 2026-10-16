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
