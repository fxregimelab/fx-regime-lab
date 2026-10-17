# Desk Strategy Framework — "Regime-anchored liquidity/structure trading"

**Version:** v1.0 (2026-10-17) · **Scope:** personal paper desk, EURUSD + USDJPY
**Governance pairs:** `docs/DESK_TRADING_PLAYBOOK.md` (procedure) · `pipeline/src/paper/config.py` (numbers)
**Version stamps:** `FRAMEWORK_VERSION = 1.0`, `PLAYBOOK_VERSION = 0.2` — receipts must cite both.

---

## 0. Doctrine (one paragraph)

We do **not** pick a single school. The desk fuses three things where each is strongest:
the lab's **quantitative regime models** decide *when and which direction* is allowed
(Layer 1); **market structure and liquidity analysis** decide *where* an entry is honest
and where stops must never sit (Layer 2); **checklist-gated execution** decides *when
exactly* and *how big* (Layer 3); and the **scorecard loop** kills whatever the data
doesn't support (Layer 4). "Quantamental", "retail strategy", "SMC", and
"liquidity/market-structure" are treated as *ingredients with known failure modes* —
never as doctrine.

## 1. Why not one school

| School | Strength we take | Weakness we don't take |
|---|---|---|
| Quantamental (our lab) | Regime, bias, conviction, DQS, macro context, statistical validation | No intraday entry/stop mechanics; below-coin-flip live record so far — it proposes, it doesn't decide alone |
| Retail indicator strategies | Momentum/volatility context as *confirmation* | Naked indicator crossovers; no level model; stop placement by fixed pips |
| SMC / liquidity | Liquidity pools, stop-hunt sweeps, structure breaks — hugely useful for stop placement | Unfalsifiable claims (order blocks as dogma, "smart money" narratives); we keep only the testable core |
| Market structure | Trend/higher-high-lower-low framing, range edges, invalidation logic | Subjectivity without written rules |

## 2. The four layers

**L1 — Regime & bias (WHEN / WHICH DIRECTION).** Input: pipeline `2.0-live` calls
(EURUSD, USDJPY) — bias, conviction, entry_timing, stop_level, DQS; 8-signal
decomposition; macro context. Output: allowed directions per pair, conviction context,
daily invalidation reference. A candidate never trades against a live bias unless the
setup is explicitly counter-trend and capped at B-grade.

**L2 — Structure & liquidity (WHERE).** Input: desk store bars (D1/H4/H1/M15). Output
per pair: H4/H1 trend structure (HH/HL vs LL/LH), swing map, liquidity pools
(equal highs/lows, session extremes, round numbers), supply/demand zones as *zones*,
and the computed rule: stops sit **beyond** pools with a ≥0.25×ATR_H1 buffer — this is
the anti-liquidity-hunt requirement, mechanized (implemented: `paper/levels.py` +
checks S6/S7 in `paper/checklist.py`).

**L3 — Trigger & execution (WHEN EXACTLY / HOW BIG).** Input: L1 + L2 + checklist
module. Output: binary checklist score (14 checks) → grade → slot-scaled risk; entry
trigger (H1/M15); scale-out plan (50% at 1R, SL→BE+buffer, chandelier trail); early-cut
and time-stop triggers; expiry (≤8h typical, T+5 max).

**L4 — Validation & adaptation (DOES IT WORK).** Every trade tagged (cohort, setup,
grade, checklist vector, session, management events, operator id). Weekly scorecard:
per-setup/per-grade statistics, checklist-item predictiveness, scale-out vs full-run
retro-sim, operator scores. Parameters adapt only through this loop — never mid-trade,
never by vibe.

## 3. The tradable setups (v1)

Each setup is a falsifiable rule set; all pass through the same 14-check gate.

**SU1 — Regime trend pullback** *(primary; expected highest frequency)*
- Preconditions: L1 bias aligned; H4 structure intact (HH/HL for longs); H1 pullback to
  value (EMA20_H1 area or prior structure level) without breaking H1 structure.
- Trigger: H1/M15 reversal evidence at the level (reclaim candle, structure micro-break).
- Stop: beyond the pullback extreme + buffer. Invalidation: H1 structure break.

**SU2 — Liquidity sweep reversal** *(the SMC core, testable form)*
- Preconditions: a swing/session extreme swept (wick through, close back inside) in the
  direction *against* the D1/H4 bias — i.e., a stop hunt into a pool.
- Trigger: reclaim of the swept level + M15 retest held.
- Stop: beyond the sweep wick + buffer (the sweep extreme *is* the invalidation).
- Note: we trade the *reclaim with the higher-TF bias*, not every wick — sweeps against
  both L1 and L2 are skipped (they are breakouts, not hunts).

**SU3 — Structure breakout + retest**
- Preconditions: H1/H4 range edge or swing level broken with momentum, L1 bias aligned.
- Trigger: retest of the broken level held (M15/H1), not chased.
- Stop: back inside the broken structure + buffer. Skip if the breakout is into a
  major opposing pool (no room).

**SU4 — Range rotation** *(experimental; B-grade cap, half slot ceiling)*
- Preconditions: L1 says range/neutral; H1 range defined by ≥2 touches each side;
  entry faded from the extreme with tight invalidation.
- Trigger: rejection evidence at the range edge (not limit-order catching).
- Stop: beyond the range edge + buffer. Kill rule: two consecutive failed rotations
  in the same range → stand down on that pair's range for the session.

