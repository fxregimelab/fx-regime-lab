# Mini Prompt: M.2/M.3 Fixes + Missing Tests

> **Scope:** 2 bug fixes + 7-10 new tests. No new features. No threshold changes.

---

## Fix 1: Remove USDINR Post-Hoc Nudges

**File:** `pipeline/src/scheduler/orchestrator.py`
**Lines:** ~1210-1220

**Current buggy code:**
```python
elif pair == "USDINR":
    if india_vix is not None and india_vix > 25.0:
        special_signal = (special_signal or 0.0) - 0.3
        logger.info("USDINR India VIX stress triggered (%.2f)", india_vix)
    if inr_forward_premium is not None and inr_forward_premium < -2.0:
        special_signal = (special_signal or 0.0) - 0.2
        logger.info(
            "USDINR forward premium decline triggered (%.2f%%)",
            inr_forward_premium,
        )
```

**Fix:** Delete the entire `elif pair == "USDINR":` block. The India VIX and INR forward premium are already stored in the `signals` table and feed into the special signal via `compute_special_signal()`. Post-hoc arithmetic nudges bypass the composite's normalization — this is the exact anti-pattern the audit flagged.

**Keep the USDJPY intervention blend** (lines ~1194-1199) — that is a formal weighted blend (`0.85 * special + 0.15 * intervention`), not a post-hoc nudge.

---

## Fix 2: Update EURUSD special_label

**File:** `pipeline/src/scheduler/orchestrator.py`
**Lines:** ~1491-1496

**Current buggy code:**
```python
"EURUSD": (
    "frag_risk"
    if (bund_btp_spread is not None and bund_btp_spread < -2.0)
    else "EURUSD_placeholder"
),
```

**Fix:** Replace with signal-aware label:
```python
"EURUSD": (
    "frag_risk"
    if abs(special_signal or 0.0) > 0.5
    else "macro_special"
),
```

This reflects the actual special signal strength instead of a hardcoded Bund-BTP threshold. The label is UI-only text and does not affect the composite math.

---

## Fix 3: Add Missing Tests for M.2 + M.3

Write tests in existing test files. Follow the existing style (no external fixtures, minimal mocks, assert on exact math where possible).

### 3.1 Precision Weights (`tests/test_composite.py`)

```python
def test_precision_weights_upweight_high_beta() -> None:
    """High |beta| signals get more weight than static."""
    from src.regime.composite import _precision_weights

    static = {"rate": 0.40, "cot": 0.30, "vol": 0.20, "oi": 0.10}
    betas = {"rate": 0.25, "cot": 0.02, "vol": 0.15, "oi": 0.01}
    w = _precision_weights(static, betas)
    assert w["rate"] > static["rate"]  # High beta → more weight
    assert w["cot"] < static["cot"]    # Low beta → less weight

def test_precision_weights_floor() -> None:
    """No signal drops below 10% of its static weight."""
    from src.regime.composite import _precision_weights

    static = {"rate": 0.40, "cot": 0.30}
    betas = {"rate": 0.50, "cot": 0.0}
    w = _precision_weights(static, betas)
    assert w["cot"] >= static["cot"] * 0.10

def test_precision_weights_fallback_when_all_weak() -> None:
    """If all |beta| < 0.05, fall back to static weights."""
    from src.regime.composite import _precision_weights

    static = {"rate": 0.40, "cot": 0.30}
    betas = {"rate": 0.02, "cot": 0.03}
    w = _precision_weights(static, betas)
    assert w == static
```

### 3.2 Redundancy Penalty (`tests/test_composite.py`)

```python
def test_redundancy_penalty_same_sign() -> None:
    """Penalty increases when signals agree."""
    from src.regime.composite import _redundancy_penalty

    values = {"rate": 0.8, "cot": 0.6, "vol": -0.2}
    betas = {"rate": 0.15, "cot": 0.12, "vol": 0.10}
    p = _redundancy_penalty(values, betas)
    assert p > 0.0  # rate and cot agree → penalty
def test_redundancy_penalty_no_penalty_when_disagree() -> None:
    """No penalty when signals disagree."""
    from src.regime.composite import _redundancy_penalty

    values = {"rate": 0.8, "cot": -0.6}
    betas = {"rate": 0.15, "cot": 0.12}
    p = _redundancy_penalty(values, betas)
    assert p == 0.0
```

