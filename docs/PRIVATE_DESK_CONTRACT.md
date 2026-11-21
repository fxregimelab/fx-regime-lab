# Private FX research desk — contract 14

Owner direction: 1 October 2026. A private, authenticated research desk supports manual technical analysis and execution. The owner authorized independent design decisions. This scope replaces the former restriction for private research only; existing published calls retain their original identity.

Universe, latest owner amendment: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY, EURGBP. USDJPY is explicitly restored; EURGBP remains an additional research cross. USDINR remains in the prior public research population. Earlier seven-pair references below describe their historical checkpoints and do not prohibit this expansion.

Latest owner direction, 2 October 2026 IST: the primary desk confirms or challenges technical-analysis bias over two to five business days. The owner chooses entries, stops, exits and management. Descriptive price phases and continuation/reversal watches do not require the legacy exact-entry strategy to qualify. Preserve honest source/data checks, all old research and recorded outcomes. Positive skew and high win probability are separate unproven objectives; a power law needs its own evidence. See docs/PRIVATE_BIAS_CONTEXT_CONTRACT.md.

Historical fixed-exit research policy, retained separately: signal from completed observations; next-bar entry; 3 and 5 business-day horizons initially; stop distance based on lagged ATR; half the position exits at +1R, the remaining half targets +3R and moves its stop to entry after the first target. Daily bars with an unknown intrabar order use the adverse outcome and explicitly count ambiguity. Costs include spread, slippage and holding charge assumptions. Net-zero price exit can still lose after costs. No guarantee of a positive trade or 60–70% win rate is accepted.

Data and methods: immutable local captures with source URL, receipt time, hash, first/last bar and interval. Actual provider coverage must be shown. Current-vintage macro and current AI news cannot enter historical predictive labels. Daily reconstruction and session/intraday evidence are separate cohorts. Preserve all model trials and chronological train/validation/test separation, with an embargo at least the holding horizon. No calibration or expected-return number is allowed without sample counts and held-out evidence. Ranking may abstain from every trade.

AI: all outbound model calls use pipeline/src/ai/client.py. Ground the response in dated, attributed inputs. AI provides fundamental thesis, opposing evidence and event risks; it cannot invent data, add numeric win probabilities or submit an order. Credentials stay server-side. Local dashboard authentication gates report, export and refresh routes.

Live review found incorrect rate-bound arithmetic and an unsupported carry conclusion in model prose. The private client now limits output to conditional headline scenarios: thesis and opposing fields start with `If`, quantitative/rate-bound/carry claims fail closed, and the global summary is deterministic. Policy observations remain in the verified table. These structural controls reduce an observed failure; they do not prove factual article-body grounding or predictive value. Current inputs contain titles and links, not full research documents.

## Revision 2 — data quality finding

Yahoo daily OHLC failed range validation on actual data. Preserve the failed raw captures. Use valid hourly data as a separately labelled recent cohort; any daily aggregation needs explicit completed FX session boundaries and missing-weekday controls. Add load_reference_history(pair, *, cache_dir, refresh=False) returning official ECB reference closes and metadata, and analyze_reference_pair(pair, series) for a separate long directional study. Reference closes cannot validate intrabar stops, targets, execution prices or session timing.

## Revision 3 — quarantined daily windows

Retain every valid original daily candle and preserve rejected raw rows in immutable captures. Malformed rows are excluded without repairing their prices. Mark and infer missing weekdays. Exclude the entire feature window and maximum signal-to-horizon path if either crosses a gap, even when the simulated stop would have fired earlier. The latest contaminated feature window forces abstention. The selected policy needs its own held-out positive-return evidence; profits from other policies cannot qualify it. A full reference archive is fetched once per report and its verified capture is shared across the seven derivations.

Net-positive trade rate, TP1 hit rate and directional accuracy are separate outcomes. Current numeric probability means P(net R > 0) after the assumed costs; it is not the probability of reaching +1R. Revision 3 originally pooled BUY and SELL. Revision 4 below replaces that rule. Current AI policy/news context is independent of the historical price model and does not qualify a trade.

