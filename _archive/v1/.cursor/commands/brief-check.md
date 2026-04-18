# brief-check

Workflow for validating morning brief quality before it goes live:
1. Pull today's brief from morning_brief.py output
2. Check: does it have regime call with confidence for all three pairs?
3. Check: does it have validation accuracy stats at the top?
4. Check: are all signal changes explained in one sentence each?
5. Check: does it follow the structure defined in PLAN.md Phase 3.2?
6. Check: are there any [MISSING DATA] placeholders from failed fetches?
7. If any check fails: identify which pipeline module failed and invoke pipeline-debugger subagent

This command will be available in chat with /brief-check
