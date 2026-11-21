# FPI observations and signal eligibility

Status: source definitions and original HTML verified on 27 September 2026. The parser, pure value construction and private raw-capture storage are implemented. Scheduled acquisition, durable parsed membership/qualification and model activation remain unimplemented. Current calls keep FPI unavailable. The [source review](../reports/repair-fpi-source-research.md) contains the primary evidence and retrieval limits.

Packet 23 correction: the initial first-seen and selection rules below are historical and insufficient for durable research. The former selector lost an A → B → A reversion and could not represent durable visibility after retrieval. It is now retired and raises before inspecting input. Its former passing structural tests did not prove causal selection. The [timing review](../reports/repair-fpi-timing-review.md) and replacement [selection contract](FPI_SELECTION_CONTRACT.md) supersede those assumptions with occurrence membership, qualification events and exact decision snapshots. The replacement must pass independent verification and receive a proven durable reader before production integration. Raw captures follow the separate [capture contract](FPI_CAPTURE_CONTRACT.md); database stored_at is not available_at.

The former SEBI scraper used an unverified endpoint, guessed four table columns, and asserted an unsupported publication hour and archive length. Both fetch APIs now reject before I/O. A scalar `fpi_flow` from an old signal row cannot qualify a new call. Existing records remain intact.

## What the proposed series measures

Proposed identity: `NSDL_FPI_CONFIRMED_REPORTED_ALL7_INR_CRORE_DAILY_V1`.

Use the investment section of the [NSDL production report](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx), measured in INR crore. Preserve its reporting date. This is not a verified trade date, settlement date or release timestamp. Custodian reporting can cover trades on and before prior trading days.

Keep all seven category subtotals: Equity, Debt-General Limit, Debt-VRR, Debt-FAR, Hybrid, Mutual Funds and AIFs. Keep their route or scheme components, gross purchases, gross sales and net investment. The final total must reconcile with category subtotals under a documented rounding tolerance. Do not double count component rows and subtotals. Do not substitute the USD-million column or the separate derivatives section. Reject incomplete, duplicate, unknown or conflicting groups rather than reconstructing a partial total.

