# JPY and portfolio research — bounded coordinator receipt

1 October 2026. The private desk includes seven USD majors and the retained EURGBP research cross. JPY was previously excluded at the owner's request; the later instruction restores it. Public three-pair history is preserved.

## Implemented and measured

The separate chronological admission replay allows at most five planned open positions, five new entries per ISO week and two positions per correlated directional risk group at admission. Correlations use only preceding observations: a 60-return window, at least 40 matched returns and a signed-correlation threshold of 0.70. Current 20-, 60- and 250-observation diagnostics are descriptive. BUY/SELL signs matter; negative raw correlation does not establish a profitable hedge.

Actual eight-pair source report `e03e3a56f2a967b7bddced8563307d583da156cc8609e15902e1049bafe922e9` corrected the JPY provider-symbol receipt. It is preserved alongside the original seven-pair report `a15080e656b5ee021855719a116d6293ddf0bf5f7a2819389e52db08b9377f43`. A separate refresh later made report `d70d94256bc4c16986d69793e596927429d5bc1619d820c5292865e428543c81` current. Its initiating actor is unverified. The outcome-journal packet preserved that newer report and independently replayed it; its current AI review remains unqualified.

| Measured result | Value |
|---|---:|
| Historical price calls | 2,417 |
| Admitted research calls | 2,320 |
| Skipped calls | 97 |
| Complete weeks inside all eight test ranges | 799 |
| Offered calls per common-coverage week | 1.9199 |
| Admitted calls per common-coverage week | 1.8298 |
| Common-coverage weeks meeting 3–5 target | 229 / 799 |
| Common-coverage zero-entry weeks | 149 |
| Broad admitted mean net return after assumed costs | −0.03940R |
| Broad realised-close drawdown | 93.4628R |

The broad return and drawdown use the wider historical admission population, not just the 799 common-coverage weeks. Per-call R is not account equity and the drawdown excludes unrealised losses. The weekly target is not met. Most of the frequency shortfall already exists before the portfolio filters.

Daily group diagnostics checked 4,605 reserved open weekdays and found five later group-size breach dates. Continuous enforcement/rebalancing remains UNQUALIFIED. The two-per-group rule is proved at admission only. Currency position counts are not notional exposure or account sizing. Stress-era correlations, instability thresholds, tested hedge ratios, hedge costs and a continuous concentration response remain open.

## Verification and boundaries

At the portfolio checkpoint: 2,617 pipeline tests, Ruff and MyPy267 passed; actual eight-pair offline replay passed in 44.75 seconds. See [the transcript](D:/Projects/fxregimelab/reports/private-portfolio-checks.txt), [primary-source research](D:/Projects/fxregimelab/reports/private-portfolio-source-research.md), [independent review](D:/Projects/fxregimelab/reports/private-portfolio-independent-review.md) and the actual local HTTP/export receipt at `.private-fx/portfolio/verification.json`. Independent review passed bounded admission/evidence and held continuous control, stress and hedge qualification.

Subsequent integrated outcome-journal revision: 2,663 tests, Ruff and MyPy270 passed; newer current-report offline replay passed in 34.95 seconds. See [the outcome receipt](D:/Projects/fxregimelab/reports/private-outcomes-acceptance.md). The authenticated desk is http://127.0.0.1:8765/ and includes JPY, measured frequency, daily group diagnostics and separate outcome history.

JPY's historical/current Japanese policy inputs and BoJ coverage are not established. All eight current candidates abstain; probabilities remain unavailable. No profitable hedge, 60–70% probability, guaranteed +1R, complete strategy repair or production acceptance is claimed. Existing R1–R5 and public repair holds remain open. The goal remains active.

Unlazy: two bounded manual gates met, three runnable gates remain unmet pending inspected checker approval, none abandoned. Direct check results do not certify the checker gates or release held leases. No commit, push, deployment, migration, production database write or broker order was made. Required loopback service restarts used the existing manual launcher; no automatic startup was enabled.
