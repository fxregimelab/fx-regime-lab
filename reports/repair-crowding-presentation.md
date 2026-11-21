# Public crowding description repair

Date: 27 September 2026  
Branch: `codex/frontend`  
Source HEAD: `9fa150538d08ab5a2a6c587976552944f47a724d`

## Result

The desk card now treats only the exact `crowding-description-v1` payload as a current crowding description. Valid rows show the supplied reported net as provisional, its alignment with the frozen call, the COT report date, the unknown category definition, and unverified source availability. The price line shows the signed close difference from the 40-observation arithmetic mean and the latest close date.

Missing, legacy and malformed diagnostic payloads have separate unavailable messages. None of those states becomes a low-risk or no-divergence conclusion.

The reader accepts the producer's partial-price result: one to 39 valid observations retain the latest supplied close and date while the mean and deviation remain unavailable. COT and price availability are independent, so a missing component does not erase the valid one. An unavailable price cannot carry a spot, date, mean or deviation.

The diagnostic pair must match the card pair. Dates cannot be later than the diagnostic as-of date; report age must match the dates; spot and mean values must be positive; the price deviation must agree with spot and mean; and reported-net direction and alignment must agree with the pair orientation and frozen call. These checks cover EURUSD, USDJPY and USDINR.

The current query mapper leaves stored database rows unchanged but returns `null` for legacy pain, Apex score and global rank, and it no longer calculates rank jumps from stored global ranks. The telemetry type accepts the scheduler's explicit null values for `cot_is_stale`, `underwater_triggered` and `Systemic_Cluster`.

The desk brief keeps valid bias and catalyst text. It discards both the old `squeeze_risk` / `swing_factor` text and unstructured raw legacy prose, replacing that field with `Participant losses and squeeze probability unavailable` under `DIAGNOSTICS`.

## Render receipt

`web/tests/crowding-diagnostic.test.mjs` renders the actual `DeskCard` and `DeskCardTelemetryRow` with React DOM server. The scoped loader only replaces animation, icon-like wrapper and browser-only dependencies; it does not replace either component under test or the crowding parser.

The rendered fixtures verified:

- `-1,200` reported contracts, `opposed to call`, report date `2026-09-22`, category definition unknown and source availability unverified.
- `-2.50%` close versus the 40-observation mean with latest close date `2026-09-27`.
- Exact preservation of numeric zero as `0 contracts` and `0.00%`.
- The actual core short-history shape: provisional latest close/date with 39 observations and null mean/deviation, without hiding valid COT.
- Valid COT with missing price, and valid price with unavailable COT.
- Matching presentation for all three locked pairs and rejection of a USDJPY payload on an EURUSD card.
- Rejection of future report/latest dates, nonpositive spot/mean values, contradictory net direction/alignment, inconsistent signed deviation and unavailable prices carrying a deviation.
- Explicit missing, legacy and malformed payload messages.
- Rejection of `NaN`, falsely qualified point-in-time data and a falsely verified release status.
- Removal of high pain, Apex score, rank jump, asymmetric setup, underwater and old squeeze-danger output.
- Query output nulls for stored pain `99`, Apex `0.98` and rank `1`, with no prior-rank query.

## Checks

- `node --test tests/crowding-diagnostic.test.mjs`: 10 passed, 0 failed.
- `node --test tests/*.test.mjs`: 28 passed, 0 failed.
- `npx tsc --noEmit`: passed.
- `npx biome check src/components/ui/desk-card.tsx src/lib/queries.ts src/lib/crowding-diagnostic.ts tests/crowding-diagnostic.test.mjs`: passed.
- `git diff --check -- web/src/components/ui/desk-card.tsx web/src/lib/queries.ts`: passed.
- `npx --yes gitnexus detect-changes --repo fx-regime-lab`: exited 0 with no change map; it emitted only an unrelated CRLF warning for `pipeline/tests/test_writer.py`.

GitNexus impact checks labeled every inspected UI/query symbol CRITICAL, with 38–70 supposed dependants. The returned graph was not credible: it linked React components and a desk-row mapper to unrelated Python backfill, fetcher and staged-pipeline flows. Direct source inspection found one actual `DeskCard` consumer (`compare-view.tsx`), no current `DeskCardTelemetryRow` consumer, and `mapDeskRow` only inside the desk snapshot hook. The implementation kept the existing prop interface so those consumers remain compatible.

Follow-up impact checks for the new `readCrowdingDiagnostic` and `isPrice` symbols returned `UNKNOWN` because the current GitNexus index does not contain either new file symbol. No index rebuild was performed.

Docker and the heavier Hermes runtime were not required. These checks use local TypeScript, Biome, Node and server rendering only. No network fetch, credentials, database write, AI call, production runtime, full build, commit or deployment was used. Browser visual QA and the canonical Linux/Vercel build remain outside this leaf; layout classes and the existing visual identity were otherwise retained.

## File hashes (SHA-256)

- `web/src/components/ui/desk-card.tsx`: `86F630DEF15E408FD3E9AE5758E389DEE06B670B26F22AFDE12303B9E5512BBC`
- `web/src/lib/queries.ts`: `D7A6BF0D5E3CA0FC1F2EA1A0786C8ECD5D141F8563F02E95B14B334EC78C9767`
- `web/src/lib/crowding-diagnostic.ts`: `D0D340A79CBCB8B5E15ADEBD7712AC80ED831DC9597985410DC30C83F4E04FA0`
- `web/tests/crowding-diagnostic.test.mjs`: `2EAFECE6827D6EC7D8B4F01C1EB79F340D39EDF1888EEF8AF9DF9CB59C06A429`

## Parent acceptance additions

The parent added rejection of an overflowing intermediate price ratio and preserved valid COT when the core returns UNAVAILABLE price arithmetic with its retained latest close/date/count. The final focused render gate passes 10 tests; actual Python-to-TypeScript bridge 243 payloads passes. Full local frontend verification and build are in repair-crowding-integration.md. These additions supersede the two earlier parser/test hashes above.

- `web/src/lib/crowding-diagnostic.ts`: `ec8ff77e6f679d451d344680aabfa153d90202f02dfbd84a6509fc288e8a80d8`

- `web/tests/crowding-diagnostic.test.mjs`: `111534b07debb4867cf24fa0970cca009f590c14ac5da1d01fc274955d6d7860`
