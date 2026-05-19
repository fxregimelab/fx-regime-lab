# Backend Prompt: Phase M.5 — Diagnostic Calibration & Validation

> **Session Type:** Backend / Pipeline  
> **Tier:** 2 (Diagnostic tooling, no production code changes to signal logic)  
> **IDENTITY Gate:** Phase A met  
> **Scope:** Validate M.1-M.3 changes on historical data. Measure actual accuracy improvement. No threshold changes.

---

## 🎯 Objective

Run two diagnostic analyses on historical data to validate the M.1-M.3 signal improvements:

1. **Permutation Importance:** Which signal families actually contribute to directional accuracy?
2. **Simulation Comparison:** Old composite (pre-M.1) vs. New composite (post-M.3) on the same historical data.

Both analyses read existing `signals` and `historical_prices` tables — no new data fetching.

---

## Task 1: Permutation Importance Script

**Create:** `pipeline/src/diagnostics/permutation_importance.py`

### What it does

For each pair, read the last N days of `signals` rows, recompute the composite N times (once per signal family shuffled), and measure the drop in T+5 directional accuracy.

### Algorithm

```python
def run_permutation_importance(
    pair: str,
    lookback_days: int = 252,
    n_shuffle: int = 5,
) -> dict[str, float]:
    """For each signal family, shuffle its historical values and measure accuracy drop.

    Returns {family: delta_accuracy} where delta = baseline_accuracy - shuffled_accuracy.
    A large positive delta means the signal family is important.
    A near-zero or negative delta means the signal family adds noise.
    """
```

**Steps:**
1. Read `signals` rows for `pair` over `lookback_days`
2. Read corresponding `historical_prices` to get T+5 returns
3. Compute baseline accuracy using the current composite logic (M.3)
4. For each family in ("rate", "cot", "vol", "oi", "special", "fpi"):
   a. Shuffle that family's normalized values across the lookback window
   b. Recompute composite with shuffled values
   c. Compute new accuracy
   d. Delta = baseline - new_accuracy
5. Return deltas

**Key implementation details:**
- Use the EXISTING `compute_composite()` from `src.regime.composite`
- Use the EXISTING validation logic (T+5, 5bps dead-band) from `src.validation.engine`
- Shuffle must be **within-family only** — don't break cross-family correlations
- Run `n_shuffle` times per family and average the delta (reduces shuffle variance)
- For COT, shuffle BOTH traditional net long AND smart spread together
- For rate, shuffle z_blended (not tactical/structural separately)

**Output format:**
```json
{
  "pair": "EURUSD",
  "lookback_days": 252,
  "baseline_accuracy": 0.512,
  "families": {
    "rate": {"delta": 0.035, "n_shuffle": 5},
    "cot": {"delta": 0.012, "n_shuffle": 5},
    "vol": {"delta": -0.008, "n_shuffle": 5},
    "oi": {"delta": -0.003, "n_shuffle": 5},
    "special": {"delta": 0.021, "n_shuffle": 5}
  }
}
```

**CLI:**
```bash
python -m src.diagnostics.permutation_importance --pair EURUSD --lookback 252
python -m src.diagnostics.permutation_importance --pair USDJPY --lookback 252
python -m src.diagnostics.permutation_importance --pair USDINR --lookback 252
```

---

## Task 2: Simulation Engine Update

**File:** `pipeline/src/backfill/simulation_engine.py`

### What to update

The simulation engine currently uses a SIMPLIFIED composite (no betas, no COT, placeholder special signal). Update it to use the FULL M.3 logic.

**Current issues in simulation engine:**
1. `special_signal = compute_special_signal(pair, {})` — empty cross_asset_data, so EURUSD gets 0.0
2. `compute_composite(rate_norm, cot_norm, vol_norm, oi_norm, pair=pair, special_signal=special_signal)` — no betas passed
3. Rate normalization uses simple mean/std Z-score instead of MAD
4. No COT data loaded
5. No smart spread
6. No z_blended

**Fixes needed:**

1. **Special signal:** For EURUSD, pass `bund_btp_spread` and `ecb_balance_sheet` from `signals` table if available. For other pairs, use the existing cross-asset logic.

2. **Betas:** Compute dynamic betas from historical signal rows (read from DB or recompute from spot returns).

3. **Rate normalization:** Use `normalize_rate_signal()` with MAD Z-score instead of simple mean/std. This requires historical yield data, which is already loaded.

4. **COT:** The simulation engine currently skips COT (`cot_norm = None`). Add COT loading from `signals` table or recompute from `cot_rows`.

5. **Smart spread:** If COT data is available, compute smart spread and blend 70/30.

6. **z_blended:** Use `rate_norm_z.z_blended` instead of simple Z-score.

**Simplification:** Instead of updating the full simulation engine (which is complex), create a NEW function `run_pair_simulation_v2` that wraps the existing engine but uses the M.3 logic. Keep the old function for backward compatibility.

