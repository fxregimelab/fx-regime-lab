# Database Architecture Audit & Strategy

> **Date:** 2026-05-15  
> **Scope:** Align Supabase schema with the pair-specific 3-pair pipeline (EURUSD, USDJPY, USDINR)  
> **Status:** ✅ **COMPLETE** — All migrations applied to production DB
>
> **See `docs/DB_STATUS.md` for the live canonical schema reference.**
>
> **Round 1 Commits (merged to main):**
> 1. `db: add cleanup migration for stale columns (signals, validation_log)`
> 2. `refactor(queries): replace validation_log ghost columns with live data`
> 3. `types: remove stale columns from signals and validation_log types`
> 4. `fix(migrations): resolve duplicate timestamp + broken DROP POLICY; fix pre-existing ruff errors`
>
> **Round 2 Commit (merged to main):**
> 5. `db: drop unused notes from validation_log; clean stale table types`

---

## 1. Executive Summary

The Supabase schema has evolved organically through 40+ migrations. It now contains **stale columns** (added by earlier iterations but never written by the current pipeline), **missing constraints**, and a **TypeScript type definition** that diverges from both the Postgres schema and the Python pipeline. The good news: there is **no USDINR COT table** (the data lives in the shared `signals` table, which is correct). The bad news: the `signals` table has 8 columns that are never populated, and 2 columns added by migration that the pipeline never writes to.

**Recommendation:** **Surgical cleanup via migration** (Option A). Do **not** scrap and rebuild — the immutable ledgers (`regime_calls`, `validation_log`) contain forward-walked validation history that cannot be regenerated without replaying months of market data.

---

## 2. Current State Audit

### 2.1 Table Inventory

| Table | Purpose | Row Count Est. | Immutable? |
|---|---|---|---|
| `regime_calls` | Daily regime + composite per pair | ~2,000 | **Yes** (trigger) |
| `signals` | Raw signal snapshot per pair per day | ~2,000 | No |
| `validation_log` | T+5 / T+20 outcome scoring | ~1,500 | **Yes** (conditional trigger) |
| `brief` | Per-pair AI-generated narrative | ~2,000 | No |
| `brief_log` | Daily systemic synthesis | ~300 | No |
| `historical_prices` | OHLCV per pair | ~15,000 | No |
| `macro_events` | Economic calendar | ~200 | No |
| `audit_log` | Immutable audit trail | Growing | Append-only |
| `desk_open_cards` | Layer-3 execution HUD | ~2,000 | No |
| `strategy_ledger` | Alpha edge tracking | ~500 | No |
| `research_analogs` | Historical analog matches | ~200 | No |
| `event_risk_matrices` | MIE / tail-risk per event | ~100 | No |
| `universe` | Instrument registry (7 pairs) | 7 | No |
| `pipeline_errors` | Structured exception log | ~50 | No |
| `ai_usage_log` | AI request metering | ~100 | No |
| `health_checks` | Pipeline health telemetry | ~100 | No |
| `research_memos` | Memo archive | ~20 | No |

### 2.2 `signals` Table — Column-Level Audit

**Pipeline writes 37 columns. DB has 45. Gap = 8 stale columns.**

