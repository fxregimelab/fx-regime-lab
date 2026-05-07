# daily-run

Trigger or validate the daily pipeline run:
1. Check Prefect Cloud for last successful run timestamp
2. Verify `signals` table has today's rows for all 3 pairs
3. Verify `regime_calls` has today's rows
4. Check `pipeline_errors` for new failures
5. If gaps found: invoke `fx-regime-pipeline-triage` skill

Usage: `/daily-run`
