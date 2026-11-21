# Private FOMC history and fixed-study independent review

**Initial verdict: HOLD.** The original source reconstruction is internally consistent and the focused checks pass, but the report attachment and routine-refresh paths can preserve an old study without replayable source evidence. The named test packet also does not exercise the manifest/result/publication chain required by the frozen contract. No development-study outcome has been calculated, so this receipt makes no return or directional claim.

## Review boundary

This was a read-only review of the frozen contract, the new FOMC source and study modules, report and CLI integration, the named fixtures/tests, and the private dashboard. I did not change implementation, source captures, the report, AI records, journal records, providers, services, gates, or production state. The only file written is this independent receipt. I made no network, model, broker, order, database, deployment, or journal call. GitNexus was not available as evidence of impact, so I manually followed the source, study, report, replay, publisher, current-review, journal, and UI paths.

## Consequential findings

### 1. Source attachment can retain stale FOMC evidence instead of failing closed

`attach_fomc_evidence` returns immediately when `evidence.json` is absent. It does not remove or replace an existing `fomc_history` or `fomc_study` value in the report. When the source history exists but `studies/latest.json` is absent, it replays the history but leaves any existing `fomc_study` untouched.

I confirmed both cases with an in-memory sentinel. Against the current `.private-fx` state, which contains valid source history and no study directory, attachment changed the sentinel history to `SOURCE_RECONSTRUCTION` but preserved `{'status': 'STALE_STUDY', 'marker': 'must-not-survive'}`. Against an absent state directory it preserved both stale values. A recalculation or build from an existing report can therefore carry an old study after its source or current study pointer is missing. This conflicts with the contract's fail-closed source and replay boundary.

The safe behavior is explicit: absent history must make both FOMC fields unavailable; valid history without a valid latest study must make the study unavailable. A stale embedded result must never survive because a pointer is missing.

### 2. A routine current-context refresh does not replay the frozen FOMC study

`refresh_current_report` verifies general report structure and capture hashes, refreshes news/fundamentals, and applies a current review. It never calls `attach_fomc_evidence`, `load_study`, or `run_study`. This means an embedded FOMC result can be altered while its referenced source files remain intact, then pass the general capture check and be republished by the routine review path without semantic replay.

The frozen contract explicitly requires a routine refresh to load and replay the study against its own pinned captures without retuning it against refreshed prices. The refresh path must perform that replay before publication and fail closed on any mismatch.

### 3. Required manifest and publication controls have no regression coverage in the named packet

The 24 focused tests exercise official wording, identity and ambiguity, meeting/publication separation, cancellation, predecessor-chain failure, non-target continuity, orientation, delayed entry, matched directions, future-price isolation, risk/holding gaps, quarantine, date-only exclusion, deterministic intervals, and one malformed-history attachment case.

No test calls `register_study`, `run_study`, `load_study`, or `publish_fomc`. The packet therefore lacks executable evidence that:

- the manifest is written before outcome calculation and binds code, source, and all seven price captures;
- code, source, price, manifest, result, and latest-pointer tampering are rejected;
- a saved result replays exactly;
- the exact parent is archived and cannot be replaced;
- prior AI/current-review evidence is preserved and detached;
- publication uses the shared journal path while preserving null probabilities and abstentions.

These are explicit acceptance requirements, not optional broad coverage. Focused temporary-state tests can cover them without network or model calls.

## Additional contract discrepancies

The manifest calls `git diff --binary` for `dirty_patch_sha256`. That command excludes staged and untracked files. The reviewed FOMC/private-desk files are untracked in this workspace, so this field is not a hash of the full current dirty workspace described by the contract. The outcome-critical contract, FOMC modules, and engine are separately bound, which limits the immediate calculation risk, but the dirty-patch provenance label is incomplete. A complete deterministic workspace-delta manifest, or narrower wording that states exactly what is hashed, is needed.