| Column | In Pipeline | In DB Types | Written By | Stale? | Action |
|---|---|---|---|---|---|
| `pair` | ✅ | ✅ | writer.py | — | Keep |
| `date` | ✅ | ✅ | writer.py | — | Keep |
| `rate_diff_2y` | ✅ | ✅ | writer.py | — | Keep |
| `rate_diff_10y` | ✅ | ✅ | writer.py | — | Keep |
| `cot_percentile` | ✅ | ✅ | writer.py | — | Keep |
| `realized_vol_20d` | ✅ | ✅ | writer.py | — | Keep |
| `realized_vol_5d` | ✅ | ✅ | writer.py | — | Keep |
| `implied_vol_30d` | ✅ | ✅ | writer.py | — | Keep |
| `spot` | ✅ | ✅ | writer.py | — | Keep |
| `day_change` | ✅ | ✅ | writer.py | — | Keep |
| `day_change_pct` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_vix` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_dxy` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_oil` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_us10y` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_gold` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_copper` | ✅ | ✅ | writer.py | — | Keep |
| `cross_asset_stoxx` | ✅ | ✅ | writer.py | — | Keep |
| `oi_delta` | ✅ | ✅ | writer.py | — | Keep |
| `volume_rvol` | ✅ | ✅ | writer.py | — | Keep |
| `structural_instability` | ✅ | ✅ | writer.py | — | Keep |
| `breakeven_inflation_10y` | ✅ | ✅ | writer.py | — | Keep |
| `rate_diff_10y_real` | ✅ | ✅ | writer.py | — | Keep |
| `rate_z_tactical` | ✅ | ✅ | writer.py | — | Keep |
| `rate_z_structural` | ✅ | ✅ | writer.py | — | Keep |
| `realized_vol_rank` | ✅ | ✅ | writer.py | — | Keep |
| `skew_alignment` | ✅ | ✅ | writer.py | — | Keep |
| `risk_reversal_25d` | ✅ | ✅ | writer.py | — | Keep |
| `fpi_flow` | ✅ | ✅ | writer.py | — | Keep |
| `cot_net_pos` | ✅ | ✅ | writer.py | — | Keep |
| `cot_asset_mgr_net` | ✅ | ✅ | writer.py | — | Keep |
| `cot_lev_money_net` | ✅ | ✅ | writer.py | — | Keep |
| `ecb_balance_sheet` | ✅ | ✅ | writer.py | — | Keep |
| `bund_btp_spread` | ✅ | ✅ | writer.py | — | Keep |
| `boj_policy_rate` | ✅ | ✅ | writer.py | — | Keep |
| `india_vix` | ✅ | ✅ | writer.py | — | Keep |
| `inr_forward_premium` | ✅ | ✅ | writer.py | — | Keep |
| `rate_diff_mom` | ❌ | ✅ | — | **Yes** | **Drop** |
| `realized_vol_21` | ❌ | ✅ | — | **Yes** | **Drop** |
| `atm_vol` | ❌ | ✅ | — | **Yes** | **Drop** |
| `oi_price_alignment` | ❌ | ✅ | — | **Yes** | **Drop** |
| `rate_diff_zscore` | ❌ | ✅ | — | **Yes** | **Drop** |
| `vol_skew` | ❌ | ✅ | — | **Yes** | **Drop** |
| `id` | N/A | ✅ | Auto | — | Keep |
| `created_at` | N/A | ✅ | Auto | — | Keep |

### 2.3 `regime_calls` Table — Column-Level Audit

All columns in `database.types.ts` are either (a) fields of the `RegimeCall` dataclass, (b) auto-generated (`id`, `created_at`), or (c) audit fields (`write_hash`, `correlation_id`). **No stale columns detected.**

| Field | Source | Status |
|---|---|---|
| `regime`, `confidence`, `signal_composite`, `rate_signal`, `primary_driver` | `RegimeCall` dataclass | ✅ |
| `cot_signal`, `vol_signal`, `oi_signal`, `rr_signal` | `RegimeCall` dataclass | ✅ |
| `special_signal_value`, `special_signal_label` | `RegimeCall` dataclass | ✅ |
| `entry_timing`, `position_size`, `stop_level` | `RegimeCall` dataclass | ✅ |
| `data_quality_score`, `stress_level` | `RegimeCall` dataclass | ✅ |
| `predicted_direction`, `directional_bias`, `conviction` | `RegimeCall` dataclass | ✅ |
| `model_version` | `RegimeCall` dataclass | ✅ |
| `write_hash`, `correlation_id` | Audit / tamper-evident | ✅ |

### 2.4 `validation_log` Table — Column-Level Audit

The validation log has the most organic growth. Many columns exist from early iterations:

