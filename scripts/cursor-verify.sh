#!/usr/bin/env bash
#
# cursor-verify.sh — Standalone verification script for Cursor delegation results
# Usage: ./scripts/cursor-verify.sh [--spec <file>] [--all]
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_FILE=""
VERIFY_ALL=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --spec) SPEC_FILE="$2"; shift 2 ;;
    --all) VERIFY_ALL=true; shift ;;
    *) break ;;
  esac
done

run_tests() {
  local exit_code=0
  
  echo "=== Running Pipeline Tests ==="
  if (cd "$REPO_ROOT/pipeline" && pytest) >> /tmp/verify.log 2>&1; then
    echo "✓ pytest passed"
  else
    echo "✗ pytest failed"
    exit_code=1
  fi
  
  echo "=== Running Frontend Build ==="
  if (cd "$REPO_ROOT/web" && npm run build) >> /tmp/verify.log 2>&1; then
    echo "✓ npm run build passed"
  else
    echo "✗ npm run build failed"
    exit_code=1
  fi
  
  echo "=== Running Frontend Lint ==="
  if (cd "$REPO_ROOT/web" && npm run lint) >> /tmp/verify.log 2>&1; then
    echo "✓ npm run lint passed"
  else
    echo "✗ npm run lint failed"
    exit_code=1
  fi
  
  echo "=== Running Pipeline Lint ==="
  if (cd "$REPO_ROOT/pipeline" && ruff check .) >> /tmp/verify.log 2>&1; then
    echo "✓ ruff check passed"
  else
    echo "✗ ruff check failed"
    exit_code=1
  fi
  
  echo ""
  echo "=== Git Diff ==="
  git -C "$REPO_ROOT" diff --stat | head -20
  
  return $exit_code
}

if [[ "$VERIFY_ALL" == true ]]; then
  echo "Running full verification suite..."
  rm -f /tmp/verify.log
  run_tests
elif [[ -n "$SPEC_FILE" ]]; then
  echo "Verifying spec: $SPEC_FILE"
  
  # Extract test commands from spec
  tests=$(python3 << PYEOF
import re
with open('$SPEC_FILE') as f:
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

print('\n'.join(tests))
PYEOF
)
  
  local all_passed=true
  while IFS= read -r test_cmd; do
    [[ -z "$test_cmd" ]] && continue
    echo "Running: $test_cmd"
    if (cd "$REPO_ROOT" && eval "$test_cmd") >> /tmp/verify.log 2>&1; then
      echo "✓ PASSED"
    else
      echo "✗ FAILED"
      all_passed=false
    fi
  done <<< "$tests"
  
  if [[ "$all_passed" == true ]]; then
    echo ""
    echo "✓✓✓ All verification checks passed"
    exit 0
  else
    echo ""
    echo "✗✗✗ Some verification checks failed"
    exit 1
  fi
else
  echo "Usage: $0 --spec <file.md> | --all"
  exit 1
fi
