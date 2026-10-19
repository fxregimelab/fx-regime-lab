# Private desk audit — payoff-first revision

2026-10-19. Read-only strategy investigation at `d9c31ee`, followed by a
documentation/development-agent installation. Scope: private strategies, evidence,
management, readiness and handoff. Not a public methodology audit, live account
inspection or profitability certification. No DeepSeek calls or broker orders.

## Verdict

**Research/shadow only.** Preserve useful infrastructure, repair measurement,
then test macro-aware and payoff-management hypotheses. Neither current technical
research nor additional agents establishes the intended complete desk's edge.
The earlier price-only failure does not prove macro-informed trading impossible.

## Strategy inventory (current source, not old task checkboxes)

- SU1 pullback/reclaim: implemented `pipeline/src/paper/strategies.py:196–331`.
- SU2 sweep/reclaim: detector exists `strategies.py:334–465`; textbook geometry
  conflicts with unchanged stop floor; `tests/test_ad_strategies.py:1–8,327`
  acknowledges this. Not a demonstrated executable positive setup.
- SU3 breakout/retest: implemented `strategies.py:468–592`.
- SU4 neutral rotation: specified in AD data spec lines175–190, no detector in
  the current SU1–SU3 dispatcher (`strategies.py:595–606`).
- SU-R1 relative value: research-only in strategy framework lines90–98; no fitted
  spread/hedge/stationarity/paired execution implementation found.
- Legacy source cohorts S0–S6: planning definitions, not a complete scanner.
- Dense: implemented 30 price/time/tick-volume features, separate fits per pair,
  causal/purged walk-forward and fixed-exit labels (`backtest/dense.py:47–126,
  475–559,634–808`). Not a macro or complete management backtest.
- Rules: implemented London breakout/mean reversion/momentum baselines,
  `backtest/rules.py:61–215`, using the fixed-exit simulator.
- Structural management simulator: `backtest/engine.py:336–489`; not a runtime
  manager. No private executor/reconciler/watchdog/sizing/settlement or grounded
  desk reasoner/evolution runtime found in current source inventory.

## P0 — block execution integration

**P0-01 Trusted control chain incomplete.** `paper/admission.py:15–59` consumes
caller readiness flags, not independently verified operational facts. Private
transaction primitives are useful but not a completed risk/permit/send/reconcile/
manage/settle chain. Do not convert unit-test PASS to execution readiness.

**P0-02 Calendar coverage/policy mismatch.** `calendar.py:155–169` requests only
t-15min..t+24h while `entry_blackout` lines187–214 needs knowledge of red releases
up to two hours earlier. A source honoring the query can omit them. Separately,
playbook line119 says no red event in next2h, while code blocks only15min before.
Independent synthetic probe observed no blackout for an event90min ahead.
PD-00A must fix source-window completeness and resolve policy precedence before
integration. Do not silently weaken either protected policy or calendar coverage.

## P1 — measurement and economic validity

**P1-01 Future outcome used before settlement.** `engine.py:545–602` immediately
credits simulated final P&L/stop state while advancing entry candidates. Later
entries can depend on future outcomes. `scripts/backtest_desk.py:52–70` runs
pairs independently, not a joint risk portfolio. Quarantine structural equity,
stop/cooldown and feasible-frequency claims until event-time replay (PD-00C).

**P1-02 Gap/horizon defects.** `engine.py:394–408` books protective stops at the
stop even when opening beyond it. A synthetic entry100/SL99/open98 booked -1R
instead of -2R before costs. Lines463–468 settle residual exposure at the full
input's last bar after breaking the horizon loop; a one-day probe held50h.
Calendar days also differ from specified broker trading sessions. PD-00B owns
repair. The dense simulator's adverse gap handling is separate and not accused
of this defect. Structural sensitivity figures remain historical, not certified
portfolio results; do not claim their exact P&L survives these repairs.

**P1-03 Management contract mismatch.** `engine.py:427–461` has a one-close
early cut and unconditional Friday flatten, unlike AD execution spec190–209's
two-close/no-reclaim logic and conditional protection. Missing management
components include structural/falsifier/session semantics. Dense explicitly
omits this policy. Neither validates exact intended management economics.

