# Backend Prompt: Stream A — Signal Depth (Tasks A.1–A.6)

> **Session Type:** Backend / Pipeline  
> **Tier:** 2 (New fetchers, no threshold changes, no immutable table edits)  
> **IDENTITY Gate:** Phase A met  
> **Scope:** Add 6 pair-specific macro signals. No architecture rebuild. All new data feeds into the EXISTING composite via new `signals` table columns or the `special_signal` slot.

---

## 🎯 Objective

Add 6 new pair-specific macro data signals to reduce model underfitting. Each signal must:
1. Have a dedicated fetcher function
2. Be stored in the `signals` table (new column or existing slot)
3. Be documented in the methodology
4. Have unit tests
5. Be wired into the daily orchestrator

---

## 📁 Files You Will Modify

| File | Purpose |
|------|---------|
| `pipeline/src/fetchers/yields.py` | Add FRED-based fetchers for ECB balance sheet, BoJ policy rate |
| `pipeline/src/fetchers/cross_asset.py` | Add Bund-BTP spread, India VIX, INR forward premium fetchers |
| `pipeline/src/fetchers/fx_spot.py` | Add intervention proximity heuristic (USDJPY spot check) |
| `pipeline/src/scheduler/orchestrator.py` | Wire new fetchers into daily run; populate new signal columns |
| `pipeline/src/db/writer.py` | Ensure new columns are written to `signals` table |
| `pipeline/src/types.py` | Add new fields to `SignalRow` dataclass if needed |
| `web/src/lib/supabase/database.types.ts` | Add new columns to `signals` table TypeScript types |
| `supabase/migrations/` | Create migration to add new columns to `signals` table |
| `pipeline/tests/test_signals.py` or new test files | Unit tests for each new signal/fetcher |

---

## 🔧 Task A.1: EURUSD — ECB Balance Sheet (ECBASSETSW)

**Data Source:** FRED series `ECBASSETSW` — ECB Total Assets (weekly, millions of EUR)  
**What it measures:** Eurozone balance sheet expansion/contraction. Expansion = EUR weakness pressure.

> **Note:** `ECBASSETSW` replaces the discontinued `ECBASSETS` and invalid `WBSDTLEZ`. It is current to present and updates weekly.

### Implementation

1. **Add fetcher function** in `pipeline/src/fetchers/yields.py` (or create `pipeline/src/fetchers/ecb.py` if you prefer separation):

```python
def fetch_ecb_balance_sheet(fred: Fred | None = None) -> float | None:
    """Fetch latest ECB total assets (ECBASSETSW) from FRED.
    
    Returns the latest value in billions EUR, or None if unavailable.
    The FRED series is in millions of EUR — divide by 1000 before returning.
    """
```

- Use `fredapi.Fred` with `FRED_API_KEY` env var (same pattern as `_fred_leg` in `yields.py`)
- Series ID: `ECBASSETSW`
- Call `fred.get_series_latest_release("ECBASSETSW")`
- Divide by 1000 to convert millions → billions EUR
- Return the most recent non-null value as `float`
- Log warnings on failure, never raise

2. **Add column to `signals` table:**
- Migration: `ALTER TABLE public.signals ADD COLUMN ecb_balance_sheet float;`
- TypeScript: Add `ecb_balance_sheet: number | null;` to `signals` Row/Insert/Update types
- `SignalRow` dataclass: Add `ecb_balance_sheet: float | None = None`

3. **Wire into orchestrator:**
- In the EURUSD signal generation path, call `fetch_ecb_balance_sheet()`
- Store raw value in `signals.ecb_balance_sheet`
- Compute z-score vs 2-year (504 trading days) history and store in `special_signal_value` for EURUSD only (or create a new `ecb_balance_zscore` column)

4. **Test:**
```python
def test_fetch_ecb_balance_sheet_smoke():
    result = fetch_ecb_balance_sheet()
    assert result is None or isinstance(result, float)
    if result:
        assert result > 0  # ECB balance sheet is always positive
```

---

## 🔧 Task A.2: EURUSD — Bund-BTP Spread

