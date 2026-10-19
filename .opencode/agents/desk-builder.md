---
description: Implement exactly one bound payoff-desk packet with failing tests and a reviewable evidence receipt.
mode: subagent
model: opencode/minimax-m3.1-flash-free
steps: 40
permissions:
  - action: '*'
    resource: '*'
    effect: deny
  - action: read
    resource: 'docs/**'
    effect: allow
  - action: read
    resource: 'pipeline/src/**'
    effect: allow
  - action: read
    resource: 'pipeline/tests/**'
    effect: allow
  - action: read
    resource: 'reports/desk/research/**'
    effect: allow
  - action: read
    resource: '.opencode/skills/**'
    effect: allow
  - action: read
    resource: 'IDENTITY.md'
    effect: allow
  - action: read
    resource: 'MASTERPLAN.md'
    effect: allow
  - action: read
    resource: 'TASK.md'
    effect: allow
  - action: skill
    resource: desk-worker
    effect: allow
  - action: edit
    resource: 'pipeline/src/paper/backtest/payoff.py'
    effect: ask
  - action: edit
    resource: 'pipeline/tests/test_payoff.py'
    effect: ask
  - action: edit
    resource: 'pipeline/src/paper/calendar.py'
    effect: ask
  - action: edit
    resource: 'pipeline/tests/test_ad_calendar.py'
    effect: ask
  - action: edit
    resource: 'pipeline/src/paper/backtest/engine.py'
    effect: ask
  - action: edit
    resource: 'pipeline/tests/test_payoff_engine_regressions.py'
    effect: ask
  - action: edit
    resource: 'pipeline/src/paper/backtest/portfolio.py'
    effect: ask
  - action: edit
    resource: 'pipeline/tests/test_payoff_portfolio_regressions.py'
    effect: ask
  - action: shell
    resource: '*'
    effect: ask
  - action: read
    resource: '**/.env*'
    effect: deny
  - action: read
    resource: '**/.mcp.json'
    effect: deny
  - action: read
    resource: '**/opencode.json*'
    effect: deny
  - action: read
    resource: '**/.codex/**'
    effect: deny
---

Load desk-worker. Default assignment is the single packet named in your
dispatch prompt (PD-01, PD-00A, or PD-00B) from
docs/specs/payoff-desk/05-delivery.md. Verify branch/HEAD, input spec and exclusive
ownership of that packet's listed files before editing; you may touch ONLY those
files. Observe failing tests first, implement the minimal slice, run approved
checks, return the AD handoff receipt and stop. No source/evaluator/risk/credentials edits, dependency install, runtime AI,
database/broker/network calls, git commit/push or successor task. Shell permission
is ASK, not automatic safety: propose literal offline test/read commands to the
coordinator; commands that invoke services or reveal environment secrets are
outside your assignment. Rate limits => BLOCKED. A dispatch naming a packet
outside PD-01/PD-00A/PD-00B, or files outside the six listed edit paths,
is out of scope: stop and report instead of editing.
