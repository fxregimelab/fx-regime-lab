#!/usr/bin/env bash
#
# worktree-runner.sh — Run Cursor in an isolated git worktree for risky changes
# Usage: ./.agent/scripts/worktree-runner.sh --spec <spec.md> [--yolo]
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SPEC=""
YOLO=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --spec) SPEC="$2"; shift 2 ;;
    --yolo) YOLO=true; shift ;;
    *) break ;;
  esac
done

if [[ -z "$SPEC" ]]; then
  echo "Usage: $0 --spec <spec.md> [--yolo]"
  exit 1
fi

WORKTREE_NAME="cursor-worktree-$(date +%s)"
WORKTREE_PATH="${REPO_ROOT}/.agent/worktrees/${WORKTREE_NAME}"

echo "=== Worktree Runner ==="
echo "Original: $REPO_ROOT"
echo "Worktree: $WORKTREE_PATH"
echo "Spec: $SPEC"
echo ""

# Create worktree
echo "Creating isolated worktree..."
git worktree add "$WORKTREE_PATH" -b "$WORKTREE_NAME"

# Copy spec to worktree
SPEC_BASENAME=$(basename "$SPEC")
cp "$SPEC" "${WORKTREE_PATH}/${SPEC_BASENAME}"

# Run Cursor in worktree
echo "Running Cursor Agent in worktree..."
CMD=(agent --print --trust --approve-mcps)
[[ "$YOLO" == true ]] && CMD+=(--yolo)
CMD+=(--model claude-sonnet-4-5)
CMD+=(--workspace "$WORKTREE_PATH")
CMD+=("Execute the Implementation Spec in ${WORKTREE_PATH}/${SPEC_BASENAME} exactly as written.")

if "${CMD[@]}"; then
  echo ""
  echo "✓ Cursor completed successfully in worktree"
  echo ""
  
  # Show diff
  echo "Changes made in worktree:"
  git -C "$WORKTREE_PATH" diff --stat
  
  echo ""
  echo "To merge changes back:"
  echo "  cd $REPO_ROOT"
  echo "  git worktree merge ${WORKTREE_NAME}"
  echo "  # OR manually copy changed files"
  echo ""
  echo "To discard worktree:"
  echo "  git worktree remove ${WORKTREE_PATH}"
  echo "  git branch -D ${WORKTREE_NAME}"
else
  echo ""
  echo "✗ Cursor failed in worktree"
  echo "Worktree preserved for inspection: $WORKTREE_PATH"
fi