| Column | Origin | Written By Current Pipeline? | Action |
|---|---|---|---|
| `id`, `date`, `pair`, `call`, `outcome`, `return_pct` | Initial schema | Legacy only | Keep (legacy rows) |
| `call_id` | Round 1 audit | ✅ `write_validation_row` | Keep |
| `validation_date`, `is_correct`, `pnl_bps` | Round 1 audit | ❌ Never populated | **Drop** |
| `call_date` | Round 3 validation | ✅ | Keep |
| `actual_direction_t5`, `actual_direction_t20` | Round 3 validation | ✅ | Keep |
| `log_return_t5_bps`, `log_return_t20_bps` | Round 3 validation | ✅ | Keep |
| `correct_t5`, `correct_t20` | Round 3 validation | ✅ | Keep |
| `brier_score_t5`, `brier_score_t20` | Round 3 validation | ✅ | Keep |
| `is_superseded` | Round 3 validation | ✅ | Keep |
| `actual_return_20d`, `correct_20d`, `brier_20d` | P0 immutability | Partial (T+20 backfill) | Keep |
| `brier_5d` | P0 immutability | Partial | Keep |
| `actual_return_1d`, `alpha_return_1d`, `correct_1d`, `dxy_return_1d` | Early iterations | ❌ Stale | **Drop** |
| `max_intraday_adverse_bps` | Early iterations | ❌ Stale | **Drop** |
| `predicted_direction`, `predicted_regime` | Early iterations | ❌ Stale | **Drop** |
| `regime_at_call`, `vol_regime_at_call` | Early iterations | ❌ Stale | **Drop** |
| `notes` | Early iterations | Possibly | Review |
| `confidence` | Early iterations | Possibly | Review |
| `created_at` | Auto | — | Keep |

### 2.5 Other Tables

- **`brief`**: Clean. Matches `write_brief()` signature.
- **`brief_log`**: Clean. Matches `write_brief_log()` signature.
- **`historical_prices`**: Clean. Matches `write_historical_prices()` signature.
- **`macro_events`**: Clean. Matches `write_macro_events()` signature.
- **`desk_open_cards`**: Clean. Matches `DeskOpenCardRow` dataclass.
- **`strategy_ledger`**: Clean. Matches `StrategyLedgerRow` dataclass.
- **`audit_log`**: Clean. P0 immutability migration.
- **`pipeline_errors`**: Clean. P1 audit trail fix.
- **`universe`**: Clean. 7 rows, matches `universe.json`.
- **`research_analogs`**, `event_risk_matrices`, `health_checks`, `research_memos`: Clean.

---

## 3. Pair-Specific Validity Rules

The 3-pair lock means certain columns are **always NULL** for certain pairs. This is expected and correct — the schema should remain a **shared sparse table**, not split into pair-specific tables.

| Column | EURUSD | USDJPY | USDINR | Rationale |
|---|---|---|---|---|
| `ecb_balance_sheet` | ✅ Data | ❌ NULL | ❌ NULL | ECB is EUR-specific |
| `bund_btp_spread` | ✅ Data | ❌ NULL | ❌ NULL | Bund-BTP is EUR fragmentation |
| `boj_policy_rate` | ❌ NULL | ✅ Data | ❌ NULL | BoJ is JPY-specific |
| `india_vix` | ❌ NULL | ❌ NULL | ✅ Data | India-specific stress |
| `inr_forward_premium` | ❌ NULL | ❌ NULL | ✅ Data | INR forward market |
| `cot_percentile` | ✅ Data | ✅ Data | ⚠️ Fallback | USDINR uses `net_long` fallback (no liquid futures) |
| `cot_net_pos` | ✅ Data | ✅ Data | ⚠️ Fallback | Same as above |
| `cot_asset_mgr_net` | ✅ Data | ✅ Data | ⚠️ Fallback | Same as above |
| `cot_lev_money_net` | ✅ Data | ✅ Data | ⚠️ Fallback | Same as above |
| `fpi_flow` | ❌ NULL | ❌ NULL | ✅ Data | NSDL FPI is INR-specific |

> **Verdict:** The shared-table design is correct. Splitting into pair-specific tables would create 3× the migration surface and complicate the writer. The sparse column approach is the right trade-off for a 3-pair system.

---

## 4. Strategy Options

### Option A: Surgical Cleanup (Recommended)

**Approach:** One migration that drops stale columns, adds any missing ones, and syncs `database.types.ts`.

**Pros:**
- Preserves all immutable ledger history
- Zero data loss
- Can be done in ~30 minutes
- Writer.py and types.ts stay in sync

**Cons:**
- Does not eliminate migration debt (40+ files remain)
- Cannot rename columns easily (would break existing queries)

