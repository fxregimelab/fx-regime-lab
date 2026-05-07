# Pre-Session Hook

Runs automatically at the start of every Cursor agent session in this workspace.

## Actions

1. Read `AGENTS.md` — project overview and hard rules
2. Read `TASK.md` — current sprint status
3. Read `OMEGA_PROTOCOL.md` — persona council reference
4. Verify workspace is `fx-regime-lab/` (not a subdirectory)
5. Check `git status` for uncommitted changes
6. Run `cd pipeline && pytest --co -q` to confirm test suite loads

## Context injection

Inject into agent context:
- Current branch name
- Number of uncommitted changes
- Last commit hash
- Test suite status (loaded / failed to load)

## Warning conditions

- If `pytest --co` fails: warn user that tests are broken before any edits
- If branch is not `main`: remind to create feature branch
- If > 10 uncommitted files: suggest committing before starting
