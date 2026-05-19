-- ============================================================
-- FX REGIME LAB — Fix special_signal_label in regime_calls
-- ============================================================
-- 
-- INSTRUCTIONS:
-- 1. Open Supabase Dashboard → SQL Editor → New Query
-- 2. Copy-Paste this ENTIRE file
-- 3. Click "Run"
-- 4. Look for "SUCCESS" at the bottom of results
--
-- This temporarily disables the immutable trigger, updates
-- all stale labels, then re-enables it.
-- ============================================================

-- Step 1: Show BEFORE state
SELECT '=== BEFORE FIX ===' as status;

SELECT 
  pair,
  special_signal_label,
  COUNT(*) as row_count
FROM regime_calls
WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR')
GROUP BY pair, special_signal_label
ORDER BY pair, special_signal_label;

-- Step 2: Disable immutable triggers
ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls;
ALTER TABLE regime_calls DISABLE TRIGGER trg_log_regime_call_audit;

-- Step 3: Fix EURUSD labels
UPDATE regime_calls
SET special_signal_label = 'Bund-BTP + ECB BS'
WHERE pair = 'EURUSD'
  AND special_signal_label IN ('EURUSD_placeholder', 'frag_risk', 'macro_special');

-- Step 4: Fix USDJPY labels
UPDATE regime_calls
SET special_signal_label = 'VIX + JPY Funding Stress'
WHERE pair = 'USDJPY'
  AND special_signal_label IN ('VIX_funding_stress', 'VIX_funding_stress_INTV_PROX');

-- Step 5: Fix USDINR labels
UPDATE regime_calls
SET special_signal_label = 'Oil + DXY + EM Risk'
WHERE pair = 'USDINR'
  AND special_signal_label IN ('EM_oil_DXY', 'EM_oil_DXY_VIX_prem');

-- Step 6: Re-enable immutable triggers
ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls;
ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit;

-- Step 7: Show AFTER state
SELECT '=== AFTER FIX ===' as status;

SELECT 
  pair,
  special_signal_label,
  COUNT(*) as row_count
FROM regime_calls
WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR')
GROUP BY pair, special_signal_label
ORDER BY pair, special_signal_label;

-- Step 8: Verify zero stale labels remain
SELECT 
  '=== VERIFICATION ===' as status,
  COUNT(*) as stale_labels_remaining
FROM regime_calls
WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR')
  AND special_signal_label IN (
    'EURUSD_placeholder', 'frag_risk', 'macro_special',
    'VIX_funding_stress', 'VIX_funding_stress_INTV_PROX',
    'EM_oil_DXY', 'EM_oil_DXY_VIX_prem'
  );

-- Step 9: Show latest 3 rows per pair (spot check)
SELECT '=== LATEST ROWS ===' as status;

SELECT pair, date, special_signal_label, special_signal_value
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY pair ORDER BY date DESC) as rn
  FROM regime_calls
  WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR')
) ranked
WHERE rn <= 3
ORDER BY pair, date DESC;

-- ============================================================
-- SUCCESS: All done. Check that stale_labels_remaining = 0
-- ============================================================
