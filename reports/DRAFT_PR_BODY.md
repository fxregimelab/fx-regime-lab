# DRAFT PR BODY — fx-live-personal → main (DO NOT MERGE without human approval)

> Background branch only. Main stays archived at `v2.1-archive` until a human
> merges this. 6 root gates remain open. No VERIFIED RELEASE claimed.

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
- Ledger: regime_calls 19,503 / validation_log 19,485 (non-superseded), all 3
  pairs fresh through 2026-10-15. Two branch E2E attempts aborted at DQS gate
  (0.20 < 0.50, pre-close timing artifact — Packet 3); AFTER snapshots prove
  **zero writes, hashes identical**. [UPDATE after 22:05 UTC run: green run
  SHA + AFTER counts/hashes + delta=new-rows-only proof here.]
- Footer stays DEGRADED until branch preview + live proof verified by operator.

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
