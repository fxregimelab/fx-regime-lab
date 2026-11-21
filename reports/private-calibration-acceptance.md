# Direction and overlapping-call repairs

1 October 2026. The private desk is running at http://127.0.0.1:8765. This packet advances R4; the larger goal, R1–R5 and public repair register remain open. The strategy has no qualified current trades.

## What changed

Current probability and expected-return evidence now use the selected policy, BUY/SELL direction and strength bucket. The calibration forecast needs forty matured trades in that direction and twenty in its exact policy-direction-bucket cell. The training comparison forecast uses the same direction. Current qualification requires one hundred matured held-out predictions and positive lower approximate expected-return bounds in the exact held-out cell. Another direction or bucket cannot qualify it. The twelve fixed trials and training-only policy selection remain.

A deterministic control shows the original problem: one hundred BUY losses and one hundred SELL wins, each forecast at 50%, pass the pooled calibration check. Each direction separately fails. A second control gives BUY a 0% estimate and SELL a 100% estimate from their own forty-trade buckets; removing twenty BUY observations makes BUY unavailable despite sufficient SELL evidence. Strength-bucket and chronological-prefix controls remain.

An independent methodology review accepted the direction repair and identified a cross-bucket return weakness in revision 1. Revision 2 applies both held-out calibration and expected-return checks to the exact cell. The review's initial marginal-count allegation was disproved: the twenty bucket observations are counted after policy and direction filtering. Its correction and remaining limits are in [the source review](private-calibration-source-research.md). The coordinator also read the [official calibration documentation](https://scikit-learn.org/stable/modules/calibration.html), [time-series split documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) and [calibration research](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jrssb.pdf). A proper score, reliability check and historical sample do not establish future economic value.

## Actual overlap results

The fixed counterfactual takes held-out price calls, including unqualified forecasts. It reserves one research risk unit per accepted call and allows at most two planned positions, with no repeated currency. It releases capacity strictly after the full planned horizon date. Ranking uses only existing fold-time forecasts, followed by the fixed pair order when forecasts tie or are unavailable. It cannot use realised profit or early exits to improve selection.

| Measure | Actual saved result |
|---|---:|
| Input calls | 2,000 |
| Accepted calls | 1,198 |
| Skipped currency collisions | 802 |
| Accepted calls with unavailable probability | 1,198 |
| Realised net research R | −54.2754744435 |
| Realised close-date drawdown R | 56.2683511368 |
| Net-profitable call fraction | 47.8297% |
| Worst observed modeled call R | −4.0750846321 |
| Mean of worst 60 calls, ceiling(5% × 1,198) | −1.1058845509 |
| Qualified current trades | 0 |

All fold-time probabilities are unavailable in this saved sample, so simultaneous calls use the fixed pair order. These results are descriptive and do not show that a probability-ranked strategy succeeds. The worst observed accepted call is EURUSD, signal 6 February 2008, entry 7 February, recorded gap-stop exit 8 February. It is a provider-candle calculation with assumed costs, not a witnessed fill or a verified historical price event.

Simultaneous closures are summed before building the realised curve. This curve excludes unrealised losses, account capital, leverage, monetary sizing, account-currency conversion and margin rules. Its drawdown cannot qualify account survival or worst loss while a position is open. Currency exclusion is a concentration assumption; it is not a correlation model or hedge. The observed tail is a sample description, not a future loss bound.

## Preservation and replay

The revised price method is `private-price-v2-direction`; the overlap rule is `private-overlap-v1`. `recalculate` creates a new report from hash-checked saved daily captures without network or AI calls. Earlier reports remain intact. An old-method replay raises an explicit recalculation instruction rather than silently accepting changed calculations.

The prior release report remains at `.private-fx/reports/20261001T124533-release-e9d5dc234ac14a14a52a402442e322ad.json`, SHA-256 `ef3a93e23ad0743ff00344e5893fe7b5db2f5ef45d38015e7f79883e352a7847`. Coordinator equality checks preserve news, source metadata, historical vintage/release audits, current fundamental captures, reference/session studies and bid/ask evidence. The 2,000 original price-call identities, policies, directions, fills, costs and net returns are unchanged. Per-pair outcome summaries are unchanged. Calibration fields and candidate qualification intentionally change.

Old AI text is retained separately as `prior_ai_summary` and `prior_ai_analysis`. The displayed review is unavailable with an explicit older-input explanation. No new AI request was made. A later ordinary research refresh may run a new review against the then-current inputs; neither review becomes historical model evidence.

Current report: `.private-fx/reports/20261001T131739-recalculate-14f1ae6ae2d64e0cb0c009609b8c2db5.json`, SHA-256 `b8eb3155582288476ee046a8010be1b250b28a09ae723b3b7dd5d3b08bf05ecb`. The current `report.json` matches it. Offline replay reproduces seven daily/reference/session/bidask studies, vintage/release audits and the overlap audit in **9.80 seconds**, with `PRIVATE_PORTFOLIO_REPLAY_OK` and `PRIVATE_DESK_REPLAY_OK`.

## Verification and remaining work

Direct checks: **97 focused tests**, **2,332 full pipeline tests**, Ruff and MyPy **252 source files** passed. Final full-check runtime was 53.97 seconds; [the transcript](private-calibration-checks.txt) contains `PRIVATE_DESK_CHECKS_OK`. The initial full run passed its tests but failed five line-length checks; after correction, MyPy identified two annotation issues. Those were corrected and the complete check command passed. UI verification passed all four groups, including missing/invalid overlap data, unsafe text, chart rendering, conditioning evidence and the existing lifecycle.

Actual Chromium checks cover all seven briefs, the revised overlap counts and loss values, unavailable probabilities, detached AI review, realised curve, a 2,000-row protected CSV with exactly 1,198 accepted and 802 skipped decisions, authenticated reload, CSRF403 and report/status/CSV401 after logout. The final 390px mobile page has client/document width390 with no body overflow. An injected positioned 900px control does produce overflow. Desktop and mobile screenshots were reviewed; the mobile grid was changed to two columns and the chart coordinate width adapted for readable labels. [The browser transcript](private-calibration-browser.txt) records the final result. Browser text checks normalize CSS uppercase labels; the initial normal-flow, zero-height overflow probe was ineffective and was replaced by a measurable positioned control. Neither issue was a data or authentication failure.

GitNexus impact/API-impact attempts remain UNKNOWN because index storage42 differs from reader40. Manual callers cover only private generation/replay, CSV export, UI and tests. No index-wide modification was made. The desk uses its existing manual launcher and local JSON storage; no Docker, PostgreSQL or heavy Hermes component was required. No broker action, production write, commit, push or deployment occurred.

The source-review gate is manually met. Implementation ledger: seven gates, three manual outcomes reviewed, four automatic gates pending explicit bound checker approval, zero abandoned. Direct command success is not Unlazy certification. No `--approve` or whole-scope release was used.

R4 still needs dependence-aware and selection-aware uncertainty, calibration-bin sensitivity, measured joint stress and account risk. R1 needs executable price/cost evidence; R2 needs adequate historical currency-leg availability and expectations; R3 needs predeclared fundamental trials and a later untouched evaluation; R5 needs forward paper qualification and dependable operations. This losing, unqualified baseline is not ready for live strategy use. The next substantive work is historical feature coverage and predeclared fundamental trials, alongside executable-price evidence—not lowering the probability gates until calls appear.
