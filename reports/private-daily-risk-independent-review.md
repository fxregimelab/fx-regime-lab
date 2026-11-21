# Private daily holding-risk independent review

**Verdict: PASS_BOUNDED**

I found no consequential defect within this frozen, development-only packet. The result supports publication of the named daily holding-risk study through the existing private journal path. It does not qualify the strategy, show profitability, establish executable exits or hedges, prove intraday or continuous control, approve a forecast, or approve production trading.

## Review boundary

This was an independent, read-only code and evidence review. I did not change implementation, source captures, the current report, AI records, journal records, or any production state. I made no network, model, broker, order, or service call. I did not run the full repository checks. The only file written by this review is this receipt.

I read `IDENTITY.md` first, then the top of `MASTERPLAN.md`, `TASK.md`, the frozen `docs/PRIVATE_DAILY_RISK_CONTRACT.md`, the humanscope skill, and the quality-first orchestration policy. GitNexus impact/context was unavailable for this work; I treated its result as unknown and manually followed the private simulator, correlation, report, replay, journal-publication, CLI, and UI callers. This receipt does not claim zero blast radius.

## Findings

No consequential finding remains in the reviewed boundary.

The implementation uses returns strictly before each review or entry date. Active positions are reviewed from the state carried from the preceding daily boundary. Correlation groups are connected components, so indirect links remain in the same group. Missing pair evidence is treated as unknown and reduces the retained or admitted set. Entries are ordered by earlier entry, then probability descending with null last, then the fixed universe order.

Capacity and pair reservations last through the original planned horizon even when a modelled or natural path closes early. A lower-priority held position can be modelled out when a held edge becomes unknown, while its pair remains reserved and a replacement admission remains blocked. The study checks the retained set again after decisions and fails the entire replay if an unknown edge, a group over two, or more than five active positions remains.

The optional simulator exit occurs only at the requested daily open. It runs before that day's high/low logic, keeps the existing natural open-gap priority, and gives a gap through +1R the intended partial-exit treatment. Existing spread, two-sided slippage, and calendar-day financing remain in the result. Extra forced-exit slippage is bounded to 0, 1, and 3 pips and is scaled to the remaining half-unit after a partial exit. Invalid indices, negative/non-finite slippage, gaps in a holding path, changed source bytes, malformed costs, and non-reproducing original trades fail closed.

The publication function re-reads the current report, checks that it did not change during the offline calculation, saves an immutable parent archive keyed by its SHA-256, detaches the prior current review while preserving it, and calls the shared report publisher. The shared publisher records the report with the journal before replacing the current report, then commits the publication and evaluates pending outcomes. The CLI replay recomputes the daily attachment and requires exact equality. I reviewed this path but did not execute publication; the coordinator owns the actual publication and its resulting journal evidence.

The dashboard calls this a daily-boundary development counterfactual. It displays the negative modelled mean, modelled exit count, zero post-decision breaches, and the unqualified continuous/execution state. It does not turn the modelled open exit into a broker fill or a return claim. The UI verifier also exercises a negative mean, null executable return, unqualified states, and hostile text.

## Independent evidence replay

The pinned parent was 71,595,922 bytes with SHA-256 `1af3f4192c4086b73ad468d32ad4fff493d75561d6fbc7359b0a7d90372f6a2c` before and after my checks.

I loaded that parent, recomputed `attach_daily_risk_evidence` from the eight original capture bytes, and compared the full resulting Python object with `.private-fx/daily-risk/candidate.json`. They were exactly equal. The candidate is 82,843,390 bytes with SHA-256 `998ec6061c829954a4a9873a907129d730cb7ae1d3a3f5786d5b12ccb8f312cf`. Relative to the parent, its only top-level addition is `daily_risk_audit`; all prior top-level values, including pair reports, portfolio audit, correlation audit, current review, prior current review, AI summary, and prior AI summary, are equal.

