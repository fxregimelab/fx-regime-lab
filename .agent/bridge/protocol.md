# Agent Bridge Protocol

> Two-way communication channel between Kimi and Cursor.
> Agents leave structured messages for each other in `.agent/bridge/`.

## Message Format

```json
{
  "from": "kimi|cursor",
  "to": "kimi|cursor",
  "timestamp": "2026-05-06T12:00:00Z",
  "type": "spec|question|answer|status|error|fix_request|completion",
  "session_id": "session-123",
  "task_id": "task-456",
  "content": "...",
  "metadata": {}
}
```

## Message Types

| Type | From | To | Purpose |
|------|------|-----|---------|
| `spec` | Kimi | Cursor | Implementation Spec to execute |
| `question` | Cursor | Kimi | Ask for clarification on spec |
| `answer` | Kimi | Cursor | Answer to Cursor's question |
| `status` | Cursor | Kimi | Progress update (50% complete, etc.) |
| `error` | Cursor | Kimi | Execution failed, need help |
| `fix_request` | Cursor | Kimi | Auto-generated fix needed |
| `completion` | Cursor | Kimi | Task done, report attached |

## Usage

### Kimi sends spec to Cursor
```bash
python3 -c "
import json, datetime
msg = {
  'from': 'kimi',
  'to': 'cursor',
  'timestamp': datetime.datetime.now().isoformat(),
  'type': 'spec',
  'session_id': 'sess-001',
  'task_id': 'task-001',
  'content': 'Build EURUSD volatility panel...',
  'metadata': {'priority': 'high', 'files': ['web/src/components/panel.tsx']}
}
with open('.agent/bridge/kimi-to-cursor-$(date +%s).json', 'w') as f:
  json.dump(msg, f, indent=2)
"
```

### Cursor asks Kimi a question
```bash
python3 -c "
import json, datetime
msg = {
  'from': 'cursor',
  'to': 'kimi',
  'timestamp': datetime.datetime.now().isoformat(),
  'type': 'question',
  'session_id': 'sess-001',
  'task_id': 'task-001',
  'content': 'Should the panel use Recharts or lightweight-charts?',
  'metadata': {'file': 'web/src/components/panel.tsx'}
}
with open('.agent/bridge/cursor-to-kimi-$(date +%s).json', 'w') as f:
  json.dump(msg, f, indent=2)
"
```

## Reading Messages

```bash
# List all unread messages
ls -lt .agent/bridge/*.json | head -10

# Read specific message
cat .agent/bridge/kimi-to-cursor-*.json | jq .

# Mark as read (move to archive)
mv .agent/bridge/message.json .agent/bridge/archive/
```
