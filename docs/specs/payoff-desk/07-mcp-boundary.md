# MCP boundary and configuration receipt

2026-10-19: user disconnected MT5 and authorised repository audit/configuration.
Native repository access now works. Earlier MT5 initialization instructions had
required server-root-only file access; no bypass was used while they applied.
Disconnecting a tool does not itself validate broker readiness.

## Observed and changed

- Local, Git-untracked/ignored `opencode.json` contains legacy remote MT5 entries.
- `mt5-terminal` uses localhost HTTP port 22346; no Python/Node launcher is
  configured there. Authentication exists and was inspected only in redacted
  structural form. No token is copied into this document.
- Its persisted `enabled` was true despite session disconnection. Set ONLY
  `mcp.mt5-terminal.enabled` to **false**, so reopening this project does not
  intentionally reconnect it. This legacy field is documented as supported by
  OpenCode V2 normalisation; no unnecessary migration/authentication rewrite.
- MetaEditor at port 22345 and all global/other-client settings remain unchanged.
- JSON parsing and a sanitized structural check verified terminal false and
  MetaEditor true. No service was restarted and no broker action was attempted.
- Do not commit `opencode.json`, `.mcp.json` or `.codex/config.toml`: they may
  contain authentication data. The receipt, not the secret file, is versioned.

OpenCode's connection setting does not change server read/write roots. No
documented MT5 root-configuration input was found; do not invent `read_roots`
keys or broaden all tool permissions. Project settings may affect other sessions
on next load; no global server restart is justified for this audit.

## Reconnect later

Owner explicitly resumes MT5 read-only verification after the repository task.
Inspect the actual installed server's documentation/policy first, reconcile any
initialization restrictions with intended workflow, and recheck capabilities.
Enable only the required endpoint through its supported client setting. The
executor's permission is separate and remains disabled until AD readiness.
Reconnection is not part of installing development agents. Never test access by
placing, modifying or closing an order. Restoring the previous client setting
is a local `enabled: true` change, not a root-policy fix or trading grant.