```python
def run_pair_simulation_v2(
    pair: str,
    start: date,
    end: date,
    yields_by_series: dict[str, dict[date, float]],
    signals_by_date: dict[date, dict[str, Any]] | None = None,
) -> list[tuple[SignalRow, RegimeCall]]:
    """Simulation using M.3 signal logic (betas, real special signal, z_blended, smart COT)."""
```

**Data sources:**
- `historical_prices` — spot bars (already loaded)
- `historical_yields` — yield series (already loaded)
- `signals` — pre-computed signal rows (for COT, special, OI, etc.)

**CLI addition:**
```bash
python -m src.backfill.simulation_engine --pair EURUSD --start 2024-01-01 --v2
```

---

## Task 3: Accuracy Comparison Report

**Create:** `pipeline/src/diagnostics/accuracy_report.py`

### What it does

Run both old and new simulation logic on the same historical window and output a side-by-side comparison.

```python
def compare_old_vs_new(
    pair: str,
    start: date,
    end: date,
) -> dict[str, Any]:
    """Run old (pre-M.1) and new (post-M.3) composite logic on same data.

    Returns accuracy, Brier score, and per-family contribution for both.
    """
```

**Metrics to compute:**
- T+5 directional accuracy
- T+20 directional accuracy
- Brier score (using calibrated confidence)
- Per-family permutation importance (from Task 1)
- Composite dispersion (std dev of composite scores)
- Regime transition frequency (how often regime changes)

**Output:** Markdown report saved to `pipeline/reports/accuracy_comparison_{pair}_{start}_{end}.md`

**Example report:**
```markdown
# Accuracy Comparison: EURUSD (2024-01-01 to 2024-12-31)

## Baseline (Pre-M.1)
- T+5 accuracy: 48.2%
- T+20 accuracy: 51.1%
- Brier score: 0.312
- Composite dispersion: 0.42

## Post-M.3
- T+5 accuracy: 53.7% (+5.5 pp)
- T+20 accuracy: 55.2% (+4.1 pp)
- Brier score: 0.278 (-0.034)
- Composite dispersion: 0.58

## Permutation Importance
| Family | Delta Accuracy | Verdict |
|--------|---------------|---------|
| rate | +3.5 pp | CRITICAL |
| special | +2.1 pp | HIGH |
| cot | +1.2 pp | MEDIUM |
| vol | -0.8 pp | NOISE |
| oi | -0.3 pp | NOISE |

## Key Findings
1. Real yield blending (M.3.2) contributed +3.5 pp — the single largest improvement.
2. EURUSD special signal (M.3.1) contributed +2.1 pp.
3. Vol and OI add noise — consider further reducing weight or removing.
```

---

## Task 4: Update Simulation Engine Tests

**File:** `pipeline/tests/test_simulation_engine.py` (new)

```python
def test_simulation_v2_produces_more_dispersion() -> None:
    """M.3 composite should produce wider dispersion than baseline."""
    # Run both versions on same small window
    # Assert v2 composite std > v1 composite std

def test_simulation_v2_higher_accuracy_on_known_regime() -> None:
    """On a known trending period, v2 should have higher accuracy."""
    # Use a 30-day window with clear trend
    # Assert v2 accuracy > v1 accuracy
```

---

## 📁 Files You Will Create / Modify

| File | Action |
|------|--------|
| `pipeline/src/diagnostics/permutation_importance.py` | **New** |
| `pipeline/src/diagnostics/accuracy_report.py` | **New** |
| `pipeline/src/backfill/simulation_engine.py` | **Modify** — add `run_pair_simulation_v2` |
| `pipeline/tests/test_simulation_engine.py` | **New** |
| `pipeline/reports/` | **New directory** — output reports go here |

---

## 🧪 Test Requirements

- Permutation importance runs without errors on all 3 pairs
- Simulation v2 runs without errors and produces more results than v1
- Accuracy report generates markdown
- All tests pass: `cd pipeline && pytest`

---

## 📋 Verification Checklist

- [ ] `permutation_importance.py` runs on EURUSD, USDJPY, USDINR
- [ ] `simulation_engine.py` has v2 function that uses M.3 logic
- [ ] `accuracy_report.py` generates side-by-side comparison
- [ ] Reports saved to `pipeline/reports/`
- [ ] pytest passes (262+ tests)
- [ ] ruff clean
- [ ] mypy clean on new modules
- [ ] No changes to production signal logic (read-only diagnostic)
- [ ] No changes to immutable tables

---

## 🚫 What NOT to Do

- Do NOT modify `compute_composite`, `compute_special_signal`, or other production signal functions
- Do NOT modify `regime_calls`, `validation_log`
- Do NOT add new data fetchers
- Do NOT change thresholds
