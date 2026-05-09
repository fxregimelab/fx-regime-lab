# Kimi Configuration for FX Regime Lab

This directory exists to document that Kimi is wired to use the same skills as Cursor, and knows how to delegate to Cursor when appropriate.

## How Kimi reads this repo's config

1. **Handover**: Kimi reads `HANDOVER.md` (workspace root) automatically for operator identity, locked decisions, and career context.
2. **Skills**: Kimi loads all `SKILL.md` files from `.cursor/skills/` AND `.kimi/skills/` via `extra_skill_dirs` in `~/.kimi/config.toml`.
3. **Rules**: Kimi reads `AGENTS.md` (workspace root) automatically. That file points to `.cursor/AGENTS.md` and `.cursorrules` for the full rule set.
4. **Delegation**: Kimi can delegate complex tasks to Cursor Agent CLI via the `cursor-delegation` skill.

## What works in both agents

| Config | Cursor | Kimi |
|--------|--------|------|
| `HANDOVER.md` | ✅ | ✅ (auto-read) |
| `SKILL.md` files | ✅ | ✅ (via `extra_skill_dirs`) |
| `.cursorrules` | ✅ | ✅ (readable as repo file) |
| `AGENTS.md` | ✅ | ✅ (auto-read) |
| `.mdc` rules | ✅ | ❌ (Cursor-specific format) |
| Slash commands | ✅ | ❌ |
| Pre/post hooks | ✅ | ❌ |
| Subagent JSON | ✅ | ❌ |
| MCP servers | ✅ | ✅ (separate config) |

## Kimi → Cursor Delegation

Kimi can delegate complex tasks to Cursor Agent using the `cursor-delegation` skill or the wrapper script:

```bash
./scripts/cursor-delegate.sh \
  --task "Implement the Terminal layout shell component" \
  --files "web/src/app/terminal/layout.tsx" \
  --tests "npm run build" \
  --mode auto
```

See `.kimi/skills/cursor-delegation/SKILL.md` for full delegation protocol.

## Manual step if you move the repo

If the repo path changes, update `~/.kimi/config.toml`:

```toml
extra_skill_dirs = [
  "/new/path/to/repo/.cursor/skills",
  "/new/path/to/repo/.kimi/skills"
]
```
