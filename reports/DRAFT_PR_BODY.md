> **Draft PR — human merge only. Do not auto-merge.** Background branch;
> main stays archived at `v2.1-archive` until a human merges this. 6 root
> gates remain open. No VERIFIED RELEASE claimed.

## What this branch does

- First LLM reader slice: frozen regime call + brief → 5-line analyst note
  with cited inputs (`pipeline/src/ai/analyst_reader.py`,
  `pipeline/src/ai/renderers/analyst_note.py`). One reader only. No new
  signals. No new pairs. 3-pair lock enforced in code. AI only via
  `pipeline/src/ai/client.py`, rate limiter untouched, deterministic fallback.
- Eval harness (`pipeline/src/eval/llm_reader_eval.py`): faithfulness, number
  accuracy per pair, Brier on conviction, versioned scores → local JSON+MD
  under `reports/` (`llm_reader_eval_v1.md`, `llm_reader_eval_v2_live.md`).
- Read-only ledger snapshot tool (`pipeline/scripts/ledger_snapshot.py`,
  paginated counts + SHA-256) + live-run launcher
  (`pipeline/scripts/run_live_personal.py`).
- Docs on branch only: README status, AGENTS.md counts, TASK.md sprint,
  CONTEXT.md repair section, HANDOVER.md addendum, MASTERPLAN.md phase note,
  `docs/DB_STATUS.md` migration table 49→58 (dedup + remote-verified),
  `reports/REPAIR_CHECKPOINT.md` packets 1–5.

## Receipts

- `pytest` 391/391 (379 baseline + 12 new), `ruff` clean, `mypy` clean (new),
  `tsc --noEmit` 0 errors, `biome check` clean, `npm run build` pass.
- Vercel branch previews: READY (both attached projects, latest branch SHAs).
- **Live green run 2026-10-17 08:07–08:11 UTC** (branch, 52 min ahead of
  prod's 09:00 UTC run): Prefect flow Completed() (08:11:15 UTC); published
  3 calls @ 2026-10-16 — EURUSD NEUTRAL, USDJPY NEUTRAL, USDINR INR_NEUTRAL
  (model 2.0-live, created_at 08:08 UTC). DQS gate passed (publication
  implies it: gate fires before any write).
- Ledger proof BEFORE → AFTER: regime_calls 19,503 → 19,506 (+3; old-subset
  SHA-256 `eec0749c…` byte-identical → history intact); validation_log
  current 19,485 → 19,491 (+12 inserts − 6 flag-only supersessions; no
  content mutation, no deletes). Snapshots:
  `reports/ledger_snapshot_full.json`,
  `reports/ledger_snapshot_after_live_green.json`. Two earlier DQS aborts
  (pre-close timing, Packet 3) wrote zero rows — hashes identical.
- Eval on the fresh calls: `reports/llm_reader_eval_v3_latest.md`
  (faith 1.000 / num 1.000, 3 rows @ 2026-10-16; Brier n=0 not matured).
- Footer stays DEGRADED until operator verifies the branch preview.

## Known issues (deferred, not in this PR)

- Free-tier AI providers unreachable (Groq model IDs 404/decommissioned,
  Gemini 429 quota, NIM 410 EOL, OpenRouter `:free` 404) → reader falls back
  deterministically; no paid calls made. Model-ID refresh needs a human
  pinning decision (`src/ai/providers/groq.py`).
- Yahoo `^JG10Y/^IN10Y/^TGD10Y` delisted → absorbed by existing FRED
  fallbacks; log noise only.
- MOF/ECB-SDW live fetchers deferred (proxies only). No v3 scope.

## Operator verify steps (before merge)

1. `git rev-parse v2.1-archive` unchanged; `main` untouched by this branch.
2. Compare AFTER snapshot hashes vs `reports/ledger_snapshot_full.json`
   (history identical, only new dated rows added).
3. Open branch preview (Vercel SSO login): DEGRADED footer, fresh calls,
   eval report present.
4. Confirm no UPDATE/DELETE on `regime_calls`/`validation_log` (triggers +
   `writer.py` conflict/versioning paths only).

## Merge

Human merges. Never auto-merge. No force push. No history rewrite.
