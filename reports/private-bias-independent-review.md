# Private bias context — independent design review

**Review state:** early contract and architecture gate, before implementation and before current bias metrics  
**Verdict:** **HOLD** for implementation acceptance and any current-result acceptance  
**Review date:** 2 October 2026 IST

The proposed boundary is sound: a separate, descriptive `bias_brief` can help a person inspect past price behaviour without turning it into a forecast or an executable trade. The contract correctly preserves the legacy candidate, keeps probabilities null, treats the heuristic labels as descriptions, and requires source-bound replay. Two unresolved choices can change the recorded metric or its later outcome, so the method is not yet exact enough to implement as a frozen first version.

This is a design review only. `pipeline/src/private_desk/bias.py` did not exist when I reviewed the design. I did not calculate current bias results, run tests, call a model or network service, publish a report, or change any source, journal, evidence, or strategy gate. No result in this receipt qualifies a strategy, forecast, order, or production use.

## Consequential holds

1. **The 20-bar range is not defined exactly.** The contract asks for a 21-observation window for the twenty-weekday change and efficiency, then asks for the last close's position in an “observed 20-bar high/low range.” It must name the exact bars. For example, it could use the final 20 bars of the 21-observation window, excluding the starting close, or all 21 bars. Those choices can produce different range positions. The frozen method, registration record, implementation and tests must all use the same explicit inclusive indexes.

2. **The new frozen direction has no predeclared diagnostic horizon.** The owner goal covers two to five business days, while the current legacy journal evaluates a candidate-selected three- or five-day horizon. A new bias direction cannot silently borrow the legacy candidate's `holding_days`; doing so would mix the two methods that the contract requires to stay separate. The bias method must freeze its own horizon or fixed horizon set before current results are inspected. If it does not, the direction-specific diagnostic must remain unavailable. Any new fixed horizon must use only the direction frozen at recording time and retain the existing uniform BUY/SELL benchmark beside it.

These are design holds, not evidence that the descriptive approach is invalid. Resolve them before registering `private-bias-context-v1` and before calculating its first current results.

## Required exact behaviour for the implementation review

- **Cutoff and windows:** record the capture UTC timestamp and a date-only observation cutoff. The usable cutoff is the earlier of the explicit observation cutoff and the last calendar date strictly before the capture's UTC date. A five-day change requires six valid consecutive weekday closes; a twenty-day change and efficiency require 21. Each component remains independently available. The method must state what happens when the long component is valid and the short component is not; the present contract only states the inverse case. No bar after the cutoff may affect any component.
- **Availability and labels:** for `SHORT_TERM_ONLY`, freeze the exact zero-return handling and enum. A defensible exact rule is positive=`BULLISH`, negative=`BEARISH`, zero=`MIXED`, with the full phase unavailable. With both components complete, use only the frozen sign and efficiency rules in the contract. Do not add thresholds after viewing current results.
- **No invented confirmation:** keep `calibrated_probability` null. Keep forecast expectancy, power-law qualification, total OTC volume confirmation, and fundamental directional confirmation unavailable. Existing dated policy facts and conditional AI text may be displayed as context, but cannot populate `fundamental_bias` or `fundamental_relation` without a separately registered, source-vintage-safe mapping that uses both currency legs. The two-event all-seven-pair FOMC result is descriptive development evidence only; it is not predictive support for a bias.
- **Source-bound brief:** freeze a canonical brief containing the pair, method/version, exact observation date, capture path or immutable source reference, capture SHA-256, capture UTC clock, component values and availability, classification, qualification and limitations. Reject pair, receipt, hash, clock, cutoff or replay disagreement. All publication and recalculation paths must reproduce the same brief from the original bytes.
- **Stale projection:** request-time stale or invalid evidence must visibly hold current directional context without deleting or rewriting the last saved historical brief. A request-time hold is not a new market observation and must not create a changed journal identity by itself.
- **Legacy journal compatibility:** when `bias_brief` is absent, reproduce the existing observation identity exactly; adding a null field would change it. When a brief is present, use an explicitly versioned identity over the canonical frozen brief and its source identity. Freeze it alongside, rather than inside or in place of, the original candidate. Old decisions, report snapshots, evaluations and repeat links must replay unchanged.
- **Repeats and cohorts:** identical pair, observation date, bias method and source-bound brief are repeats even when republished. Keep legacy candidate and bias cohorts separate. Report distinct `(pair, observation_date)` counts so a method revision or repeat publication does not increase the apparent number of market observations. If multiple method revisions are shown, display their counts separately while deduplicating the underlying pair/date population.
- **Outcome separation:** a bias diagnostic may exist only for a frozen `BULLISH` or `BEARISH` direction and a predeclared bias horizon. `MIXED`, `UNAVAILABLE`, absent risk, missing observations, quarantined gaps, stale evidence or source failure must remain unavailable. Never select whichever BUY/SELL direction later won. Do not call a fixed-bracket outcome the owner's discretionary result or a continuation probability.
- **Publication order and UI:** attach and verify the bias brief before binding any current AI response. Preserve the legacy candidate and every saved study. Present the new descriptive context in fixed universe order and place entry/stop/target material in a clearly labelled legacy-study disclosure. Distinguish unavailable price context from rejected legacy trade eligibility. Render source and reason text safely.

