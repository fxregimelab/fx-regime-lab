#!/usr/bin/env bash
#
# cursor-warmup.sh — Pre-warm Cursor's codebase index for faster delegation
# Run this once before a long session to ensure Cursor has indexed the repo.
#
# Usage: ./scripts/cursor-warmup.sh
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Cursor Warm-up ==="
echo "Workspace: $REPO_ROOT"
echo ""

# Run a lightweight indexing prompt through Cursor agent
# This forces Cursor to scan and index the codebase
agent --print --trust --workspace "$REPO_ROOT" --model claude-sonnet-4-5 \
  "Index this codebase. Read AGENTS.md, .cursorrules, and the top-level directory structure. Do not make any changes. Just confirm you have indexed: pipeline/src/, web/src/, supabase/migrations/, workers/, docs/. Report the total file count you see." \
  2>/dev/null || true

echo ""
echo "=== Warm-up Complete ==="
echo "Cursor should now have the codebase indexed for faster subsequent runs."
