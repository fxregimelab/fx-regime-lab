# PD delivery DAG and owner runbook

## Operating rules

One worker, one packet, one owned file set. Start on `fx-live-personal` at a
verified clean/understood revision; never main. Treat input documents as pinned
requirements, not permission to rewrite the evaluator. Existing AD task labels
are not proof of implementation: confirm actual interfaces and receipts first.

Lifecycle: needs-binding -> ready -> claimed -> candidate -> independently
reviewed -> accepted. BLOCKED/REQUEST_CHANGES are successful honest reports,
not accepted implementations. No automatic successor from an agent summary.
Limit two concurrent read-only specialists and one code writer; stop after
three unsuccessful repair iterations or 45 minutes. Save evidence and escalate.

For existing symbols run GitNexus impact before editing. At this checkpoint
graph queries fail with LadybugDB 42/40 mismatch; risk is UNKNOWN. List direct
callers manually and obtain reviewer disposition; do not claim no impact.
Do not rebuild or upgrade a shared index in another session's environment.

Every code packet requires observed red regression, green focused test,
Ruff/mypy, phase regression checks, diff/secrets review and independent review.
Use temp databases/fakes; tests must deny broker/model/production DB effects.

## PD-00A — Calendar source window and policy adjudication

Status: source-window repair READY; blackout policy decision BLOCKED pending
explicit precedence review, not guessed by a worker.

Reads: `paper/calendar.py`, `tests/test_ad_calendar.py`, AD data/execution specs,
`docs/DESK_TRADING_PLAYBOOK.md` red-event rule, current authority/version pins.
Writes: only `pipeline/src/paper/calendar.py`,
`pipeline/tests/test_ad_calendar.py` after impact/caller review.

Required cases: source honours EXACT requested interval and returns only events
inside it; prior red release 90min ago must be observable for a 2h post-release
blackout; verify exact boundaries and latest revision handling; event 90min in
future exposes -15min versus -2h policy conflict. Fix collection lookback to
cover the active rule, with matching receipt validation and tests. Do not claim
calendar integration ready until documented policy, code and version pins agree.
Preserve existing stricter owner constraints pending adjudication; report conflict.

Command from pipeline: `.venv\Scripts\python.exe -m pytest tests/test_ad_calendar.py -q`.
No real feed entitlement or broker access is needed/proved by these tests.

## PD-00B — Structural execution-price and horizon repair

Status: READY after baseline/impact; independent of macro collection.
Reads: `backtest/engine.py` `simulate_trade`, its direct callers and
`tests/test_paper_backtest.py` if present (discover exact current tests first),
AD execution management/horizon rules.
Writes: `pipeline/src/paper/backtest/engine.py` and NEW
`pipeline/tests/test_payoff_engine_regressions.py`; no report regeneration.

Red oracles: long entry100/stop99/gap-open98 must lose 2 price-R before costs;
mirror short gap; a one-day research horizon cannot settle at input's 50h
close; appending post-horizon bars cannot change settlement; partial fractions
and original-risk denominator preserved; final bar/censored path explicit.
Bind broker-session T+5 semantics separately; calendar-day research horizon is
not certified as trading-session T+5. Do not hide the mismatch by relabelling.

Command: `.venv\Scripts\python.exe -m pytest tests/test_payoff_engine_regressions.py -q`.
Successor PD-00C stays closed until all regression/caller checks accepted.

## PD-00C — Event-time and joint portfolio replay

Status: needs-binding after PD-00B. Reuse existing engine records; do not create
another private ledger. Expected scope: structural `run_backtest` plus joint-pair
driver and focused replay tests; exact files/subtasks bind after interface review.

Required evidence: pending exits do not affect equity/last-stop before exit;
chronological stable event ordering; overlapping pair entries share global caps,
USD-sign exposure and loss capacity; identical timelines reproduce; no futures
fund earlier trades; restart/replay uses immutable R. Same-timestamp ambiguity
must be explicitly conservative. This task proves feasible replay, not an edge.

## PD-01 — Payoff mathematics, first small-model packet

Status: READY for offline development after the package is accepted. This pure
math slice does not depend on the defective structural simulator.

Owner: `desk-builder`; reviewer: fresh `desk-auditor`.
Reads: mandate money definitions and payoff-study hand oracles; existing
`RiskBreakdown`/settlement contracts and tests to avoid unit collisions.
Writes: NEW `pipeline/src/paper/backtest/payoff.py`,
NEW `pipeline/tests/test_payoff.py` ONLY.

