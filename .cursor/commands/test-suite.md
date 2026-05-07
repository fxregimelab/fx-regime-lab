# test-suite

Run the full test suite and report results:
1. `cd pipeline && pytest` — all 121 tests must pass
2. `cd web && npm run build` — zero errors
3. `cd pipeline && ruff check .` — zero lint errors
4. `cd pipeline && mypy .` — zero type errors
5. Report pass/fail for each stage

Usage: `/test-suite`