## Shared implementation interface

New module pipeline/src/private_desk, local artifacts .private-fx (ignored), UI private-desk/index.html. FastAPI binds 127.0.0.1:8765. No database is required.

Data leaf defines load_history(pair, *, interval='1d', start='1997-01-01', cache_dir: Path, refresh=False) -> tuple[list[dict[str, Any]], dict[str, Any]]; bars use time (ISO UTC/date), open/high/low/close finite floats. Metadata describes actual first/last, source, receipt, hash, provisional status and errors. fetch_news() -> list[dict[str, Any]] with title/url/source/published_at/retrieved_at. fetch_fundamentals(cache_dir: Path) -> dict[str, Any] supplies only witnessed current descriptive values and availability; no fabricated missing legs.

Quant leaf defines analyze_pair(pair, bars, *, horizons=(3,5)) -> dict[str, Any]. Return pair, data_coverage, backtest (trials, folds, sample counts, net R, hit rates, probability calibration, assumptions), candidate (direction/entry/stop/tp1/tp2/holding_days/probability/expected_r/status/reasons/as_of), chart (recent OHLC and equity in cumulative per-call R), and session (measured or UNAVAILABLE; proposed review windows do not masquerade as optimized timing). Candidate numeric probability may be null. Unknown/malformed/insufficient input fails closed.

API report schema: schema_version='private-fx-v1', generated_at, universe, policy, pair_reports (quant dictionaries plus fundamentals and ai_analysis), data_status, research_status, news, sources, warnings. No fabricated demonstration values in the actual report. UI must tolerate nulls and explicit UNAVAILABLE status.

Endpoints: GET / serves login or dashboard shell; POST /api/login accepts password and returns csrf_token, HTTP-only cookie; GET /api/report returns report and csrf_token after login; GET /api/status reports progress after login; POST /api/refresh requires same-origin request and X-CSRF-Token; POST /api/logout; GET /api/export.csv returns per-trade audit rows after login. No API accepts broker credentials or submits orders.

Acceptance: meaningful policy/leakage/auth regressions, real seven-pair source capture or visible source failure, reproducible backtest artifact, direct pipeline pytest/Ruff/MyPy, static JS/browser checks of login/refresh/nulls/export/logout, and a working local dashboard link. Twenty–thirty years of qualified macro/news and a 60–70% profitable-trade rate remain research questions until measured.

## Revision 4 — exact probability evidence and overlapping calls

Current price probabilities and expected returns use the exact selected policy, BUY/SELL direction and strength bucket. Require at least 20 matured joint-cell calibration calls, 40 same-direction calls and 100 held-out cell predictions, plus calibration and positive net-return checks. See docs/PRIVATE_CALIBRATION_PORTFOLIO_CONTRACT.md for the complete definitions. These are research gates and do not establish independent confirmation or economic validity. The fixed two-position overlap replay reserves both currencies through the full planned horizon; it cannot claim account drawdown or live approval.

## Revision 5 — seven-currency retrospective policy histories

Use original bounded BIS daily snapshots from 5 January 1999 onward. Validate source definitions against the independently reviewed exact metadata and dated instrument registry. Keep M/NaN observations missing. Pair features use exact dates and complete six-observation, five-weekday windows; no filling and no changes across an instrument splice. Source observation dates are neither announcement clocks nor historical arrival/vintage evidence. These features remain retrospective, separate from price-model selection, AI inputs, probability and trade eligibility. See docs/PRIVATE_POLICY_HISTORY_CONTRACT.md.

## Revision 6 — bound current review and Jev assessment

The current-review command refreshes descriptive policy/news and one central-client AI review while preserving every non-context research field. Save exact input and accepted structured output bytes, parent report and predecessor fields; offline replay verifies these bindings without a model call. Enforce publisher/host/scope/digest and UTC freshness boundaries. Require complete single-sentence conditional scenarios with supplied citations; calculate displayed coverage risk notes in code. These controls do not prove article-body support or prediction. See docs/PRIVATE_CURRENT_REVIEW_CONTRACT.md and reports/private-current-review-acceptance.md.