The exact replay measured:

- 2,417 input calls, 2,321 admitted, and 96 skipped.
- 4,485 checked daily boundaries.
- One pre-review breach and one modelled open-exit request: USDCHF on 2022-08-24 for `CORRELATED_GROUP_FULL`.
- Zero post-decision breach days and zero post-decision unknown days.
- Modelled net result of -93.7360040694134R, mean -0.04038604225308634R per admitted call, and closed-path drawdown of 95.78443653800262R.
- On the preserved common-coverage basis, 799 complete weeks and mean 1.8322903629536922 admitted calls per week.

The source captures independently matched their recorded hashes:

| Pair | Bytes | SHA-256 |
|---|---:|---|
| AUDUSD | 1,648,093 | `94ef9417f09019dd6feed2ce6091b580231073ce5137d7d5b6d5beaaf91d3edb` |
| EURGBP | 2,261,265 | `f0c8d276467849affd0b187b19fb02f41cd791e3b066f580141160cf8417fcfa` |
| EURUSD | 1,841,109 | `ab0914412fe8d77db04e99c58886ab6290e1e6d8de59c33b9214d525a434983f` |
| GBPUSD | 1,847,252 | `14e6ff16123d66a89bd1ef2aeb0e0afa1c26f57047e3631014ab44a01a5f0a7d` |
| NZDUSD | 1,818,711 | `e3fc596916e152cffbb432ed381af0a8726db119573128136cff7ba2b55ab0ed` |
| USDCAD | 1,863,988 | `b88214d82fbd083072b408ae9cf6def70ddbf8e15b1dda34ca469fda7052218d` |
| USDCHF | 1,868,344 | `2a264e8584f3e8cc3d957ff2b60f2a1982e9dcbb6c0ce3daf6354672fc739649` |
| USDJPY | 2,355,610 | `d58f3476d89d4d2b2385bcace82af4f9a99e0d82af24955da2ab5b2168c311a1` |

## Checks independently run

From `pipeline`:

```text
python -m pytest -q tests/test_private_desk_daily_risk.py tests/test_private_desk_engine.py tests/test_private_desk_correlation.py
78 passed in 2.64s
```

From the repository root:

```text
node private-desk/verify-ui.mjs
PRIVATE_DESK_UI_VERIFIED
```

The focused tests cover the old drift remaining red, strict same-day cutoff, future-path non-interference, source-gap rejection, unknown held-edge reduction, persistent reservations, blocked replacement admissions, original-path corruption, unchanged legacy simulation defaults, partial and natural gap priorities, JPY pip costs, and invalid forced-exit requests. These checks are narrower than the coordinator's full-suite and actual-publication responsibilities.

## Reviewed snapshot

| File | SHA-256 |
|---|---|
| `docs/PRIVATE_DAILY_RISK_CONTRACT.md` | `2a811f16e9e0b3aae1ae80d2c9aa185a56d656035170ae573c6ab4029e2d85b1` |
| `pipeline/src/private_desk/risk_control.py` | `bc00c13e2e44c1e64948588c6c3d66bca698a15caad020afbd318d558973d780` |
| `pipeline/src/private_desk/engine.py` | `3a2aa79e9bbd3677fa9ecf61f78d9bf496680833093547ebeb49cda5a74f07c9` |
| `pipeline/src/private_desk/correlation.py` | `88418c1711da2da1e818ce1d512cedb90d99cae779b6cd2f9a921cc0fbc79e69` |
| `pipeline/src/private_desk/report.py` | `ef52e9bf555937641a6082bf304e8fe8ece22de4d0f19fc1829b2fb83ca2f76a` |
| `pipeline/src/private_desk/cli.py` | `0f4c8d9e88ed5a1fb7cf5889d6a0a7523a96a5d268f3433ee21c81995e860c78` |
| `private-desk/index.html` | `eb4c659bef920a2c4b71fcf208c4d34e65c77618d5be95cbbb2c02915a1ce6ae` |
| `private-desk/verify-ui.mjs` | `1b23986265b6ffce5bd2118106ca38d8b851f048cb0720e7a94d08747dfa2e91` |
| `pipeline/tests/test_private_desk_daily_risk.py` | `b923d1435569ff16ecd3cf58a03eff50613776c8ddc59748639227b05f5a9dc3` |
| `pipeline/tests/test_private_desk_engine.py` | `8489350d3b8de5758d2a0fc137b7c8974c47bc98240fcca90e52c5b3dae2bde8` |
| `pipeline/tests/test_private_desk_correlation.py` | `c0cc2a1975626511c24a4acdbaf9dd153cd2ff4ee98fd8252d100c4986932617` |

