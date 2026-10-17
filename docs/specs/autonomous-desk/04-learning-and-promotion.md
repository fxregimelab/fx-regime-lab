# AD specification 04 — Autonomous learning, experiments and promotion

**Provider contracts:** evaluation/evolution. Automatic demo promotion is owner-authorized.
The research model cannot change this evaluator, its trial budgets or the hard safety
manifest. “Self-improvement” here means evidence-backed artifact selection, not guaranteed
profitability, consciousness, or automatic foundation-model weight training.

## 1. Exactly what can evolve

An artifact is canonical data: `artifact_type, parent_digest, primitive_version,
parameter_values, prompt_digest, feature_version, management_policy_version,
scope, created_at, rationale_refs`. Reject arbitrary executable expressions, imports,
Python/SQL, shell commands, network destinations, file paths and unknown keys.

V1 allowlisted variants, each a NEW registered experiment:
- SU1 pullback lookback {4,6,8} H1 bars, touch band {.15,.25,.35}ATR.
- SU2 sweep depth minimum {.05,.10}ATR, maximum {.35,.50}ATR; retest expiry {2,4} M15 bars.
- SU3 breakout lookback {20,30,40}H1; breakout margin {.10,.15,.20}ATR;
  retest expiry {4,8}M15 bars.
- SU4 range window {24,36,48}H1; edge tolerance {.15,.20,.25}ATR; neutral-only/B cap
  and half-risk constraint immutable. Its often-below-floor risk means legitimate skips.
- Shorter holding expiry {4h,8h,one broker session}; never lengthen an existing parent.
- Prompt candidate limited to explanatory/ranking/abstention instructions with the same
  required schema/facts/clauses; no change to tool access, hard gates or safety language.
- Model choice among a locally provisioned allowlist with measured entitlement/cost;
  model/provider/fallback change invalidates previous prompt-quality certification.

Frozen in v1: ATR/EMA definitions, risk percentages/grade mappings/slot logic, event
blackouts, source allowlist, release criteria, score coefficients, stop widening ban,
protected management formulas, broker capability and feature/evaluator implementations.
New primitives, feature math or management algorithms require reviewed development,
not unattended artifact promotion. Expanding a tunable range requires owner policy change.

The system can discover and write broader ideas into a research backlog, including
relative value/stat-arb, without treating them as deployable artifacts.

**V1 eligibility restriction:** SU4 remains shadow/research only. Its mandatory B cap
cannot satisfy the initial A/A+-only demo canary, and .25canary scaling usually falls
below the1% floor. Implement/test its detector and research variants, but return
`CANARY_GRADE_INELIGIBLE` for activation. Do not lift its cap or risk to force promotion.
A future owner-reviewed canary-policy revision is needed for SU4 demo graduation.

## 2. Three measurements, never one “intelligence score”

**Process safety:** verified receipt/evidence/cap compliance, unsupported facts, missed
protective actions, duplicate sends, late exits and tampering. A lucky profitable breach
remains a breach. Security/evaluator tampering is a hard latch, not a finite point debit.

**Trade utility:** fully settled parent net R; +4 points per +1R capped +12/trade,
−6 per −1R floored −18/trade, −20 process breach, −15 daily kill. These are arbitrary
owner preferences, not proper forecast scores. Preserve uncapped net R, costs, drawdown,
tail loss, MAE/MFE and holding duration for actual analysis. Starting score100 is untested.
Score history global to desk across model changes; per-model views are descriptive only.
No points for an unclosed runner, target proximity, trade frequency, bigger risk or a
synthetic backtest win. Rejected/no-trade opportunities are retained without fake PnL.

**Prediction quality:** optional forecast for a fixed registered binary event, captured
before outcomes. V1 event: whether the fixed reference execution/management plan yields
strictly positive net parent R by its declared expiry. Define transaction-cost handling,
no-fill exclusion and unresolved labels before evaluation. Include forecasts on abstained
opportunities using the same counterfactual reference; report missing forecast coverage.
Binary Brier=(p−y)^2; report n, baseline and calibration bins. Never interpret 9/9 checks
as p=1 or asymmetric points as calibrated confidence. Unresolved outcomes are not losses
or wins; late labels cannot be moved between evaluation sets to favor a candidate.

