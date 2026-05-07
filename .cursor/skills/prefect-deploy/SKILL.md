---
name: prefect-deploy
description: >-
  Manages Prefect Cloud deployment for FX Regime Lab pipeline.
  Use when changing orchestration, scheduling, or deployment config.
---

# Prefect Cloud Deployment

## Deployment spec

- **File**: `pipeline/prefect.yaml`
- **Name**: `Daily_G10_Alpha_Engine`
- **Entrypoint**: `src/scheduler/orchestrator.py:run_daily`
- **Schedule**: Every 24 hours (`interval: 86400`)
- **Work pool**: `default` (managed)

## Secrets

Secrets injected via `job_variables.env` with shell substitution `{{ $VAR }}`:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `FRED_API_KEY`
- `OPENROUTER_API_KEY`

Never commit real values to git.

## Deploy command

```bash
set -a && source .env && set +a
cd pipeline
prefect deploy --prefect-file prefect.yaml --name Daily_G10_Alpha_Engine
```

Requires `prefect cloud login` first.

## Local testing

```bash
cd pipeline
python -m src.scheduler.orchestrator  # or relevant module
```

## Changing the deployment

1. Edit `pipeline/prefect.yaml`.
2. Update `entrypoint` if orchestrator changes.
3. Update `schedule` if cadence changes.
4. Add env vars to `job_variables.env` if new secrets needed.
5. Re-deploy with command above.

## Hard rules

- No GitHub Actions for pipeline automation.
- Never expose secrets in logs.
- Flow must handle missing env vars gracefully (skip writes, not crash).
