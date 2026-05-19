# Backend Prompt: Phase M.1 — Bias Fixes (No-Regret, Zero Overfitting)

> **Session Type:** Backend / Pipeline  
> **Tier:** 2 (Bug fixes + minor weight adjustments, no new model layers)  
> **IDENTITY Gate:** Phase A met  
> **Scope:** Fix 5 causal biases and noise sources. No new data sources. No threshold tuning. No architecture rebuild.

---

## 🎯 Objective

Fix 5 statistical biases and noise sources identified by the triple-persona audit. Each fix must:
1. Be mathematically correct (strictly causal, no look-ahead)
2. Preserve backward compatibility where possible
3. Have unit tests
4. Pass the full test suite (235+ tests)
5. Not change any regime thresholds or composite logic beyond the specified fix

---

## 📁 Files You Will Modify

| File | Task |
|------|------|
| `pipeline/src/signals/cot.py` | M.1.1 Fix look-ahead bias in COT percentile |
| `pipeline/src/signals/special.py` | M.1.2 Fix look-ahead bias in Special percentile |
| `pipeline/src/logic/math_utils.py` | M.1.3 Fix spot Z-score inclusion of current point |
| `pipeline/src/signals/fpi.py` | M.1.4 Replace FPI SD with MAD |
| `pipeline/src/regime/composite.py` | M.1.5 Reduce OI weight to ≤0.05 |

---

## 🔧 M.1.1: Fix Look-Ahead Bias in COT Percentile

**File:** `pipeline/src/signals/cot.py`
**Bug:** The current observation (`last`) is included in the sample `vals` when computing the percentile. This creates an upward bias for extreme values.

**Current buggy code (lines 48-52):**
```python
window_rows = chronological[-window_reports:]
vals = [r.net_long for r in window_rows]
last = vals[-1]
n = len(vals)
pct = 100.0 * sum(1 for v in vals if v <= last) / float(n)
```

**Fix:** Exclude the current observation from the ECDF denominator. The percentile should be computed against the historical distribution only.

**Correct implementation:**
```python
window_rows = chronological[-window_reports:]
vals = [r.net_long for r in window_rows]
last = vals[-1]
hist = vals[:-1]  # Exclude current observation
n = len(hist)
if n == 0:
    return None
pct = 100.0 * sum(1 for v in hist if v <= last) / float(n)
```

**Important considerations:**
- If `window_reports=1`, `hist` will be empty → return `None` (insufficient history)
- If `window_reports < min_reports + 1`, the effective sample is too small → return `None`
- Update the docstring to state: "The current observation is excluded from the reference distribution (strictly causal)."
- Update `min_reports` logic: we need at least `min_reports` historical points AFTER excluding the current observation. So the total window must be at least `min_reports + 1`.

**Test to add in `pipeline/tests/test_cot.py` (or new file):**
```python
def test_cot_percentile_causal() -> None:
    """Current observation must not be in its own reference distribution."""
    from datetime import date, timedelta
    from src.signals.cot import compute_cot_percentile
    from src.types import CotRow

    base = date(2024, 1, 1)
    rows = [
        CotRow(date=base + timedelta(weeks=i), pair="EURUSD", net_long=i * 100, open_interest=1000)
        for i in range(10)
    ]
    # Last net_long = 900. Without look-ahead bias, percentile against 0..800 should be 100.0
    pct = compute_cot_percentile(rows, "EURUSD", window_reports=10, min_reports=5)
    assert pct is not None
    assert pct == 100.0  # 900 is strictly greater than all 9 historical values

def test_cot_percentile_insufficient_history() -> None:
    """When window is too small after excluding current, return None."""
    from datetime import date, timedelta
    from src.signals.cot import compute_cot_percentile
    from src.types import CotRow

    base = date(2024, 1, 1)
    rows = [
        CotRow(date=base + timedelta(weeks=i), pair="EURUSD", net_long=i * 100, open_interest=1000)
        for i in range(3)
    ]
    pct = compute_cot_percentile(rows, "EURUSD", window_reports=3, min_reports=5)
    assert pct is None
```

---

## 🔧 M.1.2: Fix Look-Ahead Bias in Special Percentile

**File:** `pipeline/src/signals/special.py`
**Bug:** `percentile_rank` explicitly takes a `history` that "must include the current print." This biases extreme values toward more extreme percentiles.

**Current buggy code (lines 22-40):**
```python
def percentile_rank(value: float | None, history: Sequence[float] | None) -> float | None:
    """Empirical CDF rank of ``value`` on ``history`` (must include the current print).
    Returns a percentile in ``[0, 1]``, or ``None`` if the sample is too thin or invalid.
    """
    if value is None or not history:
        return None
    raw: list[float] = []
    for x in history:
        if x is None:
            continue
        fv = float(x)
        if np.isfinite(fv):
            raw.append(fv)
    sample = np.array(raw, dtype=np.float64)
    if sample.size < _MIN_RANK_SAMPLE:
        return None
    return float(np.mean(sample <= float(value)))
```

