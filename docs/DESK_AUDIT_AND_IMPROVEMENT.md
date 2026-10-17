# Private demo desk — audit, remediation and improvement contract

**As of 2026-10-18. Branch: `fx-live-personal`. Framework 1.1 / playbook 0.3.**

## Verdict

**Not ready for unattended execution.** The previous completion message overstated
enforcement: version strings do not prove specifications were read; score settings
were not an implemented adaptation engine; a passing test suite did not establish
execution readiness. This audit fixes local policy defects, not the entire broker loop.

No live account/order operation, production DB write, AI call, deployment, or expansion
of the execution universe is part of this remediation. Keep EURUSD/USDJPY only.
The owner's demo-autonomy authorization remains, but operational readiness is a
separate prerequisite. Until it is proved, autonomy means research and shadow proposals.

## Findings and disposition

### Critical — soft exposure veto allowed prohibited candidates

`pipeline/src/paper/checklist.py` previously scored same-USD exposure as S9; failure
merely reduced grade. `size_risk()` did not enforce that cap. Negative exposure selected
slots from the end of the tuple; an operator multiplier above one increased risk.

**Fixed:** invalid exposure/multipliers fail; caps block risk allocation even when the
candidate grade is otherwise acceptable. Wrong-side, zero, negative and nonfinite
prices, corrupt/cross-pair/out-of-order bars and invalid DQS fail validation. Missing
H1/H4 history fails the data gate. Failed bias/structure agreement caps grade at B.
This conservative boolean cap cannot distinguish neutral from contradictory structure;
typed three-state alignment is a subsequent research change.

### Critical — 15% open risk was incompatible with a 10% remaining daily budget

`paper/config.py` implied that a full 15% stop-out round stops at 10%. It does not:
an entry lockout cannot stop existing positions losing another 5% or more.

**Fixed policy:** `paper/admission.py` evaluates equity anchors, executable MTM,
residual stop loss, pending reservations, proposed risk and cost/stress reserve.
Each must fit BOTH the 15% aggregate cap AND remaining 10% daily/25% weekly capacity.
The stricter bound wins. Example: $10,000 day-start equity, $600 open stop risk and
a $500 proposal with $10 reserve is rejected ($1,110 > $1,000 daily budget).

UTC day/Monday-week anchors must be immutable and cashflow-adjusted by the caller;
open stop risk is additional loss from current marks (do not count MTM losses twice).
Stops and reserves cannot guarantee realized loss limits through gaps or disconnections.
**Still open:** broker reconciliation, atomic reservations, persistence and existing-book
emergency actions. Pure admission input booleans are not evidence of those systems.

### Critical — management and execution controls were described, not operating

`docs/DESK_TRADING_PLAYBOOK.md` directs two-leg orders, BE/trailing and settlements,
while its build list marks management/news/session/scorecard integration pending.
The generic `paper/store.py` ledger does not impose trading state transitions.

**Readiness blocked:** admission rejects unverified management, reconciliation,
input coverage, specification attestation, graduation, cooldown or non-demo status.
No runner currently calls this policy. A human/AI with unrestricted raw MT5 tools
can bypass it; a future executor must own the sole trading capability.

### High — risk groups were confused with broker tickets

One parent thesis has one initial risk budget. Child A and B each receive half;
they do not each receive 5%. Parent concurrency is 4, per-pair 2, same-USD-sign 2;
this implies up to 8 child tickets before reductions. Five new trades/day counts
parents. EURUSD-long + USDJPY-short both express short USD, not diversification.

**Clarified:** admission counts parents; checklist legacy `open_tickets` and
`same_usd_sign_tickets` now mean parent risk groups. No broker adapter exists yet,
so the parent/child mapping still requires integration tests. Reservations must cover
both children before sending either; second-leg failure cannot trigger blind retries.
Ticket-count heuristics are not substitutes for signed currency notional and stress risk.

### High — forming candle and mutable history threatened point-in-time validity

`paper/prices.py::Mt5BarFeed.fetch_bars` requested broker position 0.

**Fixed:** fetch starts at position 1; a terminal-free regression test proves the offset.
**Still open:** existing cache rows are not purged or reclassified; immutable decision
snapshots must filter completed bars, record acquisition time/revisions and verify
coverage. Server-time interpretation needs empirical UTC/DST verification. Confirmed
k=2 swings must not be used before the two confirming bars close in historical replay.

### High — asymmetric points were mistaken for learning

The 4-points-per-winning-R / 6-points-per-losing-R policy is an owner preference,
not a statistically optimized objective. It conflates luck, opportunity and model skill.
At 60% +1R/-1R wins, expected points are zero even before clipping (4×0.6−6×0.4),
despite positive gross trade expectancy. Starting a new model at 100 reset accountability.