**Migration scope:**
1. `signals`: Drop 6 stale columns (`rate_diff_mom`, `realized_vol_21`, `atm_vol`, `oi_price_alignment`, `rate_diff_zscore`, `vol_skew`)
2. `validation_log`: Drop 10 stale columns (`validation_date`, `is_correct`, `pnl_bps`, `actual_return_1d`, `alpha_return_1d`, `correct_1d`, `dxy_return_1d`, `max_intraday_adverse_bps`, `predicted_direction`, `predicted_regime`, `regime_at_call`, `vol_regime_at_call`)
3. `database.types.ts`: Regenerate / manually sync to match cleaned schema
4. `SignalRow` dataclass: Remove `rate_diff_mom` and `realized_vol_21` if they were ever added (they were not)
5. `web/src/lib/supabase/queries.ts`: Remove references to dropped columns

### Option B: Rebuild from Scratch

**Approach:** Dump historical data, drop all tables, create a single clean migration, reload data.

**Pros:**
- Perfectly clean schema
- Single source of truth (one migration file)

**Cons:**
- **Loses immutable ledger metadata**: `write_hash`, `correlation_id`, audit_log references
- `regime_calls` trigger makes bulk-reinsertion painful (would need to disable trigger)
- `validation_log` conditional trigger even more painful
- Historical price data (~15k rows) must be re-fetched or dumped/reloaded
- Risk of data corruption during dump/load
- Estimated effort: 4-6 hours vs. 30 minutes for Option A

**Verdict:** Overkill. The schema is not broken — it just has cosmetic staleness.

### Option C: Ignore & Document

**Approach:** Leave stale columns in place, add comments, update documentation.

**Pros:** Zero risk.

**Cons:**
- TypeScript types continue to lie about available data
- Frontend developers may build features around `atm_vol` or `vol_skew` that are always NULL
- Database hygiene degrades over time

**Verdict:** Unacceptable. The user explicitly requested no empty/invalid tables.

---

## 5. Recommended Execution Plan (Option A)

### Phase 1: Preparation (5 min)

1. **Backup:** `supabase db dump` or export critical tables (`regime_calls`, `validation_log`, `signals`)
2. **Freeze pipeline:** Ensure no runs are scheduled during migration window
3. **Open PR branch:** `git checkout -b db-cleanup-migration`

### Phase 2: Migration SQL (10 min)

Create `supabase/migrations/20260515000004_db_cleanup_stale_columns.sql`:

```sql
-- ============================================================
-- DB Cleanup: Remove stale columns that are never written by
-- the current 3-pair pipeline (post M.1-M.3).
-- ============================================================

-- 1. signals: drop columns never populated by writer.py
ALTER TABLE public.signals
    DROP COLUMN IF EXISTS rate_diff_mom,
    DROP COLUMN IF EXISTS realized_vol_21,
    DROP COLUMN IF EXISTS atm_vol,
    DROP COLUMN IF EXISTS oi_price_alignment,
    DROP COLUMN IF EXISTS rate_diff_zscore,
    DROP COLUMN IF EXISTS vol_skew;

-- 2. validation_log: drop columns from early iterations
ALTER TABLE public.validation_log
    DROP COLUMN IF EXISTS validation_date,
    DROP COLUMN IF EXISTS is_correct,
    DROP COLUMN IF EXISTS pnl_bps,
    DROP COLUMN IF EXISTS actual_return_1d,
    DROP COLUMN IF EXISTS alpha_return_1d,
    DROP COLUMN IF EXISTS correct_1d,
    DROP COLUMN IF EXISTS dxy_return_1d,
    DROP COLUMN IF EXISTS max_intraday_adverse_bps,
    DROP COLUMN IF EXISTS predicted_direction,
    DROP COLUMN IF EXISTS predicted_regime,
    DROP COLUMN IF EXISTS regime_at_call,
    DROP COLUMN IF EXISTS vol_regime_at_call;
```

### Phase 3: TypeScript Sync (10 min)

1. Regenerate `web/src/lib/supabase/database.types.ts` from the cleaned schema.
   - If using `supabase gen types`, run: `supabase gen types typescript --project-id <ref> > web/src/lib/supabase/database.types.ts`
   - If manually maintained, delete the dropped columns from the `signals` and `validation_log` Row/Insert/Update types.
