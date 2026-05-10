# confidence

## Purpose
Computes how confident the model is in its directional call. Confidence is NOT the same as conviction — confidence is a probability (0–1), conviction is a discrete rating (1–5).

## File
`pipeline/src/regime/confidence.py`

## Key Functions

### `compute_confidence(composite, rate_norm, cot_norm, pair, special_signal)`
Returns confidence as float in [0.30, 0.90].

## Mathematics

### Base Confidence
```
base_conf = clip(|composite| / 2.0, 0.10, 0.90)
```
- **Why |composite|/2.0:** A composite of +2.0 (max) → base_conf = 1.0. A composite of 0 → base_conf = 0.
- **Clip to [0.10, 0.90]:** Never claim 0% or 100% confidence. Markets are probabilistic.

### Alignment Bonus
```
if rate_norm and cot_norm have same sign:
    bonus += 0.05
if |rate_norm| > 0.3 and |cot_norm| > 0.3:
    bonus += 0.05
```
- **Why:** When rate and positioning agree, the signal is stronger. When both are materially non-zero, the alignment is significant.

### Pair Adjustment
```
if pair == "USDJPY": adj -= 0.02  # JPY is more volatile
if pair == "USDINR": adj -= 0.03  # INR is managed float
```
- **Why:** Some pairs are inherently noisier. The model is slightly less confident in them.

### Final Clip
```
raw = clip(base_conf + bonus + pair_adj, 0.30, 0.95)
confidence = clip(raw - 0.03, 0.30, 0.90)
```
- **Why the -0.03:** Calibrates down slightly to avoid overconfidence. The model tends to be overconfident in backtests; this is a humility tax.

## Connections
- **Inputs from:** [[composite]] (composite score), [[rate]] (rate_norm), [[cot]] (cot_norm)
- **Outputs to:** [[layer2_directional]] (conviction cap), [[writer]] (regime_calls.confidence)
- **Used in:** [[validation_engine]] (Brier score calibration)
- **Tests:** `tests/test_regime.py`

## Why This Logic

Confidence exists for **probabilistic calibration**. The Brier score measures how well-calibrated the model is:
- If the model says 70% confidence and is correct 70% of the time → well-calibrated (Brier ≈ 0.21)
- If the model says 70% confidence and is correct 50% of the time → overconfident (Brier ≈ 0.29)

The current model achieves Brier scores of ~0.25–0.28, which is reasonably calibrated but slightly overconfident. The -0.03 humility tax is designed to improve this over time.