**Fix:** The caller must pass history EXCLUDING the current print. Update the function signature to make this explicit, and update all callers.

**Correct implementation:**
```python
def percentile_rank(value: float | None, history: Sequence[float] | None) -> float | None:
    """Empirical CDF rank of ``value`` on a strictly causal ``history``.

    ``history`` must contain ONLY past observations (the current print must NOT
    be included). Returns a percentile in ``[0, 1]``, or ``None`` if the sample
    is too thin or invalid.
    """
    if value is None or not history:
        return None
    raw: list[float] = []
    for x in history:
        if x is None:
            continue
        fv = float(x)
        if np.isfinite(fv):
            raw.append(fv)
    sample = np.array(raw, dtype=np.float64)
    if sample.size < _MIN_RANK_SAMPLE:
        return None
    return float(np.mean(sample <= float(value)))
```

**Update all callers** to pass history excluding current:

1. **`_norm_from_hist` (line 49-53):** Already receives `hist` separately from `value` — no change needed IF callers pass `hist` without the current value. Verify callers.

2. **`compute_special_signal` — AUDUSD (lines 96-108):**
   ```python
   n_io = _norm_from_hist(iore[-1], iore[:-1])  # Exclude current
   n_cu = _norm_from_hist(cup[-1], cup[:-1])     # Exclude current
   n_au = _norm_from_hist(gld[-1], gld[:-1])     # Exclude current
   ```

3. **`compute_special_signal` — USDCAD (lines 111-125):**
   ```python
   n_wti = _norm_from_hist(oil[-1], oil[:-1])    # Exclude current
   # For change series, current change is oil[-1] - oil[-2]
   # History for change should be changes up to t-1
   ```
   The change series `chg` is built from differences. The current change `chg[-1]` should be scored against `chg[:-1]`.

4. **`compute_special_signal` — USDCHF (lines 127-142):**
   ```python
   n_eurchf = _norm_from_hist(inv_latest, inv_hist[:-1])  # Exclude current
   n_snb = _norm_from_hist(latest, clean[:-1])            # Exclude current
   ```

5. **`compute_special_signal` — USDJPY (lines 144-152):**
   ```python
   n_vix = _norm_from_hist(vix[-1], vix[:-1])   # Exclude current
   ```

6. **`compute_special_signal` — USDINR (lines 154-167):**
   ```python
   n_oil = _norm_from_hist(oil[-1], oil[:-1])   # Exclude current
   n_dxy = _norm_from_hist(dxy[-1], dxy[:-1])   # Exclude current
   ```

**Critical:** The `_tail_hist` function returns the last `_SPECIAL_RANK_WINDOW` closes. When we call `_norm_from_hist(value, hist)`, we must pass `hist` WITHOUT the current value. The cleanest approach is to update `_norm_from_hist` to automatically exclude the last element if it equals `value`, OR update all callers to pass `hist[:-1]`.

**Recommended approach:** Update all callers to pass `hist[:-1]` explicitly. This is more transparent.

**Test to add in `pipeline/tests/test_special.py` (or new file):**
```python
def test_percentile_rank_causal() -> None:
    """Current observation must not be in its own reference distribution."""
    from src.signals.special import percentile_rank

    # Value = 100, history = [0..90] (10 values, excluding current)
    hist = list(range(10))  # 0..9
    pct = percentile_rank(100.0, hist)
    assert pct is not None
    assert pct == 1.0  # 100 is greater than all 10 historical values

    # Value = 5, history = [0..9] excluding 5
    hist_no5 = [0, 1, 2, 3, 4, 6, 7, 8, 9]
    pct = percentile_rank(5.0, hist_no5)
    assert pct is not None
    assert pct == 0.5  # 5 is greater than 0..4 (5 values) out of 9

def test_percentile_rank_insufficient_sample() -> None:
    """Return None when history is too short."""
    from src.signals.special import percentile_rank, _MIN_RANK_SAMPLE

    hist = list(range(_MIN_RANK_SAMPLE - 1))
    pct = percentile_rank(5.0, hist)
    assert pct is None
```

---

## 🔧 M.1.3: Fix Spot Z-Score Inclusion of Current Point

**File:** `pipeline/src/logic/math_utils.py`
**Bug:** The `rolling_zscore_series` or `rolling_zscore_last` function includes the observation being scored in its own mean and variance calculation.

**Investigate the implementation.** Find the function that computes rolling Z-scores for spot returns in `math_utils.py`. The current implementation likely uses a window that includes the current index:

```python
# Hypothetical buggy pattern:
window = series[i - window_size + 1 : i + 1]  # Includes i
mean = np.mean(window)
std = np.std(window)
z = (series[i] - mean) / std
```