**P1-04 Reward denominator/partial mismatch.** Config lines95–99 takes half at1R
and trails; checklist lines262–274 checks room only to1.25 price-R. No blended
3 parent-R admission exists. AD execution spec41,94–95,231–237 freezes all-in
initial risk, while research uses price-stop R. Required runner target for net
3 parent-R is `5+6k+2c` price-R (half at1, k=reserve/G, c=cost/G). With k=c,
it is `5+8c`. See new mandate; do not compare unlike units. Playbook partial
"net >=0.90R" wording is not whole-parent realised return.

**P1-05 Intended macro edge untested.** Structural regime context is an EMA
proxy (`engine.py:208–233,295–308`); dense is common technical features with
separate pair fits, not distinct expectation-aware macro mechanisms. Public
pair-specific architecture is already specified; reuse it through PIT evidence,
not a new blanket claim that all pairs share one strategy.

**P1-06 Provenance incomplete.** CSV `data.py:85–102` and simple `OHLCBar`
(`features.py:44–54`) do not attest source availability/broker clock/vintage.
Dense training-label purge is real (`dense.py:613–631,658–679`), but does not
prove complete historical input availability. New designs need fresh forward
evidence; all inspected 2022–2026 history is development data now.

**P1-07 Current measured evidence rejects promotion.** Selection winner holdout
EURUSD -45.1182R, USDJPY -21.7357R; stable post-hoc cell -7.33R combined,
USDJPY +0.0337R/trade with weekly p0.5259/PF1.0558. Sources:
`dense_holdout_select_winner.json`, `dense_holdout_stable.json` and reviewed
`DENSE_FINDINGS.md:171–237`. These are fixed-exit, price-risk-R results. 12.8/week
fits the per-pair concurrency cap, NOT proof it survives every portfolio,
session, news, cooldown and equity restriction. Historical claims remain scoped.

## P2 — integration/specification debt

- Checklist grades are heuristics, not probabilities; weaker legacy boolean
  alignment can hide neutral/unknown (`checklist.py:277–371`).
- Operator asymmetric points are separate from expectancy. At uncapped +/-1R,
  +4/-6 points needs60% wins for zero point drift, not50%; no point-based
  optimiser should replace economic evaluation (`operator_score.py:60–109`).
- Canonical cost deductions exist but are marked unmeasured; commissions/swap/
  broker valuation remain incomplete (`config.py:61–68`, `dense.py:503–507`).
- AI chain injection seam exists, but durable private budget implementation is
  not established by a test double (`ai/providers/chain.py:37–80`,
  `tests/test_ad_ai_budget.py:1–52`). Default telemetry can be production-bound.
- Evidence schemas establish references/coverage, not semantic claim support.
- TASK/CONTEXT and old AD baseline statements are historical. New top checkpoints
  route readers to this audit without deleting or falsifying prior receipts.
- IDENTITY line46's one-way JPY intervention description is not authoritative
  institutional policy. Official MOF/BoJ distinction in research ledger should
  govern proposed evidence semantics; changing IDENTITY remains owner-gated.

## Reuse and remediation

Reuse contracts, disabled authority, private writer/journal/transaction primitives,
snapshots/spec bundles, read-only broker checks, causal features, SU1/SU3, dense
purge/gap/benchmarks and score replay. Keep SU2 unresolved, SU4/SU-R1 research-only.
Reuse tests as engineering evidence, not profitability evidence.

Order: PD-00 measurement/calendar repairs + PD-01 pure payoff math -> contract
reconciliation -> joint full-management replay -> entitled PIT macro evidence ->
bounded AI/independent challenge -> registered ablations/fresh forward evaluation
-> only then remaining AD execution/recovery/graduation work. See
`docs/specs/payoff-desk/05-delivery.md` for files and acceptance cases.

## Fresh checks

Baseline before package: pytest917 passed in81.70s; Ruff clean; mypy clean282
files. GitNexus query attempted and failed LadybugDB storage42/runtime40; graph
risk UNKNOWN. No existing Python symbol was edited by this package. Package
validation and independent delivery review are recorded separately at completion.