Interfaces to implement with Decimal/pure functions (no I/O):
- compute gross/net price-R and all-in parent-R from G, frozen A, fractions,
  fills and actual/scenario costs; return all named units distinctly;
- solve minimum runner price-R for planned net parent-R, including partial;
- explicit validation of finite inputs, G>0, A/cost>=0, fractions 0..1 and
  quantity sum; reject impossible runner fraction, don't return infinity;
- no mutation of initial risk or implied guarantee that targets are reachable.

Red oracles: 0.5 at1 + 0.5 at3 =2 price-R; at5 =3 gross; G100/A10/cost10
needs runner5.8 to achieve3 parent-R; runner5.2 fails3 parent-R; zero fractions,
100% partial, negative costs, NaN, empty fills, long/short normalized symmetry.
Test costs once per actual fill and define inputs to avoid entry double-count.

Commands: `.venv\Scripts\python.exe -m pytest tests/test_payoff.py -q`,
`.venv\Scripts\python.exe -m ruff check src/paper/backtest/payoff.py tests/test_payoff.py`,
`.venv\Scripts\python.exe -m mypy .` from pipeline. Runtime integration is NOT
part of PD-01. A module returning plausible numbers without unit oracles fails.

## Later stages — needs-binding, not executable packets yet

- PD-02: align typed PayoffPlan/PathOutcome with existing AD schemas and policy
  versions; no duplicate denominator. Needs PD-01 and authority reconciliation.
- PD-03: identical-entry M0–M3 management study with intrabar ambiguity and lot
  steps. Needs PD-00B/C, PD-02 and exact M3 definition. Match full desk policy.
- PD-04: pair-context source adapters with PIT consensus/vintages and coverage.
  Needs real source entitlement; web articles are not a feed provision.
- PD-05: bounded grounded analyst + challenger, private AI budget/telemetry.
  Needs existing AD-T12 isolation seam AND actual durable private policy; the
  test-double budget is not runtime enforcement. All AI via ai/client.py.
- PD-06: matched ablations and new forward registration; embargo already-viewed
  history from any claim of untouched final evidence. Protected AD evaluation
  thresholds remain unchanged; propose changed lower-frequency graduation to owner.
- PD-07: bind remaining AD risk/permit/execution/recovery/management/watchdog/
  settlement tasks to accepted evidence. Only then operational shadow, canary,
  demo graduation. No shortcut from a backtest or 3R target to order permission.

Each later packet must name actual start commit, dependencies, file ownership,
interfaces, red/green commands, resource budget and rollback before dispatch.

## Handoff receipt

Use existing AD spec06 receipt fields, adding unit convention and model route:
task/spec hash; branch/start commit; dependencies; pre-existing changes; files;
red tests with expected/actual failures; green command/working-dir/exit/log refs;
impact/manual callers; actual model/provider; assumptions; side effects;
independent reviewer/findings/disposition; PASS/BLOCKED/REQUEST_CHANGES.
No secret/raw provider headers/full licensed article in a receipt.

## How the owner uses sessions

Keep this coordinator/auditor session. Open one fresh worker session on the SAME
project (or a reviewed isolated worktree when separate ownership is needed).
Send: "Use desk-builder and desk-worker for PD-01 in
docs/specs/payoff-desk/05-delivery.md. Read current authority/index, bind HEAD,
implement only its two new files, run its checks, return the receipt, then stop."
Send the resulting diff/receipt to `desk-auditor` with the original spec hash.
Do not run two code writers in the same tree. No full-chat dump is required.

Model shortlist verified in OpenCode catalog on this date: MiniMax
`opencode/minimax-m3.1-flash-free` for bounded extraction/worker trials; GPT
`opencode/gpt-6-luna` for a possible economical code route ONLY if Go coverage
or spend permission is verified; strong inherited model for architecture/review.
No model choice has a proved local quality score yet. Definition files use the
free route for low-risk tasks, inheritance for high-judgment review; no paid
route or DeepSeek is pinned. Rate-limit failure => BLOCKED; no silent paid fallback.
Verify actual route at launch; discovery/catalog presence is not entitlement.

Development agents have no broker/model-runtime privileges. Shell commands need
approval, not blanket wildcard execution. Installing definitions is not a sandbox
for any tool permitted elsewhere; inspect effective permissions before a live task.
Read paths are limited to named root instructions, documentation, source/tests,
research reports and local skills (auditor also reads agent definitions). Glob
and content-search tools are deliberately disabled; the coordinator supplies
file inventories. This prevents a grep route around secret-file read exclusions.
Workers may request a scoped source-search command through ASK-shell review;
that is not permission to search raw configs, credentials or private databases.