**Fix:** Use a strictly causal window that excludes the current observation:

```python
# Correct pattern:
window = series[i - window_size : i]  # Excludes i
mean = np.mean(window)
std = np.std(window)
z = (series[i] - mean) / std
```

**Important:** This function may be used in multiple places. Verify ALL callers to ensure the causal window is appropriate:
- `layer1_gate.py` — spot return Z-score (`d_spot`)
- Any other signal that uses rolling Z-scores

If the function is shared and some callers need the inclusive window while others need the exclusive window, create a new `rolling_zscore_last_causal` function rather than breaking existing callers.

**Test to add:**
```python
def test_rolling_zscore_causal() -> None:
    """Rolling Z-score must not include the current observation in its reference window."""
    import numpy as np
    from src.logic.math_utils import rolling_zscore_last

    series = np.array([1.0, 2.0, 3.0, 4.0, 100.0], dtype=np.float64)
    # With a causal window of 4, the Z of 100.0 should use mean/std of [1, 2, 3, 4]
    z = rolling_zscore_last(series, window=4, min_periods=3)
    expected_mean = 2.5
    expected_std = np.std([1.0, 2.0, 3.0, 4.0], ddof=0)
    expected_z = (100.0 - expected_mean) / expected_std
    assert z is not None
    assert abs(z - expected_z) < 1e-10
```

**Note:** If the current implementation already excludes the current point, document this explicitly in the docstring and skip this task. But the audit report explicitly flagged this as a bug — verify carefully.

---

## 🔧 M.1.4: Replace FPI SD with MAD

**File:** `pipeline/src/signals/fpi.py`
**Bug:** The FPI signal uses population standard deviation on a 20-day window. FPI flows are outlier-prone (policy announcements, month-end flows). SD has breakdown point 0% — a single outlier dominates the Z-score. This is also inconsistent with the rate signal which uses MAD.

**Current buggy pattern (investigate exact lines):**
```python
# FPI signal likely computes something like:
mean = np.mean(flows_20d)
std = np.std(flows_20d, ddof=0)  # Population SD
z = (latest - mean) / std
```

**Fix:** Replace with MAD-based robust Z-score, consistent with `rate.py`:

```python
import numpy as np

MAD_NORMAL_SCALE = 1.4826
MAD_NOISE_FLOOR = 0.0001

def _mad_z(values: np.ndarray, value: float) -> float | None:
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med)))
    if mad < MAD_NOISE_FLOOR:
        return 0.0
    z = (value - med) / (mad * MAD_NORMAL_SCALE)
    return float(z)

# In the FPI signal computation:
# flows = np.array(historical_fpi_flows, dtype=np.float64)
# latest = flows[-1]
# hist = flows[:-1]  # Causal
# z = _mad_z(hist, latest)
```

**Important:**
- Use causal history (exclude current observation)
- Clip the resulting Z to [-1, 1] if that's the current contract
- Ensure `MAD_NORMAL_SCALE = 1.4826` is used (same as `rate.py`)
- Handle empty or near-constant history gracefully (return 0.0 or None)

**Test to add:**
```python
def test_fpi_signal_mad_robust() -> None:
    """FPI signal should use MAD, not SD, and be robust to outliers."""
    import numpy as np
    from src.signals.fpi import compute_fpi_signal  # or whatever the function is called

    # 19 days of calm flows + 1 outlier today
    flows = [100.0] * 19 + [10000.0]
    signal = compute_fpi_signal(flows)
    # With SD, the outlier would dominate. With MAD, signal should be moderate.
    assert signal is not None
    assert abs(signal) < 2.0  # MAD should not explode on single outlier
```

---

## 🔧 M.1.5: Reduce OI Weight to ≤0.05

**File:** `pipeline/src/regime/composite.py`
**Problem:** Open Interest has near-zero directional edge. All three auditors agree it adds noise. Reduce weight and reallocate to rate/special.

**Current weights (lines 24-31):**
```python
PAIR_COMPOSITE_WEIGHTS: dict[str, PairWeightConfig] = {
    "EURUSD": PairWeightConfig(rate=0.40, cot=0.25, vol=0.20, oi=0.10, special=0.05, fpi=0.0),
    "USDJPY": PairWeightConfig(rate=0.30, cot=0.20, vol=0.25, oi=0.15, special=0.10, fpi=0.0),
    "GBPUSD": PairWeightConfig(rate=0.35, cot=0.25, vol=0.25, oi=0.10, special=0.05, fpi=0.0),
    "AUDUSD": PairWeightConfig(rate=0.25, cot=0.20, vol=0.20, oi=0.10, special=0.25, fpi=0.0),
    "USDCAD": PairWeightConfig(rate=0.25, cot=0.15, vol=0.20, oi=0.10, special=0.30, fpi=0.0),
    "USDCHF": PairWeightConfig(rate=0.30, cot=0.15, vol=0.20, oi=0.10, special=0.25, fpi=0.0),
    "USDINR": PairWeightConfig(rate=0.25, cot=0.10, vol=0.20, oi=0.10, special=0.20, fpi=0.15),
}
```

