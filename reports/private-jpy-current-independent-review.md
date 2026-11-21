# Independent review — current JPY policy and official headlines

**Review date:** 2 October 2026  
**Verdict:** **HOLD**

The actual current-JPY publication and its saved v4/v3 evidence replay cleanly, but the source parser does not satisfy the contract's conflicting-guideline rule. A current page with one `Guideline` heading and two conflicting valid guideline assertions is accepted using the first assertion. The packet should not receive bounded code acceptance until that case fails closed and has a regression test.

This review is separate from `reports/private-jpy-policy-independent-review.md`; that historical receipt was not changed. This receipt covers only the files and pinned artifacts listed below. It does not approve a forecast, probability, strategy, model output, production change or release.

## Findings

### 1. Conflicting guideline assertions do not fail closed

`pipeline/src/private_desk/data.py` requires exactly one heading whose text is `Guideline`, then calls `heading.find_next("a")` and validates only that first anchor. It does not count all guideline assertions associated with the heading or reject disagreement among them.

I independently supplied one `Guideline` heading followed by two otherwise valid BOJ state-page anchors: one said around `1.25 percent`, the other around `2.00 percent`. `_boj_policy` returned an available 1.25% observation instead of rejecting the conflict.

This violates the contract and source-review requirement to reject absent, multiple or conflicting current guidance rather than choose one silently. The existing duplicate negative control duplicates the heading, so the 128 focused tests still pass while this case remains open.

Required repair: identify the bounded guideline section, require exactly one qualifying assertion and source link within it, reject a second qualifying or conflicting assertion, and add a regression using one heading with two guideline anchors.

### 2. The v4 admission boundary is broader than the reviewed BOJ host

The original RSS parser correctly requires `www.boj.or.jp`. The v4 saved-input admission map uses `boj.or.jp` with a general subdomain rule, so a constructed item at `https://unreviewed.boj.or.jp/...` with syntactically valid metadata is admitted as Bank of Japan evidence. This did not affect the actual captured report, whose 52 BOJ items all came from the exact reviewed host.

The repair should make the v4 BOJ publisher rule match the exact reviewed host and add that negative control. The saved input remains a review boundary and should not depend solely on the upstream parser having run correctly.

## Reviewed source snapshot

| File | SHA-256 |
|---|---|
| `docs/PRIVATE_JPY_CURRENT_CONTRACT.md` | `014271cbd7bfa946f3351f1019c62ebab2e67b92cb8990918f6bb607fe9395ec` |
| `reports/private-jpy-current-source-research.md` | `60b68394a1ab8fa3f3f8b96d31e0d0fe936a17aabcdb815dda2fc406a227c2bf` |
| `pipeline/src/private_desk/boj_current.py` | `d1c24e4cef36d140a6762beffffa4927d9c2bf8ac781bb84c21396adfbe9066b` |
| `pipeline/src/private_desk/data.py` | `470237aa2c156d89775c13193b53698ded5ffe08ab78901f505e619c2337b46e` |
| `pipeline/src/private_desk/current_review.py` | `c019b513a10e2761b96e62bf5cc4f4230bef04dae3972f8c1684b8018e1477fd` |
| `pipeline/src/ai/client.py` | `69c947c59bf9c3d6c0738dac179b32392045585be5dd04c0d8924f39143820e3` |
| `pipeline/tests/test_private_desk_jpy_current.py` | `008c72e75071b879cc3e9f15c798fb7a71ead80d7c7f947730f9102dd42648a1` |
| `pipeline/tests/test_private_desk_data.py` | `3d883067dd9cc8eb4c18bf06ca4a1faee028c38cf44b272b6be4afa41ec573ae` |

## Focused checks

From `pipeline/`:

```text
python -m pytest -q tests/test_private_desk_jpy_current.py tests/test_private_desk_data.py tests/test_private_desk_current_review.py
128 passed in 3.70s
```

