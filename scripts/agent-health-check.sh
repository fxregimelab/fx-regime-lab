#!/usr/bin/env bash
#
# agent-health-check.sh — Verify the entire agent system is healthy
# Usage: ./scripts/agent-health-check.sh
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0
WARNINGS=0

check_pass() { echo "  ✓ $1"; }
check_fail() { echo "  ✗ $1"; ERRORS=$((ERRORS + 1)); }
check_warn() { echo "  ⚠ $1"; WARNINGS=$((WARNINGS + 1)); }

echo "=== Agent Health Check ==="
echo "Repo: $REPO_ROOT"
echo ""

# 1. Core files exist
echo "1. Core Configuration"
[[ -f "AGENTS.md" ]] && check_pass "AGENTS.md exists" || check_warn "AGENTS.md missing (expected at workspace root)"
[[ -f "../AGENTS.md" ]] && check_pass "Workspace AGENTS.md exists" || check_warn "Workspace AGENTS.md missing"
[[ -f ".cursorrules" ]] && check_pass ".cursorrules exists" || check_fail ".cursorrules missing"
[[ -f ".agent/index.json" ]] && check_pass ".agent/index.json exists" || check_fail ".agent/index.json missing"
[[ -f ".agent/maps/CODEMAP.json" ]] && check_pass "CODEMAP.json exists" || check_fail "CODEMAP.json missing"
[[ -f ".agent/maps/SKILLMAP.json" ]] && check_pass "SKILLMAP.json exists" || check_fail "SKILLMAP.json missing"
[[ -f ".agent/maps/RULEMAP.json" ]] && check_pass "RULEMAP.json exists" || check_fail "RULEMAP.json missing"
[[ -f ".agent/context/HOTFILES.md" ]] && check_pass "HOTFILES.md exists" || check_fail "HOTFILES.md missing"

echo ""
echo "2. Maps Freshness"
for map in CODEMAP SKILLMAP RULEMAP; do
  if [[ -f ".agent/maps/${map}.json" ]]; then
    age=$(( $(date +%s) - $(stat -c %Y ".agent/maps/${map}.json") ))
    if [[ $age -lt 3600 ]]; then
      check_pass "${map}.json is fresh (< 1h old)"
    elif [[ $age -lt 86400 ]]; then
      check_warn "${map}.json is stale ($((age/3600))h old) — run regenerate-maps"
    else
      check_fail "${map}.json is very stale ($((age/86400))d old) — run regenerate-maps"
    fi
  fi
done

echo ""
echo "3. Git Hooks"
[[ -f ".git/hooks/post-commit" ]] && check_pass "post-commit hook exists" || check_warn "post-commit hook missing"
[[ -f ".git/hooks/post-merge" ]] && check_pass "post-merge hook exists" || check_warn "post-merge hook missing"
[[ -f ".git/hooks/pre-commit" ]] && check_pass "pre-commit hook exists" || check_warn "pre-commit hook missing"

echo ""
echo "4. Scripts Executable"
for script in scripts/cursor-delegate.sh scripts/cursor-verify.sh scripts/cursor-warmup.sh scripts/kimi-cursor-orchestrator.sh .agent/scripts/regenerate-maps.sh .agent/scripts/file-watcher.sh; do
  if [[ -x "$script" ]]; then
    check_pass "$script is executable"
  else
    check_warn "$script is not executable (run chmod +x)"
  fi
done

echo ""
echo "5. Dependencies"
command -v agent >/dev/null 2>&1 && check_pass "Cursor agent CLI installed" || check_fail "Cursor agent CLI not found"
command -v jq >/dev/null 2>&1 && check_pass "jq installed" || check_warn "jq not installed (optional)"
command -v inotifywait >/dev/null 2>&1 && check_pass "inotify-tools installed" || check_warn "inotify-tools not installed (optional)"

echo ""
echo "6. Test Suite"
if (cd pipeline && pytest -q --tb=line >/dev/null 2>&1); then
  check_pass "pytest passes"
else
  check_fail "pytest fails"
fi

echo ""
echo "=== Health Check Complete ==="
echo "Errors: $ERRORS | Warnings: $WARNINGS"

if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
  echo "✓✓✓ System is healthy (10/10)"
elif [[ $ERRORS -eq 0 ]]; then
  echo "✓ System is functional but has warnings"
else
  echo "✗ System has errors — fix before delegating"
fi

exit $ERRORS
