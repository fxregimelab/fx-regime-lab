# Git Conventions

Every commit message is a context document. Future Cursor sessions
can read git log to understand what was built and why.

## Format

```
type(scope): short description (max 60 chars)

- What specifically changed
- Why it was changed (if not obvious)
- Any constraints or gotchas discovered
- Tested: [how you verified it works]
```

## Types

feat — new feature or page
fix — bug fix
style — visual/CSS only change
refactor — code restructure, no behavior change
docs — documentation only
deploy — deployment config change
pipeline — Python pipeline change (not frontend)

## Scopes

home, brief, terminal, performance, about — page names
nav, footer, layout — shell components
regime, signal, validation — data components
queries, types, constants — lib changes
config — wrangler.toml (if reintroduced), framework config in future app package
ci — GitHub Actions

## Examples

feat(brief): convert to dynamic edge route, wire to brief_log table

- Changed brief/page.tsx from static to dynamic edge route
- Added getBriefByDate() and getLatestBrief() to queries.ts
- Handles missing Supabase env with "Brief unavailable" fallback
- Tested: renders on fxregimelab.com/brief with today's brief text

fix(terminal): correct pair ID lookup for regime_calls query

- PAIRS constant used "EURUSD" but regime_calls.pair stores "EUR/USD"
- Updated PAIRS constant pair field to match DB values
- Tested: pair desks show live regime data, not "No regime call"

deploy: document Worker API-only deploy after UI removal

- Removed static asset paths from workers/site-entry.js
- Tested: curl /api/health returns JSON 200

## When working with Cursor

After every Cursor session, write the commit message yourself.
Do not let Cursor write commit messages — they will be generic.
The commit message is your record of what happened and why.

---
