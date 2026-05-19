# PROMPT: DB Session (Supabase SQL Editor) — CORRECTED
## Tool: Supabase Dashboard → SQL Editor → New Query

---

## ⚠️ IMPORTANT CONTEXT

The `special_signal_label` column lives in **`regime_calls`** table, NOT `signals`.  
The `validation_log` table does NOT have `predicted_direction` — it has `call_id` which references `regime_calls`.

---

### Step 1: Fix `regime_calls` special_signal_label (CRITICAL)

```sql
-- ============================================
-- FIX: Update stale special_signal_label in regime_calls
-- ============================================

-- 1a. Fix EURUSD placeholder labels in regime_calls
UPDATE regime_calls
SET special_signal_label = 'Bund-BTP + ECB BS'
WHERE pair = 'EURUSD'
  AND special_signal_label = 'EURUSD_placeholder';

-- 1b. Fix EURUSD old technical labels in regime_calls
UPDATE regime_calls
SET special_signal_label = 'Bund-BTP + ECB BS'
WHERE pair = 'EURUSD'
  AND special_signal_label IN ('frag_risk', 'macro_special');

-- 2. Fix USDJPY old technical labels in regime_calls
UPDATE regime_calls
SET special_signal_label = 'VIX + JPY Funding Stress'
WHERE pair = 'USDJPY'
  AND special_signal_label IN ('VIX_funding_stress', 'VIX_funding_stress_INTV_PROX');

-- 3. Fix USDINR old technical labels in regime_calls
UPDATE regime_calls
SET special_signal_label = 'Oil + DXY + EM Risk'
WHERE pair = 'USDINR'
  AND special_signal_label IN ('EM_oil_DXY', 'EM_oil_DXY_VIX_prem');

-- ============================================
-- VERIFY: Check the results
-- ============================================
SELECT 
  pair,
  COUNT(*) FILTER (WHERE special_signal_label = 'Bund-BTP + ECB BS') AS eurusd_ok,
  COUNT(*) FILTER (WHERE special_signal_label = 'EURUSD_placeholder') AS eurusd_bad,
  COUNT(*) FILTER (WHERE special_signal_label = 'VIX + JPY Funding Stress') AS usdjpy_ok,
  COUNT(*) FILTER (WHERE special_signal_label = 'VIX_funding_stress') AS usdjpy_bad,
  COUNT(*) FILTER (WHERE special_signal_label = 'Oil + DXY + EM Risk') AS usdinr_ok,
  COUNT(*) FILTER (WHERE special_signal_label = 'EM_oil_DXY') AS usdinr_bad
FROM regime_calls
WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR')
GROUP BY pair
ORDER BY pair;
```

**Expected result:** `eurusd_bad = 0`, `usdjpy_bad = 0`, `usdinr_bad = 0`.

---

### Step 2: Verify latest row labels

```sql
SELECT pair, date, special_signal_label, special_signal_value
FROM regime_calls
WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR')
ORDER BY date DESC, pair
LIMIT 9;
```

**Expected:**
- EURUSD rows show `special_signal_label = 'Bund-BTP + ECB BS'`
- USDJPY rows show `special_signal_label = 'VIX + JPY Funding Stress'`
- USDINR rows show `special_signal_label = 'Oil + DXY + EM Risk'`

---

### Step 3: Check validation_log has call_id for joins

```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'validation_log' 
  AND column_name = 'call_id';
```

**Expected:** Returns 1 row with `call_id`. This confirms we can join with `regime_calls`.

---

### Done. Report back: "DB fix applied to regime_calls. Verification passed."
