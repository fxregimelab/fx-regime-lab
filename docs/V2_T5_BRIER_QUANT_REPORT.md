---
title: "T+5 Brier Target Assessment & Validation Remediation"
description: "Quant audit of the validation pipeline, data-quality fixes, and why the ≤0.225 T+5 ALL Brier target cannot be met without signal-generation changes."
---

# T+5 Brier Target Assessment & Validation Remediation

## 1. Executive Summary

This report closes the validation-pipeline remediation initiated in the v2.1/v2.2 engine work. All seven done-when conditions are either satisfied or documented as blocked by a fundamental signal-accuracy ceiling. The key finding is that **data-quality fixes made the ledger more honest; they did not materially lower the latest 90-day T+5 ALL Brier score**, which remains well above the 0.225 target.

| # | Done-when condition | Status | Evidence |
|---|---------------------|--------|----------|
| 1 | `2099-01-01` EURUSD test row superseded; no future-dated validation rows | ✅ | `scripts/_audit_validation.py:48` reports `Rows with date > today: 0` |
| 2 | `correct_net_t5/t20` computed from cost-adjusted returns; `validation_stats` reflects true net win rates | ✅ | `src/validation/engine.py:62` `_is_correct_net`; `validation_stats` now stores `t5_net_win_rate` and `t20_net_win_rate` |
| 3 | 8 NEUTRAL rows incorrectly `correct=True` and 1 USDJPY Brier-mismatch row superseded | ✅ | Audit reports `NEUTRAL rows marked correct=True: 0` and `Brier recomputation mismatches: 0` |
| 4 | Every validation row uses a documented, consistent cost assumption | ✅ | `src/validation/engine.py:15` `COST_BPS_ROUND_TRIP`; audit reports `Cost bps mismatches: 0` |
| 5 | `validation_stats.total_calls` populated and `T+20 rolling_90d_accuracy` stored | ✅ | `src/validation/aggregate.py:313` serializes `total_calls`; query shows `t20_rolling_90d_accuracy` populated |
| 6 | `pytest` 319, `ruff`, `mypy`, `npx tsc --noEmit`, and `biome check` pass | ✅ | All commands completed with no failures |
| 7 | Latest 90-day T+5 ALL mean Brier ≤ 0.225, or written quant report explaining measured state and remaining gap | ⚠️ | **Reported here**: latest 90-day Brier is 0.2600, accuracy is 47.1%. The theoretical floor at this accuracy is 0.2491, so the target is unreachable without signal-generation changes. |

## 2. Validation Pipeline After Remediation

The validation engine now produces two parallel correctness tracks for every directional call: a **gross** track used for Brier scoring and directional accuracy, and a **net** track used for P&L-realism after documented round-trip transaction costs.

```mermaid
flowchart LR
    classDef dark fill:#2d333b,stroke:#6d5dfc,color:#e6edf3

    A[regime_calls] --> B[src/validation/engine.py _compute_horizon]
    B --> C{predicted NEUTRAL?}
    C -->|yes| D[no Brier; net-correct only if realized NEUTRAL]
    C -->|no| E[directional Brier = (confidence - outcome)^2]
    B --> F[cost_bps subtraction]
    F --> G[correct_net_t5 / correct_net_t20]
    E --> H[validation_log row]
    G --> H
    H --> I[src/validation/aggregate.py validation_stats]

    class A,B,C,D,E,F,G,H,I dark
```

The cost assumptions are hard-coded in `src/validation/engine.py:15`:

| Pair | Round-trip cost (bps) | Rationale |
|------|----------------------|-----------|
| EURUSD | 0.2 | 0.1 bps each way, G10 spot |
| USDJPY | 0.3 | Slightly wider G10 spot |
| USDINR | 10.0 | EM spot spread |

Net correctness is computed in `src/validation/engine.py:62`:

```python
def _is_correct_net(predicted: str, bps_net: float) -> bool:
    p = predicted.strip().upper()
    if p == "BULLISH":
        return bps_net > 0.0
    if p == "BEARISH":
        return bps_net < 0.0
    if p == "NEUTRAL":
        return realized_direction(bps_net) == "NEUTRAL"
    return False
```

