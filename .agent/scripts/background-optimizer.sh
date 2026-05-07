#!/usr/bin/env bash
#
# background-optimizer.sh — Runs optimization tasks when system is idle
# Compresses old logs, cleans up temporary files, optimizes maps
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Background Optimizer ==="
echo "Started: $(date -Iseconds)"

# 1. Compress old metrics logs
echo "[1/4] Compressing old metrics..."
if [[ -f ".agent/metrics/build-log.jsonl" ]]; then
  lines=$(wc -l < .agent/metrics/build-log.jsonl)
  if [[ $lines -gt 1000 ]]; then
    # Keep last 500 lines, archive the rest
    tail -n 500 .agent/metrics/build-log.jsonl > .agent/metrics/build-log.jsonl.tmp
    mv .agent/metrics/build-log.jsonl.tmp .agent/metrics/build-log.jsonl
    echo "  ✓ Compressed metrics log (kept last 500 of $lines lines)"
  fi
fi

# 2. Clean old worktrees
echo ""
echo "[2/4] Cleaning old worktrees..."
if [[ -d ".agent/worktrees" ]]; then
  find .agent/worktrees -maxdepth 1 -type d -mtime +7 | while read dir; do
    if [[ "$dir" != ".agent/worktrees" ]]; then
      echo "  ✓ Removing old worktree: $dir"
      rm -rf "$dir"
    fi
  done
fi

# 3. Rebuild semantic map if source changed
echo ""
echo "[3/4] Checking if semantic map needs rebuild..."
if [[ -f ".agent/maps/SEMANTICMAP.json" ]]; then
  map_age=$(( $(date +%s) - $(stat -c %Y .agent/maps/SEMANTICMAP.json) ))
  if [[ $map_age -gt 3600 ]]; then
    ./.agent/scripts/build-semantic-map.sh >/dev/null 2>&1
    echo "  ✓ Rebuilt semantic map (was ${map_age}s old)"
  else
    echo "  ✓ Semantic map is fresh"
  fi
fi

# 4. Run meta-learning if enough data
echo ""
echo "[4/4] Running meta-learning..."
if [[ -f ".agent/metrics/build-log.jsonl" ]]; then
  lines=$(wc -l < .agent/metrics/build-log.jsonl)
  if [[ $lines -gt 10 ]]; then
    ./.agent/scripts/learn-from-outcomes.sh >/dev/null 2>&1
    echo "  ✓ Updated learning patterns"
  else
    echo "  ✓ Not enough data for learning yet ($lines events)"
  fi
fi

echo ""
echo "Finished: $(date -Iseconds)"
echo "Next run: cron or manual invocation"
