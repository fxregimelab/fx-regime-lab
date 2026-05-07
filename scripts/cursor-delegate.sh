#!/usr/bin/env bash
#
# cursor-delegate.sh — Kimi (Strategy) → Cursor (Execution) delegation wrapper
# Usage: ./scripts/cursor-delegate.sh [OPTIONS] "prompt"
#
# Philosophy: Kimi plans and specs. Cursor executes. This wrapper bridges them.
#
# Examples:
#   ./cursor-delegate.sh --task "Add new signal module" --files "pipeline/src/signals/new.py"
#   ./scripts/cursor-delegate.sh --mode plan "Plan: refactor regime classifier"
#   ./scripts/cursor-delegate.sh --yolo --spec /tmp/spec.md "Execute this spec"
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${REPO_ROOT}"
MODEL="claude-sonnet-4-5"
MODE=""
YOLO=false
TRUST=true
APPROVE_MCPS=true
OUTPUT_FILE=""
TASK=""
FILES=""
TESTS=""
SPEC=""

print_help() {
  cat << 'EOF'
Cursor Delegate — Kimi → Cursor Agent wrapper

OPTIONS:
  --task <desc>        Task description (short)
  --files <list>       Comma-separated files to modify
  --tests <cmd>        Test command to run after (e.g., "cd pipeline && pytest")
  --mode <mode>        Cursor mode: plan | ask (default: full execution)
  --yolo               Force allow all commands (use with caution)
  --model <model>      Cursor model (default: claude-sonnet-4-5)
  --spec <file>        Path to Implementation Spec markdown file
  --output <file>      Save output to file instead of stdout
  --workspace <path>   Repo path (default: auto-detected)
  -h, --help           Show this help

EXAMPLES:
  ./scripts/cursor-delegate.sh --task "Add EURUSD vol signal" --files "pipeline/src/signals/vol.py"
  ./scripts/cursor-delegate.sh --mode plan --task "Refactor terminal layout"
  ./scripts/cursor-delegate.sh --yolo --tests "npm run build" "Fix all lint errors"
  ./scripts/cursor-delegate.sh --yolo --spec /tmp/spec.md "Execute this spec exactly"
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    --files) FILES="$2"; shift 2 ;;
    --tests) TESTS="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --yolo) YOLO=true; shift ;;
    --model) MODEL="$2"; shift 2 ;;
    --output) OUTPUT_FILE="$2"; shift 2 ;;
    --spec) SPEC="$2"; shift 2 ;;
    --workspace) WORKSPACE="$2"; shift 2 ;;
    -h|--help) print_help; exit 0 ;;
    --) shift; break ;;
    -*) echo "Unknown option: $1" >&2; exit 1 ;;
    *) break ;;
  esac
done

PROMPT="${*:-}"

# Build full prompt from structured args
if [[ -n "$SPEC" ]]; then
  FULL_PROMPT="You are Cursor Executor for FX Regime Lab. Execute the Implementation Spec in $SPEC exactly as written. Do not deviate from the spec. If something is unclear, state what is unclear and stop. Read the spec first, then implement it."
  [[ -n "$PROMPT" ]] && FULL_PROMPT="$FULL_PROMPT Additional context: $PROMPT"
  PROMPT="$FULL_PROMPT"
elif [[ -n "$TASK" || -n "$FILES" || -n "$TESTS" ]]; then
  FULL_PROMPT="You are working on FX Regime Lab. Read AGENTS.md and .cursorrules first."
  [[ -n "$TASK" ]] && FULL_PROMPT="$FULL_PROMPT

Task: $TASK"
  [[ -n "$FILES" ]] && FULL_PROMPT="$FULL_PROMPT

Files to modify: $FILES"
  [[ -n "$TESTS" ]] && FULL_PROMPT="$FULL_PROMPT

After changes, run: $TESTS"
  [[ -n "$PROMPT" ]] && FULL_PROMPT="$FULL_PROMPT

Additional context: $PROMPT"
  PROMPT="$FULL_PROMPT"
fi

if [[ -z "$PROMPT" ]]; then
  echo "Error: No prompt provided. Use --task or pass a prompt string." >&2
  exit 1
fi

# Build agent command
CMD=(agent --print)

if [[ "$TRUST" == true ]]; then
  CMD+=(--trust)
fi

if [[ "$APPROVE_MCPS" == true ]]; then
  CMD+=(--approve-mcps)
fi

if [[ "$YOLO" == true ]]; then
  CMD+=(--yolo)
fi

if [[ -n "$MODE" ]]; then
  CMD+=(--mode "$MODE")
fi

CMD+=(--model "$MODEL")
CMD+=(--workspace "$WORKSPACE")
CMD+=("$PROMPT")

echo "=== Cursor Delegate ===" >&2
echo "Workspace: $WORKSPACE" >&2
echo "Model: $MODEL" >&2
[[ -n "$MODE" ]] && echo "Mode: $MODE" >&2
[[ "$YOLO" == true ]] && echo "Yolo: enabled (auto-approve all)" >&2
echo "" >&2

if [[ -n "$OUTPUT_FILE" ]]; then
  echo "Running Cursor Agent... output → $OUTPUT_FILE" >&2
  "${CMD[@]}" > "$OUTPUT_FILE" 2>&1
  echo "" >&2
  echo "=== Output saved ===" >&2
  echo "File: $OUTPUT_FILE" >&2
  echo "Lines: $(wc -l < "$OUTPUT_FILE")" >&2
else
  echo "Running Cursor Agent..." >&2
  "${CMD[@]}"
fi