The owner also requested Jev research. Independent official-source review supports a bounded evidence-selection/support-check experiment, kept separate from probability and eligibility. The shadow adapter, authentic passage corpus and independent labels are next work; Jev is not connected or evaluated. Its typed confidence is not an FX win probability. See docs/PRIVATE_JEV_EVALUATION_CONTRACT.md and reports/private-jev-source-research.md. R1–R5 and public repairs remain open.

## Revision 7 — separate passage capture and optional Jev adapter

The optional adapter now exists through the central AI client and a separate explicit shadow CLI. It defaults to disabled, uses only a process-level TypeSafe key, pins the model, bounds requests and responses, validates typed answers and preserves sanitized failures without retries. Normal dashboard research and trade decisions do not call Jev. Authentic public source bodies, selected article text and exact extracted-text spans are saved and replayed independently; they do not establish full-document completeness, historical availability or vintage.

Save every deterministic shortlist and exact provider packet separately from current research. A valid response remains review-required and unqualified, with indeterminate accepted semantic support. Six actual source captures and disabled shadow receipts replay; two blocked source failures remain visible. No TypeSafe call or labelled semantic benchmark occurred. See docs/PRIVATE_JEV_SHADOW_CONTRACT.md and reports/private-jev-shadow-acceptance.md. Revision 6's adapter-next statement records the earlier checkpoint; independent labels, held-out comparisons and any predictive contribution remain future acceptance requirements. R1–R5 and public repairs remain open.

## Revision 8 — JPY restored and portfolio research

The owner now includes USDJPY and requests a weekly target of 3–5 trades, at most five concurrent positions and at most two positions in one correlated directional risk group. The minimum is a research target; missing qualified opportunities must be counted rather than replaced with manufactured signals. Preserve the original two-position/no-shared-currency replay as a baseline. Add a separate strictly lagged return-correlation replay, directional currency exposures and weekly counts including zero-entry weeks. Hedging requires a separate measured counterfactual with both legs' costs and no hindsight selection. It cannot qualify current trades by itself. See docs/PRIVATE_PORTFOLIO_EXPANSION_CONTRACT.md.

The preceding request-time freshness packet passed 99 focused and 2,600 pipeline tests, Ruff and MyPy, plus actual local authenticated checks. Its two manual gates passed; four formal gates remain pending. See reports/private-readiness-acceptance.md. This source-age check does not validate a forecast. R1–R5 remain open.

## Revision 9 — every decision and later outcome

Owner requests every suggestion and abstention to remain auditable over time. docs/PRIVATE_OUTCOME_JOURNAL_CONTRACT.md defines immutable local records, real recording clocks, publication receipts, exact report/source preservation, both-sided prospective benchmarks and separate frozen candidate-plan diagnostics. Later evaluations cannot backdate entry or choose the winning direction. Repeated publications do not increase distinct-observation or reason-group averages. Actual executions remain NOT_RECORDED; no automatic learning or threshold change occurs.

The eight initial decisions all abstain; five outcomes are pending and three benchmarks cannot freeze a valid risk window. Final direct verification: 2,663 tests, Ruff, MyPy270, actual eight-pair report replay, independent bounded journal review and authenticated browser/history/export checks. See reports/private-outcomes-acceptance.md and reports/private-portfolio-acceptance.md. The measured 1.8298 weekly entries and negative broad mean net R do not meet the trading objective. Continuous concentration, hedges, historical fundamentals, calibrated positive expectancy and observed forward results remain open. The persistent goal remains active.

## Revision 10 — Japanese historical policy and every evidence publication

Japan's original BIS history is now a separately reviewed eighth currency leg. Preserve three unsupported intervals and distinguish point targets, band midpoints, effectively-zero guidance and the YCC short-term marker. Ordinary point-target level changes remain measurable; cross-definition change windows do not. Saved seven-leg v1 evidence must still replay unchanged. JPY has a separate 16 MiB capture bound; original legs retain 8 MiB. Historical arrival/vintage and predictive qualification remain unknown.

