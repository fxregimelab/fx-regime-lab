# Signal definitions

This document reflects **Python implementations** in `pipeline.py`, `inr_pipeline.py`, `cot_pipeline.py`, `vol_pipeline.py`, `oi_pipeline.py`, `rr_pipeline.py`, `config.py`, and merge helpers in `pipeline.py` (`merge_main`, `_apply_iv_gate`, `_apply_rr_modifier`, `_compute_primary_driver`). The Next.js `RegimeLabel` union in `web/lib/types/regime.ts` is **not** the same set of strings persisted to `regime_calls.regime` (see [[DATABASE_SCHEMA]]).

## Three-layer architecture (as implemented)

### Layer 1: Rate differentials and related macro drivers

**US Treasury yields:** `pipeline.py` uses `fredapi` with `FRED_API_KEY`. Series IDs in `config.FRED_SERIES`:

- `US_2Y` → FRED `DGS2`
- `US_10Y` → FRED `DGS10`

**Other sovereign curves:** not from FRED for DE and JP in `config.py` (ECB data-api for Germany, MOF Japan CSV for JGBs). Italy has a documented FRED monthly fallback `IRLTLT01ITM156N` in `pipeline.py` comments.

**Spreads and z-scores:** `merge_main` in `pipeline.py` calls `_merge_compute_rate_zscore` to populate spread z-score columns used by composite and by `core/regime_persist._rate_signal` (for example `US_DE_2Y_spread_zscore`, `US_JP_2Y_spread_zscore`, `US_IN_10Y_spread_zscore`).

**Interpretation:** higher US vs DE spread generally reads as USD strength pressure on EUR/USD in composite construction (see `calculate_g10_composites` narrative comments).

**Failure modes:** missing `FRED_API_KEY` stops CI; ECB or MOF download failures leave NaNs that downstream code may zero-fill or skip depending on column guards.

### Layer 2: COT positioning

**Source:** `cot_pipeline.py` pulls CFTC disaggregated positioning; master merge produces percentile columns such as `EUR_lev_percentile`, `JPY_lev_percentile` (exact column naming per merge logic).

**Normalization in composite (`calculate_g10_composites` in `pipeline.py`):** `_norm_percentile` maps raw percentiles into roughly `[-1, 1]` for weighting.

**Crowding thresholds (config-level constants in `config.py`):**

- `CROWDING_HIGH = 80`, `CROWDING_LOW = 20`, `EXTENDED_HIGH = 70`.

**`regime_persist._cot_signal` thresholds:** if percentile `>= 80` → `BEARISH`; if `<= 20` → `BULLISH`; else `NEUTRAL` for EUR and JPY legs. USDINR uses `None` path (returns `NEUTRAL`).

### Layer 3: Volatility, OI, risk reversal

**FX implied vol indices (`config.CBOE_VOL_TICKERS`):**

- EUR/USD → Yahoo ticker `^EVZ`
- USD/JPY → `^JYVIX`

Fetched in `vol_pipeline.py` (see pipeline comments about Phase 3 CVOL replacement).

**CME open interest (`oi_pipeline.py`, `config.CME_OI_URL`, `CME_OI_PRODUCT_IDS`):** downloads CME volume/OI CSV, aligns to pairs `6E` and `6J`, produces `oi_delta` and `oi_price_alignment` columns merged as sidecars.

**EURUSD 25d risk reversal proxy (`rr_pipeline.py`):** uses yfinance on FXE options chain (see pipeline module header comments in repo). Merge attaches `EURUSD_risk_reversal_25d` column.

**`iv_gate` (`pipeline.py` `_apply_iv_gate`):** for `EURUSD` and `USDJPY`, builds `implied_vol_30d` percentile rank over 260d window (`{pair}_iv_pct`). Multiplier map:

- `iv_pct > 0.90` → gate `0.2` and label override `VOL_EXPANDING` on composite label column
- `> 0.75` → gate `0.7`
- `< 0.25` → gate `1.0`
- else default `1.0`

Applied by **multiplying** `{pair_lower}_composite_score` by gate.

**`rr_modifier` (`pipeline.py` `_apply_rr_modifier`):** EUR/USD only. Computes `EURUSD_rr_z` from 260d z-score of `EURUSD_risk_reversal_25d`. Compares sign of composite vs sign of RR; assigns modifier `1.15` when confirming with `|rr_z|>0.5`, `0.60` when contradicting with `|rr_z|>1.5`, else `1.0`. Multiplies `eurusd_composite_score`. Sets `EURUSD_flags` to `OPTIONS_DIVERGENCE` on contradicting branch.

