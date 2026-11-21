# Private decision and outcome journal

Owner request, 1 October 2026. Record every suggested and rejected pair observation over time, with the later result and the reasons behind the decision. This extends the private eight-pair desk. It does not rewrite public calls or establish profitable trading.

## Frozen decisions

Each new eight-pair report publication records all eight original candidates, including abstentions, before request-time age holds alter the displayed view. The record binds the exact report bytes, source evidence, method, reasons, direction, probability, reference levels and real UTC recording time. Re-recording the same report is idempotent. Older reports may be imported only with the actual import time; they cannot become past forward predictions.

The local journal uses immutable files created without overwrite. It is separate from the mutable current-report projection and makes no database writes. Damaged records fail closed. Its hashes detect alteration; this local filesystem is not an externally notarized ledger.

## Later outcomes

Entry can start only on the first weekday strictly after the real recording date in UTC. Completed source bars must cover the full frozen three- or five-weekday horizon. Missing or quarantined observations, unverified sources, invalid prices and unavailable frozen risk distances keep the result unavailable. Missing future observations remain pending; neither is a loss or a win.

Before later prices arrive, every observation freezes two separately labelled BUY and SELL benchmarks using a 1.5-times-14-day-ATR stop distance from its source window. These benchmarks use the existing adverse-first simulator, 50% at +1R, remaining half at +3R with stop to entry, and frozen explicit costs. A frozen candidate direction may select its corresponding benchmark for diagnostics; the better later direction must never be selected as the model prediction. These are uniform diagnostic benchmarks, not replay of discretionary entries or proof of the selected strategy.

Evaluation appends a new source-bound event and leaves the decision intact. Repeated evaluation against identical sources and status is idempotent. Source revisions are preserved as separate evaluations. The journal shows the most recent evaluation and retains every earlier event.

Where the frozen candidate also contains a complete, internally consistent +1R/+3R plan, evaluate its own risk distance as a separate candidate counterfactual. Move the reference bracket to the later observed entry open; do not simulate an entry before recording. This remains unqualified and hypothetical, including for rejected plans. Keep its results separate from the uniform benchmarks and actual execution.

Final interpretation: raw sources are copied into the journal and replayed. Only an exact current-report publication receipt counts as a displayed decision. A capture received before the full holding period remains pending/not ready; an adequately timed capture with a missing required observation is unavailable. Source failures have bounded codes and repair actions. Default status counts and reason-group averages exclude identical repeat publications. Repeat rows show the primary observation's outcome and retain their own publication attempt separately. Completed source-backed results remain visible when a later stale or failed attempt occurs. Entire-file deletion is not detected by a chain or external inventory; this remains a local durability limit.

## Insight and access

Show counts by decision, pair, rejection reason and outcome availability; show candidate-direction benchmark results only when that direction was frozen. Show both benchmarks for abstentions with no direction. An abstention cannot be labelled wrong simply because one benchmark later won. Do not treat repeated report revisions as independent trials or auto-optimize parameters using this history.

Authenticated endpoints expose the history and CSV. A CSRF-protected local update and the normal report publication path record and evaluate available sources. Reads do not record new decisions. No scheduled service, AI call, broker integration, actual execution record or public endpoint is added. Execution state stays NOT_RECORDED. A future manual execution journal is separate work.

Acceptance: chronology and gap controls; immutable/idempotent and tamper controls; all-eight abstention preservation; both benchmark labels; API authentication/CSRF/export controls; full Python checks; browser evidence; bounded independent review. Profitability, fundamental validity, continuous concentration control and live forecast calibration remain open.
