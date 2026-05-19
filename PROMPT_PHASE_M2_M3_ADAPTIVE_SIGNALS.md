# Backend Prompt: Phase M.2 + M.3 — Adaptive Weighting + Signal Quality

> **Session Type:** Backend / Pipeline  
> **Tier:** 2 (New signal math, no threshold changes, no immutable table edits)  
> **IDENTITY Gate:** Phase A met  
> **Scope:** Activate dynamic betas in composite weighting + upgrade 4 signal families. No architecture rebuild.

---

## 🎯 Objective

Implement the highest-EV methodology improvements from the triple-persona audit. This prompt bundles **Phase M.2 (Adaptive Weighting)** and **Phase M.3 (Signal Quality)** because they are orthogonal: M.2 changes HOW signals are weighted; M.3 changes WHAT signals are produced. Both are needed to reach 55% EUR/USD accuracy.

**Expected combined impact:** +6-12 pp across pairs (EUR/USD: ~49% → 55-60%).

---

## Phase M.2: Adaptive Weighting (3 Tasks)

### M.2.1 Use Dynamic Betas to Precision-Weight the Composite

**File:** `pipeline/src/regime/composite.py`  
**Current state:** `compute_dynamic_betas()` (lines 122-202) calculates 30D Spearman betas but they are ONLY used for dominance scores and driver text. The composite uses static `PAIR_COMPOSITE_WEIGHTS`.

**What to implement:**

In `compute_composite()`, replace static weights with beta-informed precision weights:

```python
def _precision_weights(
    static_weights: dict[str, float],
    betas: dict[str, float],
    *,
    floor_frac: float = 0.10,  # Minimum 10% of static weight
    beta_threshold: float = 0.05,  # Signals with |beta| below this get floor only
) -> dict[str, float]:
    """Adjust static weights by dynamic beta magnitude.

    Signals with stronger |beta| get more weight; weak signals get floor.
    The floor prevents any signal from being completely zeroed out.
    """
    adj: dict[str, float] = {}
    for k, w in static_weights.items():
        beta = abs(betas.get(k, 0.0))
        if beta < beta_threshold:
            adj[k] = w * floor_frac
        else:
            # Linear scaling: |beta|=0.05 → floor, |beta|=0.20 → 2× static
            scale = max(floor_frac, beta / 0.10)
            adj[k] = w * scale
    total = sum(adj.values())
    if total <= 0.0:
        return static_weights
    return {k: v / total for k, v in adj.items()}
```

**Integration into `compute_composite`:**

The `compute_composite()` signature already accepts `pair`. Use the pair to look up static weights, then if `betas` dict is provided, apply precision weighting. If `betas` is not provided or all zeros, fall back to static weights.

```python
def compute_composite(
    rate_norm: float | None,
    cot_norm: float | None,
    vol_norm: float | None,
    oi_norm: float | None,
    *,
    pair: str | None = None,
    special_signal: float | None = None,
    fpi_signal: float | None = None,
    betas: dict[str, float] | None = None,
) -> float | None:
    weights = _weights_for_pair(pair)
    if betas is not None and any(betas.values()):
        weights = _precision_weights(weights, betas)
    # ... rest of existing logic ...
```

**Update the orchestrator** (`pipeline/src/scheduler/orchestrator.py`) to pass `betas` into `compute_composite()`. The betas are already computed before the composite call — just thread them through.

**Key constraints:**
- Floor must be ≥ 10% of static weight (prevents single-signal dominance)
- If all |beta| < 0.05, fall back to static weights
- If a signal family is missing (None), it is dropped BEFORE weight adjustment, then remaining weights renormalize
- The `betas` dict may not contain all families (e.g., "special" or "fpi") — use `betas.get(k, 0.0)`

---

### M.2.2 Add Covariance-Aware Composite Variance Penalty

**File:** `pipeline/src/regime/composite.py`  
**Current state:** The composite treats signals as independent. In reality, rate and COT are positively correlated (carry trades attract positioning), and vol is negatively correlated with spot (leverage effect).

**What to implement:**

Add a `composite_variance` helper that computes the variance of the weighted sum assuming a diagonal-plus-rank-one covariance structure (Ledoit-Wolf shrinkage estimator is too complex for now; use a simple empirical covariance on a rolling window).

```python
def _composite_variance(
    weights: dict[str, float],
    values: dict[str, float],
    historical_norms: dict[str, list[float]],  # Last ~90 days of each normalized signal
) -> float:
    """Empirical variance of the weighted composite using a 90d rolling covariance.

    Returns a variance estimate in normalized units. Used to penalize confidence
    when signals are highly correlated (redundant information).
    """
    families = list(values.keys())
    # Build aligned 90d matrix of normalized signals
    # ... compute pairwise covariances ...
    # ... return w' Σ w ...
```