The passing suite confirms the implemented negative controls it contains. It does not clear finding 1 because the suite tests duplicate headings rather than two assertions under one heading.

No full suite, network request, model call, service, journal sync or broad research check was run.

## Actual pinned capture and publication replay

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| `.private-fx/report.json` | `1af3f4192c4086b73ad468d32ad4fff493d75561d6fbc7359b0a7d90372f6a2c` | 71,595,922 |
| `.private-fx/jpy-current/parent-report.json` | `861d0799918805ee6ef571deb2968820ced36a385e5f89071c87e0a2807bd745` | 71,427,625 |
| Saved legacy v3 report `.private-fx/jpy-policy/.private-fx-report.json` | `d70d94256bc4c16986d69793e596927429d5bc1619d820c5292865e428543c81` | 65,931,135 |
| BOJ homepage original body | `5dcdd87286d207642eb3df49c2adb3fbdd4fad498aefc3e8b582d7879316424d` | 64,171 |
| BOJ homepage receipt | `85c86ffe582a62e95d8cb8f03d34519b16dd8dec4c38cfc0eb62f6ad4c100b97` | 629 |
| BOJ RSS original body | `5117346484b14aa71fc798d57ad3d158b697353888573e78b793bc7bd342303f` | 17,267 |
| BOJ RSS receipt | `ec7703f28e28c3122eea67ba4cb06493d70092b896432465777282360dfd1e14` | 619 |

Read-only `verify_current_review` passed for the actual v4 report and the saved v3 report. The v4 binding is:

- input `94f0aa3c5b9db267866ca9b9d702968bfce15dde0f9ef069b3c9f65e2fe1d61c`;
- output `fe315e4bf8032a77870cc62f87928d91ca90b4ba0d879854971c446a0eaaa952`;
- parent `861d0799918805ee6ef571deb2968820ced36a385e5f89071c87e0a2807bd745`.

The preserved v3 binding remains input `f7380dbd23fd6796ef175c860b33f08cc7fbe28dbbe1ae48b603ab68060e9f50` and output `27b9a855b2eea2e1d5fca6abc16ff4bc704a941866539669e4a8547782e4de74`. It replays under `private-current-headline-v3`; changing its method label to v4 remains invalid.

The current report's non-context research exactly equals its parent. Candidate probabilities are unchanged. Because the parent had already detached the last live review while preserving it in the `prior_*` fields, the v4 publication correctly carries those archived v3 objects forward rather than treating the parent's detached/unavailable placeholders as the predecessor.

## Measured current evidence

- The homepage body and receipt hashes verify. Re-parsing the original body reproduces a 1.25% `BOJ_OVERNIGHT_CALL_RATE_GUIDELINE` with qualifier `around`.
- `current_page_observed_at` is the receipt time. `effective_from`, `decision_date` and `published_at` remain null, publication timing remains unknown, and the observation is marked current descriptive evidence rather than point-in-time history.
- The 1.25% guideline remains separate from the realised call-rate average and complementary-deposit facility. Neither neighbouring object's date or clock is borrowed.
- The RSS body and receipt hashes verify. Re-parsing produces 52 attributed BOJ headlines. Every original evidence URL remains `http://www.boj.or.jp/...`; every review/display URL is the same-host HTTPS form and says the article was not fetched.
- All 52 items retain the general-feed coverage warning. The fundamentals warnings state that the BOJ feed is incomplete policy coverage and that an absent item does not mean unchanged policy.
- The current fundamentals contain policy measurements for all eight currencies, while overall fundamentals remain `PARTIAL` because growth, inflation surprises, positioning and dated event evidence remain incomplete.
- The v4 admission records 166 supplied headlines, 89 accepted before the cap and 40 selected. JPY is covered; CAD, NZD and USD remain missing current headline publishers.
- The actual v4 response is `GENERATED_UNVALIDATED`. Its model output is saved evidence, not an accepted forecast. The current-review receipt remains `UNQUALIFIED`; portfolio and correlation strategy qualification remain `UNQUALIFIED`.