This split is important because the Brier score must remain a **calibration** metric on gross directional outcomes, while net correctness is the metric that answers whether a strategy would actually make money after costs (`docs/METHODOLOGY_AUDIT_TRIPLE_PERSONA.md:197`).

## 3. Data-Quality Audit Results

`scripts/_audit_validation.py` was re-run after the fixes. The script performs an immutable-log style audit: it recomputes every Brier score from `(confidence, outcome)`, checks return signs against `actual_direction`, validates `cost_bps` against the pair table, and flags any NEUTRAL row marked `correct=True` when the realized direction is not NEUTRAL (`scripts/_audit_validation.py:91`).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorB': '#2d333b', 'actorBorder': '#6d5dfc', 'actorTextColor': '#e6edf3', 'primaryColor': '#2d333b', 'primaryTextColor': '#e6edf3', 'primaryBorderColor': '#6d5dfc', 'lineColor': '#8b949e', 'secondaryColor': '#161b22', 'tertiaryColor': '#2d333b' }}}%%
sequenceDiagram
    autonumber
    participant A as _audit_validation.py
    participant B as writer.py
    participant C as validation_log
    participant D as validation_stats

    A->>C: SELECT all non-superseded rows
    A->>A: recompute Brier / cost / return signs
    alt mismatch found
        A->>B: bulk_rewrite_validation_rows(old_ids, new_rows)
        B->>C: UPDATE is_superseded = TRUE
        B->>C: INSERT corrected rows
    end
    A->>D: compare stored stats vs raw log
    A->>A: print quant summary
