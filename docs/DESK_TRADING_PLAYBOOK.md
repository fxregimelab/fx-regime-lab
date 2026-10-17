# Desk Trading Playbook — Operating Manual & Agent Prompts

**Version:** v0.1 (2026-10-17) · **Status:** demo phase · **Scope:** personal paper desk, EURUSD + USDJPY only
**Companion docs:** `docs/PERSONAL_TRADING_ENGINE_PLAN.md` (§5.10) · `pipeline/src/paper/config.py` (parameter source of truth)
**Audience:** the operating agent (me) and the owner. Nothing here is public.

---

## 0. Standing rules (never violated)

1. **Demo/paper only.** All execution goes to the Exness demo (`EURUSDm` / `USDJPYm`).
   Real-money equivalent = desk balance ÷ 100. Any real-money phase re-enables an explicit
   owner approval gate — this playbook's autonomy applies to demo trades **only**.
2. **Pairs locked:** EURUSD + USDJPY. No other instrument, ever, in this phase.
3. **No emotion, no bias, no improvisation:** every trade decision follows this playbook,
   stage by stage. Any deviation (or judgment call outside the checklist) must be written
   as a ledger note with a stated reason *before* acting. If it can't be justified in one
   sentence referencing data, it doesn't happen.
4. **Guardrails are the control surface** (owner removed per-trade approval for the demo
   phase, 2026-10-17): per-trade risk, concurrency caps, daily/weekly kill-switches, event
   blackouts, full receipts. The owner can pause the desk at any time; limits are never
   silently widened.
5. **Every action is receipted:** proposals, checklist scores, executions, management moves,
   exits — appended to the hash-chained ledger and (for trades) to the daily desk note.
6. **Measurement before profit:** the desk exists to produce clean, honest data. "No trade
   today" is a correct and frequent output. A-grade setups are rare by design.

---

## 1. The trading loop (stages — do not skip)

**Stage 0 — Context load.**
Read, in order: desk store state (open positions, today's realized P&L, limits usage, ledger
head), fresh bars (sync first: D1/H4/H1/M15), pipeline calls for both pairs (live model only,
`2.0-live`), economic calendar next 24h, headline scan. Never from memory.

**Stage 1 — Candidate scan.**
Run the strategy cohort scan (S1–S5 + baselines where appropriate). For each pair list every
candidate with which cohort fired and the raw numbers. If nothing fires → write the "no
candidate" desk note with the scan table and stop. That is a complete session.

**Stage 2 — Deep research packet (per candidate).**
Build the full packet (see §6): macro context, event risk, multi-timeframe read (§5),
liquidity map, bull/bear/neutral cases *each with at least one falsifier*, historical cohort
stats. The packet is part of the trade's permanent record.

**Stage 3 — Binary checklist → confidence grade (§2).**
Score all 14 checks Y/N with the evidence line for each. Hard-gate failure ⇒ skip the
candidate (recorded). Grade A or B ⇒ proceed; C ⇒ skip (recorded).

**Stage 4 — Trade plan construction.**
Direction, entry trigger, stop (structure-based, liquidity-aware — §3), partial plan
(50% at 1R), break-even + trail plan, early-cut triggers, expiry (≤8h typical, T+5 max),
risk in $ and %, grade-based size. The plan is a JSON block stored with the proposal.

**Stage 5 — Portfolio & concurrency gate (§4).**
Check every limit: open positions ≤ 3, ≤ 1 per pair, total open risk ≤ 2.25%, daily/weekly
stops not hit, no event blackout, cooldown respected, correlated-USD aggregate OK. Any fail
⇒ skip (recorded).

**Stage 6 — Execution.**
Pre-validate (`trade_check_market_order`, margin check), place the scale-out structure
(ticket A: 50% at TP=1R; ticket B: 50% runner — both with SL attached), verify fills, append
ledger rows (proposal + fill) with the plan JSON, write the desk note. No market orders in
the first/last 15 minutes of the session; only during 07:00–16:30 UTC.

