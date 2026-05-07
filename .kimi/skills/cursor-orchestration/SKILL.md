---
name: cursor-orchestration
description: >-
  Master orchestration skill for Kimi → Cursor delegation pipeline.
  Manages spec queuing, parallel execution, auto-verification, and retry.
  Use when delegating multiple tasks or complex multi-step implementations.
---

# Cursor Orchestration — Kimi → Cursor Pipeline

## Philosophy

Kimi = Strategy (plans, researches, decides). Cursor = Execution (implements, tests, reports).

For single tasks: delegate directly via `cursor-delegation` skill.  
For multiple tasks or complex pipelines: use this orchestration skill.

## When to use orchestration

Use the orchestrator when:
- You have **2+ Implementation Specs** to execute
- Tasks have **file dependencies** that require ordering
- You want **automatic verification** and **auto-retry** on failure
- You want **parallel execution** of independent tasks
- You want **structured logging** and **session tracking**

## Quick Start

### Step 1: Write Implementation Specs

For each task, write a spec:

```markdown
# Implementation Spec: [Name]

## Context
[Why]

## Files
- CREATE: `path/to/new/file.ts`
- MODIFY: `path/to/existing/file.py`

## Technical Requirements
- [Requirement 1]
- [Requirement 2]

## Acceptance Criteria
- [ ] All existing tests pass
- [ ] `npm run build` passes

## Execution Plan
1. [Step 1]
2. [Step 2]
```

### Step 2: Queue Specs

```bash
# Write specs to the queue
cp spec1.md .cursor/delegation/queue/
cp spec2.md .cursor/delegation/queue/
cp spec3.md .cursor/delegation/queue/
```

### Step 3: Run Orchestrator

```bash
# Sequential (safe, default)
./scripts/kimi-cursor-orchestrator.sh --process-queue

# Parallel (faster, for independent tasks)
./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3

# Max parallel (use all CPU cores)
./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel max

# With auto-retry and yolo mode
./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3 --yolo --max-retries 2
```

### Step 4: Review Report

The orchestrator generates a report at:
```
.cursor/delegation/logs/{session-id}-report.md
```

Read it to see:
- Which specs passed/failed
- Test results
- Git diff summary
- Session state

## Orchestrator Features

### 1. Parallel Execution

The orchestrator automatically groups specs by file dependencies:
- **Independent specs** (no overlapping files) → run in parallel
- **Dependent specs** (share files) → run sequentially

This is automatic — no manual grouping needed.

### 2. Auto-Verification

After each spec executes, the orchestrator:
1. Runs tests specified in the spec
2. Checks `npm run build` or `pytest`
3. Validates git diff
4. Reports pass/fail

### 3. Auto-Retry with Fix Specs

If verification fails:
1. Orchestrator generates a **Fix Spec** automatically
2. Re-runs Cursor with the Fix Spec
3. Re-verifies
4. Repeats up to `--max-retries` times

### 4. Session Tracking

Every run creates a session JSON:
```
.cursor/delegation/sessions/{timestamp}.json
```

Tracks:
- Specs queued/completed/failed
- Retry counts
- Start/end times
- Result files

### 5. Structured Logging

All output is logged:
- Raw Cursor output: `.cursor/delegation/logs/*-result.json`
- Verification logs: `.cursor/delegation/logs/*-verify.log`
- Session reports: `.cursor/delegation/logs/*-report.md`

## Advanced Usage

### Dry Run

See what would be executed without running:
```bash
./scripts/kimi-cursor-orchestrator.sh --process-queue --dry-run
```

### Resume Session

If a session was interrupted:
```bash
./scripts/kimi-cursor-orchestrator.sh --process-queue --session {session-id}
```

### Single Spec Execution

Process one spec immediately:
```bash
./scripts/kimi-cursor-orchestrator.sh --spec /path/to/spec.md --yolo
```

### Custom Model

Use a different Cursor model:
```bash
./scripts/kimi-cursor-orchestrator.sh --process-queue --model gpt-5.3-codex-high
```

## Workflow for Complex Projects

**Example: Build a full Terminal dashboard**

Kimi's workflow:

1. **Research & Architecture** (Kimi)
   - Analyze requirements
   - Design component hierarchy
   - Decide data flow

2. **Write Specs** (Kimi)
   ```
   spec-01-layout.md      → Terminal layout shell
   spec-02-mosaic.md      → Mosaic grid component
   spec-03-panel.md       → Individual panel component
   spec-04-queries.md     → Data fetching hooks
   spec-05-styling.md     → CSS/styling tokens
   ```

3. **Queue & Execute** (Orchestrator)
   ```bash
   cp spec-*.md .cursor/delegation/queue/
   ./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3
   ```

4. **Review Report** (Kimi)
   - Read `.cursor/delegation/logs/*-report.md`
   - Check which specs passed/failed
   - Review git diff

5. **Handle Failures** (Kimi + Orchestrator)
   - If any spec failed after retries, Kimi writes a manual Fix Spec
   - Re-queue and re-run

6. **Final Verification** (Kimi)
   - Run full test suite
   - Run build
   - Commit

## Orchestrator Command Reference

| Flag | Description |
|------|-------------|
| `--spec <file>` | Process single spec immediately |
| `--process-queue` | Process all queued specs |
| `--parallel <n>` | Parallel tasks (1, 3, or "max") |
| `--session <id>` | Resume existing session |
| `--max-retries <n>` | Max retry attempts (default: 2) |
| `--yolo` | Auto-approve all commands |
| `--model <model>` | Cursor model selection |
| `--dry-run` | Preview without executing |

## Best Practices

1. **Keep specs small** — One spec per logical component or file group
2. **List files explicitly** — The orchestrator uses file lists for dependency grouping
3. **Always include acceptance criteria** — These become verification checks
4. **Use parallel for independent tasks** — Mosaic grid + panel component can run together
5. **Use sequential for dependent tasks** — Layout must exist before page uses it
6. **Review reports** — Don't skip reading the session report
