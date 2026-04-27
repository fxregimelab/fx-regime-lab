# Cursor rules (AI agents)

Read the relevant doc before editing:

- Future frontend: [[FRONTEND_ARCHITECTURE]], [[DESIGN_SYSTEM]], [[DATA_READS_SPEC]]
- Data and Supabase: [[DATABASE_SCHEMA]]
- Pipeline and cron: [[PIPELINE_REFERENCE]]
- Signal math: [[SIGNAL_DEFINITIONS]]

## Frontend (`web/`)

**There is no `web/` package.** When a new frontend is added, restore stack-specific rules here (framework, lint, Supabase client split, chart library policy).

## Pipeline rules (repo root Python)

1. Do not edit any `*.py` file unless the task explicitly says you are changing the Python pipeline.
2. Do not edit `workers/site-entry.js` unless the task explicitly says you are changing Worker routing or behavior.
3. Do not edit `.github/workflows/*` unless the task explicitly says you are changing CI.
4. **Writers:** only Python writes financial tables via `pipeline/src/db/writer.py` patterns.
5. **Upserts:** follow existing `upsert(..., on_conflict=...)` patterns in the pipeline.

## General rules

1. Verify table and column names against [[DATABASE_SCHEMA]] before writing SQL or Supabase queries.
2. One task, one focused diff. No drive-by refactors.
3. After completing a task, list **files touched** and **what changed** in each file in your final message to the operator.

## Related docs

- [[PHASES]]
- [[FEATURE_REGISTRY]]