**Stage 7 — Management (§3).**
The planned policy is enforced exactly: partial at 1R → SL to break-even → 1.2×ATR_H1
chandelier trail (structure-aware). Early-cut triggers and time stops are checked on every
management review (hourly during open sessions and at EOD).

**Stage 8 — Settlement & scoring.**
On exit: reason (TP / trail / early cut / time stop / horizon / invalidation / manual),
horizon actual (in hours), MAE/MFE, R multiple, costs. Write settlement row + update
scorecards. Weekly: full review (§8).

---

## 2. Confidence engine — 14 binary checks

Confidence is **never** a naked number. It is the weighted result of exact binary checks,
all evidence-linked. 5 hard gates + 9 scored checks.

### Hard gates (all 5 must pass or the candidate is skipped — grade C)

| # | Gate | Pass condition |
|---|------|----------------|
| H1 | Strategy rule fires | Candidate is rule-valid for its cohort (checked against cohort definition) |
| H2 | Data quality | Pipeline DQS ≥ 0.8 **and** desk bars fresh through the last completed session (both pairs, all TFs) |
| H3 | Event window clear | No red-tier USD/EUR/JPY event within ±15 min; no red event within next 2h (intraday entries) unless cohort is event-based |
| H4 | Geometry | R:R to the 1R target ≥ 1.5 after measured costs; grade A requires ≥ 2.0 |
| H5 | Session & spread | Entry inside 07:00–16:30 UTC; spread ≤ 1.5× the pair's typical; not first/last 15 min of session; no new entries Friday after 14:00 UTC |

### Scored checks (1 point each, Y/N with evidence line)

| # | Check | Pass condition |
|---|-------|----------------|
| S1 | D1 bias aligned | Pipeline D1 regime/bias agrees with trade direction (live call, not stale) |
| S2 | H4 structure aligned | H4 prints HH/HL (long) or LL/LH (short) over the last ≥ 6 bars |
| S3 | H1 trigger present | Cohort's H1 trigger condition met (breakout/retest/pattern), not implied |
| S4 | Not overextended | \|close − EMA20_H1\| ≤ 2.5×ATR_H1 in the direction of travel |
| S5 | Stop beyond noise | Planned stop distance ≥ 1.2×ATR_H1 |
| S6 | Stop avoids liquidity | Stop is ≥ 0.25×ATR_H1 beyond the nearest prior swing extreme / round number (placed *past* the pool, never at it) |
| S7 | Room to 1R | Nearest opposing structure is at least the planned 1R distance away (no wall before TP A) |
| S8 | News tone clean | No adverse headline for the traded direction's currency in the last 4h (checked in the research packet) |
| S9 | Exposure clean | Correlated same-USD-sign exposure within §4 caps; no degenerate bias skew in the pipeline call (not ≥ 85% one-way over 30 days) |

### Grading

- **A** — all 5 hard gates + **8–9** scored → full size (0.75% equity risk)
- **B** — all 5 hard gates + **5–7** scored → half size (0.5% equity risk)
- **C** — any hard gate fails, or ≤ 4 scored → **no trade**; candidate + score recorded anyway
- 1% is the absolute cap (owner rule) and is never used by default.

Grade history is itself measured (§8): if B-grade trades underperform, the grader tightens.

---

## 3. Trade management policy (exact mechanics)

### Entry structure
- Two tickets, 50/50 volume: **A** (TP exactly at 1R, SL at plan stop) and **B** (runner, SL at
  plan stop, no TP). This is broker-native scale-out: A fills server-side without an agent present.
- Entry only inside the session window; market orders not in first/last 15 min.

### Risk-free move (after A fills)
- Move B's SL to **break-even + 1.5 pips buffer** (covers spread; "risk-free" in the honest sense:
  worst case left is costs, not stop loss).

### Trailing the runner (B)
- Chandelier rule: `new_SL = max(current_SL, best_price_since_entry − 1.2×ATR_H1)` for longs
  (mirror for shorts).
