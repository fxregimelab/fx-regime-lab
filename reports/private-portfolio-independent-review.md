# Private portfolio expansion: independent bounded review

Reviewed 1 October 2026 against `docs/PRIVATE_PORTFOLIO_EXPANSION_CONTRACT.md`. This receipt covers the eight-pair private research implementation and the final saved artifact. It does not approve a trade, forecast, profit claim, hedge, broker action, release or production change.

## Decision

**PASS for the bounded admission and evidence implementation. HOLD for continuous concentration control, stress-era diagnostics and hedge qualification.**

The current implementation preserves the accepted contract choices: eight pairs; a 60-observation correlation window; at least 40 matched returns; a signed-correlation link at `0.70`; at most five admitted open positions; at most five admissions per ISO week; and at most two positions in a connected risk group at admission. The separate 20- and 250-observation views are descriptive only. The source-research proposal's `0.60` grouping threshold, stress rule and currency-unit cap were not promoted into admission policy.

## Consequential finding

### [HOLD] The pinned replay has five later group-merger days

`pipeline/src/private_desk/correlation.py:161-190` now checks every planned holding weekday after admission and records later correlation drift. This closes the earlier observability gap without inventing a hindsight exit. The final artifact records 4,605 checked open weekdays, five days when an already-open connected group exceeded two positions, zero unknown-correlation days, and `continuous_group_control: UNQUALIFIED`.

The result is honest, but it does not meet a broad reading of the contract's maximum-two operating limit. The admission rule passed when each call entered; rolling correlations later joined existing positions. No automatic rebalance, replacement exit or continuously qualified cap exists. Keep this gate on HOLD unless the owner accepts admission-only control or adopts a separately specified forward control. The dashboard correctly labels the rule as applying “at admission” and shows the daily drift audit.

## Remaining research holds

- `pipeline/src/private_desk/correlation.py:353-365` reports 20-, 60- and 250-observation Pearson views. It does not yet implement a declared stress-era sample or an explicit sign-change/instability result, which the contract requests as diagnostics. This does not change the fixed 60/40/0.70 admission rule.
- `hedge_qualification` remains `UNQUALIFIED`. No two-leg cost, fixed hedge ratio or independent hedge evaluation was accepted.
- Current Japanese policy and BoJ news remain missing and explicit in `pipeline/src/private_desk/data.py:1120-1135`. The final report keeps all eight candidates at `ABSTAIN`, all probabilities null, all fundamental qualifications `UNQUALIFIED`, and all AI analyses `UNAVAILABLE`.
- The saved results are historical research calls from examined cohorts. They are not newly untouched evidence, qualified recommendations, account returns or evidence of future profitability.

## Verified behavior

- `pipeline/src/private_desk/universe.py` defines exactly EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY and EURGBP under `private-eight-v1`.
- USDJPY keeps direct quote orientation. The ECB cross derives JPY per USD, Yahoo metadata names the actual `JPY=X` provider symbol, and the cost model uses a `0.01` pip. Focused regressions cover the derivation, provider identity, partial exit and cost scale.
- The preserved seven-pair artifact at SHA-256 `02e0a594b4635ffab1b4ce1450d4863320d9b8afc88c20f5a6ba934d7e03ea01` replayed exactly. It remains legacy evidence and cannot pass current eight-pair readiness.
- Missing, constant, stale or insufficient correlation holds simultaneous admission. Returns use exact dates, exclude the signal date and later observations, and do not cross gaps.
- Ranking uses signal-time probability, null last, then fixed pair order. Changing realised outcomes did not change admissions. Capacity remains reserved through the full planned horizon.
- Weekly reporting includes zero weeks and shortfalls. The final artifact separately reports 799 complete weeks inside all eight pairs' test coverage: mean 1.9199 offered calls, mean 1.8298 admitted calls, 229 weeks meeting the 3–5 target and 149 zero-entry weeks. These are measured historical research calls, not a quota or forecast.
- Currency long/short/net counts are displayed separately. Equal risk units are not described as equal notionals.
- Realised-close drawdown is labelled separately from unrealised and account drawdown.
- `pipeline/src/private_desk/api.py:79-94` validates both saved audit identity sets before serving them. The CSV export keeps the new correlation decision, rejection reason and `UNQUALIFIED` status separate from the legacy overlap audit; malformed new-audit identities fail closed with HTTP 503.