NSE provisional exchange trades, NSDL confirmed reports and RBI monthly portfolio aggregates are different series. Monthly figures cannot be interpolated into daily observations. Historical category changes need separate definition versions or an explicitly comparable component series. The official note also includes corporate actions such as bonus issues and conversions. The total is neither pure cross-border cash flow nor observed spot-FX demand; funding, hedging and reinvestment are unknown. See the [original-source review](../reports/repair-fpi-original-source.md) and [official note](https://www.fpi.nsdl.co.in/web/Reports/FIINote.htm).

## Initial observation proposal — timing rules superseded

Each capture must retain the source URL, retrieval time in UTC, immutable payload hash, parser version and original payload reference. Each parsed observation must retain its series identity, reporting date, units, complete component values, total and definition version. Distinguish these timestamps:

- `retrieved_at`: when this capture completed.
- `first_seen_at`: the earliest durable observation of this exact dated component set. An identical retry must preserve it.
- `released_at`: only when independently established by source evidence; otherwise unavailable.
- `available_at`: `first_seen_at` until an accepted source-release policy supplies a stronger basis.

Hash the complete component set, not only the final total. Offsetting revisions can leave a total unchanged. Changed contents append a new version; they do not overwrite originals. First seen must be assigned atomically through `pipeline/src/db/writer.py`, never backdated from a reporting date or a guessed evening release.

## Initial time-based selection proposal — superseded

One shared selector must serve live processing, staged processing and replay. At decision time T, select only versions with `available_at <= T`. For each reporting date, choose the latest eligible version; reject conflicting ties. Select the latest eligible reporting date, not whichever old report was most recently downloaded.

Build history from unique, sorted, strictly earlier reporting dates in the same series, units and coverage definition. Exclude the current observation. Use the prior 20 observations with at least 10 valid observations. Unknown dates, unqualified versions and missing categories do not become zero. Define an explicit age/coverage policy before activation; the observed monthly page is not proof of a complete reporting calendar.

Old data first captured today may support a new decision after capture. It cannot become evidence that a historical decision knew those values. Frozen historical research must preserve that distinction.

## Numeric meaning and activation

The existing pure normalizer measures deviation from the prior median, divided by 1.4826 times median absolute deviation, clipped to [-1, 1]. Above-median outflow can produce a positive score. It does not mean positive cash inflow. Invalid numbers, insufficient history or effectively zero dispersion return unavailable, including when the current value is extreme. A measured zero in a valid varying history remains legitimate evidence.

The direction boundary treats greater relative inflow as a hypothesis for INR strength, hence USDINR down. This is an unvalidated hypothesis, not an established causal coefficient. Before activation, freeze the observation selector, feature definition, prediction horizon, missingness treatment and new model/strategy versions. Compare the feature against frozen baselines out of sample, with costs and uncertainty, and record whether it adds useful predictive information.

## Required remaining work

1. Original production HTML is privately captured with hashes and receipts; actual grouped cells and malformed footer are verified. The rejected Excel export remains unverified. Preserve source terms and raw-data redistribution limits.
2. Pure parsing is implemented and independently verified against the two original captures, including grouped cells, all categories, INR/USD reconciliation and malformed footer handling. Authored tests reject duplicate/missing/reordered data, invalid amounts and nested tables. This proves the captured schema, not all possible future source layouts.
3. Private append-only raw-capture storage and idempotent central-writer operations are implemented and locally verified. Add durable parsed membership, qualification/withdrawal and exact decision snapshots; replace the defective first-seen revision order and prove transaction visibility before integrating shared selection and coverage reporting.
4. Acquire and qualify real observations, prove live/staged/replay parity, and run the frozen feature experiment before activation.

Retiring the unsafe adapter alone completed none of these replacement requirements. The original HTML, strict parser and pure observation/selection layers now have separate evidence; storage, integrated acquisition and model activation remain open.

## Implemented normalized observation boundary

`pipeline/src/research/fpi_observation.py` accepts exactly seven named categories. Each contains its exact named routes and a subtotal; each amount object contains `purchases_cr`, `sales_cr` and `net_cr`. The total has the same three fields. These are normalized decimal strings with at most two decimal places and at most 16 integer digits. This bound is an implementation limit, not a claim about plausible activity. The parser must explicitly map source parentheses to negative values and cannot turn missing values into zero.

Calculation uses integer hundredths of crore, avoiding both binary float error and ambient Decimal-context rounding. The precision assumption is independently rounded 0.01-crore figures: row reconciliation permits at most 0.015 crore; n components against a published total permit at most (n+1)*0.005 crore. The integer comparisons implement those bounds exactly. Real captured figures reconcile exactly; the tolerance is a documented engineering assumption.

The canonical `fpi-inr-observation-v1` document hashes the series, units, date basis, reporting date and every INR detail/subtotal/total. Route order and equivalent decimal formatting do not change identity. Offsetting component changes do. USD amounts and the conversion rate remain separate source evidence in the complete raw capture, not inferred cash conversions or components of the INR feature identity.

`FpiObservation` is immutable and detached from caller dictionaries. It remains a legacy parser candidate carrying source URL, raw payload hash, parser version, retrieval time and a caller-supplied first-seen field. Its canonical INR document remains the value identity. Those metadata fields cannot establish durable visibility and must not be copied into an accepted observation's availability. `select_fpi_history` now raises an explicit retirement error for empty and populated inputs. New decision selection belongs to the separate snapshot contract.

Selection requires a capture retrieved by the decision time as well as an eligible first-seen time. A later recapture alone cannot stand in for missing earlier capture evidence. Select the latest reporting date after version selection; an old date revised today cannot replace a newer reporting date. Current and history are disjoint. Calendar-day age limits in India must be supplied explicitly; there is no invented trading calendar or default freshness guarantee. The default history uses 20 dates with at least 10; stricter or longer research windows are explicit caller policy. Status is `MISSING`, `STALE_LATEST`, `INSUFFICIENT_HISTORY` or structurally `AVAILABLE`. The latter does not mean the source, database provenance, production feature or statistical value has been accepted.

These pure functions do not write storage, certify raw hashes against bytes, implement publication releases, apply later withdrawal events, or activate a model. Tests use labeled synthetic contracts. The durable first-seen writer, acceptance/withdrawal policy, operational acquisition, shared production consumers and frozen feature evaluation remain separate required work.

## Implemented original-HTML boundary

`parse_nsdl_fpi_html` accepts at most5 MB of source bytes plus one approved source URL and an aware retrieval time. It requires the observed two unnested report tables, verifies the complete eight-column investment heading and reporting-date title, excludes derivatives, expands grouped cells and validates every category/route/subtotal/total. It recognizes the AIF span that includes the grand total and accepts the source's malformed footer only under its observed limited shape. Unknown structure returns an error rather than partial data.

The parser returns immutable `ParsedFpiDay` records. Their INR observation is canonical; `source_evidence` separately hashes all published USD net components and the conversion rate. USD sums reconcile internally; the parser does not recalculate them from rounded INR values. Numeric syntax is limited to the observed two-decimal unsigned/parenthesized forms and a positive four-decimal rate. No blank becomes zero.

Parser `first_seen_at` is legacy capture-candidate metadata equal to the supplied retrieval time. It is not an availability field for the replacement decision model. Production integration requires retained parse memberships, qualification state and exact decision-read evidence; assigning a first-seen timestamp alone is insufficient. Repeated page parsing is not a durable record. The private original-capture verifier pins both raw-body and receipt hashes, and conservatively rounds submicrosecond receipt completion up to Python microsecond precision. It verifies captured contents without claiming decision availability. Original files remain outside the repository; public tests use authored synthetic amounts and structure.

Evidence: [original source](../reports/repair-fpi-original-source.md), [parser](../reports/repair-fpi-parser.md), and [observation selection](../reports/repair-fpi-observation.md). All remain local; no acquisition schedule, database migration or model activation was performed in packet21.