- **Structure-aware floor:** never place the SL at a swing extreme or round number — keep
  ≥ 0.15×ATR_H1 beyond the nearest structure (this is the anti-liquidity-hunt buffer).
- Update **only on new completed H1 bars** or at scheduled reviews; **never** move an SL
  against the position; never widen.
- Round-number avoidance: if the computed SL lands within 5 pips of a round number that acts
  as a pool (e.g., 1.1000, 157.00), shift it 3–5 pips *further* from price.

### Early loss cut (close the full remaining position; record trigger)
1. Adverse excursion ≥ **0.5R within the first 2 hours** without a reclaim of entry area;
2. H1 closes beyond the plan's invalidation level (two consecutive closes);
3. Thesis-break news (fresh headline or data that directly contradicts the trade's premise);
4. **Time stop:** unrealized < +0.2R at **4 hours** → cut or reduce (stalled thesis).

### Profit-running rules
- Winner stays open while the trail holds; expected most trades close ≤ 8h.
- **EOD rule:** if the runner is ≤ +1R at session end and MTF alignment has broken → close.
  If ≥ +1R and D1/H4 still aligned → may hold overnight, but never past **T+5**.
- **Hard horizon: T+5.** At T+5 the book is closed, no exceptions.

### Never
- Widen a stop · average into a loser · re-enter the same pair+direction within 4h after a
  stop-out without a **new A-grade** checklist · trade through a red event with a fresh entry ·
  hold past T+5 · open trades "because the desk was quiet".

---

## 4. Concurrency & exposure limits (demo phase)

| Limit | Value |
|-------|-------|
| Max concurrent positions (tickets) | 3 |
| Max positions per pair | 1 |
| Max total open risk | 2.25% of equity (3 × 0.75%) |
| Max new trades per day | 3 |
| Daily loss kill-switch | −3% equity → stop for the day, write report |
| Weekly loss kill-switch | −6% equity → freeze + full review before resuming |
| Cooldown after stop-out | 4h same pair + direction |
| Same-USD-sign pair combo | allowed only if the second trade is grade A; counts toward open-risk cap |

Balance guard: sizing uses live demo equity, so the risk percentages hold exactly.
All limits live in `pipeline/src/paper/config.py` (`TradingLimits`); changes require a doc
update + ledger note.

---

## 5. Multi-timeframe protocol

| TF | Role | Must answer |
|----|------|-------------|
| D1 | Regime & bias | What is the daily regime/bias (pipeline call)? Where are the major levels? |
| H4 | Structure | Is the trend structure aligned with the intended direction (HH/HL vs LL/LH over ≥6 bars)? |
| H1 | Setup & trigger | Is the cohort's trigger present? Where is the invalidation? ATR_H1 for stop/trail math. |
| M15 | Precision | Where is the entry refinement and the *stop beyond the pool* (swing wick + buffer)? Session H/L map. |

**Rule:** grade A requires ≥ 2 of {D1, H4, H1} aligned (and all 5 gates); grade B requires at
least 1 aligned and no TF actively contradicting. The entry TF is H1/M15; M15 exists to place
stops past liquidity, not to chase.

---

## 6. News & research protocol (research packet)

Built per candidate, before the checklist, stored with the trade:

1. **Calendar:** terminal economic calendar, next 24h — every USD/EUR/JPY event, tiered
   (red/orange/yellow), with forecast vs prior. Red events feed gate H3.
2. **Headline scan:** targeted fetch for the pair's currencies (central bank, inflation,
   growth, geopolitics) — each item timestamped and **cited** (source + time). No headline =
   state "clean" explicitly.
