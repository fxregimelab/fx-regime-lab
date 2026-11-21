# Rate definition repair — 27 September 2026

This packet removes unsupported rate features from the local inference paths. It does not establish a working rate strategy. The existing providers cannot yet supply the matched, time-qualified history the intended features require. D01–D03 and S01/S02 therefore remain in progress or open.

## What the sources actually measure

| Configured series | Documented instrument | Frequency and unit | Consequence |
|---|---|---|---|
| DGS2 | US Treasury 2-year constant-maturity yield | Daily, percent | A US leg, not a bilateral spread by itself |
| ECBDFR | Euro-area deposit facility rate for overnight deposits | Daily, percent | Cannot substitute for a 2-year government yield |
| IRLTLT01JPM156N | Japan 10-year government benchmark yield | Monthly, percent | Neither a 2-year instrument nor a daily observation |
| INDIRLTLT01STM | India 10-year government benchmark yield | Monthly, percent | Neither a 2-year instrument nor a daily observation |
| T10YIE | US 10-year nominal Treasury yield minus inflation-indexed yield | Daily, percent | Supplies only US inflation compensation |

Definitions checked against the providers' pages: [DGS2](https://fred.stlouisfed.org/series/DGS2), [ECBDFR](https://fred.stlouisfed.org/series/ECBDFR), [Japan](https://fred.stlouisfed.org/series/IRLTLT01JPM156N), [India](https://fred.stlouisfed.org/series/INDIRLTLT01STM), [T10YIE](https://fred.stlouisfed.org/series/T10YIE). These checks establish series definitions, not runtime availability or release-time eligibility. Breakevens contain inflation risk and liquidity components; they are not pure inflation forecasts. See [Federal Reserve research](https://www.federalreserve.gov/pubs/feds/2010/201019/).

## Implemented behavior

`pipeline/src/signals/rate_inputs.py` checks currency orientation, government-yield instrument, two-year maturity, compatible frequency, percent units and finite values. Unknown symbols fail closed. A fixture with genuinely matched instruments produces a valid difference, so missing output is driven by input quality rather than an unconditional disabled function. Current configured foreign legs fail these checks. The synchronous fetcher no longer relabels German/Indian 10-year values as 2-year values.

Pair orientation is base currency minus quote currency: EUR minus USD, USD minus JPY, USD minus INR. Legacy 10-year aliases now follow this convention. Those aliases still lose source date/frequency and remain descriptive nominal context; they do not backfill a missing two-year or real-rate forecast feature.

The approximate real-rate formula is `(nominal_base - nominal_quote) - (inflation_base - inflation_quote)`. Both compatible inflation inputs are required. Zero is a valid result; absent, boolean or non-finite inputs are unavailable. Current live inputs supply only US inflation compensation, so all bilateral real-rate fields remain null.

Structural normalization no longer copies tactical carry when structural history is absent or invalid. The two components can be unavailable independently. Historical rate rows require explicit new calculation contracts before use; old one-sided inflation and mixed-instrument carry history are excluded. The markers `pair-real10y-v1` and `pair-2y-v1` are eligibility requirements, not a claim that qualified rows already exist. Acquisition, provenance persistence and writer/query support are still required before introducing such rows.

The staged path no longer repeats today's rate/inflation into invented histories. Without observed history its scores remain null and stage health is degraded. Legacy and staged in-memory signal rows record missing-rate/history notes; the normal signal writer now preserves them in its payload. The staged flow currently publishes calls without writing signal rows, and its orchestration still drops signal-stage degradation when reporting publication success. Those persistence/health gaps remain under P01/O02/U04; this packet does not claim to repair them. No original database rows are edited.

## Counterexample and checks

An isolated AST execution of the original functions at revision `9fa150538d08ab5a2a6c587976552944f47a724d` reproduced these results without importing or running the old pipeline:

| Fixture | Original | Repaired |
|---|---:|---:|
| US 2Y 4%, ECB overnight 2% | EURUSD “2Y” +2 pp | unavailable |
| US 2Y 4%, Japan 10Y 1% | USDJPY “2Y” +3 pp | unavailable |
| US 2Y 4%, India 10Y 7% | USDINR “2Y” −3 pp | unavailable |
| German 10Y 2%, US 10Y 4% | EURUSD nominal +2 pp | −2 pp |
| Nominal spread 2%, only US breakeven 2% | “real” spread 0 pp | unavailable |

The baseline comparison emitted `RATE_NEGATIVE_CONTROL_VERIFIED`. The integrated recorded-fixture test changed from composite 0.1891 to 0.3438 because the unavailable rate input no longer dilutes other components with a fabricated zero and a 45% weight. This is a definition change, not a measured forecasting gain. Focused tests exercise these paths, valid matched inputs, rejected tenor/frequency/unit combinations, missing versus zero inflation, old-history exclusion, valid qualified-history fixtures and an actual staged signal run. The parent focused suite initially passed 56 tests; additional writer/history and recorded-flow checks were then added; final counts are recorded in the current checkpoint and Unlazy ledgers.

## Remaining work

Obtain and document real matching source histories with observation, release, retrieval and vintage dates. Enforce the decision cutoff and per-source freshness, including monthly releases. Freeze a consistent volatility denominator and distinguish yield-spread/volatility from actual financed FX carry. Repair source-history handling throughout ingestion, backfills and the public methodology. The historical simulation counterpart is tracked in `reports/repair-simulation-rates.md`.

Repaired inference needs a new model/feature version before release; current publisher labels are not release-ready. No profitability, out-of-sample skill, live-data availability, public-browser acceptance or deployed repair is established by this packet. No Docker, database server or heavier Hermes component was needed.

Final parent verification: focused gate passed with 61 tests collected; full pipeline gate passed with 439 tests collected; full Ruff and MyPy (166 files) passed. The scoped simulation gate also passed on parent rerun. Unlazy has 42 met and six unmet root gates, zero abandoned.
