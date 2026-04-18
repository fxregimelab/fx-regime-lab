# run-validation

Workflow for updating the out-of-sample validation log:
1. Fetch yesterday's regime calls from regime_calls table
2. Fetch actual price returns for each pair from yfinance
3. Compute 1D and 5D returns from entry date
4. Determine correct_1d and correct_5d flags
5. Upsert to validation_log table
6. Compute rolling 20-day accuracy per pair
7. Update morning brief header with current accuracy stats
Run this: every trading day, triggered after main pipeline

This command will be available in chat with /run-validation