3. **Multiple viewpoints:** write the **bull case**, **bear case**, and **neutral/no-trade
   case** for the candidate. **Each case must list ≥ 1 falsifier** ("what data would prove
   this case wrong"). A candidate where no falsifier can be stated is a C-grade by definition.
4. **Cross-check:** does the news tone agree with the technical setup? Disagreement is not an
   auto-veto but must be reflected in S8 and in the plan (tighter trail, smaller size).
5. The packet is receipted with the proposal so future reviews can audit what was known
   at decision time — no hindsight scoring.

---

## 7. The prompts (operating instructions, copy-paste ready)

### P1 — Daily desk session

```text
You are the operator of a personal demo trading desk (EURUSD + USDJPY only, demo money,
autonomous within guardrails). Follow docs/DESK_TRADING_PLAYBOOK.md exactly. No emotion,
no bias, full receipts. Your output is a desk note; "no trade today" is a valid result.

INPUTS — read fresh, never from memory:
1. Desk state: open positions, equity, today's realized P&L, limits usage, ledger head.
2. Bars: sync D1/H4/H1/M15 (desk_prices_sync) — verify freshness for both pairs.
3. Pipeline calls: live model only (2.0-live), EURUSD + USDJPY — bias, conviction,
   entry_timing, stop_level, DQS.
4. Calendar: next 24h USD/EUR/JPY events with tiers.
5. Headlines: targeted scan for USD/EUR/JPY (cited, timestamped).

PROCEDURE:
- Stage 1: strategy cohort scan (S1–S5). List every candidate with cohort + raw numbers.
  Nothing fires → write the no-candidate note (scan table) and STOP.
- Stage 2: for each candidate, build the research packet: macro context, event risk,
  MTF read (D1/H4/H1/M15), liquidity map, bull/bear/neutral cases each with ≥1 falsifier,
  cohort history stats.
- Stage 3: score the 14 binary checks (playbook §2). Print the full table with evidence
  lines. Hard-gate fail or C grade → record and skip.
- Stage 4: build the trade plan: direction, entry, stop (structure + buffer, never at a
  pool), partial (50% at 1R), BE+trail plan (1.2×ATR_H1 chandelier, 0.15×ATR_H1 buffer),
  early-cut triggers, expiry (≤8h typical, T+5 max), risk $ and %, grade size.
- Stage 5: portfolio gate — every §4 limit checked and printed (positions, per-pair,
  open risk, daily/weekly stops, blackout, cooldown, USD-sign aggregate).
- Stage 6: on pass — pre-validate order (check + margin), place tickets A (50%, TP=1R)
  and B (50% runner) with SL attached, verify fills, append ledger rows + plan JSON.
- Stage 7: management plan registered (reviews scheduled; policy in playbook §3).
OUTPUT: the desk note — state, scan table, per-candidate checklists, plans, executions
(ticket ids), ledger refs, and the next management checkpoint.
NEVER: widen a stop; add to a loser; trade outside EURUSD/USDJPY; exceed any §4 limit;
skip the checklist; act without a ledger row; trade during a red event window.
```

### P2 — Candidate deep-research packet

```text
Build the full research packet for this candidate: <pair, direction, cohort, timestamp>.
Deliver, in order:
1. Macro context (D1 regime, rates/differentials backdrop, recent central-bank tone) — cited.
2. Event risk: next 24h calendar for the pair's currencies + tier + what each event could do.
3. MTF read: D1 bias, H4 structure (HH/HL vs LL/LH over ≥6 bars), H1 trigger + invalidation,
   M15 precision levels; ATR_H1 value.
4. Liquidity map: nearest swing highs/lows, session H/L, round numbers (pools), and where the
   honest stop must sit (beyond noise + 0.15×ATR_H1 beyond the pool).
5. Bull case, bear case, neutral case — EACH with ≥1 explicit falsifier.
6. Cohort history: this cohort on this pair — n, win rate, avg R, max DD from backtests.
7. Verdict feed: proposed hard-gate results (H1–H5) and scored checks (S1–S9) with the single
   evidence line each. Flag any check you cannot verify — unknown ⇒ fail.
```

### P3 — Management review (hourly in session / at EOD)

```text
Management review for open desk positions.
1. Sync quotes + latest H1/M15 bars. For each position: entry, R progress, MAE/MFE, time open,
   partial status, SL state.
2. Evaluate early-cut triggers (playbook §3): AE ≥ 0.5R in first 2h without reclaim;
   2 consecutive H1 closes beyond invalidation; thesis-break news; time stop (<+0.2R at 4h).
   Any trigger → close remaining position, record trigger id.
3. If ticket A filled: ensure B's SL is at break-even + 1.5 pips.
4. Trail update on new completed H1: new_SL = max(current, best − 1.2×ATR_H1), respecting the
   0.15×ATR_H1 structure buffer and round-number shift. Never move against the position.
5. EOD rule: runner ≤ +1R and MTF broken → close; ≥ +1R aligned → hold (never past T+5).
6. Record every action as a ledger row (kind, trigger, prices, reasoning one-liner).
OUTPUT: updated position table, actions taken with trigger ids, next checkpoint time.
```

### P4 — Weekly scorecard & model review

```text
Weekly desk review.
1. Aggregate settled trades: per cohort, per grade (A/B), per pair, per session; n, win rate,
   net expectancy with CI, profit factor, max DD, avg holding hours, MAE/MFE distributions.
2. Compare vs baselines (S0a/S0b) and vs the naive full-run variant of each trade
   (retro-simulation of "no partial, single stop" on the same entries) — is scale-out helping?
3. Checklist predictiveness: win rate for pass vs fail of each of the 14 checks. Flag checks
   with no separation (candidates for removal/retune).
4. Guardrail audit: limit usage, kill-switch events, any deviations recorded.
5. Proposals: parameter changes (numbers, not vibes) with the evidence line that motivates
   each; mark each proposal as auto-applicable (desk params) or pipeline-review (model change).
OUTPUT: reports/desk/research/weekly_<date>.md + ledger note with the summary lines.
```

---

## 8. Measurement & model-improvement loop

- Every trade is tagged: cohort, grade, checklist vector, MTF alignment count, session, plan
  params, management events (partial fill time, BE move, trail moves, cut triggers).
- Settlement scoring is automatic (R multiple, hours, MAE/MFE, costs) from the ledger.
- Weekly P4 review drives two improvement tracks:
  - **Desk params** (auto-applicable, versioned in `config.py` + doc): grade thresholds, trail
    multipliers, cut thresholds, session windows.
  - **Model/pipeline items** (evidence → backlog): intraday entry layer, intraday stop model,
    session/liquidity features, cohort fixes. Changes to the public pipeline follow its own
    review process — the desk never edits production signals directly.
- No promise of profit. The desk's contract is honest measurement: clean entries, exact
  management, complete records, and parameter evolution backed by data.

---

## 9. Build list (making this operational)

| # | Item | Status |
|---|------|--------|
| 1 | Intraday bars D1/H4/H1/M15 in the desk store (`desk_prices_sync --timeframes`) | ✅ done with this doc |
| 2 | `TradingLimits` in `paper/config.py` (mirrors §4) | ✅ done with this doc |
| 3 | `paper/checklist.py` — 14-check evaluator + grading, receipts | ⏳ next |
| 4 | `paper/levels.py` — swing/session/round-number liquidity map from store bars | ⏳ |
| 5 | `paper/manage.py` + `scripts/desk_manage_once.py` — policy executor (BE, trail, cuts) | ⏳ |
| 6 | `paper/news.py` — calendar + headline scan wrapper (cited, receipted) | ⏳ |
| 7 | Desk session runner + intraday scheduling (payment of P3's session loop) | ⏳ |
| 8 | Scorecard extensions (grade buckets, check predictiveness, scale-out variant sim) | ⏳ |

## 10. Owner interaction

- Default now: autonomous execution within the §4 guardrails; owner is notified with the
  receipt after each trade. Owner can pause/stop any time by saying so; any pause is recorded.
- Per-trade approval returns on: owner request, any real-money phase, or any guardrail breach.
- Weekly: P4 report surfaced to the owner — numbers, failures, proposed changes.