**Implemented:** `paper/operator_score.py` replays whole-parent settled net R,
deduplicates events, tracks counts/net R and optional binary Brier loss separately,
and carries desk safety history across operators. Incident restrictions and pauses latch;
profitable bets cannot remove them. No automatic remediation/reset endpoint is exposed.

**Limits:** event authenticity, chronological ledger adapter, frozen initial R, net-cost
settlement and pre-outcome probability capture remain integration work. The function
cannot verify facts supplied by a caller. An empty history is untested, not skill.
This changes external permissions/context, not the foundation model's weights.

### High — research coverage and supported claims were not validated

`paper/checklist.py` accepts caller-supplied session/news flags. "No search result"
was too easily interpreted as "news clean". A citation token is not claim entailment.

**Implemented contract:** `paper/evidence.py` checks intraday-news publication ≤ retrieval
≤ decision, 4h freshness, explicit coverage, known citations, three cases/falsifiers,
operator identity, source-content and feature/spec hash references. It returns a packet
digest. It performs no web fetching or AI inference. Source-domain diversity is only
a coverage heuristic: two domains may syndicate the same story. Historical macro
context belongs in a separate point-in-time feature snapshot, not this 4h news gate.

**Still open:** authoritative feed collector, archived original content, exact calendar
coverage, claim-level grounding, document hash loading/acknowledgment and freshness expiry.
Never use the public macro-calendar approximate fallback dates for trading blackouts.

### High — hidden production writes in the default AI path

The default chain in `pipeline/src/ai/providers/chain.py` calls
`writer.write_ai_request()` after a provider succeeds. The reader's no-production-write
claim is therefore false transitively. `scripts/run_live_personal.py` runs the production
pipeline, not a read-only private desk.

**Blocked, not fixed here:** do not use those defaults for desk inference. Add an explicit
local telemetry/budget adapter through `ai/client.py`; use read-only production data
credentials. Do not patch shared provider behavior casually. Production DB writes remain
centralized in `db/writer.py`; this change introduces no DB writes. Existing private
SQLite storage is unchanged.

### High — replay/evaluation evidence needs its own remediation

Review identified these separate pipeline issues; they are NOT fixed in this desk patch:

- `backfill/simulation_engine.py` passes one COT row where `signals/cot.py` requires two.
- Replay beta inputs omit date/spot needed by `regime/composite.py`; fallback zeros can result.
- Historical special inputs reuse current-date macro kwargs; vintage/release joins missing.
- `tests/test_simulation_engine.py` uses a 60-bar fixture while replay skips its first 60
  positions; comparisons can pass with empty outputs.
- `eval/llm_reader_eval.py` citation/format checks do not establish semantic faithfulness;
  its Brier input is signal confidence, not necessarily the responding LLM's forecast.

These require separate impact-audited pipeline changes. Until parity is proved, do not
promote desk strategies based on those replay outputs or label reader metrics semantic
faithfulness. No public pipeline code was changed by this audit.

### High — setup rules are still assertions, not implemented strategy detectors

`strategy_rule_fires`/`trigger_present` are supplied flags, not computed SU1–SU4 signals.
The SU4 B-grade/half-slot restriction and setup-specific falsifiers are not automatically
enforced by the generic checklist. No setup is graduated by writing its description.
Keep strategy admission false until versioned detectors, setup-specific constraints and
forward-only validation exist. The new research contract validates structure/provenance,
not economic truth, source independence or profitability.

## Better reasoning: evidence before persuasion

Use a short structured decision record, not demands for longer private reasoning:

1. **Frozen observation:** decision time; account/demo identity; completed-bar snapshot;
   live model/version/DQS; calendar/news coverage; specification and feature hashes.
2. **Deterministic calculations:** ATR/EMA/confirmed swings; pip/tick value; conversion;
   stop-side/distance; measured spread/commission/slippage; parent and child volumes;
   volume-step rounding; margin; leverage; signed currency exposure; loss capacity.
3. **Hypothesis:** registered setup/version, market regime, entry trigger, invalidation,
   expiry, expected payoff/costs, explicit bull/bear/wait cases and cited falsifiers.
4. **Adversarial check:** strongest contrary evidence, missing facts, freshness and
   source conflicts. The verifier can veto; it cannot invent a higher grade or risk.
5. **Independent policy:** grade eligibility then admission; unknown readiness blocks.
   Research text has no authority to edit limits or place an order.
6. **Receipt:** concise factual rationale, failed checks, rejected alternatives, action,
   parent/child IDs, operator/provider/model/prompt versions, hashes and expiry.

Treat fetched text as untrusted data. Headlines cannot issue tool instructions.
Separate model identity, signal model version and deterministic fallback identity.
Cache only by immutable snapshot/config/prompt hashes, not pair/date alone; account
state/calendar freshness changes invalidate execution eligibility.

## Better rewards: three separate ledgers of evidence