2. Update `web/src/lib/supabase/queries.ts`:
   - Remove `rate_diff_mom`, `realized_vol_21`, `atm_vol`, `oi_price_alignment`, `rate_diff_zscore`, `vol_skew` from `LatestSignal` interface and `toLatestSignal()` if present.
3. Run `npm run build` to verify TypeScript compiles.

### Phase 4: Pipeline Sync (5 min)

1. Verify `pipeline/src/types.py` `SignalRow` does **not** reference dropped columns.
   - Current state: `SignalRow` already does not have `rate_diff_mom`, `realized_vol_21`, `atm_vol`, etc. ✅
2. Verify `pipeline/src/db/writer.py` `write_signal_row()` does **not** reference dropped columns.
   - Current state: Writer already does not write them. ✅
3. Run `pytest` to confirm pipeline tests pass.

### Phase 5: Validation & Rollout (5 min)

1. **Local test:** Apply migration to local Supabase, run `pytest`, run `npm run build`
2. **Staging:** Apply to staging project, run a single pipeline date, verify rows insert cleanly
3. **Production:** Apply via Supabase dashboard or CLI `supabase db push`
4. **Smoke test:** Query `signals` and `validation_log` from frontend, confirm no errors

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Dropping a column that the web app still references | Low | High | grep all `web/src/` for column names before dropping |
| Dropping a column that a legacy query still uses | Low | Medium | Check `_legacy_archive/` and `docs/` for references |
| `supabase db push` fails due to dependency (view/index) | Medium | Medium | Migration uses `IF EXISTS`; check for dependent views first |
| TypeScript build fails after type sync | Low | High | Run `npm run build` before committing |
| Pipeline fails because writer tries to write dropped column | Very Low | High | Writer already does not write these columns |

---

## 7. Future Hygiene Rules

To prevent this drift from recurring:

1. **Column addition policy:** Every new column added to `signals` or `regime_calls` must be:
   - Added to `pipeline/src/types.py` dataclass
   - Added to `pipeline/src/db/writer.py` payload
   - Added to `web/src/lib/supabase/database.types.ts`
   - Added to `web/src/lib/supabase/queries.ts` if exposed to UI
   - Documented in `docs/DATABASE_SCHEMA.md`

2. **Pre-commit hook:** Add a script that diffs `SignalRow` fields against `database.types.ts` signals Row.

3. **Monthly audit:** Run `SELECT column_name, COUNT(*) FROM signals GROUP BY column_name` to detect always-NULL columns.

4. **Migration naming:** Use descriptive names (`add_eur_special_signal_cols`) instead of timestamps-only.

---

## 8. Post-M.5 Notes

Phase M.5 (Diagnostic Calibration & Validation) added diagnostic scripts that **read** from existing tables only — no new columns were added. The `simulation_engine.py` v2 function reads the following already-audited columns:

- `ecb_balance_sheet`, `bund_btp_spread` — EURUSD special signal (Stream A)
- `boj_policy_rate` — USDJPY rate input (Stream A)
- `india_vix`, `inr_forward_premium` — USDINR macro inputs (Stream A)
- `cot_asset_mgr_net`, `cot_lev_money_net` — COT smart spread (M.3.3)
- `rate_z_tactical`, `rate_z_structural` — z_blended (M.3.2)
- `fpi_flow` — USDINR FPI proxy (v2)

All of these columns are already in the pipeline `SignalRow` dataclass and are written by `writer.py`. No schema changes required for M.5.

## 9. Appendices

### A. Full `signals` column matrix

See Section 2.2 for the complete audit.

### B. Commands used for this audit

```bash
# List all migrations
ls supabase/migrations/

# Extract all CREATE TABLE / ADD COLUMN statements
grep -n "CREATE TABLE\|ADD COLUMN" supabase/migrations/*.sql

# Compare pipeline fields to DB types
python3 -c "import re; ..."

# Find unused columns in web/src/
python3 -c "import os, re; ..."
```

### C. Related docs

- `docs/DATABASE_SCHEMA.md` — High-level schema documentation
- `docs/PIPELINE_REFERENCE.md` — Writer module contract
- `docs/IMMUTABILITY.md` — Ledger immutability rules
- `AGENTS.md` — Hard rules (3-pair lock, immutable tables)