Governance inputs read: `IDENTITY.md` SHA-256 `3ef34e31589f384c6daa2918ac21b0aa9a7600a99562d570c61de60192295260`; `MASTERPLAN.md` SHA-256 `1d6810185e8aace69f64184400e946bc591a435d1e3a9b748cff4dc74908c3a7`; `TASK.md` SHA-256 `b7d37f9e46140bde1954a24740ecab9e4af133da3d4034fea1539d51770647d8`; humanscope SHA-256 `fad6f1c133e9f91f482d2ea1bb9c4b94162ace4339399a72ff733c68abf3d2e9`; quality-first policy SHA-256 `978d41786b2b7538eda1e05cc05677e19681bbea86ede69f2151400a7a2bf15d`.

## Review amendments and remaining holds

The initial review found no consequential defect. The final amendment confirmed the explicit unknown-held-edge/lower-priority-exit case, continued pair reservation, blocked replacement admission, and the expanded UI negative fixture. No earlier finding was removed or hidden.

The result remains a retrospective daily-OHLC counterfactual under generic costs. It does not observe intraday limit breaches, executable liquidity, actual exit fills, account notionals, live financing, or hedges. The closed-path curve excludes unrealised losses. The negative modelled mean does not improve profitability. Historical examination is not untouched forward evidence. Actual report publication, parent archive creation, AI/current-review detachment, shared-journal preservation, full-suite checks, authenticated browser evidence, and any coordinator acceptance remain outside this independent receipt.

## Final typing-only amendment — 2026-10-02

**Amended verdict: PASS_BOUNDED.** No consequential finding was introduced by the CLI typing correction.

The only reviewed delta changes the daily-risk branch's local variable from `result` to `risk_report` on the assignment and its following status print. The existing `result` local used for `subprocess.run` in the `checks` branch remains unchanged. Replacing those two `risk_report` occurrences in memory with `result` reconstructs the exact earlier 18,131-byte CLI file and its recorded SHA-256 `0f4c8d9e88ed5a1fb7cf5889d6a0a7523a96a5d268f3433ee21c81995e860c78`. The corrected 18,141-byte `pipeline/src/private_desk/cli.py` has SHA-256 `edd5561dc6cb0652f3ad7a64ec07a511f406a1acc5409ac20e3a7139d860c45e`.

I independently ran:

```text
python -m mypy src/private_desk/cli.py
Success: no issues found in 1 source file
```

The pinned parent remains SHA-256 `1af3f4192c4086b73ad468d32ad4fff493d75561d6fbc7359b0a7d90372f6a2c`; the candidate remains SHA-256 `998ec6061c829954a4a9873a907129d730cb7ae1d3a3f5786d5b12ccb8f312cf`. The previously reviewed risk control, engine, report attachment/publication, dashboard, UI verifier, and daily-risk test files also retain the hashes recorded above. I did not repeat the full or focused pytest suites. The coordinator-reported full pipeline and Ruff results are not claimed as independently run here, and actual publication remains outside this receipt. All earlier profitability, execution, hedge, continuous-control, forecast, production, and coordinator-acceptance holds remain unchanged.
