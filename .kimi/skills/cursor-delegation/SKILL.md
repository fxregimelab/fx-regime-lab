---
name: cursor-delegation
description: >-
  Kimi delegates ALL code implementation to Cursor Agent CLI.
  Kimi writes Implementation Specs; Cursor executes them.
  Use for every task that involves writing or modifying source code.
---

# Cursor Delegation — Kimi Plans, Cursor Executes

## Philosophy

**Kimi is the brain. Cursor is the hands.**

Kimi NEVER writes production code directly. Kimi writes Implementation Specs. Cursor executes them.

This applies to:
- New files
- Modified files
- Refactored files
- Deleted files
- Type changes with cascading effects

### When Kimi writes code directly (exceptions)

- One-line fixes (typos, missing imports)
- Configuration files (.env, config.json)
- Test assertions (after analyzing failures)
- Documentation updates

Everything else → Cursor Agent.

## Implementation Spec Format

Before delegating, Kimi MUST produce a spec:

```markdown
# Implementation Spec: [Task Name]

## Context
[Why this is being built, what user story it serves]

## Files
- CREATE: `path/to/new/file.ts`
- MODIFY: `path/to/existing/file.py`
- DELETE: `path/to/obsolete/file.tsx`

## Technical Requirements
- [Specific requirement 1]
- [Specific requirement 2]
- [Design pattern to follow]
- [Types/interfaces to use or create]

## Acceptance Criteria
- [ ] Criterion 1 (testable)
- [ ] Criterion 2 (testable)
- [ ] All existing tests pass
- [ ] `npm run build` or `pytest` passes

## Execution Plan
1. [Step 1 — what to do first]
2. [Step 2 — what to do next]
3. [Step 3 — final verification]

## Context Snippets
[Relevant code excerpts Cursor needs to see]
```

## Delegation Command

### Quick delegation (simple tasks)
```bash
agent --print --trust --approve-mcps --yolo \
  --workspace /home/shreyash/Projects/fx_regime_lab/fx-regime-lab \
  --model claude-sonnet-4-5 \
  "Execute: [concise task description]"
```

### Spec-based delegation (complex tasks)
```bash
# Write spec to a temp file first
cat > /tmp/spec.md << 'EOF'
# Implementation Spec: ...
[paste full spec]
EOF

agent --print --trust --approve-mcps --yolo \
  --workspace /home/shreyash/Projects/fx_regime_lab/fx-regime-lab \
  --model claude-sonnet-4-5 \
  "Execute the implementation spec in /tmp/spec.md. Read the spec first, then implement it exactly."
```

### Using the wrapper script
```bash
./scripts/cursor-delegate.sh \
  --task "Add EURUSD vol signal" \
  --files "pipeline/src/signals/vol.py,pipeline/src/db/writer.py" \
  --tests "cd pipeline && pytest" \
  --yolo
```

## Verification Protocol (Kimi's job after Cursor finishes)

1. **Run tests**: `cd pipeline && pytest` or `cd web && npm run build`
2. **Check git diff**: `git diff --stat` — verify only expected files changed
3. **Validate acceptance criteria** from the spec
4. **If failures**: Write a "Fix Spec" and re-delegate:
   ```
   # Fix Spec: [Task Name]
   
   ## Failure
   [What test/build failed]
   
   ## Root Cause
   [Kimi's analysis]
   
   ## Fix Required
   [Exact change needed]
   
   ## Files
   - MODIFY: `path/to/file`
   ```

## Safety Rules

- **Never delegate**: `rm -rf`, `git push --force`, `git reset --hard`, `supabase db reset`
- **Never delegate**: secrets management or `.env` changes
- **Always verify** Cursor used the correct `--workspace`
- **Always run tests** after Cursor completes
- **Always review git diff** before declaring success
