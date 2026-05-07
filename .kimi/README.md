# Kimi Configuration for FX Regime Lab

This directory exists to document that Kimi is wired to use the same skills as Cursor.

## How Kimi reads this repo's config

1. **Skills**: Kimi loads all `SKILL.md` files from `.cursor/skills/` via `extra_skill_dirs` in `~/.kimi/config.toml`.
2. **Rules**: Kimi reads `AGENTS.md` (repo root) automatically. That file points to `.cursor/AGENTS.md` and `.cursorrules` for the full rule set.
3. **Commands / Hooks / Subagents**: These are Cursor-specific. Kimi does not use them directly, but the same logic is available via skills and `AGENTS.md`.

## What works in both agents

| Config | Cursor | Kimi |
|--------|--------|------|
| `SKILL.md` files | ✅ | ✅ (via `extra_skill_dirs`) |
| `.cursorrules` | ✅ | ✅ (readable as repo file) |
| `AGENTS.md` | ✅ | ✅ (auto-read) |
| `.mdc` rules | ✅ | ❌ (Cursor-specific format) |
| Slash commands | ✅ | ❌ |
| Pre/post hooks | ✅ | ❌ |
| Subagent JSON | ✅ | ❌ |
| MCP servers | ✅ | ✅ (separate config) |

## Manual step if you move the repo

If the repo path changes, update `~/.kimi/config.toml`:

```toml
extra_skill_dirs = ["/new/path/to/fx-regime-lab/.cursor/skills"]
```
