# Agent Workflow

> How to use Kimi subagents to develop the FX Regime Lab efficiently.

## The Operating Model

```
Kimi (Strategy) → Spec → Kimi Subagent (Execution) → Verify → Commit
```

- **Kimi (you)**: Plans, researches, decides, reviews
- **Subagent**: Executes cross-file implementation, explores codebases, debugs
- **You verify**: Run tests, review diffs, commit

## Subagent Types

### `explore` — Investigation
Use when you need to understand something without changing code.

**Examples:**
- "Find all files that import `writer.py`"
- "How does the rate signal flow from fetcher to Layer 2?"
- "What tests cover the confidence computation?"
- "Trace the data flow from `fx_spot.py` to `regime_calls` table"

**Why use it:** Faster than grepping manually. The explore agent reads files and summarizes relationships.

### `coder` — Implementation
Use when you need to modify multiple files.

**Examples:**
- "Add a new COT fetcher with tests and integrate into composite"
- "Refactor layer2_directional.py to extract rate positioning logic"
- "Fix the failing test in test_layer3_execution.py"
- "Create a new Supabase migration for the desk_cards table"

**Why use it:** Cross-file consistency. The coder agent sees all files in context and updates imports, tests, and docs together.

### `plan` — Architecture
Use when you need to decide HOW to build something before writing code.

**Examples:**
- "Should we add Redis caching or stay stateless?"
- "Design the schema for a new `research_notes` table"
- "Plan the migration from Python 3.11 to 3.12"

**Why use it:** Prevents rewriting. Architecture decisions are expensive to undo. Plan first.

## The Development Loop

```bash
# 1. Simple fix (< 3 files, obvious change)
# → Edit directly, test, commit

# 2. Complex feature (3+ files, cross-module)
# → Write spec → Explore to verify → Coder subagent → Verify → Commit

# 3. Architecture decision (new pattern, new dependency)
# → Plan subagent → Review plan → Coder subagent → Verify → Commit
```

## Verification Checklist

Before every commit:
- [ ] `cd pipeline && pytest` — all tests pass
- [ ] `cd pipeline && ruff check .` — lint clean
- [ ] `cd web && npm run build` — frontend builds (if web changed)
- [ ] `git diff --stat` — reviewed the diff

## Spec Template

A good spec has four sections:

```markdown
# Spec: <What>

## Task
One-paragraph description of what to build.

## Files to Modify
- `path/to/file1.py` — what to change
- `path/to/file2.py` — what to change

## Acceptance Criteria
- [ ] Criterion 1 (measurable)
- [ ] Criterion 2 (measurable)
- [ ] All tests pass

## Context
- Relevant conventions or patterns to follow
- Links to similar implementations
```

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| Launch coder without a spec | Write explicit file list and acceptance criteria |
| Skip verification after subagent | Always run pytest before commit |
| Use subagent for 1-line fixes | Edit directly |
| Ignore diff review | `git diff --stat` before every commit |
| Launch multiple coders on same files | Parallelize only independent tasks |

## Connections
- Subagents read: [[CODEBASE_MAP]], [[Pipeline]], [[Frontend]], [[Database]]
- Subagents modify: source files (tracked by git)
- Subagents are verified by: pytest, ruff, npm build
