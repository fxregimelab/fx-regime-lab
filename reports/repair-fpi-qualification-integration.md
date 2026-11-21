# Qualification order integration — packet25

Packets 25 and 26 are accepted locally on 28 September 2026. The full repair goal remains active. Neither pure qualification objects nor retained source bytes authorize FPI activation.

Parent froze docs/FPI_QUALIFICATION_ORDER_CONTRACT.md and recorded the command/event/head/resolution-witness meanings in the existing glossary before dispatch. Two disjoint workers implemented the pure model and investigated executed-code trust. The separate parent reference script, pipeline/scripts/verify_fpi_qualification.py, compares independently accumulated actions and resolutions to compact head/witness state, including decreasing clocks, broader scope blocks, reinstatement, candidate additions and shuffled inputs. It compared 8,920 membership states and 4,440 date resolutions across 40 seeds. Three deliberately wrong scalar/batch evaluators were detected.

Current PostgreSQL status was rechecked and remains stopped. Pure logic and offline private-source verification need no Docker or heavy Hermes runtime. No production access, new provider requests, credentials, notifications or activation are authorized by these checks. GitNexus CLI returned target-not-found/UNKNOWN for the new reference verifier; zero mapped callers is not a no-impact guarantee. No index rebuild or commit occurs.

## Database protocol source check

The parent checked PostgreSQL17 primary documentation before carrying the earlier SQL design forward. At Read Committed, successive queries can observe different committed sets; one ordinary SELECT uses its statement snapshot. This supports a single evidence-materializing statement and rules out treating several independent RPC reads as one saved snapshot. [Transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html).

A VOLATILE procedural function obtains a fresh snapshot for each query it executes, while STABLE/IMMUTABLE functions use the calling query snapshot. The qualification lock must therefore be acquired before a separate fresh-head query in the VOLATILE append entry point. [Function volatility](https://www.postgresql.org/docs/17/xfunc-volatility.html). Transaction-level advisory locks last to transaction end; all qualification writers must cooperate through the same lock. [Advisory locks](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS).

These sources support the proposed mechanism; they do not prove the application implements it. Real blocked-writer, rollback, post-lock freshness and decision-read tests remain required when the SQL layer is written. No production-ready ordering claim follows from the pure model.

## Accepted execution-trust investigation

Parent accepted leaf25.2 as implemented offline evidence and a reviewed architecture, not deployed verification authority. The final original-source probe passed under independent gate re-verification: output SHA-2568532969e5809e6f6b1b5df9cfe8f0278be3cd4aa5a74a870ec5377af3b2a53ae,249bytes. The parent also replaced the probe's actual parsed Latest output in memory with a newly constructed, internally reconciled result: purchases and sales rose by0.02 in an equity route and corresponding subtotal/total while the net was unchanged. The original observation builder accepted it, but the retained-output comparison rejected it with TRUST_COMPARISON_REJECTED. Marker FPI_ACTUAL_EXECUTION_OUTPUT_NEGATIVE_CONTROL_VERIFIED. Original files stayed unchanged.

The chosen next architecture independently recomputes retained inputs under a separately approved immutable release. It makes no claim that the original submitter ran that release. Protected release authority, clean process/import/native-runtime controls, a dedicated verifier database identity and exact saved-read/result binding still require implementation and deployment evidence. A same-process disk hash or synthetic approval fixture cannot establish them. The private retained row analysis is a pinned comparison claim from earlier inspection, not authenticated upstream ground truth. See repair-fpi-execution-trust-design.md.

## Final parent acceptance

The parent re-ran the 215-test qualification gate: 136 v2 cases and 79 unchanged v1 cases. Output SHA-256: 6ccfdcc306093cf1ca5095c1235b3a72e6b5c5a5d4d017359b62868e3445c824. The independent reference gate passed with output SHA-256 81e76aa2d1e9d4019e43d5c5b2dc90b579a0d8e39622aef8f013827604cf1bda.

Review includes actual 16,000,000-byte overflow before complete event reconstruction, one view reconstruction and 20,000 member evaluations for the bulk interface, and 750 historical witness lookups across 250 dates. Hashes bind canonical identities and current/historical evidence. Supplied ordinals and membership universes remain assertions until the database protocol supplies them.

The independent packet26 logging control extracted only the original sync/async FRED functions from HEAD through AST. A synthetic credential-bearing error URL and malformed value leaked through both baseline paths; the repaired functions omitted both while returning None. The parent re-ran the 49-test gate, including 14 new privacy cases. Third-party library logging and other fetcher modules remain within the wider security audit.

The final integrated pipeline gate passed, with 1,632 tests independently collected. Full Ruff passed and MyPy passed across 224 files. R2 output SHA-256: b6f797bb6db68a7e5c6a1170996219e2434f1ce12a51b448c5ab77f229557302. The checker exit of one reflects six pending root gates, not a regression failure. Frontend files were unchanged by these packets; packet19 remains their latest acceptance. No database runtime was required. No production write, commit, push or deployment occurred.

FPI-T07 is resolved for the pure v2 representation only. Durable ordinal assignment, complete saved reads, protected recomputation authority and real consumer parity remain required. FPI stays inactive.
