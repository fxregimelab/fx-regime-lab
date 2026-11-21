# Private outcomes journal — independent review

**Review date:** 1 October 2026  
**Reviewer:** Codex, independent read-only review  
**Result:** **PASS — bounded local decision/outcome journal**

This review accepts the journal only for preserving and replaying private research observations. It does not accept profitability, forecasting skill, calibrated confidence, strategy learning, actual execution, production release or tamper-proof storage.

## Accepted scope

The reviewed implementation:

- records all eight private-desk pair decisions from a complete report, including every `ABSTAIN`;
- freezes the real UTC recording time and permits entry only on the first weekday strictly after that date;
- preserves the exact report and daily source bytes with SHA-256 bindings;
- publishes a decision only after the exact report bytes became the current projection;
- appends later evaluations without changing the frozen decision;
- distinguishes `PENDING`/`SOURCE_NOT_YET_READY` from missing, quarantined or unverified evidence;
- replays every displayed source-backed result from the retained source bytes and rejects forged or altered results;
- keeps BUY and SELL 1.5-ATR diagnostics separate, so an abstention is not retrospectively assigned the better direction;
- evaluates a complete frozen candidate bracket separately as `FROZEN_CANDIDATE_COUNTERFACTUAL`, using the later observed open and the frozen risk distance;
- labels every outcome hypothetical and keeps execution `NOT_RECORDED` and forecast qualification `UNQUALIFIED`;
- counts repeated report publications separately and excludes them from distinct-observation and rejection-reason aggregates;
- retains bounded source failure codes with a concrete repair action; and
- exposes journal reads and CSV only behind the existing authentication, with journal updates protected by CSRF.

No automatic learning, policy change, threshold change or confidence upgrade is performed by the journal.

## Independent checks

Run from `D:/Projects/fxregimelab/pipeline`:

```text
python -m pytest -q tests/test_private_desk_journal.py tests/test_private_desk_api.py
...................................................                      [100%]
51 passed in 14.96s
```

Run from `D:/Projects/fxregimelab`:

```text
node private-desk/verify-ui.mjs
PASS 1: HTML, script syntax, accessibility hooks and safe content sinks
PASS 2: All eight pairs including USDJPY, missing observations, null probability and empty charts
PASS 3: Engine schema, charts, long-history separation, session evidence, pagination and untrusted content
PASS: Private outcome journal preserves abstention, pending status and safe text
PASS 4: Authentication, failed login, CSRF refresh, progress, report recovery, export and logout
PRIVATE_DESK_UI_VERIFIED
```

The focused regressions cover complete eight-pair recording, identical retry idempotence, weekday entry clocks, partial-universe rejection, both diagnostic directions, malformed/gapped/stale sources, source deletion recovery, altered journal files, forged rehashed outcomes, out-of-order evaluation, publication commit boundaries, source rollback, repeated-publication counting, and valid or inconsistent frozen candidate plans.

The repository's full Python, Ruff and MyPy checks were not repeated by this reviewer because the coordinator owns final runtime verification and asked that no heavy suite run concurrently. This receipt does not replace those checks.

## Supplemental navigation review

After the review above, the only implementation delta was one dashboard navigation link: `Outcome history` now points to the existing `#decisionJournal` section. Read-only inspection confirmed that the target ID exists and the link does not change journal data, authentication, evaluation or publication behavior. This narrow navigation delta is accepted. The coordinator's later UI, full-suite and runtime results remain separate evidence and were not rerun or adopted as independent checks in this receipt.

## Supplemental journal API regression review

The previously omitted `pipeline/tests/test_private_desk_journal_api.py` was inspected and run separately from the earlier 51-test check:

```text
python -m pytest -q tests/test_private_desk_journal_api.py
........                                                                 [100%]
8 passed in 2.46s
```

This bounded file verifies authentication on all three journal endpoints, CSRF protection for updates, read-only GET behavior, preservation of eight abstentions with `NOT_RECORDED` execution in CSV, fail-closed responses for damaged journal history, and spreadsheet-formula escaping in exported metadata. No finding was identified. This supplemental result does not broaden the review to the coordinator's full suite, replay or real runtime receipt.

## Reviewed file hashes

| File | SHA-256 |
|---|---|
| `pipeline/src/private_desk/journal.py` | `22c25d5420a5b8cdbc1a8c12a9921172ce54ed354b089acc3605cbaef3e53001` |
| `pipeline/src/private_desk/api.py` | `d7ad78bdc6bdbfef6af6738a13edea0d55dab0b8e73587e926b335a21f1030c2` |
| `pipeline/src/private_desk/report.py` | `5b25d85dcffd99f7467ef351f8ed9e8fefb86438d99a4cd9f4a6a7948f36799d` |
| `pipeline/src/private_desk/cli.py` | `f74bb8f4e62d256ae4ecd92f9b2732d2e040984bc06de99c6c555d174a7294e8` |
| `private-desk/index.html` | `745f29448290ea1280e44ecf8d965b9653a34349f295424ffbcfb36f0d497838` |
| `private-desk/verify-ui.mjs` | `a6a7cf02a8ca6d466416b998a66ee0664517a2bc2a8aa60dc5a750d483c641a6` |
| `pipeline/tests/test_private_desk_journal.py` | `752f7954bc829bc9d00dd28851a5d060be70d8a9a53ba113cf7deee13f307bc8` |
| `pipeline/tests/test_private_desk_api.py` | `dc8a91df605886efcede602a151f4f79281abc780b4f83e0797c1c645592b7ab` |
| `pipeline/tests/test_private_desk_journal_api.py` | `be520e0a1f5a91c5033362d95efcbed013f00ce6a5aa3af9286eb5d43ebc260d` |
| `docs/PRIVATE_OUTCOME_JOURNAL_CONTRACT.md` | `9dee618434a0cd409bd80d37a67f34a8fc3d5e0392996554cd4c1b6644813f53` |

## Remaining holds

- The uniform BUY/SELL outcomes and frozen candidate-plan outcomes are counterfactual daily-bar research. They are not executed trades or broker-fill evidence.
- Daily bars retain adverse intrabar ordering and assumed cost limitations. They do not establish session timing or executable bid/ask performance.
- Repeated observations and overlapping holding windows are not independent trials. The displayed reason groups are descriptive and do not establish causal filter value.
- A profitable later benchmark does not make an abstention wrong, qualify the rejected setup, or authorize hindsight direction selection.
- The journal does not prove predictive value, fundamental validity, portfolio suitability, calibrated confidence or live forward performance.
- Local content hashes detect altered retained files, but the journal is not externally notarized or tamper-proof.
- Full-suite verification, live authenticated runtime evidence and final coordinator acceptance remain separate gates.

Within those limits, the implementation passes this independent review.