The frozen contract specifies a four-event moving-block bootstrap. `_interval` samples circular blocks: a block starting near the end wraps to the first event. The manifest changes the description to “circular moving blocks,” but the frozen contract does not authorize that variant. Circular block bootstrap and ordinary moving-block bootstrap produce different resamples at the boundary. The implementation and contract must use the same named method before the first calculation.

## Source reconstruction reviewed

`.private-fx/fomc-history/evidence.json` is 273,118 bytes with SHA-256 `d1522ba96513670ed80169c171cf7303775bc03a60eb677330e6c244956ae24b`.

Independent `load_history` replay matched the saved object. I also read and hashed every referenced receipt and original body. All eight index receipts/bodies and all 84 statement receipts/bodies matched their recorded SHA-256 and byte length. Every HTTP status was 200, every body was marked complete, every content type was HTML, and all URLs and receipts were distinct. The eight index bodies total 839,423 bytes; the 84 statement bodies total 6,969,179 bytes; the largest index was 165,460 bytes and the largest statement was 85,772 bytes, within the separate two-megabyte bounds.

The reconstruction contains the 2014-12-17 seed plus 83 inventory statements for 2015–2024. Yearly counts are exactly 8/8/8/8/9/10/8/8/8/8. It has 83 admitted event rows, zero failures, 81 target decisions, the 2019-10-11 implementation-only statement, and the 2020-03-23 other-policy statement. It records 28 adjacent target changes and 75 exact source clocks; all eight 2015 events remain date-only. Historical receipt, transmission, effective date, vintage, consensus, surprise, probability, and forecast qualification remain unknown or unqualified as required.

The parser binds each page to one official statement URL, requested date, article, title, date line, and release line. It rejects foreign hosts, queries, duplicate identities, conflicting Committee ranges, dissent/Desk substitutions, invalid fractions, wrong time zones, and unavailable bodies. A missing target decision breaks the predecessor chain; the two named non-target statements do not. The study orientation, two-weekday delay, preceding 14-day ATR over 15 consecutive weekday bars, exact holding windows, adverse-first simulator, fixed costs, matched opposite-direction mask, seven-pair complete-event aggregate, event-level averages, all-cell reporting, and zero-week frequency framing are otherwise consistent with the contract.

## Checks independently run

From `pipeline`:

```text
python -m pytest -q tests/test_private_desk_fomc.py
24 passed in 0.59s

python -m ruff check src/private_desk/fomc_history.py src/private_desk/fomc_study.py tests/test_private_desk_fomc.py
All checks passed!

python -m mypy src/private_desk/fomc_history.py src/private_desk/fomc_study.py
Success: no issues found in 2 source files
```

From the repository root:

```text
node private-desk/verify-ui.mjs
PRIVATE_DESK_UI_VERIFIED
```

The UI verifier covers negative and unavailable results, null probability, unqualified status, the “not a surprise” and weekly-frequency limits, and hostile text. I did not run the full pipeline suite.

## Reviewed snapshot

| File | SHA-256 |
|---|---|
| `docs/PRIVATE_FOMC_HISTORY_CONTRACT.md` | `c9446460881dc0c3ab109df32696e2cc161df6cbc0dc7aa3355584cc4a28e50d` |
| `pipeline/src/private_desk/fomc_history.py` | `f2fe049afdee0c3e2a11149a19a429bda9bf38c5da36e314490264b904d8d745` |
| `pipeline/src/private_desk/fomc_study.py` | `807a530532fcc99c3838a1e0e5fd4dcdf4f3fbfa7009aa68f56349991083590a` |
| `pipeline/src/private_desk/report.py` | `3893f73f5677078de093fd61d536f938263854f2d2fb07bd36fb4f76fc6a68a8` |
| `pipeline/src/private_desk/cli.py` | `4366646d4ba5808df27f42cf05eeadb0777833f3f2e17f86e8c17ddd1379c6e4` |
| `pipeline/tests/test_private_desk_fomc.py` | `9c3dfad24bf6880bbd173c1b1ae563e50c7654fab678377c1fdbecd9a50f58bd` |
| `pipeline/tests/fixtures/private_fomc_fragments.json` | `e674a93f609f34cb0ded3f5aa5a240f1aa4a6550082711aefd01f92ff014fa50` |
| `private-desk/index.html` | `b477fc1126d773cccd92d41085c2f3695c87c4920f10c8bdc6c4ecc70757fa07` |
| `private-desk/verify-ui.mjs` | `ce0f0b131469647b47873b774a9937708efb0c85764f7864044759c4c8d4ac98` |

