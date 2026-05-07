# FX Regime Lab — Daily Workflow

> One page. Everything you need.

## Agents

- **Kimi** = Brain (plans, researches, decides)
- **Cursor** = Hands (implements, tests, reports)

Kimi NEVER writes production code. Cursor NEVER plans.

## Commands

```bash
# One-time setup
fx-agent init

# Check system health
fx-agent status

# Create a spec from template
fx-agent spec create signal      # pipeline signal
fx-agent spec create page        # Next.js page
fx-agent spec create migration   # DB migration

# Validate before delegating
fx-agent spec validate spec.md

# Execute (delegates to Cursor automatically)
fx-agent run spec.md

# Execute all queued specs
fx-agent run --queue

# Run full test suite
fx-agent verify

# Regenerate maps manually
fx-agent maps
```

## Typical Session

**You want:** Build a new EURUSD volatility panel.

```bash
# 1. Check system
fx-agent status

# 2. See what's active
cat .agent/context/HOTFILES.md

# 3. Find relevant files
jq '.pipeline.fetchers[] | select(.file | contains("vol"))' .agent/maps/CODEMAP.json

# 4. Create spec from template
fx-agent spec create signal
# → Edit .cursor/delegation/queue/spec-*.md

# 5. Validate
fx-agent spec validate .cursor/delegation/queue/spec-*.md

# 6. Execute (Kimi → Cursor)
fx-agent run .cursor/delegation/queue/spec-*.md

# 7. Verify
fx-agent verify

# 8. Commit (hooks auto-regenerate maps)
git add -A && git commit -m "[pipeline] Add EURUSD vol signal"
```

## Hard Rules

| Rule | Detail |
|------|--------|
| Pairs | EUR/USD, USD/JPY, USD/INR ONLY |
| DB Writes | `pipeline/src/db/writer.py` ONLY |
| AI Calls | `pipeline/src/ai/client.py` (ON HOLD) |
| Immutable | `regime_calls` + `validation_log` append-only |
| CI/CD | Prefect Cloud only |
| Tests | `pytest` 121 tests + `npm run build` must pass |

## Maps

| Map | What | Command |
|-----|------|---------|
| CODEMAP | All files | `jq '.pipeline.fetchers' .agent/maps/CODEMAP.json` |
| SKILLMAP | All skills | `jq '.skills[].name' .agent/maps/SKILLMAP.json` |
| RULEMAP | All rules | `jq '.rules[].file' .agent/maps/RULEMAP.json` |
| SEMANTICMAP | Functions | `jq '.files[0].functions' .agent/maps/SEMANTICMAP.json` |
| HOTFILES | Recent changes | `cat .agent/context/HOTFILES.md` |

## Design Tokens

- **Swiss Monochrome:** `#000000` bg, white text, 1px borders
- **No rounded corners, no shadows**
- **EUR/USD:** `#4da6ff`, **USD/JPY:** `#ff9944`, **USD/INR:** `#e74c3c`
- **All financial numbers:** `tabular-nums`
