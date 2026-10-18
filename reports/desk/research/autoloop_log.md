# Autonomous Loop Log — fx-live-personal

> Owner is AFK. Agent running the loop: diagnose → fix (subagent) → verify (coordinator) →
> commit → independent review → next. Hard rules: demo only, 3-pair lock, no live orders,
> no destructive DB ops without a verified backup, subagents never commit, one editor per
> file at a time.

**Last updated:** 2026-10-18 (session 3 — autonomous trading-readiness push)

## Session 3 outcome (autonomous trading-readiness push)

- Full suite **843 passed** (was 755); Ruff clean; mypy clean (259 files).
- **RF2b committed `a20eec5`**: replay now computes the live-definition 2Y pair spread
  (DGS2 − causal quote; missing JPY/INR quotes stay unavailable — the earlier silent
  raw-US-yield substitution was found by the new red tests and removed), stores it as
  `rate_diff_2y`, and normalizes the same risk-adjusted carry as live. Independent
  review **PASS** (10 focused tests; 180-row independent reference reconstruction;
  prefix-invariance after future appends). Non-blocking note: EUR legacy-fallback
  warning fires per-run, not per-date.
- **AD-T07 committed `64445f8`** (agent-implemented, coordinator-gated): strict
  read-only BrokerReadPort with explicit MCP schema bindings (no guessed tools),
  numeric demo/hedging gates, exact symbol mapping, freshness/completed-bar/gap
  checks, 3-sample evidence-bound clock. 48 tests, red-first observed. Live schema
  discovery and terminal clock observations remain provisioning blockers.
- **AD-T08 committed `f39e62b`**: registered-source-only calendar/news collectors
  with affirmative CoverageReceipts, latest-revision red-event blackout, and the
  two-publisher-family headline rule; verified-empty calendar is legitimate, weak
  news coverage blocks entry. 27 tests.