### 3.3 z_blended (`tests/test_rate.py`)

```python
def test_z_blended_60_40() -> None:
    """z_blended = 0.6*z_tactical + 0.4*z_structural when both exist."""
    from src.signals.rate import normalize_rate_signal

    hist = [0.01] * 252 + [0.02] * 10
    structural_hist = [0.005] * 2520 + [0.015] * 10
    result = normalize_rate_signal(
        spread=0.025,
        pair="EURUSD",
        historical_spreads=hist,
        spread_structural=0.020,
        historical_structural=structural_hist,
    )
    assert result.z_blended is not None
    assert abs(result.z_blended - (0.6 * result.z_tactical + 0.4 * result.z_structural)) < 1e-10

def test_z_blended_fallback_to_tactical() -> None:
    """When structural is missing, z_blended = tactical."""
    from src.signals.rate import normalize_rate_signal

    hist = [0.01] * 252 + [0.02] * 10
    result = normalize_rate_signal(
        spread=0.025,
        pair="EURUSD",
        historical_spreads=hist,
    )
    assert result.z_blended == result.z_tactical
```

### 3.4 EURUSD Special Signal (`tests/test_special.py`)

```python
def test_eurusd_special_signal_with_scalar_fallbacks() -> None:
    """EURUSD special signal uses scalar fallbacks when history is unavailable."""
    from src.signals.special import compute_special_signal

    result = compute_special_signal("EURUSD", {}, bund_btp_spread=-2.5, ecb_balance_sheet=7500.0)
    assert result is not None
    assert isinstance(result, float)
    assert -1.0 <= result <= 1.0
    # Wide Bund-BTP (-2.5) should push signal toward USD strength (positive)
    assert result > 0.0

def test_eurusd_special_signal_none_when_no_inputs() -> None:
    """EURUSD special signal returns None when no inputs provided."""
    from src.signals.special import compute_special_signal

    result = compute_special_signal("EURUSD", {})
    assert result is None
```

### 3.5 Smart Spread Causal (`tests/test_cot.py`)

```python
def test_cot_smart_spread_causal() -> None:
    """Current observation excluded from smart spread percentile."""
    from datetime import date, timedelta
    from src.signals.cot import compute_cot_smart_spread_percentile
    from src.types import CotRow

    base = date(2024, 1, 1)
    rows = []
    for i in range(10):
        rows.append(CotRow(
            date=base + timedelta(weeks=i),
            pair="EURUSD",
            net_long=0,
            open_interest=1000,
            asset_mgr_net=i * 200,
            lev_money_net=-i * 100,
        ))
    pct = compute_cot_smart_spread_percentile(rows, "EURUSD", window_reports=10, min_reports=5)
    assert pct is not None
    assert pct == 100.0  # Last spread is max; excluded from its own distribution
```

### 3.6 Carry v2 (`tests/test_rate.py`)

```python
def test_carry_v2_prefers_implied_vol() -> None:
    """v2 uses implied vol when provided."""
    from src.signals.rate import compute_risk_adjusted_carry_v2

    result = compute_risk_adjusted_carry_v2(2.0, 8.0, 10.0, "EURUSD")
    assert result == 2.0 / 10.0

def test_carry_v2_fallback_to_rv20() -> None:
    """v2 falls back to RV20 when implied vol is None."""
    from src.signals.rate import compute_risk_adjusted_carry_v2

    result = compute_risk_adjusted_carry_v2(2.0, 8.0, None, "USDINR")
    assert result == 2.0 / 8.0
```

---

## Verification

```bash
cd pipeline && pytest --tb=short -q
```

Target: **260+ tests passing** (was 250, +10 new).

Also run:
```bash
cd pipeline && ruff check src/scheduler/orchestrator.py tests/
cd pipeline && mypy src/scheduler/orchestrator.py tests/test_composite.py tests/test_rate.py tests/test_special.py tests/test_cot.py
```

---

## 🚫 What NOT to Do

- Do NOT modify any other part of the orchestrator
- Do NOT change regime thresholds
- Do NOT add new data sources or fetchers
- Do NOT modify immutable tables