**Integration:** Export `composite_variance` from `composite.py`. In the orchestrator, after computing the composite, compute its variance and pass it to `compute_confidence()` (see M.2.3).

**Simpler MVP approach:** If implementing full covariance is too complex, start with a "redundancy penalty" based on the number of active signal families and their pairwise Spearman correlations:

```python
def _redundancy_penalty(
    values: dict[str, float],
    betas: dict[str, float],
) -> float:
    """Penalty 0.0–0.15 based on how many signals are saying the same thing.

    If rate and COT have same sign and both |beta| > 0.05, they are redundant.
    """
    # Count pairs of active signals with same sign
    # Penalty = 0.03 per redundant pair, cap at 0.15
    # ...
```

Use the simpler approach for now. Document that full covariance is a future enhancement.

---

### M.2.3 Calibrate Confidence to Empirical Probability

**File:** `pipeline/src/regime/confidence.py`  
**Current state:** `compute_confidence()` produces a score in [0.30, 0.90] that is explicitly "NOT a probability." The Brier score is therefore invalid.

**What to implement:**

Add Platt scaling (logistic calibration) to map raw confidence to empirical probability:

```python
def calibrate_confidence(
    raw_confidence: float,
    pair: str,
    *,
    a: float | None = None,
    b: float | None = None,
) -> float:
    """Map raw confidence to calibrated probability using Platt scaling.

    If a and b are not provided, fall back to a default calibration
    that can be updated from historical validation data.
    """
    # Default calibration: learned from validation_log history
    # For MVP, use heuristic: compress toward 0.50 to reduce overconfidence
    if a is None or b is None:
        # Heuristic: sigmoid-like compression
        # raw 0.30 → 0.45, raw 0.60 → 0.55, raw 0.90 → 0.70
        return float(0.35 + 0.40 * raw_confidence)
    return float(1.0 / (1.0 + math.exp(-(a * raw_confidence + b))))
```

**Key design decision:** Do NOT require a training step for MVP. Use the heuristic calibration above. Add a TODO comment that future work should fit `a` and `b` per pair by minimizing Brier score on `validation_log`.

**Update `compute_confidence()`** to return the calibrated value instead of raw confidence. Update the docstring to clarify that the output is now an *uncalibrated estimate* heading toward a true probability.

**Update Brier score computation** in validation to use the calibrated confidence.

**File:** `pipeline/src/validation/engine.py` (or wherever Brier is computed)

---

## Phase M.3: Signal Quality (4 Tasks)

### M.3.1 Build Real EUR/USD Special Signal (Remove 0.0 Placeholder)

**File:** `pipeline/src/signals/special.py`  
**Current state:** `compute_special_signal()` returns `0.0` for EURUSD.

**What to implement:**

Replace the placeholder with a real signal. Use the **Eurozone-US CPI differential** as the MVP signal because:
1. Data is readily available (FRED)
2. It was the dominant driver of EUR/USD in 2022-2023
3. It complements the rate signal (real yields = nominal - inflation)

```python
def fetch_eurozone_us_cpi_diff(fred: Fred | None = None) -> float | None:
    """Fetch Eurozone HICP YoY minus US CPI YoY from FRED.

    Returns differential in percentage points, or None if unavailable.
    Positive = Eurozone inflation higher than US = EUR weakness pressure
    (higher inflation → tighter ECB → but also terms-of-trade shock).

    FRED series:
    - Eurozone HICP: CP0000EZ19M086NEST (not verified — search FRED)
    - US CPI: CPIAUCSL
    """
```

**Simpler alternative if Eurozone HICP series is hard to find:** Use the existing real yield spread (nominal 10Y - breakeven) as a proxy. The rate signal already computes `rate_diff_10y` and `breakeven_inflation_10y`. For EUR/USD, create a synthetic special signal from:

1. **Bund-BTP spread** (already fetched in orchestrator) — percentile-ranked on 60d history
2. **ECB balance sheet** (already fetched) — percentile-ranked on 2Y history
3. **Real yield differential proxy** — US real 10Y minus DE real 10Y (use nominal spread minus breakeven spread)

Blend these three into a EUR/USD special signal:

```python
if key == "EURUSD":
    # Fetch or receive the pre-computed macro values
    # These are passed via cross_asset_data or fetched separately
    bund_btp = cross_asset_data.get("bund_btp_spread")
    ecb_bs = cross_asset_data.get("ecb_balance_sheet")
    # ... percentile rank each on appropriate history ...
    # ... blend: 40% bund_btp + 40% ecb_bs + 20% real_yield ...
    # ... return negative of composite (high fragmentation / ECB expansion = EUR weakness) ...
```