**Data Source:** FRED series `IRLTLT01DEM156N` (Germany 10Y) and `IRLTLT01ITM156N` (Italy 10Y)  
**What it measures:** 10Y Bund - 10Y BTP. Widening = fragmentation risk = EUR weakness.

> **Note:** `IRLTLT01DEM156N` is ALREADY used in `yields.py` for the Germany 10Y yield. Re-use the existing fetch logic — do not create a duplicate FRED call.

### Implementation

1. **Add fetcher function** in `pipeline/src/fetchers/yields.py`:

```python
def fetch_bund_btp_spread(fred: Fred | None = None) -> float | None:
    """Compute 10Y Bund - 10Y BTP spread from FRED.
    
    Returns spread in percentage points, or None if either leg missing.
    
    IMPORTANT: Re-use the existing Germany 10Y fetch (IRLTLT01DEM156N)
    already present in this module. Do not duplicate the FRED call.
    """
```

- Fetch `IRLTLT01ITM156N` (Italy 10Y) via `_fred_leg`
- Re-use the existing Germany 10Y value (`IRLTLT01DEM156N`) already fetched for yields
- Return `bund - btp` (not absolute value — positive = Bund trades above BTP)

2. **Add column to `signals` table:**
- Migration: `ALTER TABLE public.signals ADD COLUMN bund_btp_spread float;`
- TypeScript: Add `bund_btp_spread: number | null;`
- `SignalRow`: Add `bund_btp_spread: float | None = None`

3. **Wire into orchestrator:**
- Store raw spread in `signals.bund_btp_spread`
- For EURUSD composite: when spread widens above 2.0 standard deviations from 1-year mean, amplify `special_signal_value` toward EUR weakness (negative)

4. **Test:**
```python
def test_fetch_bund_btp_spread():
    spread = fetch_bund_btp_spread()
    assert spread is None or isinstance(spread, float)
```

---

## 🔧 Task A.3: USDJPY — BoJ Policy Rate