**OI normalization (`_apply_oi_alignment`):** builds `{pair}_oi_norm` from alignment string `confirming` vs `diverging` vs other, using price delta sign. Flags `UNWIND_IN_PROGRESS` when crowded COT plus shrinking OI for 3 consecutive days (uses `EUR_lev_percentile` or `JPY_lev_percentile` `> 90`).

### EUR/USD composite (pre gate, inside `calculate_g10_composites`)

Uses `US_DE_10Y_spread` 252d z clipped to `[-3,3]` then divided by 3 as `spread_z`.

Weighted sum `eur_raw` before `* 100` clip:

```text
0.30 * spread_z
+ 0.20 * lev_sig
+ 0.10 * am_sig
+ 0.10 * vol_sig
+ 0.15 * corr_sig
+ 0.08 * oil_sig
+ 0.07 * dxy_sig
```

Then `eurusd_composite_score = clip(eur_raw * 100, -100, 100)` rounded to 0.1.

Label function `_g10_label` on that score:

- `> 60` → `STRONG USD STRENGTH`
- `> 30` → `MODERATE USD STRENGTH`
- `> -30` → `NEUTRAL`
- `> -60` → `MODERATE USD WEAKNESS`
- else → `STRONG USD WEAKNESS`

### USD/JPY composite (pre gate)

`jpy_raw`:

```text
0.25 * jpy_spread_z
+ 0.20 * jpy_lev_sig
+ 0.10 * jpy_am_sig
+ 0.10 * jpy_vol_sig
+ 0.15 * jpy_corr_sig
+ 0.10 * jpy_oil_sig
+ 0.05 * gold_sig
+ 0.05 * jpy_dxy_sig
```

Same `* 100` clip and `_g10_label` mapping as EUR.

### INR composite (`inr_pipeline.py`)

Synthesizes `inr_composite_score` in `[-100, 100]` when required columns exist: `oil_inr_corr_60d`, `dxy_inr_corr_60d`, `US_IN_10Y_spread`.

Per-row computation (conceptually):

- Oil term: `0.25 * oil_corr * sign(Brent 1d change)`
- DXY term: `0.20 * dxy_corr * sign(DXY 1d change)`
- FPI term: `0.25 * clip(FPI_20D_flow / 20000, -1, 1)` with sign flip baked into flow handling
- RBI term: `0.20 * score_map[rbi_intervention_flag]` where map is `ACTIVE SUPPORT -0.30`, `ACTIVE CAPPING +0.20`, else `0.0`
- Rate term: `0.10 * sign(-US_IN_10Y_spread)` (sign helper treats NaN as 0)

Then clip to `[-100,100]`.

Labels `_inr_score_label_fn`:

- `> 60` `STRONG DEPRECIATION PRESSURE`
- `> 30` `MODERATE DEPRECIATION PRESSURE`
- `> -30` `NEUTRAL`
- `> -60` `MODERATE APPRECIATION PRESSURE`
- else `STRONG APPRECIATION PRESSURE`

**USDINR in `regime_persist`:** if label missing, fallback string `DIRECTIONAL_ONLY` is used when writing the row.

### Primary driver text (`_compute_primary_driver`)

For each of `eur`, `jpy`, `inr` keys, picks max absolute weighted contribution among:

- rate `0.30 * abs(rate_z)`
- cot `0.25 * abs(cot_pct - 50) / 50` (cot absent for INR branch in `_cot_signal` path; driver still uses cot column name mapping in driver function for EUR/JPY)
- vol_skew `0.15 * min(abs(vol_skew)/3,1)`
- rr `0.15 * min(abs(rr_z)/2,1)`
- oi `0.15 * abs(oi_norm)`

Writes `{pair_key}_primary_driver` like `rate:0.42` on latest index row.

### Confidence in `regime_calls`

`_conf_from_score` maps `abs(composite_score) / 100` clamped to `[0,1]`.

## Normalization and clipping summary

- Many sub-signals pass through `_norm_percentile` or `_norm_corr` helpers in `pipeline.py` to keep subterms bounded before weighting.
- Composite scores always clipped to `[-100, 100]` after scaling.

## Related docs

- [[PIPELINE_REFERENCE]]
- [[DATABASE_SCHEMA]]