All four evidence-acquisition CLI commands use the shared report publisher and decision journal. Preserve prior AI/review evidence and detach it when a report changes. The actual extension produced eight repeated publications, leaving eight distinct observations, five pending outcomes and three unavailable benchmarks. No current probability or backtest improved. Direct checks passed 2,697 tests, Ruff and MyPy272; report replay and authenticated browser/HTTP checks passed. See reports/private-jpy-policy-acceptance.md and docs/PRIVATE_POLICY_HISTORY_CONTRACT.md. Current JPY descriptive inputs, R1–R5, public repairs and the persistent goal remain open.

## Revision 11 — current Japanese policy and official headlines

docs/PRIVATE_JPY_CURRENT_CONTRACT.md and reports/private-jpy-current-acceptance.md record the original BoJ around-guideline and attributed official headlines, separately hashed original bodies/receipts and strict publisher attribution. Current observations do not establish historical release/arrival/vintage. General-feed coverage remains incomplete; article bodies are not inferred from titles. Overall fundamentals remain PARTIAL even when current policy measurements cover all eight currencies.

Current AI inputs use v4; saved v3 input/output replay under frozen original publisher maps. One actual central-client response remains GENERATED_UNVALIDATED. The journal now has 24 publication records, eight distinct observations and 16 repeats; five pending and three unavailable outcomes. No probability, candidate, backtest, historical study or portfolio result changed. Direct checks passed 2,729 tests, Ruff and MyPy274, with independent repaired-code/source review, actual source/legacy replay and authenticated dashboard evidence. Three manual gates met and three runnable gates remain pending formal approval. R1–R5, public repairs and the overall goal remain open.

## Revision 12 — daily holding-risk study and preserved outcomes

docs/PRIVATE_DAILY_RISK_CONTRACT.md and reports/private-daily-risk-acceptance.md define a separate daily-boundary study. It preserves the original five-breach diagnostic, reviews surviving simulated positions, models a lower-priority open exit on an oversized or unavailable group, and keeps full-horizon capacity reserved. Fixed extra-slippage sensitivities and partial/gap rules remain assumptions; executable exits, hedges and intraday control stay unqualified.

Actual source replay admits 2,321 of 2,417 calls, requests one modelled exit, and has zero group breaches immediately after 4,485 daily decisions. The mean remains negative at −0.040386R and 799 common weeks average 1.8323 entries. Profitability and the weekly target remain unmet. The publication preserves its exact parent and detaches the prior AI binding. The journal now has 32 publication records, eight distinct observations and 24 repeats, with five pending and three unavailable outcomes. Final direct checks pass 2,751 tests, Ruff and MyPy276, independent reviews, source replay and actual authenticated dashboard checks. Three manual gates met, three runnable gates pending formal approval; none abandoned. R1–R5, public repairs and the overall goal remain open.


## Revision 13 — Fed history and fixed development evidence

reports/private-fomc-history-acceptance.md records the 83-statement original-source reconstruction and one frozen unoptimized development study. There are 200 admitted pair/horizon paths but only two complete all-seven events per horizon. No probability or robust edge is established. Exact parent/research/prior AI and 52 older journal files are preserved. Journal40 publications, eight distinct observations, 32 repeats, five pending, three unavailable. Direct checks pass 2,786 tests, Ruff/MyPy279, full replay, separate independent actual/source review and authenticated HTTP/browser. Three manual gates met, three formal runnable pending; R1–R5 and the goal remain open.

## Revision 14 — manual bias context

The latest owner direction replaces exact entries/exits as the primary product objective. docs/PRIVATE_BIAS_CONTEXT_CONTRACT.md separates descriptive direction/phase evidence, fundamental support, calibrated probability and trade qualification. It preserves original studies and records. Implementation and independent verification remain pending; no result or improvement is claimed yet.
