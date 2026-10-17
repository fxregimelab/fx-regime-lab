# Autonomous Demo Desk Implementation Plan

> **For execution agents:** use the available `executing-plans` workflow task-by-task;
> preserve the repository's TDD, impact-analysis and review requirements. Older tools
> may call this `superpowers:executing-plans`; do not invoke an unavailable alias.

**Goal:** build a private demo desk that autonomously researches, proposes, tests,
trades graduated strategies, evaluates outcomes and promotes validated improvements
without granting the research model control over its safety rules or evaluator.

**Architecture:** an unprivileged research plane proposes versioned data artifacts.
A deterministic, separately protected control plane validates evidence, manages risk,
executes/reconciles demo orders and promotes only certified artifacts. Immutable events
make decisions, outcomes, recoveries and experiments replayable.

**Tech stack:** existing Python pipeline, pytest/Ruff/mypy, local SQLite and hashed
files, existing `ai/client.py`, a constrained Windows MT5 executor, Prefect Cloud
for workflow scheduling; no GitHub Actions or public frontend work.

**Document status:** implementation-ready DRAFT v1, 2026-10-18. This delivery drafts
the specification, proposed build order and task packets together at the owner's
request; it does not approve code not yet written or prove trading readiness.
**Owner decision recorded:** automatic promotion into **demo** trading is authorized
when the independent acceptance gates pass; per-promotion approval is not required.

---

## 1. Start here: five-minute agent orientation

1. Read `IDENTITY.md`, then `MASTERPLAN.md`, then the latest section of `TASK.md`.
2. Read this index and select exactly one task in
   [05-implementation-tasks.md](../specs/autonomous-desk/05-implementation-tasks.md).
3. Load only that task's source files and referenced spec sections. Do not load every
   implementation packet into a small model's context at once.
4. Inspect `git status`; previous audit changes may be uncommitted. Preserve them.
5. Confirm task dependencies using verified artifacts, not a checkbox or chat summary.
6. Write/run the specified failing tests, implement the slice, verify it and produce the
   handoff receipt defined in [06-agent-prompts-and-runbook.md](../specs/autonomous-desk/06-agent-prompts-and-runbook.md).
7. A task is done only when its tests pass and an independent review addresses findings.
   A blocked prerequisite means `BLOCKED`, not a stub, fallback success or skipped test.

## 2. Authority, scope and non-goals

This is the owner's private research/validation extension on `fx-live-personal`.
It is not a public trading service, public roadmap replacement or new frontend product.
The public research pipeline retains its three-pair lock and immutable ledgers.
Runtime execution remains EURUSD/USDJPY on an allowlisted **demo account only**.
Additional instruments and real money require separate explicit authorization and
their applicable repository gates; the general wish for autonomy does not satisfy them.

Automatically allowed after gates exist:
- Gather approved data; archive evidence; compute features; register hypotheses.
- Test bounded setup variants and prompt variants; run matched shadow evaluations.
- Promote a certified challenger; schedule entries for graduated artifacts.
- Manage/reconcile existing positions; settle; reduce exposure; revoke artifacts;
  roll back to a still-valid champion or stand down if none is valid.

Never autonomous in this version:
- Raise hard risk ceilings, alter evaluator/test thresholds or change permissions.
- Edit evaluator code, install dependencies, deploy arbitrary generated Python or
  execute model-produced shell/SQL. Runtime evolution is data/config/prompt selection.
- Erase events, reset the operator safety history, merge to main or publish private state.
- Convert demo success into a claim that real-money performance is established.

The owner can pause immediately. A permanent integrity/security/owner stop requires
owner release. An unattended system can safely remain paused indefinitely; “entirely
autonomous” does not mean it invents permission to resolve every possible incident.

## 3. Existing baseline versus proposed work

Observed local baseline from the preceding audit (not a fresh claim of execution):
- `paper/store.py`: generic append-only hash chain and mutable bars cache.
- `paper/prices.py`: validation/sync, completed-bar fetch at MT5 position 1.
- `paper/levels.py`, `paper/checklist.py`: pure levels, checks and candidate eligibility.
- `paper/admission.py`: pure readiness/loss-capacity policy with caller-supplied flags.
- `paper/operator_score.py`: pure outcome-point replay and latched restrictions.
- `paper/evidence.py`: bounded intraday-news packet validation, not a collector.
- Prior audit verification: 478 pytest, Ruff/mypy, Biome and production build passed.

Not installed: protected execution authority, atomic reservation, broker reconciliation,
management/watchdog, authoritative calendar/news archive, deterministic SU1–SU4
detectors, trusted readiness facts, experiment evaluator, promotion service or daemon.
See [audit findings](../DESK_AUDIT_AND_IMPROVEMENT.md). Baseline files may still be local
uncommitted work; future implementers must reconcile that explicitly before branching.

