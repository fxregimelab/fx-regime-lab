# validate-signal

Validate a signal module end-to-end:
1. Run module in isolation: `python -m pipeline.src.signals.<module>`
2. Verify output dict has: `value`, `percentile`, `direction`, `regime`
3. Check Supabase upsert succeeded (query table)
4. Verify CSV fallback written to `data/`
5. Run `pytest` for the signal's test file

Usage: `/validate-signal <module_name>`
