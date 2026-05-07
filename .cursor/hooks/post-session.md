# Post-Session Hook

Runs automatically at the end of every Cursor agent session.

## Actions

1. Run `cd pipeline && pytest` — all tests must pass
2. Run `cd web && npm run build` — zero errors
3. Run `cd pipeline && ruff check .` — zero lint errors
4. Check `git diff --stat` for changed files
5. Suggest commit message based on changed files

## Commit message format

```
[<scope>] <verb> <description>

- Scope: pipeline|web|db|worker|docs
- Verb: add|fix|update|refactor|remove
- Description: max 50 chars
```

Examples:
- `[pipeline] fix EURUSD yield fetcher timeout`
- `[web] add Terminal layout component`
- `[db] add validation_log indexes`

## Failure handling

If tests or build fail:
- List failing files
- Suggest fixes
- Block commit suggestion until resolved
