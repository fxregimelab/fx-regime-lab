# Causal spot-history cutoff repair

Date: 2026-09-27

## Outcome

Both live inference paths now select spot bars through one pure boundary before any spot-derived feature is calculated. The selector accepts only EURUSD, USDJPY and USDINR, checks exact dates, validates finite positive OHLC values and finite nonnegative volume, enforces the requested pair, sorts observations, removes exact duplicate rows and rejects conflicting rows for the same pair and date. Bars after the requested date are excluded.

`IngestionSnapshot.today_bar_for` now returns the latest valid observation on or before the snapshot date. `yesterday_bar_for` returns the immediately earlier ordered observation or `None`. The core dict adapter constructs `SpotBar` with the dataclass field list, so provider metadata fields added to `SpotBar` are copied instead of being silently lost.

The dict adapter requires all four OHLC fields. It rejects booleans, malformed numbers, nonfinite values, nonpositive prices and negative volume with `SpotHistoryError`; it does not fill missing open, high or low values from close.

The staged `SignalStage` uses the selected history for closes, volatility, Layer 1, Layer 3, volume and day change. It raises before publication if there is no earlier observation. The legacy daily flow replaces the raw spot bucket with selected histories before stress, realized volatility, signal, layer, builder and research calculations. A pair with no earlier observation is skipped and recorded in the run's existing signal-quality notes.

`ProductionFetcherPort` and the legacy live daily flow now accept only the current UTC date. They reject historical and future requested dates before the current-data provider is called. The live daily parser also rejects timestamps and trailing text instead of truncating them. Recorded snapshots, fake ports and replay paths remain usable for historical work.

This date cutoff does not prove that a provider response was available at the historical decision time. Provider retrieval timestamps, session definitions and immutable observation archives are separate evidence gates.

## Compatibility and risk

GitNexus CLI reported `IngestionSnapshot` as MEDIUM risk. It reported `today_bar_for` as CRITICAL because its transitive graph reached 87 processes; the exact direct consumers are `RegimeCallBuilder` and `SignalStage`. The focused compatibility suite covered those consumers, staged orchestration, multi-pair execution and simulation snapshots. The repository-wide `detect-changes` result is CRITICAL because the shared checkout contains 66 changed files from the broader repair, so it cannot isolate this leaf's risk.

No Docker, Hermes gateway, production provider, credentials, database write, alert or deployment was needed for this pure selection and unit-contract repair.

## Verification

- Repair gate: `75 passed`, followed by `REPAIR_PYTEST_VERIFIED`.
- Focused compatibility suite: `34 passed` across regime-call builder, staged happy path, multi-pair flow, staged orchestrator and simulation contracts.
- Full pipeline type check: `mypy .` checked 179 source files with no issues.
- Scoped Ruff check over all owned source and test files: clean.

The parent still needs to review all supported live inference consumers and independently verify the causal boundary for gate G2.