## Design provisions that passed this early review

- The brief is separate from trade qualification and leaves execution with the owner.
- The fixed heuristic uses observed 5- and 20-weekday price changes and path efficiency; it does not describe the output as a probability.
- Short and long components are allowed to fail independently instead of manufacturing a complete classification.
- Accumulation, distribution, Wyckoff A–E phases and institutional order flow are forbidden without the missing price/volume evidence. Total OTC volume is explicitly unavailable.
- The contract preserves old candidates, studies, files and outcomes and requires old journal identities to remain exact when the optional brief is absent.
- Repeated publications and method cohorts are separated, and the proposed uniform BUY/SELL benchmark remains distinct from the frozen bias direction.
- Stale request-time context fails closed while saved history remains intact.
- Current AI cannot be retroactively treated as source evidence or directional confirmation.

These provisions are **PASS_BOUNDED_DESIGN** only. They do not clear the two holds above and do not accept any future code or result.

## Evidence reviewed

| Item | SHA-256 | Bytes | Use |
|---|---:|---:|---|
| `docs/PRIVATE_BIAS_CONTEXT_CONTRACT.md` revision 1 | `a21a6f11f70fe1787a6e5b6f256fd59b56153dcfcedc52a655aed60d4bb5e6ba` | 6,336 | Normative proposed method and integration boundary |
| `reports/private-bias-source-research.md` | `4b166d16eb70d4b2770917c8306601a90c82998fe9f2b0009fc20596ed1e8ca6` | 18,010 | Primary-source limits on Wyckoff, OTC volume, momentum, fundamentals and probability |
| `IDENTITY.md` | `3ef34e31589f384c6daa2918ac21b0aa9a7600a99562d570c61de60192295260` | 9,477 | Hard project boundary |
| `MASTERPLAN.md` | `0c07df76c7f854f461aa9b49f2d2a2a725dab7c001abf8437a3ecf21de5a7867` | 25,150 | Owner amendment and product direction |
| `TASK.md` | `9038653d89d04ca04b51282ff4091ca8eba26ed25566139e5d759601b376e9f5` | 15,965 | Current sprint state |
| `C:/Users/sakha/.codex/skills/humanscope/SKILL.md` | `fad6f1c133e9f91f482d2ea1bb9c4b94162ace4339399a72ff733c68abf3d2e9` | 7,113 | Owner-facing writing rules |
| `C:/Users/sakha/.codex/quality-first-orchestration.md` | `978d41786b2b7538eda1e05cc05677e19681bbea86ede69f2151400a7a2bf15d` | 5,487 | Independent-review and orchestration boundary |

I also inspected the current integration surfaces as architecture context, not as the future implementation: `journal.py` SHA-256 `22c25d5420a5b8cdbc1a8c12a9921172ce54ed354b089acc3605cbaef3e53001`; `readiness.py` `1f86a3adb74a4d39d43224f3e82777a44483fb1d20c497e924bcf213c585e6af`; `current_review.py` `c019b513a10e2761b96e62bf5cc4f4230bef04dae3972f8c1684b8018e1477fd`; `report.py` `c7fd6210b62b31443f20571a208c290165f640a299b970ecda535a846776c819`; `cli.py` `4366646d4ba5808df27f42cf05eeadb0777833f3f2e17f86e8c17ddd1379c6e4`; and `private-desk/index.html` `b477fc1126d773cccd92d41085c2f3695c87c4920f10c8bdc6c4ecc70757fa07`. These hashes describe the pre-implementation baseline and will necessarily change during implementation.

## Preserved evidence boundary

The report inspected at this gate remains SHA-256 `c7fca95ddfaf994ecf499bc63dc4026dc0581b7add23765d3d82e28ae437c804`. The FOMC source snapshot remains `4a9ad8d577c8840a60094e84ca524c4a4c5ca0fb6a27384a7b6e1d216db77283`; its frozen manifest remains `bdbbe0c59a6818fe6f6266b60fbe2d621e60e0422387b28cac31ff08d2d54eb8`; and its result remains `beb09bece37530bde2e228d3a3ff740a9f1a3256fa77a963bf6deff3d22423d4`. I did not modify or recalculate them. The FOMC result's two common events per horizon are too few for uncertainty or predictive claims and cannot qualify the new bias method.

## Next independent gate

After the method choices above are frozen and the code is ready, the implementation review should hash-bind the new module and every changed integration/test/UI file; replay original captured price bytes; prove future-price invariance and separate 5/20 availability; verify exact legacy journal identities and prior report/AI/study preservation; test repeat/cohort counts and no hindsight direction selection; and inspect the first registered current artifact separately. Until then there is no accepted bias metric, current direction, probability, performance, or forecast.
