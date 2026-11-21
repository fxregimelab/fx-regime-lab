# Directional regression fixture repair

27 September 2026. Packet 18.4 repaired the eight assigned regression test files. No production source, provider, database, AI, notification, or runtime was changed.

## What the old assertions meant

- Composite tests treated volatility and open interest as directional votes. They now prove that only rate, COT, special, and FPI inputs can enter the directional numerator and denominator. A VOL-only fixture returns no composite rather than inventing direction.
- EUR/USD classifier tests treated a positive pair-up score as a dollar bid. They now assert the quotation-aware meaning: positive EUR/USD is USD weakness; negative EUR/USD is USD strength. The strong-prior hysteresis fixture uses `USD_WEAKNESS_STRONG` for the same reason.
- Builder tests expected the former model and strategy versions, bullish/bearish VOL/OI labels, and a third synthetic EM component for USD/INR. They now assert `3.0-directional-reference`, `pair-direction-v1`, descriptive VOL/OI states, and `Oil + DXY`. Positive `oi_norm` means a physically low open-interest percentile, while negative means high.
- The two old inline builder comparisons duplicated label-building logic. They still check that the signal row and unaffected call fields remain equal, but the changed contract fields now have independent authored assertions. The expected labels are not calculated from the builder output.
- The simulator fixture expected the superseded explicit version `2.1-m3`. It now checks both directional reference version constants on backtest calls.
- The multi-pair and shadow fixtures supplied fabricated COT rows for USD/INR. Those rows are removed. The fixtures now provide 30 prior synthetic oil/DXY observations plus a separate current observation, which is enough for the causal percentile calculation and exercises genuine USD/INR publication coverage. Missing-data coverage remains elsewhere and was not weakened.
- The recorded EUR/USD staged fixture expected the old mixed-state score. Its expected `0.8722222222` is derived from fixture inputs: both COT measures rank at 100%, so the blended COT input is `1.0`; Bund-BTP gives `-0.8` after its raw USD-strength contribution and ECB balance-sheet expansion gives `1/3`, producing raw special `-0.233333...`; EUR/USD quotation conversion makes special `+0.233333...`. With rate history unavailable, `(1.0 * 0.25 + 0.233333... * 0.05) / (0.25 + 0.05) = 0.872222...`.

## Verification

- Focused repair gate: `91 passed in 31.13s`; `REPAIR_PYTEST_VERIFIED`.
- Split diagnostics: `69 passed in 1.83s` and `22 passed in 26.35s`.
- Ruff on all eight assigned test files: `All checks passed!`.
- `git diff --check` on the assigned tests: clean.
- MyPy was not run because this packet changes tests and documentation only; the parent owns the full pipeline verification.

GitNexus impact analysis was run before each changed test/helper symbol. It returned CRITICAL for leaf test functions while listing unrelated production and UI callers, matching the known generic-index mismatch in the packet. The coordinator was warned before edits. `npx gitnexus detect-changes --repo fx-regime-lab` did not return a scope report; it exited with only an unrelated CRLF warning for `pipeline/tests/test_writer.py`. No index rebuild was attempted.
