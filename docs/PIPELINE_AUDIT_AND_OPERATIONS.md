---
title: Pipeline audit and operations
description: Canonical run order, CI env, deploy rules, merge exit codes, and links to the E2E audit report.
tags:
  - pipeline
  - ops
  - ci
aliases:
  - Pipeline E2E
  - LAYER3_STRICT
---

# Pipeline audit and operations

> **Obsidian:** If this vault’s root is the **repository root**, you can use wikilinks like `[[docs/PIPELINE_AUDIT_AND_OPERATIONS]]` and `[[reports/pipeline_e2e_audit]]`. Same-folder notes in `docs/` use `[[CODEBASE_AND_PROJECT_REFERENCE]]`.

Authoritative orchestration lives in [`run.py`](../run.py) `STEPS`. Full **contract matrix**, silent-failure notes, and remediation status: [**Pipeline E2E audit**](../reports/pipeline_e2e_audit.md).

**FedWatch spike (not in `STEPS`):** [`scripts/dev/fedwatch_spike.py`](../scripts/dev/fedwatch_spike.py) — manual probe for CME FedWatch accessibility; requires ToS review and explicit approval before any new pipeline module.

---

## Canonical `run.py` step order

```text
fx → cot → inr → vol → oi → rr → merge → text → macro → ai → substack → html → validate → deploy
```

| Step | Script |
|------|--------|
| fx | `pipeline.py` |
| cot | `cot_pipeline.py` |
| inr | `inr_pipeline.py` |
| vol | `vol_pipeline.py` |
| oi | `oi_pipeline.py` |
| rr | `rr_pipeline.py` |
| merge | `scripts/pipeline_merge.py` → `pipeline.merge_main()` |
| text | `morning_brief.py` |
| macro | `macro_pipeline.py` |
| ai | `ai_brief.py` |
| substack | `scripts/substack_publish.py` |
| html | `create_html_brief.py` |
| validate | `validation_regime.py` |
| deploy | `deploy.py` |

**Non-blocking** (failure does not stop `run.py`): `macro`, `ai`, `validate`, `substack`.

---

## Environment variables (operational)

| Variable | Where | Effect |
|----------|--------|--------|
| `LAYER3_STRICT=1` | CI (`daily_brief.yml` job env); optional locally | `vol` / `oi` / `rr` exit **1** if Layer 3 cannot produce required sidecars (see pipelines). |
| `GITHUB_ACTIONS` | Set by GitHub | `deploy.py` disables **stale** `briefs/*.html` fallback unless overridden. |
| `DEPLOY_ALLOW_STALE_BRIEF=1` | CI or local | Allow deploying **newest** brief in `briefs/` when today’s `brief_{DATE_SLUG}.html` is missing (use sparingly on CI). |
| `FRED_API_KEY` | `.env` / GHA | Required for FX/yield pulls. |
| `SUPABASE_*` | `.env` / GHA | Optional locally; enables remote writes and `pipeline_errors`. |

**Local errors without Supabase:** `log_pipeline_error` appends to `runs/{TODAY}/pipeline_errors_local.jsonl` (see [`core/signal_write.py`](../core/signal_write.py)).

---

## Deploy (`deploy.py`)

- Brief path uses **`config.DATE_SLUG`** — same as `create_html_brief.py` output (`briefs/brief_{DATE_SLUG}.html`).
- Fatal conditions (no deployable brief, corrupt HTML) → **`sys.exit(1)`**.
- **GitHub Actions:** if today’s brief file is missing, deploy fails unless `DEPLOY_ALLOW_STALE_BRIEF=1`. Local runs may still use newest brief with a **WARN**.

---

## Merge step

- `merge_main()` returns **`bool`**: `False` if master CSV missing, unreadable, or not written.
- [`scripts/pipeline_merge.py`](../scripts/pipeline_merge.py) exits **1** on `False` or exception so `run.py` marks the merge step failed.

---

## CI workflow summary

File: [`.github/workflows/daily_brief.yml`](../.github/workflows/daily_brief.yml)

1. `python run.py --skip deploy` (retry once; exit codes written to **GitHub Step Summary**).
2. Verify `briefs/brief_$(date -u +%Y%m%d).html` (UTC slug).
3. `python scripts/publish_brief_for_site.py`
4. `python deploy.py`
5. `npx wrangler deploy`

Job env includes **`LAYER3_STRICT: '1'`**.

---

## Terminal CSV freshness (`site/data/`)

The research terminal can load merged history from **`/data/latest_with_cot.csv`** when the browser has no Supabase client (see [`docs/TERMINAL_DEEP_REFERENCE.md`](./TERMINAL_DEEP_REFERENCE.md) §10–11).

[`scripts/publish_brief_for_site.py`](../scripts/publish_brief_for_site.py) copies a fixed set of pipeline outputs into **`site/data/`** for Cloudflare Pages:

- `latest_with_cot.csv`, `cot_latest.csv`, `inr_latest.csv`, `macro_cal.json` (see `_DATA_FILES` in that script).

**Expectation after a successful CI run:** the **date index** of `site/data/latest_with_cot.csv` should match the latest **`signals.date`** written by the same run (within the same calendar batch). If publish is skipped or fails with WARN, the terminal may serve **older** CSV while Supabase is newer—operators should check step logs and `site/data/` timestamps.

**Optional manual check:** `HEAD https://fxregimelab.com/data/latest_with_cot.csv` and compare `Last-Modified` to the pipeline run time (no secrets required).

---

## Operator helpers

| Script | Purpose |
|--------|---------|
| [`scripts/dev/verify_data_supabase_brief.py`](../scripts/dev/verify_data_supabase_brief.py) | Compare last master row vs Supabase `signals` (wide column set); probes `regime_calls` / `brief_log` / `validation_log`. Use `--warn-only` for non-blocking. |
| [`reports/pipeline_e2e_audit.md`](../reports/pipeline_e2e_audit.md) | Full audit matrix, §3 silent paths, §6 implementation status. |

---

## Related docs

- [[CODEBASE_AND_PROJECT_REFERENCE]] — repo map and mermaid (keep in sync with `run.py`).
- [`contaxt files/PLAN.md`](../contaxt%20files/PLAN.md) — phase gates.
- [`contaxt files/CONTEXT.md`](../contaxt%20files/CONTEXT.md) — narrative context.
- [`AGENTS.md`](../AGENTS.md) — structural map for humans and AI.

---

*Last updated to reflect pipeline audit remediations (deploy exits, merge bool, `LAYER3_STRICT`, local JSONL logs).*
