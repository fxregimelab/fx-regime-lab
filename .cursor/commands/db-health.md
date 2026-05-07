# db-health

Check database health and recent activity:
1. Query row counts: `signals`, `regime_calls`, `validation_log`, `pipeline_errors`
2. Check latest dates in each table
3. Verify 3-pair coverage (EURUSD, USDJPY, USDINR)
4. Check `pipeline_errors` for recent failures
5. Report any gaps or anomalies

Usage: `/db-health`
