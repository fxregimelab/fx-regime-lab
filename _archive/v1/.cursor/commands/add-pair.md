# add-pair

Workflow for adding a new currency pair to the framework:
1. Confirm pair is in approved expansion roadmap (GBPUSD → AUDUSD → USDCAD)
2. Create [pair.lower()]_pipeline.py following exact structure of existing pair pipelines
3. Add FRED series IDs for rate differential (2Y and 10Y)
4. Add CFTC COT product code for new pair
5. Add CME CVOL endpoint for new pair
6. Add ETF ticker for synthetic RR (FXB for GBP, FXA for AUD, etc.)
7. Add pair identity color to brand system
8. Add pair to all dashboard panels and morning brief
9. Run backfill for last 52 weeks to populate Supabase history

This command will be available in chat with /add-pair
