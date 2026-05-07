---
name: cursor-delegation
description: >-
  Delegates complex implementation tasks from Kimi to Cursor Agent CLI.
  Use when a task requires deep cross-file refactoring, complex Next.js
  component architecture, or multi-module pipeline changes that benefit
  from Cursor's codebase-wide analysis.
---

# Cursor Delegation — Kimi → Cursor Agent

## When to delegate

Delegate to Cursor Agent **only** for:
- **Multi-file refactoring** (> 3 files changing simultaneously)
- **Complex Next.js component architecture** (new route groups, layout changes)
- **Pipeline signal modules** that touch fetchers + signals + regime logic
- **Cross-file type migrations** (changing interfaces used in 5+ places)
- **Audit tasks** requiring full codebase search and analysis

**Do NOT delegate** for:
- Simple single-file edits
- Test fixes
- Documentation updates
- migrations that only add a column

## How to delegate

### Step 1: Construct the prompt

Write a **self-contained prompt** with all context Cursor needs:

```
You are working on FX Regime Lab. Read AGENTS.md and .cursorrules first.

Task: [specific description]
Files to modify: [list]
Supabase tables: [read/write targets]
Tests to run: [pytest / npm run build / etc.]
Acceptance criteria:
- [ ] Criterion 1
- [ ] Criterion 2

Current state: [any relevant code snippets or file paths]
```

### Step 2: Run the delegation command

Use the wrapper script (recommended):

```bash
./scripts/cursor-delegate.sh \
  --task "Implement the Terminal layout shell component" \
  --files "web/src/app/terminal/layout.tsx,web/src/components/terminal/shell.tsx" \
  --tests "npm run build" \
  --mode auto
```

Or run Cursor agent directly:

```bash
agent --print --trust --approve-mcps \
  --workspace /home/shreyash/Projects/fx_regime_lab/fx-regime-lab \
  --model claude-sonnet-4-5 \
  "Your detailed prompt here"
```

### Step 3: Capture and review output

Cursor output is printed to stdout. Save it:

```bash
agent --print --trust --approve-mcps --workspace . "prompt" > /tmp/cursor-output-$(date +%s).txt 2>&1
```

**Always review Cursor's output before considering the task complete.**

## Delegation patterns

### Pattern A: Plan first, execute after review

1. Run with `--mode plan` to get a read-only plan:
   ```bash
   agent --print --trust --workspace . --mode plan "Plan: refactor the signals module to use dataclasses"
   ```
2. Review the plan
3. Run full execution:
   ```bash
   agent --print --trust --approve-mcps --yolo --workspace . "Execute: [same prompt with plan context]"
   ```

### Pattern B: Direct execution (trusted tasks only)

For well-understood, low-risk tasks where the scope is clear:

```bash
agent --print --trust --approve-mcps --yolo \
  --workspace . \
  "Add tabular-nums class to all price displays in web/src/components/terminal/"
```

### Pattern C: Worktree isolation (experimental)

For risky refactors, use an isolated git worktree:

```bash
agent --print --trust --approve-mcps --yolo \
  --workspace . \
  --worktree cursor-delegation-$(date +%s) \
  "Major refactor: split the regime classifier into separate modules"
```

## Safety rules

- **Never delegate** `rm -rf`, `git push --force`, `git reset --hard`, `supabase db reset`
- **Never delegate** secrets management or `.env` changes
- **Always verify** Cursor is using the correct `--workspace` (should be repo root)
- **Always run tests** after Cursor completes (`pytest`, `npm run build`)
- **Always review git diff** before committing Cursor's changes

## Cost awareness

Cursor Agent runs consume API credits. Typical costs:
- Simple task (1–2 files): ~$0.10–0.30
- Medium task (3–5 files): ~$0.50–1.50
- Complex refactor (10+ files): ~$2.00–5.00

Delegate judiciously. Kimi handles most tasks faster and cheaper.
