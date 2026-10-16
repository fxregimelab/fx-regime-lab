# FX Live Personal Task - Background Branch Only - 2026-10-17

Goal: make FX live and useful for personal use on a background branch while main stays archived at v2.1-archive. Flagship stays first at 45 percent. FX stays at 10 percent.

## Branch rule
- Work only on branch fx-live-personal, cut from main bb089f3 which includes v2.1-archive tag.
- Never push to main. Never move tag v2.1-archive. Push autonomously only to fx-live-personal.
- Merge to main only by human approved PR after ledger proof and test receipts.

## Hard guards
- Ledger append only. No UPDATE or DELETE on regime_calls or validation_log. Prove with counts plus hashes before and after.
- No production writes from test or repair scripts. No secrets in logs. Do not print .env.local values.
- No history rewrite. No force push. No new pairs. 3 pair lock stays.
- No paid evals. No product claims. No investment advice. Footer stays honest.

## Step 1 - Triage bugs to live
- List all failing checks: pytest baseline 379, web build, Supabase migrations 59 files, Prefect schedules, Vercel deploy, data fetchers FRED ECB MOF CFTC Yahoo SEBI.
- Fix in order: deploy blockers, pipeline crashers, data gaps, then accuracy items. Record each fix with file plus test.
- Target: pipeline runs end to end on background branch, site builds, latest calls refresh. Keep DEGRADED footer until it is truly green, then change to LIVE with date.

## Step 2 - First AI plus eval slice
- Add one LLM reader only. Input is frozen regime call plus brief. Output is 5 line analyst note with cited inputs. No new signals. No new pairs.
- Add eval harness beside it: faithfulness to ledger inputs, number accuracy per pair, Brier on conviction, versioned scores. Reuse flagship scorecard shape when it exists. Until then keep local JSON plus markdown report under reports/.
- AI calls only through pipeline/src/ai/client.py. Respect rate limiter. No keys in repo.

## Step 3 - Push autonomously to background branch
- Commit in small slices with receipts. Push to origin fx-live-personal after each green slice.
- Never auto merge to main. Open draft PR only when live plus eval slice is green with ledger delta zero on history plus only new rows appended.

## Step 4 - Document everything
- Update on background branch only: README status table, AGENTS.md counts, CONTEXT.md active repair section, HANDOVER.md operator status, MASTERPLAN.md phases, TASK.md current sprint.
- Mark main archive note intact. Record 6 root gates still open until each is truly closed with evidence. Do not mark VERIFIED RELEASE without live observation plus release receipts.
- Keep reports/REPAIR_CHECKPOINT.md style entries for each packet with test counts, SHAs, and hashes.

## Done means
- fx-live-personal runs, site builds from that branch preview, latest calls fresh, eval report exists for LLM reader.
- History intact plus new rows only. Test receipts recorded. Docs updated on branch.
- Draft PR to main exists with SHAs, counts, hashes, and deploy verify steps. Human merges.

## Non goals
- No v3 full scope. No Kalman, HMM, or real risk reversal in this slice unless pipeline is already green and receipts prove it.
- No rebrand of fxregimelab.com. No fund or MFE claims. Those stay superseded.
