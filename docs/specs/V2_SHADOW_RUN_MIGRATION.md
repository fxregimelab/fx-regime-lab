# Staged Pipeline v2 — Shadow-Run Migration Procedure

> Issue: #18 | User stories: 7, 9

This document describes how to prove equivalence between the legacy v1 pipeline
(`src/scheduler.orchestrator.run_daily`) and the staged v2 pipeline
(`src.staged.orchestrator.run_multi_pair_flow`) before flipping any pair live.

## Feature flags

All flags live in `pipeline/src/config.py` and are read from the environment at
runtime.

| Flag | Default | Meaning |
|------|---------|---------|
| `USE_V2_PIPELINE` | `false` | Run the staged v2 pipeline as the live orchestrator. |
| `SHADOW_V2` | `false` | Run v2 alongside v1, compare outputs, do **not** write to the live ledger. |
| `SHADOW_V2_EQUIVALENCE_DAYS` | `20` | Number of consecutive equivalent trading days required before a pair can flip. |
| `V2_LIVE_RUNS_BEFORE_DEPRECATION` | `10` | Number of successful live v2 runs required before the legacy orchestrator path can be deprecated. |

## Shadow-run mode

When `SHADOW_V2=true` and `USE_V2_PIPELINE=false`, `run_pipeline()` executes the
legacy v1 orchestrator normally (so the daily Substack brief and live ledger are
unaffected), then runs v2 through `src.staged.shadow_runner.run_shadow_comparison()`
with in-memory (non-persisting) writer and alert ports.

The shadow runner compares, per pair:

- `RegimeCall` fields listed in `src.staged.shadow_runner._COMPARE_FIELDS`.
- Pair brief markdown (whitespace-normalized).
- Desk-card payload (whitespace-normalized string values).

Numeric fields (`confidence`, `signal_composite`, `special_signal_value`) are
tolerated within `±0.01` to account for harmless floating-point path differences.

### Equivalence window

A pair is considered equivalent for a trading day when **all** compared artifacts
match. The helper `count_consecutive_equivalent_days()` counts the trailing run
of equivalent days for a pair.

Required window: **20 trading days**. This covers the T+5/T+20 validation
horizons so that the new pipeline is exercised across the full validation cycle
before it takes over.

### Running shadow mode

```bash
# Prefect Cloud / managed worker
export SHADOW_V2=true
export USE_V2_PIPELINE=false
python -m pipeline.src.scheduler.run_pipeline
```

Shadow results are logged to the `src.scheduler.run_pipeline` logger as
`INFO`-level JSON-like summaries. Operators should collect these logs (or route
them to the observability stack) to track the equivalence window.

## Flip procedure

Flip **one pair at a time** so that any v2-specific issue is isolated to a single
instrument.

1. Confirm the pair has **20 consecutive equivalent shadow days**.
2. Set the live pair list for v2. As of v2 the orchestrator already respects the
   3-pair lock (`EURUSD`, `USDJPY`, `USDINR`); partial flips are controlled by
   keeping the other pairs in v1 until they too satisfy the 20-day window.
3. For a partial flip, run v2 live **only** for the ready pair while v1 continues
   to cover the others. This can be done by temporarily running v2 directly for
   the ready pair and leaving `USE_V2_PIPELINE=false` globally.
4. Recommended order:
   1. **EUR/USD** — deepest history and most liquid; best signal-to-noise for
      validating v2.
   2. **USD/JPY** — validates carry/rate-spread and intervention-proximity paths.
   3. **USD/INR** — validates India-specific macro (FPI, RBI) and liquidity
      constraints.
5. After each flip, monitor accuracy alerts and the health dashboard for at least
   5 trading days before flipping the next pair.

## Daily brief continuity

In shadow mode, v1 remains the live orchestrator and continues to generate and
publish the daily Substack brief, macro-event briefs, and desk cards. v2 shadow
outputs are captured in memory only.

When a pair is flipped live to v2, the v2 `PublishStage` writes the pair brief
via `ProductionWriterPort.write_brief()`. Macro-event briefs and desk cards
continue to be produced by the legacy path until v2 has full feature parity; this
is tracked as a separate product milestone.

## Deprecating the legacy orchestrator

The legacy `run_daily` path may only be deprecated after **all** of the following
are true:

- All three locked pairs have been live on v2 for at least 20 trading days each.
- There are **10 or more successful live v2 runs** recorded in `pipeline_runs`
  with `steps_completed` containing `orchestrator_v2`.
- No critical alerts or regressions in rolling 90-day directional accuracy during
  the live v2 period.

## Rollback

If a live v2 run fails or accuracy regresses:

1. Set `USE_V2_PIPELINE=false` (and `SHADOW_V2=true` if desired).
2. Redeploy the Prefect flow.
3. The legacy v1 orchestrator immediately resumes live publication.
4. Investigate the v2 shadow logs to identify the divergence before re-flipping.