Governance inputs read: `IDENTITY.md` SHA-256 `3ef34e31589f384c6daa2918ac21b0aa9a7600a99562d570c61de60192295260`; `MASTERPLAN.md` SHA-256 `41ced79bf91a7285f07f03d0b021ac5aee57e6ff7b13a43c9b779f0315d13ed3`; `TASK.md` SHA-256 `0f1657028f0fc0f6a72b199db0e4509a603c74075c18026387a5174f1d16fe26`; humanscope SHA-256 `fad6f1c133e9f91f482d2ea1bb9c4b94162ace4339399a72ff733c68abf3d2e9`; quality-first policy SHA-256 `978d41786b2b7538eda1e05cc05677e19681bbea86ede69f2151400a7a2bf15d`.

## Holds

This receipt stays **HOLD** until stale attachment is removed, routine refresh performs exact frozen-study replay, the required manifest/publication regressions pass, and the bootstrap and dirty-workspace bindings match the frozen contract. The later actual study artifact still requires an amendment that verifies its manifest existed before calculation, all pinned inputs and implementation hashes, exact saved replay, every exclusion and matched mask, event-level aggregates, publication preservation, and unchanged strategy/forecast qualification.

## Pre-calculation repair amendment — 2026-10-02

**Amended code/source verdict: PASS_BOUNDED_PRECALCULATION.** The initial HOLD findings above remain part of the audit record, but all four were repaired before the first actual candidate calculation. I found no new consequential defect in the repaired revision. This is not the final study verdict because no actual outcome artifact or manifest exists yet.

The attachment now replaces a stale embedded study with an explicit `UNAVAILABLE` object before it attempts source replay. With the current valid source history and no latest study pointer, my read-only sentinel probe returned `SOURCE_RECONSTRUCTION` history plus `UNAVAILABLE` study with null probability and unqualified forecast status. With the source directory absent, both old fields became `UNAVAILABLE`; neither stale marker survived.

`refresh_current_report` now calls `attach_fomc_evidence` before `apply_current_review`. The regression records the exact `replay`, then `review` order. A routine current-context publication can no longer carry an embedded FOMC result without first reproducing the frozen study or replacing it with an unavailable state.

The uncertainty calculation now draws only contiguous four-event blocks with start positions from zero through `n - width`; it does not wrap the final events to the first events. The manifest describes the same ordinary contiguous moving-block method as the frozen contract.

The dirty-workspace binding now hashes `git diff HEAD --binary`, which includes tracked index and worktree changes relative to HEAD, followed by a sorted JSON map of every non-ignored untracked path to its byte hash. The manifest states that basis directly. The outcome-critical contract, history, study, and engine files also retain individual code bindings.

The expanded focused tests now cover deletion and missing-pointer stale-state controls; frozen code, copied source, price bytes, study rules, and price-manifest changes; saved result and manifest hashes; exact saved replay; shared publication; exact parent archive; prior central AI/current review preservation and detachment; journal completion; and refresh-before-review ordering. The publication test uses the real shared publisher and checks eight journal decisions with zero unpublished reports.

I independently ran the repaired checks:

```text
python -m pytest -q tests/test_private_desk_fomc.py
34 passed in 1.54s

python -m ruff check src/private_desk/fomc_history.py src/private_desk/fomc_study.py src/private_desk/report.py tests/test_private_desk_fomc.py
All checks passed!

python -m mypy src/private_desk/fomc_history.py src/private_desk/fomc_study.py src/private_desk/report.py
Success: no issues found in 3 source files
```