The existing `replay_score()` handles verified ordered events only. AD-T20 supplies the
settlement adapter, dedupe/correction behavior and durable restriction state. A score below
60 or process-breach latch remains until authenticated owner remediation. Automatic
rollback/promotion cannot reset it. Ordinary profitable losses are not evidence of misconduct;
postmortems distinguish valid loss, bad hypothesis, input failure and implementation fault.

## 3. Experimental identity and lineage

Register before any evaluation: hypothesis, artifact/parent digests, changed fields,
source regime/pair scope, declared outcomes, fixed baseline, candidate-independent
opportunity rule, costs/stresses, windows, seeds, primary metric, practical margin,
trial/epoch ID, sample endpoint, stopping rule and success/failure rules.

One challenger in final evaluation at a time. Maximum20 registered variants per28-day
research epoch, including failed/abandoned variants and prompt/model/parameter changes
informed by prior outcomes. Duplicate bytes cannot get a fresh budget under a new name.
Changing data eligibility, baseline, metric or primary endpoint is a new experiment.
The evaluator owns partition access; researchers cannot inspect protected final outcomes.

Historical model-known periods and developer-visible folds are development evidence,
not pristine future proof. Separate cohorts: reconstructed/backfill, live historical,
forward shadow and broker demo. Costs, data holes and unavailable vintages are reported;
missing macro context never filled with current observations.

## 4. Development validation before final holdout

Fix historical replay parity first: COT minimum observations, dynamic-beta date/spot
schema, historical macro kwargs and publication/vintage joins. Positive fixtures must
produce real signals and trades; empty-versus-empty comparisons never pass.

Default development split: 126 completed trading days training, next21days validation,
rolling forward for4 non-overlapping validation folds, each with nonempty opportunities.
Sufficient history for each fold is mandatory; no reducing windows until green.
If developer/model uses fold results to select a variant, those folds remain DEVELOPMENT,
not the final promotion test. Log all configurations inspected.

Purge observations whose outcome intervals intersect evaluation intervals. Embargo uses
timestamp intervals through the registered maximum horizon (up toT+5), not a fixed row
count. Every training set is strictly prior to evaluation; no random train/test shuffling.
Frozen reference costs include actual spreads/commissions/swaps and adverse execution.
If same-bar target and stop are both possible from OHLC without tick order, use adverse
ordering or mark ambiguous; never automatically choose the profitable path.

## 5. Common opportunities and paired portfolio measurement

Opportunity stream comes from specification02, before either strategy decides. Candidate
and champion get identical frozen source/feature snapshots and timeouts. Preserve waits,
gates, signal absence, API failures and skipped sizes. A candidate cannot select only its
winning opportunities into the paired denominator.

Replay each system as a portfolio under identical fixed **1% reference risk per parent**,
same exposure/entry-count/cost constraints and initial equity. Account for two child orders
as one parent. For a no-trade opportunity assign zero policy PnL, not missing data.
Do not normalize by executed trades alone. Opportunity-level net R is diagnostic;
primary endpoint is paired DAILY reference-portfolio return difference (candidate−champion).

Baseline is the registered, deployable current champion with frozen configuration. At
cold start use a preregistered deterministic SU1 reference artifact, not whichever baseline
looks worst after the test. Cash/no-trade zero return is an additional benchmark.
Positive candidate net expectancy is required: outperforming a losing reference alone
is insufficient. Changing champion/baseline invalidates an in-flight comparison unless
the baseline was already frozen for that experiment; activation still compares lineage.

## 6. Forward final test and fixed endpoints

