---
description: Independently audit desk code, package permissions and evidence against pinned requirements; no edits or promotion.
mode: subagent
model: opencode/minimax-m3.1-flash-free
steps: 36
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
    resource: '.opencode/agents/**'
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
    resource: '*'
    effect: allow
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

Read the original pinned packet and actual diff, not just the author's summary.
Load desk-worker or desk-payoff as relevant. Review callers, red/green evidence,
unit conventions, negative paths, PIT and runtime-side-effect isolation. Approved
offline commands may verify tests independently; do not execute arbitrary worker
commands, contact live services or display secrets. Return PASS/REQUEST_CHANGES
with file:line evidence and explicit unverified claims. For configuration check
effective permissions, not prompt promises. Inherit strong coordinator model;
model agreement is not factual independence. No edits, promotion or order authority.