The source history, contract, CLI, fixture, dashboard, and UI verifier are unchanged from the hashes recorded above. Repaired files are:

| File | Repaired SHA-256 |
|---|---|
| `pipeline/src/private_desk/fomc_study.py` | `28c0ab8495e4867ba1498ad59505430eb61f596e37965a4ab98025c9db3c3abc` |
| `pipeline/src/private_desk/report.py` | `c7fd6210b62b31443f20571a208c290165f640a299b970ecda535a846776c819` |
| `pipeline/tests/test_private_desk_fomc.py` | `2a1fd7d50c059b00a684969082dce8cdd32897d31ab0d645facf580b88478a3b` |

The original evidence remains SHA-256 `d1522ba96513670ed80169c171cf7303775bc03a60eb677330e6c244956ae24b`. No manifest, latest pointer, or result artifact existed during this amendment, and I did not calculate the actual study. The actual artifact still needs an independent supplement covering its registration time, manifest and workspace bindings, seven price captures, exact replay, exclusions, common masks, event-level results, descriptive intervals, parent/report preservation, journal publication, and all existing no-forecast/no-promotion limits.

## Workspace-binding correction amendment — 2026-10-02

**Verdict remains PASS_BOUNDED_PRECALCULATION.** The first registration attempt exposed a path-resolution defect before it created a manifest, result, latest pointer, or outcome calculation. The corrected revision resolves Git's relative untracked names from the repository root. I found no consequential defect in this narrow correction. This remains pre-calculation evidence only.

`_workspace_digest(repo)` now runs both Git commands with `cwd=repo`, hashes the exact `git diff HEAD --binary` bytes, turns every non-ignored untracked name into `repo / name`, constrains that absolute path through `bounded_path(repo, ...)`, hashes its bytes, sorts the path/hash map, and hashes the combined patch and map. I independently called the helper once from the repository root and once after changing the process directory to `pipeline`; both calls produced the same digest. The new regression also fixes the invocation directory, supplies exact tracked-diff bytes and an untracked file, and confirms that changing either input changes the digest.

The manifest's individual implementation bindings now include `universe.py`, `releases.py`, and `bidask.py` as well as the contract, FOMC history, FOMC study, and engine. This covers the fixed pair identities, release receipt/clock helpers, and bounded-path helper directly used by the source and study replay.

I independently ran:

```text
python -m pytest -q tests/test_private_desk_fomc.py
35 passed in 1.64s

python -m ruff check src/private_desk/fomc_history.py src/private_desk/fomc_study.py tests/test_private_desk_fomc.py
All checks passed!

python -m mypy src/private_desk/fomc_history.py src/private_desk/fomc_study.py
Success: no issues found in 2 source files
```

Current implementation and regression hashes are:

| File | SHA-256 |
|---|---|
| `pipeline/src/private_desk/fomc_history.py` | `f2fe049afdee0c3e2a11149a19a429bda9bf38c5da36e314490264b904d8d745` |
| `pipeline/src/private_desk/fomc_study.py` | `1639807ead1fc5b8a674c954067cfe0013ca12789c3f3c4082b8376b448f9759` |
| `pipeline/src/private_desk/engine.py` | `3a2aa79e9bbd3677fa9ecf61f78d9bf496680833093547ebeb49cda5a74f07c9` |
| `pipeline/src/private_desk/universe.py` | `0ff6299ce3459c1124fa113483b4c2c3eb88b9272cee5fe6026cff41015743c1` |
| `pipeline/src/private_desk/releases.py` | `f36184490d1ad03409e66c46bed78225ad82c2baf92cccb022c4b1efc0dbcaa8` |
| `pipeline/src/private_desk/bidask.py` | `e7674c1a831a502d35150f10996a9fca88d99f6dea35a15be735346ab8e22ece` |
| `pipeline/src/private_desk/report.py` | `c7fd6210b62b31443f20571a208c290165f640a299b970ecda535a846776c819` |
| `pipeline/src/private_desk/cli.py` | `4366646d4ba5808df27f42cf05eeadb0777833f3f2e17f86e8c17ddd1379c6e4` |
| `docs/PRIVATE_FOMC_HISTORY_CONTRACT.md` | `c9446460881dc0c3ab109df32696e2cc161df6cbc0dc7aa3355584cc4a28e50d` |
| `pipeline/tests/test_private_desk_fomc.py` | `d1282ab81d6e7b4488941c46cd5005f7341971392441e8c6374426df1edb4472` |