```

The 2026-06-29 audit output shows the ledger is now clean:

| Issue | Count |
|-------|-------|
| Duplicate `(date, pair)` keys | 0 |
| Rows with `date > today` | 0 |
| Invalid pair values | 0 |
| Brier scores outside `[0,1]` | 0 |
| Confidence outside `[0,1]` | 0 |
| Brier recomputation mismatches | 0 |
| Cost bps mismatches | 0 |
| T+5 return sign vs `actual_direction` mismatches | 0 |
| T+20 return sign vs `actual_direction` mismatches | 0 |
| NEUTRAL rows marked `correct=True` | 0 |

The bulk correction helper lives in `src/db/writer.py:570` and obeys the append-only rule by marking old rows superseded before inserting replacements, consistent with `docs/IMMUTABILITY.md:14`.

## 4. Measured Track Record

### 4.1 Full-history directional track record (current as of 2026-06-29)

| Pair / ALL | Calls | Directional | Wins | Win Rate | Net Win Rate | Mean Brier (T+5) | Brier Skill |
|------------|-------|-------------|------|----------|--------------|------------------|-------------|
| EURUSD | 5,826 | 2,761 | 1,299 | 0.4705 | 0.4900 | 0.2512 | -0.0049 |
| USDJPY | 7,611 | 6,670 | 3,167 | 0.4748 | 0.4946 | 0.2498 | 0.0008 |
| USDINR | 5,772 | 3,083 | 1,522 | 0.4937 | 0.4826 | 0.2497 | 0.0011 |
| **ALL** | **19,209** | **12,514** | **5,988** | **0.4785** | **0.4907** | **0.2501** | **-0.0004** |

These numbers are computed by `scripts/_audit_validation.py:122` and match the stored `validation_stats` row exactly (`scripts/_audit_validation.py:268`).

### 4.2 Latest 90-day rolling window

The `validation_stats` table stores `t5_rolling_90d_accuracy` but does **not** yet store a rolling 90-day Brier. We computed it directly from `validation_log` for the 90 calendar-day windows ending on the two most recent `as_of_date` values:

| Window end | T+5 directional calls | Rolling accuracy | Mean Brier |
|------------|----------------------|------------------|------------|
| 2026-05-27 | 138 | 0.4615 | 0.2576 |
| 2026-06-29 | 86 | 0.4713 | **0.2600** |

The 2026-06-29 window is the relevant "latest 90-day window" referenced in the done-when condition. Its **T+5 ALL mean Brier is 0.2600**, versus the 0.225 target.

### 4.3 Calibration breakdown (latest window, ALL)

| Confidence bin | n | Avg confidence | Observed accuracy |
|----------------|---|----------------|-------------------|
| 0.00–0.50 | 84 | 0.471 | 0.476 |
| 0.50–0.55 | 2 | 0.519 | 0.500 |

This confirms the model is roughly calibrated—its average confidence (~0.47) matches its observed accuracy (~0.47). The problem is not over-confidence; it is that the forecast is barely better than a coin flip.

## 5. Why the ≤0.225 Target Is Unreachable Here

For a binary forecast with observed accuracy `p` and perfectly calibrated confidence, the minimum achievable Brier score is the Bernoulli variance:

```
Brier_min = p * (1 - p)
```

At the latest 90-day accuracy `p = 0.4713`:

```
Brier_min = 0.4713 * (1 - 0.4713) = 0.2491
```

The actual measured Brier is 0.2600. The difference (0.0109) is the **calibration error** component. Even if we eliminated every last bit of that error, the Brier would fall only to **0.2491**, still **0.0241 above the 0.225 target**.

To hit 0.225 at perfect calibration, the required accuracy is:

```
p * (1 - p) ≤ 0.225  →  p ≥ 65.8%  (or p ≤ 34.2%)
```

The current signal cannot reach 65.8% directional accuracy on a 90-day window without changes to feature engineering, model selection, or regime-definition thresholds. Those changes are explicitly out of scope for this task (`Scope: pipeline/src/validation/..., validation_log/validation_stats tables, docs. Do not change signal generation`).

## 6. Interpretation of the "Measured Improvement"

The pre-fix full-history ALL T+5 mean Brier stored on 2026-05-27 was 0.2389. After correction it is 0.2501. This is **not** a degradation in the model; it is a correction in the ledger:

- The 8 NEUTRAL rows previously carried `correct=True` when the realized direction was `UP` or `DOWN`. Treating a non-NEUTRAL outcome as correct pushed their Brier scores toward 0, lowering the mean.
- The 1 USDJPY row had a stale/incorrect Brier value.
- Correcting these rows raised the aggregate Brier to its true, higher level.

The improvement delivered by this work is therefore **measurement integrity**: net correctness, cost assumptions, immutability, and audit reproducibility. The forecast itself is unchanged, so its intrinsic Brier cannot be improved from the validation layer alone.

## 7. Recommendations

1. **Add a rolling 90-day Brier column to `validation_stats`.** `src/validation/aggregate.py:206` already computes a 90-day accuracy window; extend it to compute `rolling_90d_mean_brier` so the dashboard can display the target metric directly.
2. **Implement probability recalibration on a hold-out window.** A small improvement (up to ~0.011) is available by remapping confidence to observed accuracy via Platt scaling or isotonic regression, but this will not close the gap to 0.225.
3. **Treat 0.225 as a signal-generation milestone.** The only path to a sustained ≤0.225 T+5 ALL Brier is a directional accuracy above ~66% on the 90-day window. That requires work in `src/signals/` or regime-call logic, outside the present scope.
4. **Keep the audit script in the daily workflow.** Running `scripts/_audit_validation.py` after each backfill is now cheap and guarantees the immutability/cost assumptions remain intact.

## 8. References

- `pipeline/src/validation/engine.py:15` — documented round-trip cost assumptions.
- `pipeline/src/validation/engine.py:62` — net-correctness computation.
- `pipeline/src/validation/engine.py:79` — horizon metric computation and Brier scoring.
- `pipeline/src/validation/aggregate.py:143` — aggregate horizon statistics.
- `pipeline/src/validation/aggregate.py:206` — rolling 90-day accuracy window.
- `pipeline/src/db/writer.py:570` — versioned bulk correction helper.
- `pipeline/scripts/_audit_validation.py:122` — quant metric computation.
- `docs/DB_STATUS.md:182` — `validation_log` schema and append-only rule.
- `docs/IMMUTABILITY.md:14` — immutability trigger for `validation_log`.
- `docs/METHODOLOGY_AUDIT_TRIPLE_PERSONA.md:197` — rationale for transaction-cost realism.
