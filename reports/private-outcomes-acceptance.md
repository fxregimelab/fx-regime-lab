# Private decision and outcome history — coordinator receipt

1 October 2026. The owner's request to record every suggested and rejected observation is implemented in the authenticated private desk. This is a bounded recording and replay acceptance; profitable trading and forecast qualification remain open.

Every new eight-pair report publication records all original candidates, including abstentions, before display-time freshness holds. The exact report and source bytes, real recording time, decision, reasons, direction, probability evidence, reference plan and costs are preserved. A publication receipt must verify that the exact report became current. Repeated publications remain visible but do not inflate distinct-observation or rejection-reason counts.

Later evaluations append separate events. Entry cannot precede the first weekday after the real recording date in UTC. BUY and SELL diagnostics are fixed beforehand, and a complete frozen candidate plan has its own separate counterfactual. The evaluator uses later completed observations and conservative ordering for ambiguous daily bars. No later winner is chosen as the earlier prediction. Missing or bad sources stay unavailable; a source that cannot yet contain the full horizon stays pending. Completed results survive later failed or stale attempts. Every displayed source-backed result replays from the preserved bytes.

The dashboard's **Outcome history** section shows each decision, outcome availability, both benchmark results when mature, frozen-plan results, rejection reasons and source repair actions. **Read record** exposes the original evidence. The CSV preserves every row. **Check saved outcomes** uses existing captures; **Refresh research** collects new source inputs through the existing research path. The normal publication path updates the journal automatically. No recurring job was added.

## Actual initial record

Current report SHA-256: `d70d94256bc4c16986d69793e596927429d5bc1619d820c5292865e428543c81`.

- Recorded at `2026-10-01T17:38:06.951317+00:00`; its earlier report generation clock was not used as the decision-recording clock.
- Eight distinct decisions: all `ABSTAIN`, including USDJPY.
- Five pending outcomes; three unavailable benchmarks: USDJPY, USDCHF and NZDUSD could not freeze a valid risk window.
- Earliest eligible entry date: `2026-10-02`. There are no matured forward wins or losses in this new journal.
- Execution remains `NOT_RECORDED`; forecast qualification remains `UNQUALIFIED`.
- Recording and repeated authenticated updates preserved the current report and prior journal events byte-for-byte.

The separate current-report refresh that produced this report occurred during ongoing work; its initiating actor is unverified. Its actual current DeepSeek review is preserved and remains unqualified. The outcome journal and its checks do not call AI, fetch external sources, submit orders or rewrite historical research.

## Verification

Final full pipeline: **2,663 tests passed in 107.47 seconds**, Ruff passed, MyPy passed **270 source files**. The [raw transcript](D:/Projects/fxregimelab/reports/private-outcomes-checks.txt) has SHA-256 `8a649d4722a997e01b694c89b08909400a52587f0889102d9e5780d019e7e167`. Focused journal/API checks passed 46 tests; the independent reviewer separately passed 51 journal/existing-API checks and a supplemental eight journal-API tests. The UI verifier passed syntax, missing evidence, safe text, authentication, CSRF, journal updates, existing trade pagination, export and logout controls.

Newer actual eight-pair offline research replay passed in **34.95 seconds**, including daily/reference/session/bidask, current-review, vintage/release/policy and both portfolio audits. Journal result replay is also enforced by every authenticated history read.

[Independent review](D:/Projects/fxregimelab/reports/private-outcomes-independent-review.md): bounded PASS, SHA-256 `e0a8c239c78d760dfadb44c23373cf39ff00ac2f7ab39a07fe93142b90cc6afb`. Its supplemental reviews accept the added navigation anchor and independently inspected the separate journal-API regression file. Source, UI and test hashes are bound in that receipt; full-suite and runtime acceptance belong to this coordinator receipt.

[Actual HTTP verification](D:/Projects/fxregimelab/reports/private-outcomes-runtime.json): SHA-256 `06f1d4f7b892852334887649e71b7a6e941bd534285b518e41e9ba420fb783be`. It independently exercised unauthenticated denials, authenticated eight-row history and CSV, missing/bad CSRF denials, successful idempotent update, logout, and original report/event preservation. The running loopback service is PID **31692**, started with the existing manual launcher after checking the prior process and idle refresh state. No Docker or heavier Hermes component was required or started.

Actual browser verification selected JPY's journal record and inspected its frozen evidence. The owner link is [the private dashboard](http://127.0.0.1:8765/#decisionJournal). There was no horizontal page overflow at a 747px viewport. The [saved screenshot](D:/Projects/fxregimelab/reports/private-outcomes-dashboard.png) shows eight distinct decisions and the five-pending/three-unavailable split. Credentials were never printed. Password and access boundaries remain unchanged.

## Remaining scope

This journal is hypothetical research, not an account execution ledger. It neither auto-learns nor adjusts policy thresholds. Reason groups overlap and do not establish a causal effect of a filter. Local hashes cannot detect deletion of an entire event plus its receipt; an external/chained inventory is future hardening, not a present claim.

The strategy still fails the weekly frequency and positive-expectancy goals. [The portfolio receipt](D:/Projects/fxregimelab/reports/private-portfolio-acceptance.md) records 1.8298 entries per common-coverage week and negative broad mean net R. Continuous correlation limits, realistic joint currency risk and validated hedges remain open. Next eligible work is R2's source-available historical fundamentals/surprises, R3's predeclared strategy trials and untouched evaluation, R4's costed continuous concentration/hedge research, and R5's genuinely observed forward paper results. R1's executable-price and cost stress holds also remain.

Unlazy scope: two bounded manual gates met, three runnable gates remain unmet pending inspected checker approval, zero abandoned. Direct checks and independent review do not imply automatic certification or release held leases. No commit, push, deployment, migration, production write or broker order occurred. The persistent overall goal remains active.
