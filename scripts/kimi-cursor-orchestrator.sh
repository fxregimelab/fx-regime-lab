#!/usr/bin/env bash
#
# kimi-cursor-orchestrator.sh — Master orchestrator for Kimi → Cursor delegation
# Manages the full pipeline: queue → parallel execution → verification → retry
#
# Usage:
#   # Queue specs and process them
#   ./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3
#
#   # Process a single spec immediately
#   ./scripts/kimi-cursor-orchestrator.sh --spec /tmp/spec.md --yolo
#
#   # Process all specs in queue with max parallelism
#   ./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel max
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${REPO_ROOT}"
QUEUE_DIR="${REPO_ROOT}/.cursor/delegation/queue"
LOGS_DIR="${REPO_ROOT}/.cursor/delegation/logs"
SESSIONS_DIR="${REPO_ROOT}/.cursor/delegation/sessions"
SPECS_DIR="${REPO_ROOT}/.cursor/delegation/specs"
MODEL="claude-sonnet-4-5"
PARALLEL=1
YOLO=false
PROCESS_QUEUE=false
SPEC_FILE=""
SESSION_ID=""
MAX_RETRIES=2
DRY_RUN=false

# Generate session ID if not provided
generate_session_id() {
  echo "$(date +%Y%m%d-%H%M%S)-$$"
}

# Ensure directories exist
ensure_dirs() {
  mkdir -p "$QUEUE_DIR" "$LOGS_DIR" "$SESSIONS_DIR" "$SPECS_DIR"
}

# Write session state
write_session_state() {
  local session="$1"
  local key="$2"
  local value="$3"
  local session_file="${SESSIONS_DIR}/${session}.json"
  
  if [[ -f "$session_file" ]]; then
    python3 -c "
import json, sys
with open('$session_file') as f: d = json.load(f)
d['$key'] = $value
with open('$session_file', 'w') as f: json.dump(d, f, indent=2)
"
  else
    echo "{\"session_id\": \"$session\", \"$key\": $value}" > "$session_file"
  fi
}

# Initialize session
init_session() {
  local session="$1"
  local session_file="${SESSIONS_DIR}/${session}.json"
  cat > "$session_file" << EOF
{
  "session_id": "$session",
  "started_at": "$(date -Iseconds)",
  "workspace": "$WORKSPACE",
  "model": "$MODEL",
  "status": "running",
  "tasks_queued": 0,
  "tasks_completed": 0,
  "tasks_failed": 0,
  "tasks_retried": 0,
  "specs": [],
  "results": []
}
EOF
  echo "$session"
}

# Queue a spec
queue_spec() {
  local spec_file="$1"
  local priority="${2:-normal}"  # normal, high, urgent
  local timestamp=$(date +%s)
  local basename=$(basename "$spec_file" .md)
  local queue_name="${timestamp}-${priority}-${basename}.md"
  
  cp "$spec_file" "${QUEUE_DIR}/${queue_name}"
  echo "${QUEUE_DIR}/${queue_name}"
}