**Fix:** Reduce OI to 0.05 across all pairs. Reallocate the freed weight to rate (primary) and special (secondary).

**New weights:**
```python
PAIR_COMPOSITE_WEIGHTS: dict[str, PairWeightConfig] = {
    "EURUSD": PairWeightConfig(rate=0.45, cot=0.25, vol=0.20, oi=0.05, special=0.05, fpi=0.0),
    "USDJPY": PairWeightConfig(rate=0.40, cot=0.20, vol=0.25, oi=0.05, special=0.10, fpi=0.0),
    "GBPUSD": PairWeightConfig(rate=0.40, cot=0.25, vol=0.25, oi=0.05, special=0.05, fpi=0.0),
    "AUDUSD": PairWeightConfig(rate=0.30, cot=0.20, vol=0.20, oi=0.05, special=0.25, fpi=0.0),
    "USDCAD": PairWeightConfig(rate=0.30, cot=0.15, vol=0.20, oi=0.05, special=0.30, fpi=0.0),
    "USDCHF": PairWeightConfig(rate=0.35, cot=0.15, vol=0.20, oi=0.05, special=0.25, fpi=0.0),
    "USDINR": PairWeightConfig(rate=0.30, cot=0.10, vol=0.20, oi=0.05, special=0.20, fpi=0.15),
}
```

**Rationale for reallocation:**
- Rate gets the majority of freed weight because it has the highest expected IR and the strongest macro rationale
- Special gets no additional weight for now (except EURUSD where it will be addressed in M.3.1)
- OI weight of 0.05 is a "presence" weight — keeps the signal in the composite for completeness but minimizes noise

**Test to add:**
```python
def test_oi_weight_reduced() -> None:
    """OI weight should be 0.05 for all pairs."""
    from src.regime.composite import PAIR_COMPOSITE_WEIGHTS

    for pair, cfg in PAIR_COMPOSITE_WEIGHTS.items():
        assert cfg.oi == 0.05, f"{pair}: OI weight is {cfg.oi}, expected 0.05"

def test_weights_sum_to_one() -> None:
    """All pair weights must sum to 1.0."""
    from src.regime.composite import PAIR_COMPOSITE_WEIGHTS

    for pair, cfg in PAIR_COMPOSITE_WEIGHTS.items():
        total = cfg.rate + cfg.cot + cfg.vol + cfg.oi + cfg.special + cfg.fpi
        assert abs(total - 1.0) < 1e-10, f"{pair}: weights sum to {total}"
```

---

## 🧪 Test Requirements

For EACH fix, write tests following the existing pattern:

1. **Causal correctness test:** Prove the current observation is excluded from the reference distribution
2. **Edge case test:** Empty history, near-constant history, single observation
3. **Regression test:** The fix does not break existing behavior for normal cases

Place tests in:
- `pipeline/tests/test_cot.py` for M.1.1
- `pipeline/tests/test_special.py` for M.1.2
- `pipeline/tests/test_math_utils.py` for M.1.3
- `pipeline/tests/test_fpi.py` for M.1.4
- `pipeline/tests/test_composite.py` for M.1.5

**All tests must pass:** `cd pipeline && pytest`

---

## 📋 Verification Checklist

- [ ] M.1.1 COT percentile excludes current observation from ECDF
- [ ] M.1.2 Special percentile excludes current observation from ECDF
- [ ] M.1.3 Spot Z-score excludes current observation from mean/std window
- [ ] M.1.4 FPI signal uses MAD (not SD) with MAD_NORMAL_SCALE=1.4826
- [ ] M.1.5 OI weight = 0.05 for all pairs; weights sum to 1.0
- [ ] All new tests pass
- [ ] Full pytest suite passes (235+ tests)
- [ ] ruff check clean on modified files
- [ ] mypy clean on modified modules
- [ ] No changes to regime thresholds (Layer 1/2/3 constants unchanged)
- [ ] No changes to composite logic beyond weight adjustments
- [ ] No new data sources or API calls

---

## 🚫 What NOT to Do

- Do NOT modify `regime_calls`, `validation_log`, or other immutable tables
- Do NOT change hysteresis thresholds, crowding thresholds, or Layer 1/2/3 constants
- Do NOT add new signal families (that's M.3)
- Do NOT implement dynamic beta weighting (that's M.2)
- Do NOT change the special signal for EURUSD beyond fixing the percentile bias (that's M.3.1)
- Do NOT create new database columns or migrations
- Do NOT modify the frontend