## 4. Capability map and dependency direction

Stable module IDs, with provider-owned contracts:

- **authority** — immutable owner policy, process/tool permissions, budgets, spec registry.
  Depends on no runtime component.
- **journal** — private writer boundary, events, snapshots, transactions, projections.
  Depends on authority/contracts.
- **observations** — broker/read-only research inputs, timestamp/coverage evidence.
  Depends on journal.
- **features** — point-in-time indicators, liquidity, deterministic setup detection.
  Depends on observations.
- **reasoning** — bounded AI packets and counterarguments, no trade capability.
  Depends on authority, journal, features; AI calls only through `ai/client.py`.
- **risk** — sizing, loss capacity, currency exposure, trusted readiness and reservations.
  Depends on journal, observations and validated proposals.
- **execution** — signed/expiring permit consumption, broker actions and reconciliation.
  Depends on risk; never on an LLM response directly.
- **management** — deterministic stops/exits, independent watchdog and settlement.
  Depends on execution and observations; continues without reasoning service.
- **evaluation** — immutable research trials, replay/shadow outcomes and scorecards.
  Depends on journal/features; historical replay does not depend on live execution.
- **evolution** — champion/challenger selection, certified promotion and rollback.
  Depends on evaluation and authority; cannot change either provider's rules.
- **operations** — orchestration/health/alerts and recovery. Health inputs are read by
  risk, but operations does not calculate trading permission. No import-cycle dependency.

Logical build: authority/contracts → journal → observations/features → reasoning +
evaluation; journal/observations → risk → execution → management/settlement;
validated evaluation + proven management → evolution → operational demo graduation.
Bootstrap the watchdog before granting execution any write capability.

## 5. Requirements and acceptance ownership

- **AD-01 Boundary isolation:** research cannot access terminal-write credentials,
  production service-role credentials, evaluator secrets or mutable authority files.
- **AD-02 Provenance:** every action references resolvable snapshots and spec hashes;
  historical features are invariant to future inputs.
- **AD-03 Exact eligibility:** registered setup rules, checklist, caps and unknown-state
  rejection are deterministic, not free-text flags supplied by an AI.
- **AD-04 Parent risk:** one thesis owns one budget shared by children; simultaneous
  proposals cannot reserve the same remaining loss capacity.
- **AD-05 Reconciliation:** ambiguous broker outcomes never cause blind resubmission;
  local state cannot authorize another entry until reconciled.
- **AD-06 Management:** server-side protection plus a separately supervised management
  loop survives model failure and has tested recovery behavior.
- **AD-07 Accounting:** net-cost parent settlement once; immutable initial R; global
  operator history persists across model changes and restarts.
- **AD-08 Grounded reasoning:** structured facts/citations/counterarguments; unsupported
  claims or incomplete source coverage cause abstention.
- **AD-09 Honest evaluation:** all trials/candidates logged; purged chronological tests;
  matched opportunities and precommitted statistical budgets.
- **AD-10 Bounded evolution:** only allowlisted artifact fields change; protected evaluator
  certifies promotions, with atomic activation and replayable rollback.
- **AD-11 Operation:** durable single-writer ownership, deadlines, budgets, health checks,
  recoverable ordinary outages and owner-visible incidents.
- **AD-12 Honest reporting:** actual versus target, uncertainty, denied proposals and all
  incidents reported; “no trade” is valid; no guaranteed return or invented evidence.

Exact test ownership and fault fixtures are in
[07-verification-matrix.md](../specs/autonomous-desk/07-verification-matrix.md).

## 6. Specification map

- [01 — Contracts and storage](../specs/autonomous-desk/01-contracts-and-storage.md):
  identities, typed records, writer boundary, event schemas, artifacts, reservations.
- [02 — Data, calculations and strategies](../specs/autonomous-desk/02-data-and-strategies.md):
  timestamps, coverage, cost units, feature math and deterministic setup definitions.
- [03 — Execution and recovery](../specs/autonomous-desk/03-execution-and-recovery.md):
  loss budgets, permits, state machine, broker ambiguity, management and watchdog.
- [04 — Learning and promotion](../specs/autonomous-desk/04-learning-and-promotion.md):
  reward separation, trials, statistical gates, tunable fields, rollback and latches.
- [05 — Implementation tasks](../specs/autonomous-desk/05-implementation-tasks.md):
  ordered small task packets with source paths, interfaces, tests and blocking conditions.
