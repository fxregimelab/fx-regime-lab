# Payoff-first private desk — implementation and handoff index

Status: **specification and development-agent package; not a trading release**.
Owner direction: 2026-10-19 conversation. Baseline: `d9c31ee`, branch
`fx-live-personal`. Only private EURUSD/USDJPY demo research is in scope.

Read `IDENTITY.md`, `MASTERPLAN.md`, then the newest `TASK.md` checkpoint first.
The public product, immutable ledgers and public accuracy/expansion gates remain
unchanged. This pack extends the private AD specifications, not their authority.

## Route by task

- [Mandate](01-mandate.md): payoff definition, supersession and protected limits.
- [Architecture](02-architecture.md): existing components, proposed joins and failures.
- [Pair evidence](03-pair-evidence.md): hypotheses, source availability and abstention.
- [Payoff study](04-payoff-study.md): exact experiments, accounting and test oracles.
- [Delivery](05-delivery.md): bounded packets, prerequisites and owner runbook.
- [Research ledger](06-research.md): external evidence, limitations and decisions.
- [Audit](../../../reports/desk/research/PAYOFF_DESK_AUDIT.md): source-backed findings.
- [MCP boundary](07-mcp-boundary.md): configuration disposition and reconnect conditions.

## Completion boundary

This delivery installs repository-local development instructions, documents the
strategy gap and binds the first implementation packet. It does not implement
runtime reasoning, management, execution, autonomous learning or profitability.
Later packets remain `needs-binding` until predecessor interfaces are accepted.
No dependency/framework purchase, schedule, order, public deployment or global
model change is authorised by this index.

## Start a worker

Use `desk-builder` for exactly PD-01 in [Delivery](05-delivery.md). Use
`desk-auditor` in a fresh child session for independent review. Agent files live
under `.opencode/agents/`; skills under `.opencode/skills/`. File installation
does not prove discovery in a running session: verify listing after reopening
the project. No DeepSeek invocation is part of this delivery.

Default model routing is inheritance, not a hardcoded provider. Keep a capable
coordinator and give a worker only its packet, current input revision and cited
files. A model's marketing name, free price or role name proves no competence.

## Definition of done for this package

All local documentation links resolve; agent frontmatter follows verified
OpenCode V2 docs; permissions fail closed; focused package tests and repository
Python checks pass; independent review dispositions are recorded. Provider
execution/discovery, broker capability and external data entitlement are separate
live acceptance checks, never inferred from a Markdown file.
