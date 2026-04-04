# new-signal
Workflow for adding a new signal to the framework:
1. Apply signal-module skill
2. Confirm signal passes all four tests (institutional validity, independence, data availability, regime relevance)
3. Create [signal_name]_pipeline.py with fetch/compute/write structure
4. Add Supabase column to signals table (generate ALTER TABLE statement)
5. Add module call to GitHub Actions workflow in correct sequence position
6. Add signal to live dashboard UI (Cloudflare Pages / site) and/or `create_html_brief.py` / charts as appropriate — there is no `create_dashboards.py`
7. Add signal mention to morning brief if it changes regime call
8. Test with last 5 trading days of data before declaring complete

This command will be available in chat with /new-signal