**Integration with orchestrator:** The orchestrator already fetches `bund_btp_spread` and `ecb_balance_sheet`. Pass them into `cross_asset_data` when calling `compute_special_signal("EURUSD", cross_asset_data)`.

**IMPORTANT:** The current Stream A nudges in `orchestrator.py` (Bund-BTP < -2.0 → -0.3, ECB BS > 7500B → -0.2) should be **REMOVED** and replaced by this formal special signal. The nudges were a temporary MVP; M.3.1 makes them proper signals.

**Test:**
```python
def test_eurusd_special_signal_not_placeholder() -> None:
    from src.signals.special import compute_special_signal
    cross_data = {
        "hist": {
            "bund_btp_spread": [0.5, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.3, -0.4,
                               -0.5, -0.6, -0.7, -0.8, -0.9, -1.0, -1.1, -1.2, -1.3, -1.4,
                               -1.5, -1.6, -1.7, -1.8, -1.9, -2.0, -2.1, -2.2, -2.3, -2.4,
                               -2.5, -2.6, -2.7, -2.8, -2.9, -3.0, -3.1, -3.2, -3.3, -3.4,
                               -3.5, -3.6, -3.7, -3.8, -3.9, -4.0, -4.1, -4.2, -4.3, -4.4,
                               -4.5, -4.6, -4.7, -4.8, -4.9, -5.0, -5.1, -5.2, -5.3, -5.4],
            "ecb_balance_sheet": [7000.0] * 60,
        }
    }
    result = compute_special_signal("EURUSD", cross_data)
    assert result is not None
    assert isinstance(result, float)
    # Wide Bund-BTP should produce a negative signal (EUR weakness)
    assert result < 0.0
```

---

### M.3.2 Elevate Real Yield Differential to Co-Primary Status

**File:** `pipeline/src/signals/rate.py`  
**Current state:** Real yield spread (nominal 10Y - breakeven inflation) is computed in `build_real_yield_10y_spread_history_from_rows()` but only used for the structural Z-score in `normalize_rate_signal()`. It does not enter the composite directly.

**What to implement:**

Blend nominal 2Y spread and real 10Y spread into a single `rate_norm` value that enters the composite:

```python
class RateNormZ:
    """Dual-horizon robust Z on the same carry series (clipped composite inputs)."""
    z_tactical: float | None      # 2Y carry / RV20
    z_structural: float | None    # Real 10Y spread
    z_blended: float | None       # NEW: weighted blend for composite input
```

In `normalize_rate_signal()`, after computing `z_tactical` and `z_structural`, compute:

```python
z_blended = None
if z_tactical is not None and z_structural is not None:
    z_blended = float(0.60 * z_tactical + 0.40 * z_structural)
elif z_tactical is not None:
    z_blended = z_tactical
elif z_structural is not None:
    z_blended = z_structural
```

**Return `z_blended` as the primary rate signal.** The orchestrator should use `z_blended` for `rate_norm` in the composite, while still logging `z_tactical` and `z_structural` separately for transparency.

**Update `RateNormZ` dataclass** to include `z_blended`.

**Update orchestrator** to use `rate_norm.z_blended` for composite input.

**Rationale:** Real yields have driven major USD cycles since 2021. The structural Z alone was too slow; blending 60% tactical (fast) + 40% structural (slow) gives both responsiveness and regime-awareness.

**Test:**
```python
def test_rate_norm_blended() -> None:
    from src.signals.rate import normalize_rate_signal
    # Create mock historical data
    hist = [0.01] * 252 + [0.02] * 10  # Quiet then shift
    structural_hist = [0.005] * 2520 + [0.015] * 10
    result = normalize_rate_signal(
        spread=0.025,
        pair="EURUSD",
        historical_spreads=hist,
        spread_structural=0.020,
        historical_structural=structural_hist,
    )
    assert result.z_tactical is not None
    assert result.z_structural is not None
    assert result.z_blended is not None
    assert abs(result.z_blended - (0.6 * result.z_tactical + 0.4 * result.z_structural)) < 1e-10
```

---

### M.3.3 Replace COT Net Long with Asset Manager vs. Leveraged Money Spread

**File:** `pipeline/src/signals/cot.py`  
**Current state:** `compute_cot_percentile()` uses `r.net_long` only. The model already fetches `cot_asset_mgr_net` and `cot_lev_money_net` (see `SignalRow` in `types.py`) but does not use them in the signal.

