# backfill

Workflow for populating historical data in Supabase:
1. Fetch historical data for specified pair from start_date to today
2. Compute all signal values for each date in range
3. Batch upsert to specified table (max 100 rows per batch)
4. Verify row count matches expected trading days
5. Log completion to pipeline_errors table with status 'BACKFILL_COMPLETE'
Use when: adding new signal to existing pairs, adding new pair, recovering from data gap

This command will be available in chat with /backfill