**Research setups (not executable yet):**
- **SU-R1 — Relative value / statistical arbitrage across correlated majors.** The
  honest form of "arbitrage" from one retail account (latency arbitrage is not
  physically available on a retail feed). Enters only as a B-grade-capped experiment
  with its own written falsifier once the execution loop is proven.

Cohort mapping (sources vs execution): the pipeline cohorts S1–S5 remain the *thesis
sources* (S5 stays research-only, never executed); the setups above are the *execution
forms*. A trade is always (source cohort × setup), tagged with both.

## 4. Multi-timeframe contract

D1 = regime/bias & major levels · H4 = structure & trend agreement · H1 = trigger,
ATR math, invalidations · M15 = entry precision and stop-beyond-pool placement.
Alignment caps the grade: fewer than 2 of {D1, H4, H1} aligned ⇒ best possible grade
is B+. M15 never creates a trade — it only refines one.

## 5. Explicitly banned (no exceptions)

- Martingale, grid, averaging into losers, "just one more" adds.
- Naked indicator triggers (RSI/MACD crosses as the reason to enter).
- News gambling: entering inside ±15 min of red events; staking on releases.
- Weekend gambling: any position held over the weekend must have SL ≥ break-even.
- Hope-holding: carrying a position past its written invalidation or T+5.
- Order blocks / FVGs as primary signals — allowed only as confluence annotations while
  the scorecard has not validated them as predictive.
- Re-entering the same setup within 4h of a stop-out (unless a fresh A/A+ candidate).
- Trading without a receipted checklist score.

## 6. The spec-gate (read-before-trade)

Before any session and any trade decision, the operator loads and cites:
1. `docs/DESK_TRADING_PLAYBOOK.md` (procedure; current v0.2)
2. `docs/DESK_STRATEGY_FRAMEWORK.md` (this doctrine; v1.0)
3. `pipeline/src/paper/config.py` (all numbers — single source of truth)

Ledger receipts are stamped with `FRAMEWORK_VERSION` + `PLAYBOOK_VERSION`. A trade
taken under anything else is a process violation and is recorded as such. The machine
form of this gate is `pipeline/src/paper/checklist.py` — it evaluates the 14 checks
and the risk lookup directly from the config spec, so what the operator scores and
what the spec says cannot drift apart.

## 7. Adaptation rules (how the desk learns)

- **Never mid-trade.** Parameters change only at the weekly P4 review, with the evidence
  line that motivates each change; every change is a versioned config edit + doc note.
- **Checklist item predictiveness:** each of the 14 checks accumulates win-rate
  separation stats; checks with no separation are candidates for removal/reweighting;
  checks with strong negative separation get investigated as inverted logic.
- **Grade multipliers** are re-tuned when bucket stats show the current mapping is
  mispriced (e.g., B trades outperforming B+ ⇒ multipliers converge).
- **Setup lifecycle:** a setup is killed after ≥40 settled trades with expectancy CI
  entirely below zero after costs; new setups enter only as B-grade-capped experiments
  with a written falsifier.
- **Kill-switches are not parameters:** daily −10% / weekly −25% (demo phase) only move
  with an owner directive.

## 8. Operator score (penalty/reward for the executing AI)

Every trade decision records the operator id (which model/agent executed it). Settled
outcomes and process violations move that operator's score — asymmetric by design:

| Event | Points |
|---|---|
| Settled +1R | +4 (cap +12 per trade) |
| Settled −1R | −6 (floor −18 per trade) |
| Process violation (unreceipted checklist, widened stop, missed cut, limit breach) | −20 |
| Kill-switch day (daily loss stop hit) | −15 |

Envelope gating (score 0–100, start 100; can only TIGHTEN limits, never loosen):

| Score | Envelope |
|---|---|
| ≥ 85 | full autonomy envelope |
| 60–84 | A/A+ grades only; slot ceilings ×0.75 |
| < 60 | desk pause → written remediation + owner notice before resuming |

Why: the operator — any model, including me — works under consequences. Losses cost
more score than wins earn, and sloppy process costs heavily. The score is computed by
scorecard v2 from the ledger; a model swap is just a new operator id, so comparing
agents is mechanical. This is the mechanistic form of "adapt and focus": behavior
changes through the envelope, and evidence accumulates per model.

## 9. Honesty clause

The lab's live directional record is currently below coin-flip. This framework does not
promise profitability; its contract is: exact entries, mechanized risk placement,
complete receipts, and parameter evolution backed by data. The aggressive demo risk
schedule exists to generate statistically meaningful samples and realistic drawdown
experience at zero real cost — the scorecard decides what survives.

**The +50%/week target** (owner-set): encoded as the desk's weekly objective and
reported every week as actual-vs-target with honest attribution. It is a target, not a
guarantee — no honest system can promise a fixed weekly return, and one that did would
be lying to you. What is guaranteed is the process: maximum aggression inside the
guardrails, full measurement, and fast adaptation.

**Instrument expansion** (owner-authorized 2026-10-17): the desk may widen beyond
EURUSD + USDJPY. Implementation enters only through the same evidence gates as any
setup; first research family SU-R1 (relative value / stat-arb across correlated majors).
The research pipeline's 3-pair lock is untouched — expansion is desk-only.