**What to implement:**

Add a new function `compute_cot_smart_spread_percentile()` that computes the percentile of `(asset_mgr_net - lev_money_net)`:

```python
def compute_cot_smart_spread_percentile(
    rows: list[CotRow],
    pair: str,
    *,
    window_reports: int = COT_PERCENTILE_WINDOW_REPORTS,
    as_of: date | None = None,
    min_reports: int = COT_PERCENTILE_MIN_REPORTS,
) -> float | None:
    """Percentile of Asset Manager net minus Leveraged Money net.

    This "smart spread" captures the disagreement between real money
    (trend-following, slow) and fast money (CTAs, macro funds). When
    real money is long and fast money is short, the spread is wide positive
    — often a contrarian signal at turning points.
    """
```

**Implementation notes:**
- Follow the same causal logic as `compute_cot_percentile` (exclude current observation)
- Use `r.asset_mgr_net` and `r.lev_money_net` from `CotRow`
- If either field is None, fall back to `r.net_long`
- The spread = `asset_mgr_net - lev_money_net`

**Update the orchestrator** to call BOTH `compute_cot_percentile` and `compute_cot_smart_spread_percentile`, then blend them:

```python
cot_pct = compute_cot_percentile(cot_rows, pair, as_of=today)
cot_smart = compute_cot_smart_spread_percentile(cot_rows, pair, as_of=today)

# Blend: 70% traditional net long + 30% smart spread
if cot_pct is not None and cot_smart is not None:
    blended = 0.70 * normalize_cot_signal(cot_pct) + 0.30 * normalize_cot_signal(cot_smart)
elif cot_pct is not None:
    blended = normalize_cot_signal(cot_pct)
else:
    blended = None
```

**Why 70/30:** The traditional net long still has signal; the smart spread adds alpha at extremes. Do NOT make this adaptive yet — keep it static for stability.

**Update `CotRow` usage:** Ensure `asset_mgr_net` and `lev_money_net` are populated from the DB. Check `pipeline/src/db/writer.py` and the orchestrator's COT fetch path.

**Test:**
```python
def test_cot_smart_spread() -> None:
    from datetime import date, timedelta
    from src.signals.cot import compute_cot_smart_spread_percentile
    from src.types import CotRow

    base = date(2024, 1, 1)
    rows = []
    for i in range(20):
        rows.append(CotRow(
            date=base + timedelta(weeks=i),
            pair="EURUSD",
            net_long=0,
            open_interest=1000,
            asset_mgr_net=i * 200,
            lev_money_net=-i * 100,
        ))
    # Smart spread = AM - Lev = 300, 600, ..., 6000
    # Last spread = 6000, should be at 100th percentile
    pct = compute_cot_smart_spread_percentile(rows, "EURUSD", window_reports=20, min_reports=5)
    assert pct is not None
    assert pct == 100.0
```

---

### M.3.4 Replace RV20 with Implied Vol in Risk-Adjusted Carry

**File:** `pipeline/src/signals/rate.py`  
**Current state:** `compute_risk_adjusted_carry()` divides `rate_diff_2y` by `realized_vol_20d`.

**What to implement:**

Add a new function that uses implied vol when available:

```python
def compute_risk_adjusted_carry_v2(
    rate_diff_2y: float | None,
    realized_vol_20d: float | None,
    implied_vol_30d: float | None,
    pair: str,
) -> float | None:
    """Risk-adjusted carry using implied vol when available, RV20 as fallback.

    Implied vol is forward-looking and better captures event risk.
    For EUR/USD: uses implied_vol_30d (EVZ proxy).
    For USD/JPY: uses implied_vol_30d (JYVIX proxy).
    For USD/INR: no liquid implied vol index → falls back to RV20.
    """
    if rate_diff_2y is None:
        return None

    # Prefer implied vol, fallback to realized
    vol = implied_vol_30d if implied_vol_30d is not None and implied_vol_30d > 0.0 else realized_vol_20d
    if vol is None or vol <= 0.0:
        return None
    return rate_diff_2y / vol
```

**Update the orchestrator** to pass `implied_vol_30d` (already fetched for EUR/USD and USD/JPY) into the carry computation.

**Update `normalize_rate_signal()`** to use `compute_risk_adjusted_carry_v2()` instead of the v1 function. Pass the implied vol through the signal row.

**No change for USD/INR** — it has no liquid implied vol index, so RV20 remains the fallback.

