#!/usr/bin/env bash
#
# cursor-verify.sh — Standalone verification script for Cursor delegation results
# Usage: ./scripts/cursor-verify.sh [--spec <file>] [--all] [--quick]
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_FILE=""
VERIFY_ALL=false
QUICK=false
LOG_FILE="/tmp/verify-$(date +%s).log"

# Colors
R='\033[0;31m'
G='\033[0;32m'
Y='\033[1;33m'
B='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${B}[verify]${NC} $(date '+%H:%M:%S') $1"; }
log_ok()    { echo -e "${G}[verify]${NC} $(date '+%H:%M:%S') ✓ $1"; }
log_warn()  { echo -e "${Y}[verify]${NC} $(date '+%H:%M:%S') ⚠ $1"; }
log_err()   { echo -e "${R}[verify]${NC} $(date '+%H:%M:%S') ✗ $1"; }

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --spec) SPEC_FILE="$2"; shift 2 ;;
    --all) VERIFY_ALL=true; shift ;;
    --quick) QUICK=true; shift ;;
    *) break ;;
  esac
done

SUMMARY_PASSED=0
SUMMARY_FAILED=0
SUMMARY_SKIPPED=0

run_check() {
  local name="$1"
  local cmd="$2"
  local skip_quick="${3:-false}"

  if [[ "$QUICK" == true && "$skip_quick" == "true" ]]; then
    log_warn "$name (skipped in quick mode)"
    SUMMARY_SKIPPED=$((SUMMARY_SKIPPED + 1))
    return 0
  fi

  log_info "Running: $name..."
  if (cd "$REPO_ROOT" && eval "$cmd") >> "$LOG_FILE" 2>&1; then
    log_ok "$name passed"
    SUMMARY_PASSED=$((SUMMARY_PASSED + 1))
    return 0
  else
    log_err "$name failed"
    SUMMARY_FAILED=$((SUMMARY_FAILED + 1))
    return 1
  fi
}

print_summary() {
  echo ""
  echo "═══════════════════════════════════════════════════"
  echo "  Verification Summary"
  echo "═══════════════════════════════════════════════════"
  echo -e "  ${G}Passed:${NC}  $SUMMARY_PASSED"
  if [[ $SUMMARY_FAILED -gt 0 ]]; then
    echo -e "  ${R}Failed:${NC}  $SUMMARY_FAILED"
  fi
  if [[ $SUMMARY_SKIPPED -gt 0 ]]; then
    echo -e "  ${Y}Skipped:${NC} $SUMMARY_SKIPPED"
  fi
  echo "  Log:    $LOG_FILE"
  echo "═══════════════════════════════════════════════════"
  if [[ $SUMMARY_FAILED -eq 0 ]]; then
    echo -e "  ${G}All checks passed ✓${NC}"
  else
    echo -e "  ${R}Some checks failed ✗${NC}"
  fi
  echo ""
}

run_tests() {
  local exit_code=0

  run_check "Pipeline Tests" "cd pipeline && .venv/bin/python -m pytest" "false" || exit_code=1
  run_check "Frontend Build" "cd web && npm run build" "true" || exit_code=1
  run_check "Frontend Lint" "cd web && npm run lint" "true" || exit_code=1
  run_check "Pipeline Lint" "cd pipeline && .venv/bin/python -m ruff check ." "false" || exit_code=1

  echo ""
  echo "=== Git Diff ==="
  git -C "$REPO_ROOT" diff --stat | head -20

  print_summary
  return $exit_code
}

if [[ "$VERIFY_ALL" == true ]]; then
  log_info "Running full verification suite..."
  run_tests
elif [[ -n "$SPEC_FILE" ]]; then
  log_info "Verifying spec: $SPEC_FILE"

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

  all_passed=true
  while IFS= read -r test_cmd; do
    [[ -z "$test_cmd" ]] && continue
    log_info "Running: $test_cmd"
    if (cd "$REPO_ROOT" && eval "$test_cmd") >> "$LOG_FILE" 2>&1; then
      log_ok "PASSED"
      SUMMARY_PASSED=$((SUMMARY_PASSED + 1))
    else
      log_err "FAILED"
      all_passed=false
      SUMMARY_FAILED=$((SUMMARY_FAILED + 1))
    fi
  done <<< "$tests"

  print_summary

  if [[ "$all_passed" == true ]]; then
    exit 0
  else
    exit 1
  fi
else
  echo "Usage: $0 --spec <file.md> | --all [--quick]"
  exit 1
fi