- **`70559c1`**: tasks/plan.md + tasks/todo.md execution index for remaining slices.
- Owner directive recorded: complete demo-execution readiness; **no credential
  rotation** (owner's decision). Demo trading stays impossible until graduation
  gates pass; nothing was waived.

## Recovery checkpoint — verified current state

- LRH committed and pushed as `8df4a9f`; independent LRH review is NOT complete.
- RF1R, VR1R and T12R returned PASS in the preceding session. The older running-agent
  table below is historical; those three reviews have finished.
- VQ implementation is complete: causal scoring `3ba5f18`, credential/legacy-SQL cleanup
  `f85a5e6`; bootstrap fix and subprocess regression `5a92695`. Latest coordinator checks:
  11 focused tests, full suite 755 passed, Ruff clean, mypy clean (251 files), diff check
  clean. Independent review remains pending; no runtime strategy promotion is implied.
- RF2b left partial source edits in `simulation_engine.py`; preserved, NOT committed or
  accepted as complete. Existing 4 simulation tests pass, but new parity tests are missing.
- LRH-review and RF2b recovery calls failed with provider HTTP 500 / rate limits. No agent
  is currently working successfully on them; do not infer completion from the queue below.
- Fixed the price-population script import bootstrap (pipeline root, not pipeline/src).
  Retried with `.env.local` loaded: 497 price bars upserted through `writer` (166 EURUSD,
  165 USDJPY, 166 USDINR). These are upsert counts, not counts of newly inserted dates.
- Before/after ledger fingerprints are identical: 19,506 regime calls and 19,491 active
  validation rows. Fingerprints cover selected columns only; NOT restorable backups.
- Read-only post-top-up audit: 589 rows flagged; category counts (overlap): cross-pair 15,
  gross 519, flag 92, net 523, Brier 85, cost 222, no-prices 68. Price coverage ends:
  EURUSD 2026-10-17, USDJPY 2026-10-16, USDINR 2026-10-18; source dates still need QA.
- VR2 ledger corrections NOT executed. `bulk_rewrite_validation_rows` performs separate
  supersede and insert requests, not an atomic transaction. Before use, require a full
  restorable affected-row backup and verified failure/recovery plan, plus independent
  approval of the exact correction manifest. No validation rows have been changed here.
- Removed hardcoded credentials from two VQ scripts; rotation remains owner action because
  historical commits still contain the exposed credential. Never copy its value into reports.
- GitNexus `detect_changes(scope='all')` still fails: storage format 42 vs runtime 40.
  Graph impact remains UNKNOWN; manual scope review and tests are the available evidence.

## Committed this loop

| Commit | What |
|---|---|
| `70559c1` | docs(desk): execution index for the remaining AD slices |
| `64445f8` | feat(desk): AD-T07 read-only broker protocol, clock and instrument boundary |
| `f39e62b` | feat(desk): AD-T08 calendar and headline coverage with fail-closed receipts |
| `a20eec5` | fix(backfill): live-definition 2Y pair spread and carry parity in replay (RF2b) |
| `47c5bb9` | docs(research): post-top-up audit + recovery gates preserved |
| `5a92695` | fix(backfill): price-population script bootstrap + subprocess regression |
| `f85a5e6` | fix(security): embedded database credential fallbacks removed |
| `3ba5f18` | fix(validation): batch scoring forward-price fallback removed (VQ) |
| `0360b80` | feat(desk): AD-T12 AI attempt budgets — reserve/settle policy, production isolation |
| `bf12c0d` | fix(validation): scorer repair — per-pair price filter, causal spot, rescore audit (VR1) |
| `1cbdb12` | fix(backfill): replay writer safety — scoped upsert + protected live/legacy dates (RF1) |
| `2845770` | fix(desk): AD-T06 ack-shape amendment — understood_clause_ids + unresolved_conflicts |
| `4390c77` | fix(backfill): replay signal fidelity — canonical COT/OI, raw beta rows (RF2) |
| `8df4a9f` | fix(rate): live z-histories from canonical yields with same-day definitions (LRH) |
| `7fa18b4` | docs(desk): AD-T06 review dispositions — spec 01 §8 ack-shape amendment + decision D7 |
| `debde0c` | fix(desk): AD-T05 review fixes (sealed index binding, post-finalize archive rejected, safe relpaths) |

## Verdicts recorded

- **AD-T05 targeted re-review: PASS** (`debde0c`): 84 adversarial probes; 11-mutant matrix all killed;
  focused 30; full suite green; ruff/mypy clean. Notes: `read_snapshot_file` is index-anchored only
  (hardening note); full-chain rewrite undetectable locally by design (external witness = spec §7
  forward work); empty directories not detected.
- **AD-T06 targeted re-review: PASS** (`2845770`): exact 5-key ack set verified; legacy `clauses` wire
  key gone and rejected; `unresolved_conflicts` strict; 12/12 mutants independently killed; pinned
  bundle digest byte-exact; focused 55; full suite green.
- Process note: the T06 fixer's on-disk mutation log was a pre-fix baseline artifact; the reviewer
  re-derived 12/12 killed from the committed files (substance confirmed).

## Running agents

| Agent | Task | Files | Status |
|---|---|---|---|
| RF1R | RF1 targeted re-review vs `1cbdb12` (read-only) | `pipeline/src/db/repositories/regime_call.py` | running |
| VR1R | VR1 targeted re-review vs `bf12c0d` (read-only) | `pipeline/scripts/*` | running |
| T12R | T12 targeted re-review vs `0360b80` (read-only) | `pipeline/src/ai/*` | running |
| LRH | live rate-history consistency fix | `orchestrator.py`, `signals/rate.py`, `fred_historical.py` | running |

## Deep-backtest findings (read-only diagnostics, 2026-10-18)

### DB lifecycle (verified live, read-only)

- `regime_calls`: EURUSD 2.1-m3 5761 (2004-02-23→2026-05-08) + 2.0-live 113 (2026-05-10→10-16) +
  0.0-legacy 51; USDJPY 2.1-m3 7595 (1997) + live 115; USDINR 2.1-m3 5758 + live 113. No overlap.
- `signals` aux COT columns (`cot_asset_mgr_net`, `cot_lev_money_net`, `cot_net_pos`, `z_blended`,
  `fpi_flow`) are populated **only in 2026 rows**; all history is NULL. USDJPY historical
  `cot_signal` is NEUTRAL 7590/7595 → replay never had a COT input for USDJPY.
- `historical_cot` table exists (weekly CFTC reports) — the canonical history source; the live
  pipeline computes COT from `CotRow`s via `signals/cot.py` (156-report causal, exclusive).
- `bulk_write_backfill_results` currently does `DELETE FROM signals/regime_calls WHERE pair=:pair`
  → would **delete live 2.0-live rows** if the sim is re-run with `--end today`. Triggers are
  disabled during the write with no try/finally.
- Unique indexes: `signals (pair,date)`; `regime_calls (pair,date)` and `(pair,date,model_version)`.
  Upserts possible; overlapping live dates must be skipped (protected).

### Confirmed replay defects (simulation_engine.py)

1. COT: single-row `CotRow` (`open_interest=1000` fabricated) → `compute_cot_smart_spread_percentile`
   always `None` (needs ≥2 rows); historical `cot_percentile` never recomputed from `historical_cot`.
2. Betas: `hist_for_betas` entries lack `date`/`spot` → `compute_dynamic_betas` returns the
   hardcoded zero fallback → dynamic betas never used in replay.
3. OI: sign-hack `50±50` instead of `compute_oi_from_cot` (production uses real COT OI).
4. Macro leak: current-day `eur_kwargs` reused for every historical beta row (key `special`
   is not even a beta family — dead input).
5. Vacuous test: 60-bar fixture ⇒ vacuous `if len(...) > 1` assertions.

### Live-attribution facts (earlier diagnostics)

- LIVE directional T5/T20: EURUSD 25.7%/17.1% (n=35), USDJPY 29.8%/53.2% (n=94),
  USDINR 44.6%/52.7% (n=74). rate_signal tracked 197/203 calls.
- COT/OI agreement is **anti-predictive** in the live window (20.6% vs 41.5% / 22.2% vs 42.6%).
- USDJPY: `rate_signal=BEARISH` 94/94 while the pair trended up.

### Root causes identified (live window, read-only, 2026-10-18)

- **RC1 — carry definition mismatch (recon vs live).** Sim stores `rate_diff_2y` = raw US 2Y yield
  (`base_yield` = DGS2) for every pair; live stores the actual pair 2Y spread (US−JP, US−IN).
  Live MAD-z then compares today's pair spread against a 2520d history of the *other definition*:
  `z_tactical` pins at −1.0 → `rate_signal=BEARISH` 107/115 (JPY) and 73/113 (INR), while the
  EURUSD scales happen to coincide (US2Y ≈ US−DE) → NEUTRAL/mixed. Evidence: live rows
  `r2y=1.5–1.9, zt≈−1` (JPY); `r2y=−2.7, zt=−1.0` (INR). **RF2 follow-up needed (RF2b).**
- **RC2 — confidence flatline.** Live `confidence` ≈ 0.47 for nearly all rows (caps:
  `0.42 + 0.10*conviction`; `compute_confidence` baseline) → site probabilities near-constant.
- **RC3 — implied vol never available.** `signals.implied_vol_30d` NULL in 341/341 live rows;
  risk-adjusted carry silently falls back to RV20 (documented fallback, but worth fixing at source).
- **RC4 — COT/OI anti-predictivity** still to be quantified on full history (edge tables pending).
  Replay had no COT at all for USDJPY (fixed by RF2 from `historical_cot`, 2010+ only).

## Queue (priority order)

1. — DONE this loop: RF1 `1cbdb12`, RF2 `4390c77`, T06 fix `2845770`, T12 `0360b80`, VR1 `bf12c0d`.
   Targeted reviews RF1R / VR1R / T12R running.
2. LRH — live rate-history consistency fix — running (brief `briefs/LRH-live-rate-history-consistency.md`).
3. RF2b — recon rate-carry definition parity — spawn after LRH (reuse LRH helpers; refine brief with
   post-RF2 line refs). Brief: `briefs/RF2b-recon-rate-definition.md`.
4. VQ — next small fix pack: `src/backfill/batch_validation_backfill.py::_get_spot` forward-fill
   (same defect family as VR1 fix 2; feeds the ledger); security sweep of
   `scripts/apply_phase1_migrations.py:11` + `scripts/recompute_validation_stats.py:12` hardcoded
   fallbacks; retire `scripts/backfill_validation_net.sql` (stale mapping + cost table).
5. VR2 — operational gate (after VR1R passes): top-up prices (`populate_historical_prices.py`) →
   `ledger_snapshot.py` → re-run audit → review diff report → supersede+rewrite only mismatched rows
   via sanctioned writer API → re-audit (expect zero unexplained diffs) → refresh `validation_stats`
   (`src/backfill/batch_validation_stats.py`) → report. VR1 live smoke: 19,491 rows, 589 flagged
   (cross_pair_corrupt 15 / gross 258 / flag 41 / net 243 / brier 34 / cost 21 / no_prices 350).
6. Analysis stream — full-history + live signal-edge tables done; next: layer2/composite behavior
   map + strategy redesign proposals (post-fix measurement first).
7. Data-quality stream — remaining: stray AUDUSD signals row, `cot_signals_join` percentile
   divergence, `gross_mismatch` bucket triage from the VR2 audit.
8. Desk backlog — T07 (broker read-only; resumes Monday 2026-10-19) → T08+; desk re-runs after LRH.

Raw DB forensic scripts used for the above (temp, read-only): `replay_lifecycle_diag`,
`cot_coverage`, `live_rate_diag`, `yields_coverage`, `edge_tables`, `sign_check`, `val_audit2`,
`val_indexes`, `stats_check` — all under `C:\Users\sakha\AppData\Local\Temp\opencode\`.

## Edge tables (full history, joined validation_log × regime_calls, n=19,484)

- **RECON Era (2.1-m3, ~19k calls):** EURUSD WR5 0.469 (n=2767) / WR20 0.497; USDJPY
  0.475 (n=6657) / 0.479; USDINR 0.492 (n=3077) / **0.555**. No family has positive edge:
  rate agree/oppos ≈ 0.46/0.50 (EUR), vol agreement is *anti-predictive* (0.431 vs 0.485 EUR;
  0.455 vs 0.492 JPY). USDJPY recon has no COT (n=4 agree) and no OI agreement (n=0).
- **LIVE Era (2.0-live, n=320 joined):** EURUSD WR5 **0.143** (n=35), WR20 0.118 (n=17);
  USDJPY 0.339 (n=62), WR20 0.78 (n=50); USDINR 0.375 (n=88) / 0.529 (n=70). Regen
  `GROWTH_SURPRISE_USD` 0/10; USDINR "rate disagrees with prediction" 0/22.
- Caveat: `log_return_net_bps_t5` sign convention needs verification before trusting the
  net-edge numbers (±493 bps/call is implausible → likely call-signed already).
- Implication: the composite stack has no measurable edge in recon either — the 55% target
  needs signal-level redesign after correctness fixes, not tuning.

## Validation-ledger integrity findings (read-only, 2026-10-18)

- **Cross-pair price contamination (proven).** `pipeline/scripts/_bulk_backfill_validation_rest.py::_load_prices`
  paginates `historical_prices` and assigns ALL pairs' rows to every pair dict (no `.eq("pair", pair)`),
  so each "pair" series is a merge of all pairs (last id wins per date). Result: identical impossible
  values across pairs — 2026-05-20 `−5057.66 bps` on EURUSD *and* USDINR; 2026-05-21 all three
  `−5033.42`; 2026-05-24/25 all three `+44127.94 / +44018.52`; 2003-12-01 EURUSD `−36218.27`.
  Several are flagged `correct=true` and are non-superseded → they feed the live metrics.
- `_get_spot` also forward-fills (uses FUTURE dates within 10 days) → lookahead in scoring.
- **Scorer-generation flag mismatches:** 194 recon rows BULLISH-with-positive-gross but `correct_t5` not
  true; 129 rows BEARISH-with-negative-gross but not true; 4 live rows likewise. (Earlier writers used
  different sign/scoring conventions; flags were never re-derived.)
- `historical_prices` is **stale since 2026-06-29** (live window Jul–Oct has no canonical prices yet).
  `pipeline/scripts/populate_historical_prices.py` exists (yfinance, 3 pairs, additive) — needs a run.
- Sanctioned repair path exists: `writer.bulk_rewrite_validation_rows` (supersede + insert corrected),
  `writer.supersede_validation_row`, `writer.update_validation_log_row`; trigger
  `protect_immutable_validation` blocks T+5 column changes/deletes on scored rows but allows
  `is_superseded` and T+20-only updates. `idx_validation_call_pair (call_date, pair) WHERE NOT superseded`
  is the uniqueness gate. `scripts/ledger_snapshot.py` is the read-only pre-write snapshot (hashes).
- `scripts/backfill_validation_net.py` (repo root) contains a **hardcoded production DB password**
  (L11) and maps `predicted=="UP"/"DOWN"` (calls are BULLISH/BEARISH → would mark everything wrong).
- Site stats (`validation_stats`, as_of 2026-10-17): EURUSD t5 0.467 / rolling-90d 0.158;
  USDJPY 0.473 / 0.382; USDINR 0.492 / 0.600. Ledger truth recomputed for live-era:
  EURUSD WR5 10.2% (net 4.6%), USDJPY 27.3% (net 4.5%), USDINR 30.6% (net 6.5%);
  rolling-90d live: 6.9% / 33.3% / 37.5%. Stats table disagrees with recomputed ledger → refresh needed
  after repair (`src/backfill/batch_validation_stats.py`).

### Repair plan (VR) — gated, two steps

- **VR1 (code only, no DB writes):** fix `_load_prices` pair filter + `_get_spot` backward-only + tests;
  build read-only `pipeline/scripts/audit_validation_rescore.py` (recompute T5/T20 from clean prices,
  diff stored vs corrected, categorized report, JSON/MD output); fix/retire root `backfill_validation_net.py`
  (remove credential, fix mapping).
- **VR2 (operational, gated):** top-up prices (`populate_historical_prices.py`) → snapshot ledger
  (`ledger_snapshot.py`) → run audit → review diff → supersede+rewrite only the mismatched rows via
  sanctioned writer API → re-audit (expect zero unexplained diffs) → refresh `validation_stats` → report.

## Verification gates used by the coordinator

- `pipeline`: `.venv\Scripts\python.exe -m pytest -q` (baseline 657), `-m ruff check .`, `-m mypy .`
- Every fix: focused tests + full suite + lint + types, then coordinator commit; independent
  review for desk packets.
- GitNexus impact tooling broken → risk recorded UNKNOWN + manual caller lists.