The failed attempt left one orphan source copy, `.private-fx/fomc-history/studies/c9f040bbfbae425cb001d226083c143b.sources.json`, 273,118 bytes, SHA-256 `cfb683e55f9357cb151fb8224752b0aca97a475f5da6f04d6bdd74eeb9f5a819`. Its parsed object exactly equals the original evidence. It has no manifest, result, latest pointer, or outcome data and is not actual-study evidence.

Actual-data acceptance remains pending. A later supplement must bind and replay the first successful manifest and result rather than treating this repaired code review or the orphan source copy as an outcome review.

## First actual frozen-study supplement — 2026-10-02

**Final bounded verdict: PASS_BOUNDED.** I found no consequential defect in the first successfully registered, calculated, and published study. This verdict covers exact reproduction and truthful presentation of this one fixed development study. It does not qualify the hypothesis, any pair, a forecast, a probability, a weekly trade source, execution, or production trading.

### Frozen chain and calculation order

The coordinator reference file `reports/private-fomc-manifest-reference.json` is 787 bytes with SHA-256 `99a5f66ed4def6ebd670acd4e8103ef3a736aefe530a3b0edfb13f710b712b6e` and names this chain:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Frozen source copy `371190c904a04c299cbfa139e0988bdf.sources.json` | 273,118 | `4a9ad8d577c8840a60094e84ca524c4a4c5ca0fb6a27384a7b6e1d216db77283` |
| Manifest `fomc-development-20261001T201223-d7fb3cb81a9b43dcaf95838004313cf8.manifest.json` | 79,759 | `bdbbe0c59a6818fe6f6266b60fbe2d621e60e0422387b28cac31ff08d2d54eb8` |
| Result `fomc-development-20261001T201223-d7fb3cb81a9b43dcaf95838004313cf8.result.json` | 421,942 | `beb09bece37530bde2e228d3a3ff740a9f1a3256fa77a963bf6deff3d22423d4` |
| Latest pointer | 247 | `98fbc81029514363339bfebaef75bb6ba7eb491f21086c5b78075cb4f783f631` |

The frozen source file's parsed object exactly equals `.private-fx/fomc-history/evidence.json`. Its filesystem creation time is 2026-10-01T20:12:23.6280863Z. The manifest records registration at 2026-10-01T20:12:23.629335Z and was created at 20:12:23.9811830Z. The result was created at 20:12:28.1540949Z, more than four seconds later. The latest pointer followed at 20:12:28.1675520Z. This supports source copy, registration, calculation, then pointer publication in that order.

The manifest binds commit `9fa150538d08ab5a2a6c587976552944f47a724d`, dirty-workspace SHA-256 `83ceec249d3338101de89423a452ea7aa0c6e687a10e28c9dd66039336e4945e`, the seven implementation/contract hashes listed in the preceding amendment, fixed method `private-fomc-change-development-v1`, the seven direct USD pairs, the copied official history, and the exact price-reference map. Its price-reference map recomputes to the saved data-manifest SHA-256 `0a6099b57febd3e0f99fc6afbd17fcffdcf26e6c165a59d97d67e5fce0d0e902`.

Every currently pinned implementation byte hash equals its manifest binding. Every price capture also equals its manifest hash:

| Pair | Bars | Capture bytes | SHA-256 |
|---|---:|---:|---|
| AUDUSD | 5,154 | 1,648,093 | `94ef9417f09019dd6feed2ce6091b580231073ce5137d7d5b6d5beaaf91d3edb` |
| EURUSD | 5,796 | 1,841,109 | `ab0914412fe8d77db04e99c58886ab6290e1e6d8de59c33b9214d525a434983f` |
| GBPUSD | 5,833 | 1,847,252 | `14e6ff16123d66a89bd1ef2aeb0e0afa1c26f57047e3631014ab44a01a5f0a7d` |
| NZDUSD | 5,557 | 1,818,711 | `e3fc596916e152cffbb432ed381af0a8726db119573128136cff7ba2b55ab0ed` |
| USDCAD | 5,878 | 1,863,988 | `b88214d82fbd083072b408ae9cf6def70ddbf8e15b1dda34ca469fda7052218d` |
| USDCHF | 5,887 | 1,868,344 | `2a264e8584f3e8cc3d957ff2b60f2a1982e9dcbb6c0ce3daf6354672fc739649` |
| USDJPY | 7,441 | 2,355,610 | `d58f3476d89d4d2b2385bcace82af4f9a99e0d82af24955da2ab5b2168c311a1` |

Direct `run_study` and pointer-based `load_study` each reproduced the complete saved result exactly.

### Independent path and exclusion reconstruction

I separately derived all 27 eligible clock-known change events from the frozen source, then recomputed each event's second-subsequent-weekday entry, immediately preceding signal day, 15-date risk window, 14 true ranges, 1.5 ATR risk distance, fixed USD orientation, and three/five-weekday window from the original price bytes. For every valid window I called the simulator directly in both the hypothesis and opposite direction with the frozen 1.2-pip spread, 0.2-pip slippage per side, and 0.15-pip calendar-day financing.

All 200 admitted saved rows were exactly equal to those independently scheduled simulator calls, including risk distance, entry, stop, partial state outcome, exit, gross R, cost R, net R, and paired difference. There were zero mismatches. The result contains 103 valid three-day pair alternatives and 97 valid five-day alternatives.

The other 178 selected event/pair/horizon attempts were excluded: 154 for `MISSING_OR_QUARANTINED_WINDOW` and 24 for `MISSING_RISK_WINDOW`. Each independent failure reason matched the saved exclusion. At event level, 55 unchanged, predecessor-unavailable, or non-target rows are `NO_TARGET_CHANGE`; the 2015-12-16 change is separately excluded because its exact release clock is unavailable. The total exclusion count is therefore 234.

The hypothesis paths include 153 time exits, 32 stops, nine breakeven exits after partial profit, four stop gaps, and two final-target exits. Fifty-three hypothesis paths reached the +1R partial target. The opposite paths include 139 time exits, 46 stops, seven stop gaps, seven breakeven exits, and one breakeven gap; 36 reached the partial target. Every hypothesis and opposite path includes a positive modelled cost. Hypothesis cost R ranges from 0.006398550536875896 to 0.038608176060931226. These are simulator outputs under assumed daily bars and costs, not fills.

### Common masks and aggregate arithmetic

Only two events have valid paths for all seven pairs at either horizon: 2023-03-22 and 2024-09-18. Each aggregate therefore uses 14 pair alternatives, while all incomplete events remain visible only as individual paths and exclusions. I recomputed every pair mean, positive fraction, paired mean difference, development-period value, and event-average difference from that common mask; all values match the artifact exactly.

