# PD architecture — reuse before extension

## Existing versus proposed

Existing pure foundations include `paper/contracts.py`, `policy.py`,
`spec_bundle.py`, `snapshots.py`, `features.py`, `strategies.py`,
`admission.py`, `operator_score.py`, `calendar.py`, `news.py`, and read-only
`broker.py`/`broker_mcp.py`. The private journal boundary is in `db/writer.py`
and its private repository. Presence and unit tests do not prove live readiness.
The older AD plan's "not installed" list is historical, not a current inventory.

Reuse the public pipeline's pair-specific observed macro facts through a
point-in-time, read-only boundary. A daily regime classification is context,
not an intraday entry or calibrated probability. All AI calls continue through
`pipeline/src/ai/client.py`; all database writes through `pipeline/src/db/writer.py`.
Preserve the private telemetry/budget injection and production isolation.

Proposed runtime roles below are NOT installed trading workers by installing
the similarly named OpenCode development agents.

## Proposed decision flow

1. Approved collectors archive immutable observations with publication,
   availability, retrieval, reference-period and revision timestamps.
2. Deterministic code builds the pair feature snapshot and data coverage report.
   No future-known revision or unfinished bar is usable.
3. Macro/pair analysis supplies an evidence-linked thesis for today/1–2 days,
   bull/bear/wait cases, next catalyst and falsifiers. It proposes no executable
   order and does not replace deterministic prices or risk calculations.
4. Independent challenge checks unsupported facts, alternative explanations and
   whether multiple citations are one syndicated story. A veto or missing
   required evidence yields WAIT. Majority voting does not grant permission.
5. Registered candidate logic plus deterministic trade construction calculates
   plausible entries, stops, management, planned net payoff and exposure.
6. Admission/reservation verifies the current authority, readiness, cooldown,
   loss capacity, account/instrument and correlated USD risk. No LLM confidence
   may lift any restriction. Execution remains blocked until AD prerequisites.
7. A separate trusted executor consumes an expiring permit. Ambiguous sends go
   to reconciliation; no generic retry may duplicate an order.
8. Deterministic management/watchdog survives LLM failure. Stops are broker-side
   where supported, and amendments require acknowledged receipts. Uncertain
   state blocks new entries, not protective reconciliation.
9. Settlement records each parent exactly once, actual net fills/costs and the
   frozen initial risk. Postmortem proposes research, not policy activation.

## Record extensions (design contract; integrate via AD typed schemas)

- `PairContext`: pair, cutoff, horizon, source snapshot IDs, regime, relative
  rate-path facts, event IDs, contrary facts, coverage and version/hash.
- `Thesis`: context ID, mechanism, scenario/falsifier refs, catalyst, expiry,
  action propose/wait/reject, reason codes, known missing facts. Probabilities
  require a registered event/calibration version; otherwise null.
- `PayoffPlan`: parent/opportunity IDs, initial risk definition, entry and stop,
  child fractions, each exit rule, protection/trail rules, planned gross/net R,
  cost scenario, policy version, evidence refs and expiry.
- `PathOutcome`: original plan hash, filled quantities/prices/times, MAE/MFE,
  first-hit barriers/times, management acknowledgements, actual costs, net R,
  ambiguity/censoring flags and account-equity state.

These are required semantics, not permission to introduce parallel incompatible
classes. Exact schema fields bind in PD-02 after inspecting existing contracts.
Unresolved/malformed references, nonfinite values, future timestamps, absent
essential evidence and incompatible versions produce INVALID/WAIT, not repair
by model invention. Source text is untrusted data, never tool instructions.

## Orchestration choice

Reuse Python and the existing Prefect Cloud scheduling boundary. Start with a
bounded directed workflow, not self-spawning agents, a new queue or LangGraph/
CrewAI dependency. Add a framework only after a measured missing capability
justifies an ADR, dependency review and maintenance cost. Default research
concurrency 2; no overlapping file writers during development. Runtime attempts,
tokens and spend remain under AD budgets; paid budget stays zero unless approved.

News triggers are deduplicated by event/revision/opportunity ID. Timeout or
model quota exhaustion means WAIT on new AI-dependent ideas; deterministic
management remains independent. Retry only idempotent reads within budget.
After a source revision, create a new thesis version; never alter an old one.

## Learning and operational expectations

Journal successes, losses, scratches, rejected candidates and errors. Attribution
separates normal stochastic loss, thesis error, timing, management, execution and
policy violation. A win does not excuse a violation. Prompt/memory improvements
are not foundation-model training.

Updates follow proposal -> registered experiment -> independent evaluation ->
shadow -> reviewed certification -> permitted demo activation. Runtime agents
cannot edit executable code, evaluator, tests, permissions or hard risk. Keep a
champion digest, predecessor and rollback evidence. Changing a model does not
reset safety history. Log actual model/provider/version, not just role labels.

Scope assumptions: one owner, two execution pairs, local/private archived data,
research latencies measured against AD deadlines, no high-frequency news-race
claim. Availability, feed licences, clock accuracy, isolated watchdog ownership
and broker receipts remain operational acceptance checks. Missing supervision
means research/shadow, not unattended trading. Owner maintains credentials and
host availability; coordinator maintains reviewed code and evidence.