**Data Source:** FRED series `IRSTCI01JPM156N` — OECD Japan Call Money/Interbank Rate  
**What it measures:** Japan policy rate proxy. Tracks BoJ policy rate closely (currently ~0.73% vs BoJ's 0.75%). Used to compute US-JP rate differential.

> **Note:** `INTDSRJPM193N` (IMF BoJ discount rate) is STALE — ends Apr 2017. `IRSTCI01JPM156N` (OECD) is current to present and closely tracks the actual BoJ policy rate.

### Implementation

1. **Add fetcher function** in `pipeline/src/fetchers/yields.py`:

```python
def fetch_boj_policy_rate(fred: Fred | None = None) -> float | None:
    """Fetch latest BoJ policy rate proxy (IRSTCI01JPM156N) from FRED.
    
    Returns rate in percent, or None if unavailable.
    
    NOTE: Uses IRSTCI01JPM156N (OECD Japan call money rate) instead of
    the stale INTDSRJPM193N. This series tracks the BoJ policy rate
    with minimal lag and is current to present.
    """
```

- Series ID: `IRSTCI01JPM156N`
- Return latest non-null value

2. **Add column to `signals` table:**
- Migration: `ALTER TABLE public.signals ADD COLUMN boj_policy_rate float;`
- TypeScript: Add `boj_policy_rate: number | null;`
- `SignalRow`: Add `boj_policy_rate: float | None = None`

3. **Wire into orchestrator:**
- Store in `signals.boj_policy_rate`
- Compute `us_2y - boj_rate` as an additional rate differential context for USDJPY
- This does NOT replace the existing `rate_diff_2y` — it supplements it

4. **Test:**
```python
def test_fetch_boj_policy_rate():
    rate = fetch_boj_policy_rate()
    assert rate is None or (isinstance(rate, float) and -1.0 <= rate <= 1.0)
```

---

## 🔧 Task A.4: USDJPY — Intervention Proximity Flag

**Data Source:** Synthetic — derived from USDJPY spot price  
**What it measures:** When USDJPY approaches 160 (historical BoJ intervention zone), raise special factor weight.

### Implementation

1. **Add function** in `pipeline/src/signals/special.py` (or `pipeline/src/signals/intervention.py`):

```python
def compute_intervention_proximity(spot: float | None) -> float | None:
    """Return intervention proximity score for USDJPY.
    
    - spot >= 160 → returns 1.0 (intervention zone)
    - spot <= 150 → returns 0.0 (safe zone)
    - 150 < spot < 160 → linear interpolation
    - spot is None → returns None
    
    This is a heuristic, not a prediction. Documented in methodology.
    """
```

2. **No new DB column needed.** This feeds into the existing `special_signal_value` for USDJPY.

3. **Wire into orchestrator:**
- In the USDJPY signal path, after fetching spot price, call `compute_intervention_proximity(spot)`
- If result is not None, blend it into `special_signal_value` with weight ~0.15
- Formula: `special_signal = 0.85 * existing_special + 0.15 * intervention_proximity`
- Set `special_signal_label` to include "INTV_PROX" when active

4. **Test:**
```python
def test_intervention_proximity():
    assert compute_intervention_proximity(162.0) == 1.0
    assert compute_intervention_proximity(160.0) == 1.0
    assert compute_intervention_proximity(155.0) == 0.5
    assert compute_intervention_proximity(150.0) == 0.0
    assert compute_intervention_proximity(148.0) == 0.0
    assert compute_intervention_proximity(None) is None
```

---

## 🔧 Task A.5: USDINR — India VIX (INDIAVIX)

**Data Source:** NSE India VIX. Ticker: `INDIAVIX` on Yahoo Finance  
**What it measures:** Indian equity market stress. High VIX = INR weakness pressure.

### Implementation

1. **Add fetcher function** in `pipeline/src/fetchers/cross_asset.py` (or new file `pipeline/src/fetchers/india_vix.py`):

```python
def fetch_india_vix() -> float | None:
    """Fetch latest India VIX from NSE via yfinance.
    
    Returns VIX level, or None if unavailable.
    """
```

- Use yfinance: `yf.Ticker("^INDIAVIX").history(period="5d")`
- Return latest close
- Handle missing data gracefully (return None, log warning)

2. **Add column to `signals` table:**
- Migration: `ALTER TABLE public.signals ADD COLUMN india_vix float;`
- TypeScript: Add `india_vix: number | null;`
- `SignalRow`: Add `india_vix: float | None = None`

3. **Wire into orchestrator:**
- Store in `signals.india_vix`
- For USDINR: high India VIX (> 25 or 90th percentile) amplifies INR weakness signal
- Feed into `special_signal_value` for USDINR

4. **Test:**
```python
def test_fetch_india_vix_smoke():
    vix = fetch_india_vix()
    assert vix is None or (isinstance(vix, float) and vix > 0)
```

---

## 🔧 Task A.6: USDINR — INR 1M Forward Premium

**Data Source:** Computed from RBI reference rate + 1M USD/INR forward  
**What it measures:** Annualized forward premium. Negative/declining premium = INR depreciation pressure.

### Implementation

1. **Add fetcher function** in `pipeline/src/fetchers/cross_asset.py`:

```python
def fetch_inr_forward_premium() -> float | None:
    """Fetch USD/INR 1-month forward premium.
    
    Returns annualized premium in percent, or None if unavailable.
    
    Formula: ((Forward - Spot) / Spot) * (12 / 1) * 100
    
    Data sources (in order of preference):
    1. FRED series (if available)
    2. yfinance USDINR=X 1M forward (if available)
    3. Manual calculation from RBI reference rate + NSE derivatives
    
    For MVP: use yfinance USDINR=X and approximate.
    """
```

- Primary: Try yfinance for USD/INR forward rates
- Fallback: Return None with warning if unavailable
- This is acknowledged as a MVP implementation — document the limitation

2. **Add column to `signals` table:**
- Migration: `ALTER TABLE public.signals ADD COLUMN inr_forward_premium float;`
- TypeScript: Add `inr_forward_premium: number | null;`
- `SignalRow`: Add `inr_forward_premium: float | None = None`

3. **Wire into orchestrator:**
- Store in `signals.inr_forward_premium`
- For USDINR: declining forward premium (more negative) amplifies INR weakness signal
- Feed into `special_signal_value` for USDINR

4. **Test:**
```python
def test_fetch_inr_forward_premium_smoke():
    premium = fetch_inr_forward_premium()
    assert premium is None or isinstance(premium, float)
```

---

## 🗄️ Database Migration Requirements

Create ONE migration file: `supabase/migrations/20260518000002_stream_a_signal_depth.sql`

```sql
-- Stream A: Signal Depth — Add pair-specific macro signal columns

ALTER TABLE public.signals
    ADD COLUMN ecb_balance_sheet float,
    ADD COLUMN bund_btp_spread float,
    ADD COLUMN boj_policy_rate float,
    ADD COLUMN india_vix float,
    ADD COLUMN inr_forward_premium float;

COMMENT ON COLUMN public.signals.ecb_balance_sheet IS 'ECB total assets (ECBASSETSW) in billions EUR. EURUSD macro input.';
COMMENT ON COLUMN public.signals.bund_btp_spread IS '10Y Bund - 10Y BTP in percentage points. EURUSD fragmentation proxy.';
COMMENT ON COLUMN public.signals.boj_policy_rate IS 'BoJ policy rate proxy (IRSTCI01JPM156N) in percent. USDJPY rate differential input.';
COMMENT ON COLUMN public.signals.india_vix IS 'India VIX level. USDINR stress indicator.';
COMMENT ON COLUMN public.signals.inr_forward_premium IS 'USD/INR 1M forward premium annualized in percent. USDINR flow indicator.';
```

**IMPORTANT:** Do NOT modify existing columns. Only ADD new nullable columns.

---

## 🔗 Orchestrator Integration Order

In `pipeline/src/scheduler/orchestrator.py`, find the daily signal generation flow and add calls in this order:

1. After yields are fetched → call `fetch_ecb_balance_sheet()`, `fetch_bund_btp_spread()`, `fetch_boj_policy_rate()`
2. After spot is fetched → call `compute_intervention_proximity(spot)` for USDJPY
3. After cross-asset is fetched → call `fetch_india_vix()`, `fetch_inr_forward_premium()`
4. Store all raw values in `signals` table columns
5. Blend new signals into `special_signal_value` for each pair as specified above

---

## 🧪 Test Requirements

For EACH new fetcher/signal, write tests following the existing pattern in `pipeline/tests/`:

1. **Smoke test:** Function returns expected type or None, does not crash
2. **Range test:** Returned values are within reasonable bounds (e.g., ECB balance sheet > 0)
3. **Edge case test:** Missing data → returns None, logs warning
4. **Intervention proximity test:** Exact values for spot = 148, 150, 155, 160, 162

Place tests in:
- `pipeline/tests/test_signals.py` for signal computation tests
- New file `pipeline/tests/test_macro_fetchers.py` for fetcher tests

**All tests must pass:** `cd pipeline && pytest`

---

## 📋 Verification Checklist

- [ ] `ecb_balance_sheet` column exists in `signals` table and populates for EURUSD
- [ ] `bund_btp_spread` column exists and populates for EURUSD
- [ ] `boj_policy_rate` column exists and populates for USDJPY
- [ ] Intervention proximity heuristic active for USDJPY (spot > 150 triggers non-zero)
- [ ] `india_vix` column exists and populates for USDINR
- [ ] `inr_forward_premium` column exists and populates for USDINR
- [ ] `database.types.ts` has all 5 new columns
- [ ] `SignalRow` dataclass has all 5 new fields
- [ ] Migration file created and can be applied
- [ ] pytest passes (228+ tests)
- [ ] No changes to `regime_calls`, `validation_log`, or other immutable tables
- [ ] No changes to composite weights or thresholds (Stream B territory)

---

## 🚫 What NOT to Do

- Do NOT create pair-specific pipeline classes (that's Stream D)
- Do NOT modify composite weight logic (that's Stream B)
- Do NOT change regime thresholds or Layer 1/2/3 logic
- Do NOT modify `validation_log` or `regime_calls` schema
- Do NOT add execution advice (position_size, stop_level) back into UI
- Do NOT create new API endpoints or external feeds
- Do NOT modify existing signal columns — only ADD new nullable columns