After selecting ONE frozen challenger, begin new forward shadow data not used for tuning.
Registration sets one exact decision endpoint, not “extend until significant”. Evaluate
the sealed window only after that fixed endpoint and all its declared labels mature.
If the window ends short of required evidence, COLLECTING has no PASS; a fresh
preregistered future window needs a new trial budget. Do not keep adding favorable days.

Preregister window length before it starts: initial150 broker trading days (30 blocks
at default5days), candidate/benchmark matched opportunities≥100, candidate settled parents
≥80, ≥20 active trading days, full label maturity through declared horizon. These are
minimum sufficiency screens, not proofs of power or independence. They can make first
promotion slow; the system remains shadow rather than manufacture evidence.

Block length fixed using training data only: ≥5 trading days or registered max holding
horizon if larger; increase for measured longer training dependence. Require≥30 complete
blocks. Preserve candidate/baseline pairing and cross-pair USD dependence. Day blocks
are dependence approximations, not magically independent because a variable says so.
An artifact with shorter maximum holding cannot shorten protected block rules on its own.

Only one final superiority test per registered candidate. Interim inspection may stop for
safety/data failure but cannot establish PASS. Final endpoint failure is REJECT, not
permission to add days/retest the same configuration until it wins. Delayed computation
after a frozen endpoint may resume on the same sealed data; it cannot add observations.

## 7. Multiplicity, uncertainty and exact PASS rules

Protected lifetime error-spending schedule: research epoch e=1,2,... receives
`alpha_epoch=.05/(e*(e+1))`; each of20 slots gets `alpha_candidate=alpha_epoch/20`.
Unused slots never replenish the budget; restart/model rename cannot reset e. This
controls repeated selection only to the extent the underlying statistical tests are valid;
dependent nonstationary market data and bootstrap approximation remain limitations.

Primary practical improvement margin δ=.0001 reference-portfolio return/day (1bp/day),
chosen as an engineering minimum, not a claimed alpha estimate. Fixed-block bootstrap
on paired daily returns, seed sealed at registration, produces a one-sided percentile
lower bound at alpha_candidate. Report exact algorithm/version, number of blocks,
effective dependence diagnostics and resampling Monte Carlo precision.

Require `B * alpha_candidate >= 1000` tail replicates; B is fixed before execution.
For e=1, alpha=.00125, so B≥800,000. Do not use10,000 replicates and claim extreme-tail
precision. Stream batches under compute budgets; resume deterministically on sealed data.
Insufficient precision/compute/data → COLLECTING/INSUFFICIENT_PRECISION, never reduce
the threshold. More replicates do not repair inadequate independent market observations.

PASS requires ALL:
1. Artifact/schema/lineage/permissions valid; zero hard safety breaches; all contract tests.
2. Source completeness, no leakage, sealed partitions/trial budget and sample minimums pass.
3. Paired lower bound candidate−champion >δ (not merely positive point estimate).
4. Candidate mean net return >0 versus cash; under doubled measured spread/slippage plus
   commission/swap, candidate mean return remains >0. Stress scenarios frozen before test.
5. At1% reference risk: max equity drawdown≤10%, worst daily loss≤5%, worst weekly≤10%,
   no portfolio/horizon violation. These stricter research-graduation screens do not replace
   the owner's separate demo hard ceilings; they cannot be evolved away.
6. Executed shadow actions deterministic/reconciled, no fabricated fills, all costs included;
   verified model outputs meet schema/claim grounding requirements in section8.
7. Protected evaluation service issues signed certificate binding exact artifact/policy/build/
   data/partition hashes. Model prose or a test log cannot self-certify.

Result states: INVALID for corrupt/leaked/ineligible evidence; COLLECTING for missing,
unmatured or insufficient-precision evidence before a valid frozen evaluation; REJECT
for safety failures or a completed endpoint failing gates; PASS only when every gate passes.
Weekly reporting cadence/return target does not trigger extra significance tests.

## 8. AI reasoning/model improvement gates

