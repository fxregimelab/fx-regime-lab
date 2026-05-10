# classifier

## Purpose
UI metadata adapter. Maps raw regime gate output to colors, labels, and descriptions for the frontend.

## File
`pipeline/src/regime/classifier.py` (~71 lines)

## Key Functions

### `classify_regime_layer1(ctx)`
Thin wrapper around `run_layer1_gate()`.

### `classify_regime(composite, pair, vol_expanding)`
Snapshot classifier for notebooks/tests. Ignores Marcus staleness.

### `get_regime_metadata(regime)`
Returns `RegimeMetadata` with `ui_color_key` and `base_regime`.

## Regime Metadata

| Regime | ui_color_key | base_regime |
|--------|-------------|-------------|
| RISK_OFF_DOLLAR_BID | bullish | USD_STRENGTH |
| GROWTH_SURPRISE_USD | bullish | USD_POLICY |
| NEUTRAL | neutral | NEUTRAL |
| RISK_ON_DOLLAR_OFF | bearish | USD_WEAKNESS |
| LIQUIDITY_SHOCK | risk_off | VOL_STRESS |
| USD_POLICY_BREAKOUT | bullish | USD_POLICY |
| CARRY_COLLAPSE | caution | CARRY_STRESS |
| INR_DEPRECIATION_STRONG | bullish | USD_STRENGTH |
| INR_DEPRECIATION_MODERATE | bullish | USD_STRENGTH |
| INR_NEUTRAL | neutral | NEUTRAL |
| INR_APPRECIATION_MODERATE | bearish | USD_WEAKNESS |
| INR_APPRECIATION_STRONG | bearish | USD_WEAKNESS |

## Vol Expanding Suffix
If `vol_expanding=True` and regime is NEUTRAL, the label becomes `NEUTRAL__VOL_EXPANDING`.

## Connections
- **Inputs from:** [[layer1_gate]] (raw regime output)
- **Outputs to:** [[Frontend]] (color, label, description)
- **Tests:** `tests/test_regime.py`
