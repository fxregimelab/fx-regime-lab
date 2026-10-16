# FX Archive Close Task - Frozen 2026-10-17

Goal: finish and archive FX Regime Lab. Archive ready, not perfect. No v3.

## Canonical checkout
- Canonical: D:/Projects/fx-regime-lab, branch Shreyash3007/fix/audit-staged-v2-fixes, 3 commits ahead of origin/main.
- Parked: D:/Projects/fxregimelab, branch codex/frontend, dirty repair tree. Do not merge wholesale.

## Scope freeze
- Freeze at packets 30/31 locally accepted per reports/REPAIR_CHECKPOINT.md 29 Sep 2026.
- 6 root gates stay open and recorded. Do not start new packets to close them.
- 45 item register stays as is. None has VERIFIED RELEASE status. Keep it that way.

## Hard guards
- No rewrite of regime_calls or validation_log history. Append only. Prove with before and after row counts plus hash sample.
- No force push to origin/main. Rebase fix branch onto origin/main, normal PR merge only.
- No production writes from repair scripts. No secrets in logs. Do not read .env.local values into output.
- No new features. No calibration, Kalman, HMM, or risk reversal changes in this task.

## Steps
1. Inventory origin/main..HEAD in fx-regime-lab. List the 3 commits and files touched.
2. Review fxregimelab dirty tree. Select only ledger safety plus keep alive items. Stash rest as bundle under D:/Projects/_history-bundles with date, do not commit to main.
3. Rebase fix branch onto origin/main. Resolve Vercel ignore anchor plus Supabase idempotent constraint cleanly.
4. Run baseline: committed pytest baseline per AGENTS.md. Record pass counts. Record full pipeline receipt only if already green. Do not invent numbers.
5. Prove append only: row counts for regime_calls and validation_log before and after, plus sample hashes.
6. Prepare merge to main plus tag v2.1-archive. Stop before deploy. Report SHAs, test receipts, and exact deploy command for human approval.

## Done means
- One main with history intact, tag v2.1-archive proposed.
- Site loads from canonical checkout. Footer still honest. README archived banner drafted but not pushed until approved.
- Repair parked as bundle. 6 roots recorded open.
- Report back with SHAs, counts, and ready to deploy note. No deploy without explicit human go.

## Non goals
- No v3. No fund or MFE framing changes in this task. Those doc patches are separate.
- No paid evals. No product launch.