Build a fixed held-out case suite with source-grounded truth labels: correct claims,
unsupported numbers, stale revisions, source conflicts, prompt injection, unknown calendar,
valid no-trade, pair-specific macro differences and deterministic fallback behavior.
Use ≥100 labelled cases with ≥10 each of injection, stale-data and unsupported-number
cases. Critical schema/permission/injection/numeric-grounding violations must be zero.
All required facts must be either correctly cited or explicitly unknown; unsupported
assertions fail even if citation tokens appear elsewhere. Pin grader version and ground
truth; an LLM judge alone cannot grant safety PASS.

Compare prompts/models on identical case/opportunity sets, actual responding identity,
fact precision/coverage, abstention quality, latency, token and dollar cost. Predeclare
non-inferiority of grounded correctness (no lost critical cases) and ≥10% reduction in
median billed cost OR a registered primary reasoning-quality improvement. Trading
promotion still needs the final portfolio evaluation; formatting alone is not alpha.
Cache by input/spec/prompt/model/tool digests; provider fallbacks are separate artifacts.
No runtime model weight fine-tuning in v1; retrieval adds verified incident/evidence
summaries, not unreviewed self-authored “lessons” as facts.

## 9. Promotion, canary and rollback

Artifact lifecycle: `DRAFT -> REGISTERED -> DEVELOPMENT -> FORWARD_SHADOW ->
CERTIFIED -> DEMO_CANARY -> ACTIVE -> RETIRED`; INVALID/REJECTED/REVOKED are explicit.
Only trusted evaluator moves to CERTIFIED; only control-plane activation moves versions.

Before first demo canary, all operational graduation tests must pass (spec07), authority
identity must match and watchdog is healthy. Canary factor .25, A/A+ only. Keep1% risk
floor; if factor×slot×grade is below1%, skip rather than lift risk. Existing owner/operator
restrictions can reduce further or block all entries. Canary minimum10 fully settled
parents across≥5 broker trading days with zero integrity/protection/incapability incidents;
loss budgets still apply. Negative expectancy/drift leads back to shadow, not more risk.
After canary passes the registered rules, automatically activate full allowed envelope;
no additional per-promotion approval is required. Report the activation receipt to owner.

Activation transaction compares expected current champion digest, verifies certificate
and live readiness, appends activation and swaps one pointer atomically. In-flight parents
retain old artifact/management. Another worker cannot activate concurrently under an old
fence. Any changed byte invalidates the certificate; atomic file rename alone is not enough.

Certificates authorize new activation for7calendar days. If canary completion is later,
trusted service may issue a renewal attestation referencing the SAME immutable statistical
result/artifact, plus current healthy canary/readiness/drift evidence. It must not rerun or
select a better statistical result on the same holdout. Renewals are not new evidence of
superiority; they preserve result lineage and require current operational validity.

Rollback triggers immediately for safety/identity/input integrity. Performance monitor:
after at least20 settled parents under new artifact, trailing20 net expectancy<−.25R or
reference-equivalent peak-to-trough drawdown>5% disables new entries and opens review.
This is a conservative shutdown heuristic, not a statistically certified drift detector;
it cannot automatically promote another untested variant. Restore last still-certified
nonrevoked compatible artifact; none valid→shadow. Never clear operator/owner/integrity
latches or rewrite existing plans during rollback.

## 10. Autonomous postmortem and memory update

After settlement/incident, deterministic extraction produces outcome facts and residuals.
Research model writes a structured hypothesis: error class, supporting facts, competing
explanation, proposed bounded change, falsifier and required experiment. “I lost, therefore
reverse direction” is not a validated lesson. Memory records distinguish verified fact,
unresolved hypothesis, rejected hypothesis and superseded result with lineage.

Nightly review can register experiments within budget; weekly review reports actual
return versus +50% target, score/risk usage, research progress and all rejected candidates.
No guarantee of weekly improvement or forced trade/promotion deadline exists. Automatic
operation includes the decision to collect more data, preserve a champion or stay paused.
