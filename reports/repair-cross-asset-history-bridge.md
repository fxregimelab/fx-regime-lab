# Cross-asset history bridge repair

Date: 27 September 2026  
Source revision: `9fa150538d08ab5a2a6c587976552944f47a724d` (`codex/frontend`, shared dirty checkout)

## Boundary repaired

`CoreIngestionSnapshot.from_buffer` now retains a validated `hist` map from the actual cross-asset fetcher payload. It accepts only the supported history legs: VIX, DXY, oil, gold, copper, the existing iron-ore proxy, STOXX, Bund-BTP spread and ECB balance sheet. Unknown keys do not cross the boundary.

Each accepted history must be a non-empty list containing only finite numeric values. A boolean, numeric string, non-numeric value, non-finite value or integer too large for a finite float rejects the whole leg. The coercer does not remove individual bad rows because that would shorten the series and change its chronology. Accepted lists are converted to new float lists, detached from the raw provider payload. `hist` is omitted when no usable history remains.

Existing scalar keys and missing-value defaults remain in place. Numeric strings still follow the old float-coercion behavior. Booleans, non-finite values and integers that overflow float conversion now become unavailable rather than entering signal math.

The core and staged `cross_asset` annotations are now `dict[str, Any]`, matching the mixed scalar/history payload already consumed by `compute_special_signal`. Both dataclass descriptions now state the practical mutability boundary: `frozen=True` blocks attribute rebinding, but nested dictionaries and lists remain mutable and must be treated as read-only. The production adapter still makes a shallow outer copy; this repair claims detachment from the raw provider payload, not deep immutability between the core and staged snapshots.

## Runtime evidence

The regression test follows the real local boundary:

`CoreIngestionSnapshot.from_buffer` -> production `_map_core_to_staged` adapter -> `SignalStage.run`

Synthetic histories contain 30 prior observations plus the current observation. Increasing VIX produces the expected negative USD/JPY special factor; increasing oil and DXY produce the expected positive USD/INR special factor. The tests also cover provider-buffer detachment, whole-leg rejection for malformed history, positive and negative infinity, oversized integers, numeric strings and booleans in history, supported special-history legs, unknown-key exclusion, scalar preservation and explicit unavailability when history is missing. When every history leg is invalid, the core snapshot omits `hist` and the actual staged adapter records `cross_asset` in `missing_fields`.

- `pytest -q tests/test_cross_asset_history_bridge.py`: **5 passed after the overflow review correction**
- `node ../scripts/repair/verify-pytest.mjs tests/test_cross_asset_history_bridge.py tests/test_ingestion_snapshot.py tests/test_staged_adapters.py tests/test_staged_multi_pair.py tests/test_staged_shadow_runner.py`: **58 passed**, `REPAIR_PYTEST_VERIFIED`, before the additive overflow regression correction; the parent owns the post-correction exact-gate rerun
- `ruff check src/core/ingestion_snapshot.py src/staged/contracts.py tests/test_cross_asset_history_bridge.py`: **passed**
- `mypy .`: **passed, 204 source files**
- `mypy src/core/ingestion_snapshot.py src/staged/contracts.py tests/test_cross_asset_history_bridge.py`: **passed after the overflow review correction, 3 files**
- `git diff --check` on the four owned paths: **passed**

No network, provider, credential, environment, database, AI, notification, commit or deployment action was used.

## Impact review

GitNexus reported MEDIUM risk for both `IngestionSnapshot` classes. It reported CRITICAL risk for `from_buffer` and `_coerce_cross_asset`, but the returned graph mixed unrelated frontend and generic processes into the result. Direct caller review found the relevant path in the production staged adapter, scalar reads in `RegimeCallBuilder`, staged snapshot copies and `SignalStage`. The implementation remains additive at that boundary: existing scalar keys keep their shape and only the validated nested history is added.

New test helpers and test functions were absent from the existing index, so their required pre-edit impact checks returned UNKNOWN with zero impacted symbols.

## File hashes

- `pipeline/src/core/ingestion_snapshot.py`: `0409B130003ABFF04B908B5BA1D8B88718A5B2E47250EC1BC1463DE62748858B`
- `pipeline/src/staged/contracts.py`: `318F6CDBF06D274827625C9DA9F674E0D35721479040A11675EFF1489A5A1EB9`
- `pipeline/tests/test_cross_asset_history_bridge.py`: `FBCC52E997D9E6DC333A14A9446475D4CB8CA9A022EE0472A69A089E8E19453D`

## Remaining qualification

The history payload contains ordered values but no observation dates, source release timestamps, market-session calendar or decision-time cutoff metadata. This repair preserves the fetcher's existing oldest-to-newest order and its current-included-last convention; it does not establish that each observation was available at the historical decision time. Full dated-source and cutoff qualification remains open under P01 and the wider research repair contract.