## Holds that remain

- Repair and independently recheck the conflicting-guideline parser case before bounded code acceptance.
- Tighten and test the BOJ exact-host rule at v4 input admission.
- The actual current capture does not establish historical first-seen availability, article-body grounding, policy-news completeness, predictive contribution, win probability, profitable execution or live strategy quality.
- Full pipeline checks, authenticated dashboard evidence, coordinator acceptance, production and release remain outside this receipt.

No source, implementation, test, capture, report, journal, service, credential, model, production or historical JPY receipt was changed by this review.

## Final repair supplement

**Recheck date:** 2 October 2026  
**Final verdict:** **PASS_BOUNDED**

Both findings above are closed in the repaired snapshot. The original HOLD and findings remain in this receipt as review history; this supplement records the independently verified repair.

### Repaired snapshot

| File | SHA-256 |
|---|---|
| `pipeline/src/private_desk/data.py` | `703509dd0b83fd8b225421524d8a041eb5ea6d23ace660515f3a4e910c4cbcff` |
| `pipeline/src/ai/client.py` | `915ae99673aa89a6c31dcec4f04b98c42c4ec9bb2d1cae8eeb019854a17cd3d0` |
| `pipeline/tests/test_private_desk_jpy_current.py` | `5d584626f9e544cd37ec2925b25e996dd6489b5f8a3e8540355078cd5177889f` |
| `pipeline/tests/test_private_desk_data.py` | `23b18982fde75ee742086c8686e6fedc785e747865fb13c0e2e7ff31f33e03e6` |
| `pipeline/src/private_desk/boj_current.py` | `d1c24e4cef36d140a6762beffffa4927d9c2bf8ac781bb84c21396adfbe9066b` |
| `pipeline/src/private_desk/current_review.py` | `c019b513a10e2761b96e62bf5cc4f4230bef04dae3972f8c1684b8018e1477fd` |

The repaired policy parser now requires the witnessed `section.policy` container, exactly one anchor in that section and exactly one qualifying guideline assertion across the page. Independent negative checks confirmed rejection of:

- two conflicting guideline anchors in the same policy section;
- one valid section assertion plus a conflicting assertion elsewhere on the page;
- a guideline placed outside the witnessed policy section.

The v4 BOJ admission boundary now requires exact `parsed.netloc == "www.boj.or.jp"`. Independent checks confirmed that `unreviewed.boj.or.jp`, `unreviewed.www.boj.or.jp` and `www.boj.or.jp:8443` admit no headline. Legacy v3 admission remains on its original publisher map.

The final focused command was:

```text
python -m pytest -q tests/test_private_desk_jpy_current.py tests/test_private_desk_data.py tests/test_private_desk_current_review.py
134 passed in 5.22s
```

Read-only replay also passed again for the unchanged actual v4 report and saved v3 report:

- v4 input `94f0aa3c5b9db267866ca9b9d702968bfce15dde0f9ef069b3c9f65e2fe1d61c`;
- v4 output `fe315e4bf8032a77870cc62f87928d91ca90b4ba0d879854971c446a0eaaa952`;
- v3 input `f7380dbd23fd6796ef175c860b33f08cc7fbe28dbbe1ae48b603ab68060e9f50`;
- v3 output `27b9a855b2eea2e1d5fca6abc16ff4bc704a941866539669e4a8547782e4de74`.

The original 64,171-byte homepage body still re-parses to the 1.25% around-guideline with null decision and effective dates. The original 17,267-byte feed still re-parses to 52 items with preserved HTTP evidence links and derived same-host HTTPS review links.

This PASS_BOUNDED accepts only the repaired current-JPY code behavior, the named focused checks and the pinned artifact replay. Historical first-seen availability, article-body grounding, policy-news completeness, predictive contribution, model prose, strategy qualification, production and release remain unaccepted. The reported full-suite and MyPy results were not adopted as independent evidence in this receipt.