## Final artifact and replay

The reviewed saved report is `.private-fx/report.json`, SHA-256 `e03e3a56f2a967b7bddced8563307d583da156cc8609e15902e1049bafe922e9`. The immutable copy is `.private-fx/reports/20261001T165935-jpy-source-correction.json` with the same hash. Its USDJPY daily source capture uses provider symbol `JPY=X`, source URL `https://finance.yahoo.com/quote/JPY%3DX/history/`, and capture SHA-256 `bba96ef35346c584a7bee8a83caeca3fa45d862e450755a98feae895550cb050`.

Offline replay passed for all eight daily/reference/session/bid-ask studies, current-review binding, historical vintage, historical releases, the legacy overlap portfolio, the new correlation portfolio and historical policy evidence: `PRIVATE_DESK_REPLAY_OK` in 32.63 seconds. No source fetch, model call or broker action occurred during this independent replay.

## Checks run independently

- Focused private-desk suite: **237 passed** in 13.22 seconds.
- Post-correction universe/correlation/report subset: **29 passed** in 3.32 seconds.
- Readiness/API export suite after the final CSV boundary change: **39 passed** in 9.97 seconds.
- Ruff on the reviewed private-desk modules and focused tests: **passed**.
- `node private-desk/verify-ui.mjs`: all four groups passed, ending `PRIVATE_DESK_UI_VERIFIED`.
- Preserved seven-pair pinned replay: `PRIVATE_DESK_REPLAY_OK` in 12.36 seconds.
- Final eight-pair pinned replay: `PRIVATE_DESK_REPLAY_OK` in 32.63 seconds.

I did not run the full repository suite, MyPy or an authenticated real-browser journey in this independent packet. Those remain coordinator checks. Docker and heavier Hermes services were not required for these local deterministic checks and were not started.

## Reviewed snapshot

Git HEAD was `9fa150538d08ab5a2a6c587976552944f47a724d` on `codex/frontend`. The working tree was intentionally uncommitted and shared. Exact reviewed file SHA-256 values:

| File | SHA-256 |
|---|---|
| `pipeline/src/private_desk/universe.py` | `0ff6299ce3459c1124fa113483b4c2c3eb88b9272cee5fe6026cff41015743c1` |
| `pipeline/src/private_desk/correlation.py` | `88418c1711da2da1e818ce1d512cedb90d99cae779b6cd2f9a921cc0fbc79e69` |
| `pipeline/src/private_desk/engine.py` | `a96adffe8ab1d3e2d2fa9ea84359b8d06f4ac77c65bd7766f141d908c541e35d` |
| `pipeline/src/private_desk/data.py` | `08225724974e0d0c315276ac239a236596b84ac93711831350479bcea34600b0` |
| `pipeline/src/private_desk/readiness.py` | `1f86a3adb74a4d39d43224f3e82777a44483fb1d20c497e924bcf213c585e6af` |
| `pipeline/src/private_desk/report.py` | `7758d00373a2b33fd1aa01f21d02f9f46fc99603c3d6d35e185892fc73065fa3` |
| `pipeline/src/private_desk/portfolio.py` | `9b0873b937b9bee77a6b8f5f73d6c0c64bc3ec31d7d9ddf66f1996b724af9eb3` |
| `pipeline/src/private_desk/cli.py` | `3e449868a9e6f236524ef778612530216287c7e34ea570114439840bf7b3c24f` |
| `pipeline/src/private_desk/api.py` | `dd0c432dc32be32c5da504af4ccc9a1b5c8a469d2956b2c3c69fd7ffd1ac1c7d` |
| `private-desk/index.html` | `3d5bd48dffb9814d1b72e2e6597d7de388584f0ef10c28c9ded7872eede34bfb` |
| `private-desk/verify-ui.mjs` | `db3228c8adb3d01a06f475ce421f3572766b019a83f70b3db5f1869064a8bf85` |

This review created only this receipt. It did not edit implementation, tests, saved reports or prior evidence.