- [06 — Agent prompts and operations](../specs/autonomous-desk/06-agent-prompts-and-runbook.md):
  copyable prompts, budgets, command contracts, startup, shutdown and incidents.
- [07 — Verification matrix](../specs/autonomous-desk/07-verification-matrix.md):
  requirement-to-test mapping, non-vacuous fixtures, mutation and fault tests, graduation.

## 7. Proposed defaults and unresolved external dependencies

Coding baseline: follow actual `pipeline/pyproject.toml` (Python≥3.11, strict mypy,
Ruff100columns). Prefer frozen dataclasses and small pure functions like the existing
paper policy modules; explicit typed input/result objects over arbitrary dictionaries
inside the trusted core. Keep Decimal at money/broker-step boundaries; no type-ignore
or broad exception-to-success workaround. No new dependency/framework without reviewed need.

These are explicit version-1 engineering choices, not claims of optimized trading edge:
- One owner, one terminal/account, two execution pairs, one local writer/executor.
- Default mode `shadow`; executable artifacts disabled until graduation certificate.
- Windows terminal host stays awake/connected; research runs separately without terminal
  write/network privileges. Prefect Cloud schedules workflows; local supervised services
  own continuous reconciliation/management. No GitHub Actions.
- UTC durable day/week anchors; broker clock verification is a prerequisite, not assumed.
- Daily AI cap 60 actual provider attempts; 8,000 input/2,000 output tokens per attempt,
  2 attempts per role/job; daily monetary cap defaults to ZERO until locally provisioned.
  Unknown prices disable paid inference; deterministic management has no AI dependency.
- One challenger evaluated at a time; at most 20 registered variants per 28-day epoch.
- Proposed timing, statistical and drift constants live in a protected policy manifest;
  their exact defaults are specified in companion documents, never secretly inferred.

External dependencies can remain blockers: authoritative release-calendar access, a
continuous host, verified broker symbol/stop/freeze rules, provider entitlement and
local secret provisioning. Missing dependencies keep the system shadow/paused; smaller
models are not authorized to substitute guessed calendars or fabricated results.

## 8. Completion gates and non-functional targets

- **G0 Local baseline:** preserve prior work; all current tests pass; policy manifest
  hashes, filesystem/tool isolation and task receipts verified.
- **G1 Point-in-time inputs:** snapshot and leakage tests pass; calendar/news coverage
  proven; production telemetry isolation proven with forbidden-write spies.
- **G2 Fake-broker operation:** deterministic sizing, reservations, all failure/restart
  scenarios and unattended management pass without external services.
- **G3 Shadow graduation:** actual forward evidence, replay parity, persistent watchdog,
  fault tests, signed evaluator certificate and authority identity checks pass.
- **G4 Demo canary:** certified A/A+ candidates at downscaled risk only; no integrity
  incidents; enough fully settled evidence. No deadlines force gate progression.
- **G5 Autonomous promotion:** protected evaluator and atomic switch/rollback demonstrated
  on a challenger; continuing demo-only authority enforced continuously.

SLOs (test load: two pairs, max four parents/eight children): risk decision p95 <250ms
excluding broker I/O; replayable feature batch p95 <2s for bounded windows; management
cycle every 5s with <15s stale-health threshold; no guarantee while host/broker is down.
No in-memory-only safety state; task cancellation/restart must preserve reservations.
Disk free <2GB or journal failure pauses entries; open-position safety continues best effort.

## 9. Decision log

- **D1 Automatic demo promotion:** accepted by owner in this conversation; conditional
  independent evidence replaces per-promotion approval, not runtime safety gates.
- **D2 Data-only evolution:** chosen over unrestricted self-modifying code so smaller
  models cannot weaken their own judge or deploy unreviewed execution logic.
- **D3 Protected control plane:** chosen over an LLM “risk reviewer”; deterministic facts
  and isolation are required even if several models agree.
- **D4 Three score dimensions:** process, outcome and probability quality stay separate;
  reward-point maximization is not equivalent to profitable, calibrated trading.
- **D5 Honest abstention:** no valid champion/input coverage means no trade; the +50%
  weekly target is reporting-only and never a release condition or override.
- **D6 Draft versus runtime:** this pack does not modify trading code, start daemons,
  register schedules, provision secrets, place orders, commit or push prior local changes.

## 10. Delivery and execution contract

This pack is the proposed private implementation contract; it does not override
`IDENTITY.md`/`MASTERPLAN.md` or authorize changes to public product direction.
When implementing, use the task DAG, execute one slice at a time and stop on a
contradiction. Document proposed spec corrections before code; a runtime model cannot
approve a policy correction for itself. The next executable task is **AD-T00**, not
“start trading” or “optimize until the weekly target is reached.”