# Get queue list sorted by priority
describe_queue() {
  ls -1 "$QUEUE_DIR"/*.md 2>/dev/null | sort || true
}

# Parse spec for metadata (files, tests, etc.)
parse_spec_metadata() {
  local spec_file="$1"
  python3 << PYEOF
import re, sys

with open('$spec_file') as f:
    content = f.read()

metadata = {
    "files": [],
    "tests": [],
    "creates": [],
    "modifies": [],
    "deletes": []
}

# Extract files section
files_match = re.search(r'## Files\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
if files_match:
    files_text = files_match.group(1)
    for line in files_text.split('\n'):
        line = line.strip()
        if line.startswith('- CREATE:'):
            metadata["creates"].append(line.replace('- CREATE:', '').strip().strip('`'))
            metadata["files"].append(line.replace('- CREATE:', '').strip().strip('`'))
        elif line.startswith('- MODIFY:'):
            metadata["modifies"].append(line.replace('- MODIFY:', '').strip().strip('`'))
            metadata["files"].append(line.replace('- MODIFY:', '').strip().strip('`'))
        elif line.startswith('- DELETE:'):
            metadata["deletes"].append(line.replace('- DELETE:', '').strip().strip('`'))
            metadata["files"].append(line.replace('- DELETE:', '').strip().strip('`'))

# Extract tests
if 'pytest' in content:
    metadata["tests"].append('cd pipeline && pytest')
if 'npm run build' in content:
    metadata["tests"].append('cd web && npm run build')

print(repr(metadata))
PYEOF
}

# Check if two specs have overlapping files
specs_overlap() {
  local spec1="$1"
  local spec2="$2"
  
  local files1=$(parse_spec_metadata "$spec1" | python3 -c "import ast,sys; d=ast.literal_eval(sys.stdin.read()); print('\n'.join(d['files']))")
  local files2=$(parse_spec_metadata "$spec2" | python3 -c "import ast,sys; d=ast.literal_eval(sys.stdin.read()); print('\n'.join(d['files']))")
  
  # Check for overlap
  comm -12 <(echo "$files1" | sort) <(echo "$files2" | sort) | grep -q '.'
}

# Group specs by dependency (overlapping files must be sequential)
group_specs_for_parallelism() {
  local specs=("$@")
  local -a groups=()
  local -a current_group=()
  
  for spec in "${specs[@]}"; do
    local can_add=true
    for grouped_spec in "${current_group[@]}"; do
      if specs_overlap "$spec" "$grouped_spec" 2>/dev/null; then
        can_add=false
        break
      fi
    done
    
    if [[ "$can_add" == true ]]; then
      current_group+=("$spec")
    else
      # Save current group and start new one
      if [[ ${#current_group[@]} -gt 0 ]]; then
        printf '%s\n' "${current_group[@]}"
        echo "---GROUP---"
      fi
      current_group=("$spec")
    fi
  done
  
  # Save last group
  if [[ ${#current_group[@]} -gt 0 ]]; then
    printf '%s\n' "${current_group[@]}"
  fi
}

# Execute a single spec
execute_spec() {
  local spec_file="$1"
  local session="$2"
  local attempt="${3:-1}"
  local basename=$(basename "$spec_file" .md)
  local log_file="${LOGS_DIR}/${session}-${basename}-attempt${attempt}.log"
  local result_file="${LOGS_DIR}/${session}-${basename}-attempt${attempt}-result.json"
  
  echo "=== Executing: $basename (attempt $attempt) ===" | tee -a "$log_file"
  echo "Spec: $spec_file" | tee -a "$log_file"
  echo "Started: $(date -Iseconds)" | tee -a "$log_file"
  echo "" | tee -a "$log_file"
  
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] Would execute: agent --print --trust --approve-mcps --yolo ..." | tee -a "$log_file"
    echo '{"status": "dry_run", "success": true}' > "$result_file"
    return 0
  fi
  
  # Run Cursor agent
  local cmd=(agent --print --trust --approve-mcps)
  [[ "$YOLO" == true ]] && cmd+=(--yolo)
  cmd+=(--model "$MODEL")
  cmd+=(--workspace "$WORKSPACE")
  cmd+=(--output-format json)
  cmd+=("You are Cursor Executor for FX Regime Lab. Execute the Implementation Spec in $spec_file EXACTLY as written. Do not deviate. Read the spec first, then implement it. After implementation, run any tests specified in the spec and report results.")
  
  echo "Command: ${cmd[*]}" >> "$log_file"
  echo "" >> "$log_file"
  
  local exit_code=0
  "${cmd[@]}" > "$log_file.raw" 2>> "$log_file" || exit_code=$?
  
  # Try to parse JSON output
  if python3 -c "import json; json.load(open('$log_file.raw'))" 2>/dev/null; then
    cp "$log_file.raw" "$result_file"
  else
    # Wrap raw output as JSON
    python3 -c "
import json, sys
with open('$log_file.raw') as f:
    raw = f.read()
with open('$result_file', 'w') as f:
    json.dump({'status': 'completed', 'raw_output': raw, 'exit_code': $exit_code}, f, indent=2)
" 2>/dev/null || echo "{\"status\": \"completed\", \"exit_code\": $exit_code}" > "$result_file"
  fi
  
  echo "" | tee -a "$log_file"
  echo "Finished: $(date -Iseconds)" | tee -a "$log_file"
  echo "Exit code: $exit_code" | tee -a "$log_file"
  echo "Result: $result_file" | tee -a "$log_file"
  echo "" | tee -a "$log_file"
  
  return $exit_code
}

# Verify a spec's results
verify_spec() {
  local spec_file="$1"
  local session="$2"
  local basename=$(basename "$spec_file" .md)
  local verify_log="${LOGS_DIR}/${session}-${basename}-verify.log"
  
  echo "=== Verifying: $basename ===" | tee -a "$verify_log"
  
  # Extract test commands from spec
  local tests=$(python3 << PYEOF
import re
with open('$spec_file') as f:
    content = f.read()

tests = []
if 'pytest' in content:
    tests.append('cd pipeline && pytest')
if 'npm run build' in content:
    tests.append('cd web && npm run build')
if 'npm run lint' in content:
    tests.append('cd web && npm run lint')
if 'ruff check' in content:
    tests.append('cd pipeline && ruff check .')
if 'mypy' in content:
    tests.append('cd pipeline && mypy .')

print('\n'.join(tests))
PYEOF
)
  
  local all_passed=true
  while IFS= read -r test_cmd; do
    [[ -z "$test_cmd" ]] && continue
    echo "Running: $test_cmd" | tee -a "$verify_log"
    if eval "$test_cmd" >> "$verify_log" 2>&1; then
      echo "✓ PASSED: $test_cmd" | tee -a "$verify_log"
    else
      echo "✗ FAILED: $test_cmd" | tee -a "$verify_log"
      all_passed=false
    fi
  done <<< "$tests"
  
  # Check git diff
  echo "" | tee -a "$verify_log"
  echo "Git diff:" | tee -a "$verify_log"
  git diff --stat | tee -a "$verify_log" || true
  
  if [[ "$all_passed" == true ]]; then
    echo '{"verification": "passed", "tests_passed": true}' > "${LOGS_DIR}/${session}-${basename}-verify.json"
    return 0
  else
    echo '{"verification": "failed", "tests_passed": false}' > "${LOGS_DIR}/${session}-${basename}-verify.json"
    return 1
  fi
}

# Generate Fix Spec from failure
generate_fix_spec() {
  local spec_file="$1"
  local session="$2"
  local attempt="$3"
  local basename=$(basename "$spec_file" .md)
  local verify_log="${LOGS_DIR}/${session}-${basename}-verify.log"
  local fix_spec="${SPECS_DIR}/${basename}-fix-attempt${attempt}.md"
  
  # Extract failure information
  local failures=$(grep -E "FAILED|Error|error:|Traceback" "$verify_log" | head -20 || true)
  local git_diff=$(git diff --stat 2>/dev/null || true)
  
  cat > "$fix_spec" << EOF
# Fix Spec: $basename (Attempt $attempt)

## Original Spec
See: $spec_file

## Failures Detected
\`\`\`
$failures
\`\`\`

## Current Git State
\`\`\`
$git_diff
\`\`\`

## Fix Required
[Analyze the failures above and determine the exact fix needed]

## Files to Modify
[Only list files that need fixing]

## Acceptance Criteria
- [ ] All previously failing tests now pass
- [ ] No new test failures introduced
- [ ] Git diff is minimal and focused

## Execution Plan
1. Read the failure logs carefully
2. Identify the root cause
3. Apply the minimal fix
4. Run tests to verify
EOF
  
  echo "$fix_spec"
}

# Process a single spec with retry logic
process_spec() {
  local spec_file="$1"
  local session="$2"
  local basename=$(basename "$spec_file" .md)
  local attempt=1
  
  while [[ $attempt -le $MAX_RETRIES ]]; do
    echo "Processing: $basename (attempt $attempt/$MAX_RETRIES)"
    
    # Execute
    if execute_spec "$spec_file" "$session" "$attempt"; then
      echo "Execution completed for $basename"
    else
      echo "Execution had issues for $basename (continuing to verify)"
    fi
    
    # Verify
    if verify_spec "$spec_file" "$session"; then
      echo "✓ $basename: VERIFIED"
      write_session_state "$session" "tasks_completed" "$(python3 -c "import json; d=json.load(open('${SESSIONS_DIR}/${session}.json')); print(d.get('tasks_completed',0)+1)")"
      return 0
    else
      echo "✗ $basename: VERIFICATION FAILED"
      
      if [[ $attempt -lt $MAX_RETRIES ]]; then
        echo "Generating Fix Spec for retry..."
        local fix_spec=$(generate_fix_spec "$spec_file" "$session" "$attempt")
        spec_file="$fix_spec"
        write_session_state "$session" "tasks_retried" "$(python3 -c "import json; d=json.load(open('${SESSIONS_DIR}/${session}.json')); print(d.get('tasks_retried',0)+1)")"
      fi
    fi
    
    attempt=$((attempt + 1))
  done
  
  echo "✗✗✗ $basename: FAILED after $MAX_RETRIES attempts"
  write_session_state "$session" "tasks_failed" "$(python3 -c "import json; d=json.load(open('${SESSIONS_DIR}/${session}.json')); print(d.get('tasks_failed',0)+1)")"
  return 1
}

# Process queue
process_queue() {
  local session="$1"
  local specs=($(describe_queue))
  local total=${#specs[@]}
  
  if [[ $total -eq 0 ]]; then
    echo "Queue is empty. Nothing to process."
    return 0
  fi
  
  echo "Session: $session"
  echo "Total specs in queue: $total"
  echo "Parallelism: $PARALLEL"
  echo "Max retries: $MAX_RETRIES"
  echo ""
  
  write_session_state "$session" "tasks_queued" "$total"
  
  if [[ $PARALLEL -eq 1 ]]; then
    # Sequential processing
    for spec in "${specs[@]}"; do
      process_spec "$spec" "$session"
    done
  else
    # Parallel processing with dependency grouping
    echo "Grouping specs by file dependencies..."
    local groups=$(group_specs_for_parallelism "${specs[@]}")
    local current_group=()
    
    while IFS= read -r line; do
      if [[ "$line" == "---GROUP---" ]]; then
        # Process current group in parallel
        if [[ ${#current_group[@]} -gt 0 ]]; then
          echo "Processing group of ${#current_group[@]} independent specs in parallel..."
          for spec in "${current_group[@]}"; do
            process_spec "$spec" "$session" &
          done
          wait
          current_group=()
        fi
      else
        current_group+=("$line")
      fi
    done <<< "$groups"
    
    # Process last group
    if [[ ${#current_group[@]} -gt 0 ]]; then
      echo "Processing final group of ${#current_group[@]} specs..."
      for spec in "${current_group[@]}"; do
        process_spec "$spec" "$session" &
      done
      wait
    fi
  fi
  
  # Finalize session
  write_session_state "$session" "status" "\"completed\""
  write_session_state "$session" "finished_at" "\"$(date -Iseconds)\""
  
  # Generate report
  local report="${LOGS_DIR}/${session}-report.md"
  python3 << PYEOF
import json, glob, os

session_file = "${SESSIONS_DIR}/${session}.json"
with open(session_file) as f:
    state = json.load(f)

report = f"""# Delegation Session Report: {state['session_id']}

## Summary
- **Started**: {state.get('started_at', 'N/A')}
- **Finished**: {state.get('finished_at', 'N/A')}
- **Total Queued**: {state.get('tasks_queued', 0)}
- **Completed**: {state.get('tasks_completed', 0)}
- **Failed**: {state.get('tasks_failed', 0)}
- **Retried**: {state.get('tasks_retried', 0)}

## Specs Executed
"""

# List all result files
for result_file in sorted(glob.glob("${LOGS_DIR}/${session}-*-result.json")):
    basename = os.path.basename(result_file)
    report += f"- `{basename}`\n"

# List verification results
report += "\n## Verification Results\n"
for verify_file in sorted(glob.glob("${LOGS_DIR}/${session}-*-verify.json")):
    basename = os.path.basename(verify_file)
    with open(verify_file) as f:
        result = json.load(f)
    status = "✓ PASS" if result.get('tests_passed') else "✗ FAIL"
    report += f"- `{basename}`: {status}\n"

report += f"""
## Session State
```json
{json.dumps(state, indent=2)}
```
"""

with open("$report", 'w') as f:
    f.write(report)

print(report)
PYEOF
  
  echo ""
  echo "=== Session Complete ==="
  echo "Report: $report"
  echo "Session: ${SESSIONS_DIR}/${session}.json"
}

# Print help
print_help() {
  cat << 'EOF'
Kimi-Cursor Orchestrator — Master delegation pipeline

OPTIONS:
  --spec <file>        Process a single spec immediately
  --process-queue      Process all specs in the delegation queue
  --parallel <n>       Max parallel tasks (default: 1, "max" for CPU count)
  --session <id>       Resume an existing session
  --max-retries <n>    Max retry attempts (default: 2)
  --yolo               Enable yolo mode for all tasks
  --model <model>      Cursor model (default: claude-sonnet-4-5)
  --workspace <path>   Repo path (default: auto-detected)
  --dry-run            Show what would be executed without running
  -h, --help           Show this help

EXAMPLES:
  # Process queue with 3 parallel workers
  ./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3

  # Process single spec
  ./scripts/kimi-cursor-orchestrator.sh --spec /tmp/spec.md --yolo

  # Dry run to see what would happen
  ./scripts/kimi-cursor-orchestrator.sh --process-queue --dry-run

  # Resume session
  ./scripts/kimi-cursor-orchestrator.sh --process-queue --session 20240115-120000-1234
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --spec) SPEC_FILE="$2"; shift 2 ;;
    --process-queue) PROCESS_QUEUE=true; shift ;;
    --parallel)
      if [[ "$2" == "max" ]]; then
        PARALLEL=$(nproc 2>/dev/null || echo 4)
      else
        PARALLEL="$2"
      fi
      shift 2 ;;
    --session) SESSION_ID="$2"; shift 2 ;;
    --max-retries) MAX_RETRIES="$2"; shift 2 ;;
    --yolo) YOLO=true; shift ;;
    --model) MODEL="$2"; shift 2 ;;
    --workspace) WORKSPACE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) print_help; exit 0 ;;
    --) shift; break ;;
    -*) echo "Unknown option: $1" >&2; exit 1 ;;
    *) break ;;
  esac
done

# Main
ensure_dirs

if [[ -z "$SESSION_ID" ]]; then
  SESSION_ID=$(generate_session_id)
fi
init_session "$SESSION_ID"

if [[ -n "$SPEC_FILE" ]]; then
  # Process single spec
  process_spec "$SPEC_FILE" "$SESSION_ID"
elif [[ "$PROCESS_QUEUE" == true ]]; then
  process_queue "$SESSION_ID"
else
  print_help
  exit 1
fi