| Horizon | Pair | N events | Hypothesis mean R | Opposite mean R | Net-positive fraction | Paired difference R |
|---:|---|---:|---:|---:|---:|---:|
| 3 | EURUSD | 2 | -0.213545 | 0.175899 | 0.50 | -0.389444 |
| 3 | GBPUSD | 2 | 0.196214 | -0.224139 | 0.50 | 0.420353 |
| 3 | AUDUSD | 2 | 0.191766 | -0.234787 | 1.00 | 0.426553 |
| 3 | NZDUSD | 2 | 0.476700 | -0.682750 | 1.00 | 1.159450 |
| 3 | USDCAD | 2 | 0.124949 | -0.320056 | 0.50 | 0.445005 |
| 3 | USDCHF | 2 | -0.032134 | -0.004504 | 0.50 | -0.027631 |
| 3 | USDJPY | 2 | -0.086749 | 0.071204 | 0.50 | -0.157953 |
| 5 | EURUSD | 2 | -0.209671 | 0.167219 | 0.00 | -0.376891 |
| 5 | GBPUSD | 2 | 0.220583 | -0.479689 | 0.50 | 0.700272 |
| 5 | AUDUSD | 2 | 0.255588 | -0.541724 | 0.50 | 0.797312 |
| 5 | NZDUSD | 2 | 0.379532 | -0.618186 | 1.00 | 0.997718 |
| 5 | USDCAD | 2 | -0.036156 | -0.025820 | 0.50 | -0.010336 |
| 5 | USDCHF | 2 | -0.116939 | 0.075624 | 0.50 | -0.192563 |
| 5 | USDJPY | 2 | -0.061008 | 0.043478 | 0.50 | -0.104485 |

The three-day event-average differences are 0.05328623318639193R and 0.48280898444498843R, for mean 0.2680476088156902R. The five-day event-average differences are -0.10972954776971382R and 0.6271660210232659R, for mean 0.25871823662677607R. Both descriptive block intervals are correctly unavailable because each common mask has two events, below the frozen eight-event minimum.

The apparent positive aggregate means do not establish a stable edge. They are driven by only two common events, mix seven correlated alternative pair expressions of the same announcement, and include pair-level sign reversals. The 2015–2018 and 2019–2020 common-mask summaries contain zero events; only the 2021–2024 development period contains the two events.

### Frequency, publication, and preservation

The result counts 27 clock-known changes over 521 complete calendar weeks, 494 zero-event weeks, mean 0.05182341650671785 events per week, and a maximum of one event in any week. Pair alternatives are explicitly not counted as separate opportunities. This evidence cannot provide three trades each week.

The result retains `probability: null`, `surprise: null`, `forecast_qualification: UNQUALIFIED`, `EURGBP: NOT_APPLICABLE_NO_DIRECT_USD_LEG`, and the full no-fitting/no-selection limitations. It reports every one of the 14 pair/horizon cells and selects no winner. Nothing in the artifact changes current eligibility or promotes a model.

The exact 82,809,534-byte parent is archived at SHA-256 `19136098e5f3b369eca5c11ba3e29e1fd3068524fec7329156969c90331a75f6`. The published 83,542,769-byte report has SHA-256 `c7fca95ddfaf994ecf499bc63dc4026dc0581b7add23765d3d82e28ae437c804`. The current report's embedded history equals the original evidence and its embedded study equals the result artifact.

Compared with the parent, the only new top-level fields are `fomc_history`, `fomc_study`, and `fomc_publication`. Existing top-level research is byte-equivalent as parsed data except for the deliberately unavailable AI summary reason and each pair's deliberately unavailable AI-analysis reason. All non-AI pair content, prior central AI, prior pair AI, prior current review, already-detached current review, daily-risk evidence/publication, portfolio, correlation, policy, news, and other research remain equal. The journal is `RECORDED`: 40 publications, eight distinct observations, 32 repeats, zero unpublished reports, eight abstentions, five pending outcomes, three unavailable outcomes, and no recorded execution.

### Remaining holds

This is already examined, incomplete development evidence from current reconstructed price archives. It has no historical FX receipt, verified vendor candle boundary, policy expectation, policy surprise, actual transmission time, effective-rate path, broker spread, broker slippage, execution record, or untouched forecast evaluation. Only two events survive the all-seven common mask, so no uncertainty interval or robust period comparison is available. R1–R5, current probabilities, strategy qualification, weekly frequency, causal interpretation, automatic learning, model promotion, and production approval all remain open.

The coordinator's final full-suite result is separate from this supplement and is not claimed as independently run here.
