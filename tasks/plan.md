# Autonomous demo desk execution plan

Use the existing approved task packets in
`docs/specs/autonomous-desk/05-implementation-tasks.md`; this file is an execution
index, not a replacement product roadmap or a weaker release policy.

## Scope and authority

- Owner requests complete continuously running demo reasoning and execution.
- Owner explicitly declines credential rotation; no rotation will be performed.
- EURUSD/USDJPY execution only; retain all protected risk and evaluation gates.
- Do not alter public production schedules or execute real-money orders.

## Ordered slices and acceptance

1. Finish RF2b replay parity: nonempty rate/carry output, causal quote history,
   EUR-only declared legacy fallback, tests and independent review.
2. AD-T07 broker-read/clock boundary: strict demo/hedging/symbol/freshness checks;
   no send interface; actual transport schemas required for integration evidence.
3. AD-T08 collectors: registered authoritative calendar and publisher-family-aware
   headline coverage with cutoff/expiry/revision validation. Missing entitlement
   remains a blocker; offline fake collectors do not count as live coverage.
4. AD-T09..T13: versioned features, registered detectors, bounded grounded AI and
   independent verifier on frozen evidence, using private request accounting.
5. AD-T14..T20: native valuation, independent admission, atomic reservations,
   fenced executor, reconciliation, deterministic management, watchdog and settlement.
6. AD-T21..T27: replay/experiments/sealed evaluation/certificates and bounded evolution.
7. AD-T28..T32: actual supervised services, fault/isolation tests, observed soak,
   certified demo canary and monitored operation. Code alone is not installation.

## Verification

Each slice needs focused positive/negative tests, full pytest, Ruff/mypy and
independent review before acceptance. Run full suite once per stable batch, not
simultaneously in every agent. Broker/environment checks are opt-in and read-only
until the approved executor and all required certificates exist. Release requires
actual observed receipts; neither missing historical time nor market observations
can be fabricated to accelerate a deadline.

## Risks

GitNexus index is incompatible (format 42/runtime 40); record UNKNOWN graph impact
and review manual callers. Agent provider rate limits may prevent independent
review. Current MCP catalog exposes no terminal tools. Source entitlements,
service isolation and host supervision must be observed, never inferred from files.