- **Process:** false facts, missing receipts, limit bypass, widened stops, missed exits
  and tampering are serious incidents independent of whether the trade made money.
- **Outcome:** parent-level net R, drawdown, tail loss, MAE/MFE, holding time, costs,
  fill quality and opportunity-adjusted returns. Never reward a partial close before
  the runner settles or let wider stops alter the original R denominator.
- **Prediction:** optional probabilities for a PREDEFINED event/horizon, captured before
  outcome; evaluate Brier/reliability against a fixed baseline on identical opportunities.
  Checklist grade is eligibility, NOT a calibrated win probability. Do not use arbitrary
  loss-weighted points as a proper probability score.

Keep the asymmetric owner points as a conservative permission heuristic. Evaluate operators
on the same frozen candidates at equal shadow risk, with model/prompt/version tags. Do not
reward trade frequency, target proximity, dollar PnL from bigger risk or hiding bad trades.
A legitimate no-trade has no fabricated PnL reward; track coverage/abstention separately.
Live permissions depend on global safety plus validated evidence, not a model leaderboard.

## Better adaptation: a controlled experiment, not weekly curve fitting

1. Log ALL candidates and rejected opportunities before outcomes. Hard-gate pass/fail
   predictiveness cannot be inferred from executed trades: all executions passed.
2. Register hypothesis, parameters, cost model, regime scope, falsifier and trial budget.
   SU1–SU4 are hypotheses, not established profitable strategies; SU-R1 stays research-only.
3. Fit on past data; walk forward with purged overlap/embargo for T+5 labels. Freeze a
   chronological holdout and count every trial; do not repeatedly retune on the same holdout.
4. Evaluate expectancy after measured costs, drawdown/tail loss, stability by regime and
   pair, and paired differences against simple baselines. Use dependence-aware/block
   confidence intervals; children/overlapping trades are not independent observations.
5. Shadow the challenger with identical inputs/risk. Promote only with evidence and written
   review; insufficient sample means continue collecting, not auto-promote or auto-kill.
   Forty trades is not a universal statistical sufficiency rule.
6. Monitor drift, data failures and process breaches continuously; reduce/pause immediately.
   Review strategy changes weekly but apply only when evidence gates pass, with versioned
   rollback. Never change a live trade's entry assumptions or initial risk retrospectively.

The +50% weekly target remains a reporting objective. It does not enter reward multipliers,
override loss budgets, induce extra trades, or justify an unsupported strategy. More risk
does not produce more independent samples. No return or profitability guarantee is claimed.

## Ordered completion gates

1. Local policy tests and honest specs — this remediation.
2. Authoritative news/calendar + immutable completed-bar/spec/feature snapshots; local-only
   AI telemetry and budget; semantic grounding evaluation.
3. Parent/child trade state machine, account allowlist, atomic reservation, broker reconciliation,
   executable sizing/conversion/margin and idempotent partial-failure recovery.
4. Persistent management/watchdog and net-cost settlement; prove missing-SL, second-leg
   rejection, stale tick, disconnect, restart, partial fill and duplicate-retry scenarios.
5. Strategy replay parity, nonempty tests, walk-forward validation and graduated shadow run.
6. Only then connect demo execution; then operator-score/ledger replay and champion/challenger
   improvement. Live money and additional symbols remain separately gated.

## Sources and verification

Research retrieved 2026-10-18 using Exa via Agent Reach routing and Chrome read access:

- Gneiting & Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*:
  https://doi.org/10.1198/016214506000001437 — proper scores encourage honest probabilities.
- Bailey et al., *The Probability of Backtest Overfitting*:
  https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf — selection across many trials
  needs controls; a reused holdout does not establish an edge.
- DeepMind, *Specification gaming: the flip side of AI ingenuity* (2020):
  https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/
  — proxy rewards can be optimized without achieving the intended goal.

Policy thresholds in this repo are engineering/owner choices, not thresholds prescribed
by those papers. The research does not substantiate the desk's weekly return target.

GitNexus impact attempts failed (database format 42 vs runtime 40); risk therefore UNKNOWN,
not zero. Manual reference search found checklist/levels callers confined to the paper
module and tests, plus bar ingestion via `desk_prices_sync.py`. Shared AI/replay/calendar
findings were intentionally not edited. Re-run graph impact when tooling is repaired.

Regression tests were added and observed failing before remediation (16 checklist cases,
forming-bar offset and invalid-level window); new-module tests first failed imports.
Final validation results are recorded in TASK.md and the delivery summary.

Final checks: **478 pytest passed**; Ruff passed; mypy passed (230 source files);
Biome passed (206 files); production build passed (existing metadataBase/edge-runtime
warnings). A deliberate same-USD-cap boundary mutation caused its regression test to
fail, and the correct boundary was restored before final validation. These checks
prove the tested local behavior, not broker integration or trading profitability.
