# Packet 18.1: directional core and publication semantics

27 September 2026. Source base: `9fa150538d08ab5a2a6c587976552944f47a724d`, with existing repair work preserved. This packet implements the frozen `docs/DIRECTIONAL_INPUT_CONTRACT.md`. It is an unvalidated reference model, not evidence of predictive accuracy.

The shared conversion accepts only the three allowed pairs, including slash aliases. Rate remains pair-up; EUR futures remain positive EUR demand; JPY futures reverse into USDJPY direction; USD special reverses for EURUSD; normalized INR demand reverses into USDINR direction. Unknown pairs, outside currencies, unsupported family/pair combinations, booleans, nonnumeric and nonfinite present inputs reject. Missing and observed zero remain distinct. The returned dataclass is frozen and the raw inputs are not changed.

The composite uses the retained relative static rate/COT/special/FPI weights, with INR COT disabled. VOL/OI never enter its numerator or denominator. Betas cannot alter direction or weights. Layer 2 orients futures positioning separately from the unchanged raw crowding percentile and returns NEUTRAL whenever composite is missing. No contrarian rule or confidence calibration was added. The pre-existing symmetric conviction change in Layer 2 was preserved.

Layer 1 now uses the existing USD_STRENGTH/WEAKNESS label strings with separate moderate and strong tiers. EURUSD and USDJPY map pair-up scores to opposite USD directions and reconstruct their prior tiers accordingly. Composite scores no longer invent risk-on, growth-surprise or risk-off labels. Separate Layer 1 shock rules remain unchanged.

The builder publishes VOL_EXPANDING, VOL_CONTRACTING, VOL_STABLE or UNAVAILABLE, and OI_HIGH, OI_LOW, OI_TYPICAL or UNAVAILABLE. An explicit expansion flag remains visible even without a normalized volatility value. INR special is named Oil + DXY. Default versions are `3.0-directional-reference` and `pair-direction-v1`; explicit version overrides remain supported.

Parent review found and corrected a physical-state inversion in the initial OI labels. The existing `compute_oi_signal` maps low percentiles to positive normalized values, so positive must publish OI_LOW and negative OI_HIGH. Its raw convention is unchanged. The added regression passes actual 0th, 50th and 100th percentile outputs through the builder, plus missing input. This catches the inversion that arbitrary normalized fixtures alone missed.

## Verification

- `node ../scripts/repair/verify-pytest.mjs tests/test_directional_input_contract.py`: 85 passed after the OI correction, `REPAIR_PYTEST_VERIFIED`.
- Scoped Ruff across all six owned Python files: passed.
- `python -m mypy .`: passed, 201 files in the concurrent checkout. A first run caught two invalid values in the new test's execution-layer fixture; corrected to existing allowed values before the passing run.
- Focused old and new compatibility suite: 117 passed, 13 failed before parent integration. The failures were diagnosed rather than rewritten here: seven builder tests assert the old version, directional VOL/OI labels or the removed EM label; five classifier tests assert old shock labels and inverted EURUSD direction; one hysteresis test combines positive EURUSD composite with the old USD-bid prior label. The parent owns those fixture changes and the full integration suite.

Coverage includes all-pair state-only counterexamples, currency signs, reciprocal sign symmetry, beta invariance, zero versus missing, rejected input types, raw non-mutation, frozen values, JPY clash orientation with unchanged crowding, all five label-tier round trips, missing-composite neutrality and publication versions/state labels.

## Pre-edit impact checks

The GitNexus CLI was called upstream for every changed existing function/method. `compute_composite`, `run_layer2_directional`, `prior_tier_from_regime` and `_tier_to_regime` each reported CRITICAL with 33 direct dependents and seven affected flows. Those summaries returned an empty symbol type and repeated a broad graph, so their apparent precision is not independently established. Reported flows include scheduler, backfill, staged signal generation and UI consumers. `build_regime_call` resolved the actual method ID and reported CRITICAL, two direct dependents and 87 affected flows. The parent was informed of the critical risk before edits.

The new `directional_inputs` and `currency_strength_to_pair` names were queried before addition; the index correctly reported them absent. The index was not rebuilt, per parent instruction. No commit was made, so a commit-time detect-changes check was not applicable.

Before the OI correction, the builder impact was rerun: CRITICAL, two direct dependents and 87 affected flows. Both the affected contract-test name and new percentile-test name were also queried; neither was present in the existing index. The critical warning was stated before editing, and all 85 focused tests plus scoped Ruff passed afterward.

## Remaining integration and evidence

The parent owns scheduler, staged, replay and diagnostic integration, publication-driver wording, old fixture corrections, independent review and full-suite gates. At inspection, `get_regime_metadata` did not map the existing USD_STRENGTH/WEAKNESS strings and fell back to neutral metadata; this was reported to the parent for an owned follow-up. `get_regime_category` already categorizes those labels as RATE_DRIVEN.

Source release timing, homogeneous source histories, economic validity of retained static weights, full live/replay parity and forecasting performance remain separate requirements. No provider access, external write, notification, paid AI, runtime startup, commit, push or deployment occurred.

## Ownership ledger

Only these files were created or edited by this worker:

| Absolute path | SHA-256 before parent integration |
| --- | --- |
| `D:/Projects/fxregimelab/pipeline/src/signals/direction.py` | `10B1C557BD60372F971F2CC9B481792F95F7587BD11E426D8E7902C647A4ABF1` |
| `D:/Projects/fxregimelab/pipeline/src/regime/composite.py` | `AAA3CD99C4AD0B65D38357D84BFAB7AE0EDC6C8CE88EA4C6775C42D60A4E7620` |
| `D:/Projects/fxregimelab/pipeline/src/logic/layer2_directional.py` | `BC50D8B81FDFA01823C772FAAC87319A620356322882278567263D00035BF78D` |
| `D:/Projects/fxregimelab/pipeline/src/logic/layer1_gate.py` | `68979A3F5F5863CD475560E160BE59A85C1E6DEA1F921233C00066430F785EE2` |
| `D:/Projects/fxregimelab/pipeline/src/core/regime_call_builder.py` | `B4EEAB3548C9381D29ADD63D7476538914B617B1F67DB13F2E5F2C533D4BAF8B` |
| `D:/Projects/fxregimelab/pipeline/tests/test_directional_input_contract.py` | `EC50890B3BE4297A91075945AF2AE6E673D3F49B42DF89A42D3A56F820983BC7` |
| `D:/Projects/fxregimelab/reports/repair-directional-core.md` | This report |