**Test:**
```python
def test_risk_adjusted_carry_v2_prefers_implied() -> None:
    from src.signals.rate import compute_risk_adjusted_carry_v2

    # Both vols provided → implied wins
    result = compute_risk_adjusted_carry_v2(2.0, 8.0, 10.0, "EURUSD")
    assert result == 2.0 / 10.0  # implied vol used

    # No implied → RV20 fallback
    result = compute_risk_adjusted_carry_v2(2.0, 8.0, None, "USDINR")
    assert result == 2.0 / 8.0
```

---

## 📁 Orchestrator Integration Order

In `pipeline/src/scheduler/orchestrator.py`, update the daily signal flow in this order:

1. **After COT fetch** → compute BOTH `cot_pct` and `cot_smart_spread`
2. **After rate fetch** → compute `z_blended` using real yield blend
3. **After cross-asset fetch** → compute EUR/USD special signal with Bund-BTP + ECB BS
4. **Before composite** → compute dynamic betas (already done)
5. **Composite** → pass `betas` to `compute_composite()` for precision weighting
6. **After composite** → compute redundancy penalty and pass to confidence
7. **Confidence** → return calibrated confidence (heuristic Platt)
8. **Remove old Stream A nudges** → delete the post-hoc Bund-BTP / ECB BS / intervention nudges from orchestrator (they are now formal signals)

---

## 🗄️ Database Schema Changes

**NONE.** All new signal values flow through existing columns:
- `special_signal_value` — now receives real EUR/USD special signal
- `rate_z_tactical`, `rate_z_structural` — already exist
- `cot_percentile` — still stores traditional net long percentile
- `implied_vol_30d` — already exists

The `cot_asset_mgr_net` and `cot_lev_money_net` columns already exist in `signals` table.

---

## 🧪 Test Requirements

For EACH task, write tests:

1. **M.2.1:** Precision weights correctly up-weight high-beta signals and floor low-beta signals
2. **M.2.1:** Missing legs still handled correctly with precision weights
3. **M.2.2:** Redundancy penalty increases when rate and COT have same sign
4. **M.2.3:** Calibrated confidence is in [0,1] and less extreme than raw confidence
5. **M.3.1:** EUR/USD special signal is not None and not 0.0 for realistic inputs
6. **M.3.2:** `z_blended` equals 0.6*z_tactical + 0.4*z_structural when both exist
7. **M.3.3:** Smart spread percentile is causal (excludes current observation)
8. **M.3.4:** V2 carry prefers implied vol over RV20

Place tests in:
- `pipeline/tests/test_composite.py` for M.2.1, M.2.2
- `pipeline/tests/test_confidence.py` for M.2.3
- `pipeline/tests/test_special.py` for M.3.1
- `pipeline/tests/test_rate.py` for M.3.2, M.3.4
- `pipeline/tests/test_cot.py` for M.3.3

**All tests must pass:** `cd pipeline && pytest`

---

## 📋 Verification Checklist

- [ ] M.2.1 `compute_composite()` accepts `betas` and produces different weights than static
- [ ] M.2.1 Floor constraint works (no signal gets < 10% of static weight)
- [ ] M.2.1 Fallback to static weights when all |beta| < 0.05
- [ ] M.2.2 Redundancy penalty is 0.0 when signals disagree, > 0.0 when they agree
- [ ] M.2.3 Calibrated confidence is bounded [0,1]
- [ ] M.2.3 Brier score uses calibrated confidence
- [ ] M.3.1 EUR/USD special signal returns non-None, non-zero for realistic inputs
- [ ] M.3.1 Stream A nudges removed from orchestrator
- [ ] M.3.2 `RateNormZ` has `z_blended` field
- [ ] M.3.2 Orchestrator uses `z_blended` for composite input
- [ ] M.3.3 `compute_cot_smart_spread_percentile()` exists and is causal
- [ ] M.3.3 Smart spread blended 70/30 with traditional net long
- [ ] M.3.4 `compute_risk_adjusted_carry_v2()` prefers implied vol
- [ ] M.3.4 USD/INR still uses RV20 fallback
- [ ] pytest passes (250+ tests)
- [ ] ruff check clean
- [ ] mypy clean on modified modules
- [ ] No regime thresholds modified
- [ ] No immutable tables touched

---

## 🚫 What NOT to Do

- Do NOT modify `regime_calls`, `validation_log`, or other immutable tables
- Do NOT change Layer 1/2/3 threshold constants (that's M.4, locked behind Phase B)
- Do NOT create new database columns or migrations
- Do NOT modify the frontend
- Do NOT add new data fetchers beyond what's specified (CPI differential is optional; use existing data first)
- Do NOT make weights fully adaptive (e.g., online learning) — keep precision weighting static per day
