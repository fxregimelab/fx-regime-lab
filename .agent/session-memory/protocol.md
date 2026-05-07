# Session Memory Protocol

> Persistent memory across Kimi/Cursor sessions.
> Each session leaves a memory entry that future sessions can read.

## Memory Format

```json
{
  "session_id": "sess-20260506-170000",
  "agent": "kimi|cursor",
  "timestamp_start": "2026-05-06T17:00:00Z",
  "timestamp_end": "2026-05-06T17:30:00Z",
  "task": "Build EURUSD volatility panel",
  "outcome": "success|failure|partial",
  "key_decisions": [
    "Used lightweight-charts instead of Recharts",
    "Split panel into 3 sub-components"
  ],
  "lessons_learned": [
    "Tabular-nums must be on parent container, not individual spans",
    "Supabase types need regeneration after schema changes"
  ],
  "files_modified": [
    "web/src/components/panel.tsx",
    "web/src/lib/supabase/queries.ts"
  ],
  "context_loaded": [
    "CODEMAP.json",
    "nextjs-frontend skill"
  ],
  "token_usage": 4500,
  "time_spent_minutes": 30,
  "follow_up_tasks": [
    "Add responsive breakpoints for mobile",
    "Hook up real-time WebSocket feed"
  ]
}
```

## Reading Memory

```bash
# List recent sessions
ls -lt .agent/session-memory/*.json | head -10

# Read specific session
cat .agent/session-memory/sess-20260506-170000.json | jq .

# Search for lessons about a topic
grep -r "lightweight-charts" .agent/session-memory/
```

## Memory-Based Recommendations

Before starting a new task, read relevant past sessions:

```bash
# Find sessions about similar tasks
./.agent/scripts/find-similar-sessions.sh "volatility panel"
```

This prevents repeating mistakes and reuses successful patterns.
