---
name: desk-worker
description: Execute or review one bound payoff-desk development packet with scoped files, test evidence and a fail-closed handoff.
---

1. Read IDENTITY.md, MASTERPLAN.md, latest TASK.md and the payoff-desk index.
2. Select exactly one READY packet in docs/specs/payoff-desk/05-delivery.md.
   Record HEAD, spec hash, dependencies, changed baseline and allowed files.
3. Stop for unbound scope, conflicting authority, missing acceptance definitions,
   unavailable model or another writer. Runtime and protected-policy access is absent.
4. Inspect direct callers and required impact analysis before existing-symbol edits.
   Tool failure means UNKNOWN with manual evidence, not automatic zero risk.
5. Observe failing contract tests, implement the minimal complete slice and run
   approved focused/full checks. No disabled assertions, ignored types, empty
   success stubs, invented logs or live broker/model/production DB calls.
6. Return the AD spec06 receipt: actual paths, commands, exits, failures,
   assumptions, model route, side effects and remaining blockers. Separate what
   ran from what was merely inspected. Independent review precedes acceptance.
7. Stop after this packet; do not commit/push, start a successor or clear a gate.

Three failed repair iterations or45min => checkpoint/BLOCKED. A smaller model
gets only the packet's cited context, not an unbounded old conversation. Request
a scope split rather than truncating safety clauses or inventing missing inputs.
