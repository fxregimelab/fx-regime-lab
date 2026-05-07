#!/usr/bin/env bash
#
# spec-validator.sh — Validate an Implementation Spec before delegation
# Checks: files exist, tests defined, acceptance criteria present, no banned commands
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC="${1:-}"

if [[ -z "$SPEC" ]]; then
  echo "Usage: $0 <spec.md>"
  exit 1
fi

if [[ ! -f "$SPEC" ]]; then
  echo "✗ Spec file not found: $SPEC"
  exit 1
fi

cd "$REPO_ROOT"

ERRORS=0
WARNINGS=0

check_pass() { echo "  ✓ $1"; }
check_fail() { echo "  ✗ $1"; ERRORS=$((ERRORS + 1)); }
check_warn() { echo "  ⚠ $1"; WARNINGS=$((WARNINGS + 1)); }

echo "=== Spec Validator ==="
echo "Spec: $SPEC"
echo ""

# Check required sections
echo "1. Required Sections"
grep -q "^# Implementation Spec:" "$SPEC" && check_pass "Has Implementation Spec header" || check_fail "Missing Implementation Spec header"
grep -q "^## Context" "$SPEC" && check_pass "Has Context section" || check_fail "Missing Context section"
grep -q "^## Files" "$SPEC" && check_pass "Has Files section" || check_fail "Missing Files section"
grep -q "^## Technical Requirements" "$SPEC" && check_pass "Has Technical Requirements" || check_warn "Missing Technical Requirements"
grep -q "^## Acceptance Criteria" "$SPEC" && check_pass "Has Acceptance Criteria" || check_fail "Missing Acceptance Criteria"
grep -q "^## Execution Plan" "$SPEC" && check_pass "Has Execution Plan" || check_warn "Missing Execution Plan"

# Check for banned commands
echo ""
echo "2. Safety Checks"
if grep -qiE "rm -rf|git push --force|git reset --hard|supabase db reset" "$SPEC"; then
  check_fail "Contains banned commands (rm -rf, git push --force, etc.)"
else
  check_pass "No banned commands"
fi

if grep -qiE "hardcode.*key|hardcode.*secret|API_KEY|password" "$SPEC"; then
  check_warn "May contain hardcoded secrets reference"
else
  check_pass "No hardcoded secrets"
fi

# Validate files section
echo ""
echo "3. File Validation"
python3 << PYEOF
import re, os

with open('$SPEC') as f:
    content = f.read()

# Extract files section
files_match = re.search(r'## Files\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
if files_match:
    files_text = files_match.group(1)
    for line in files_text.split('\n'):
        line = line.strip()
        if line.startswith('- CREATE:'):
            path = line.replace('- CREATE:', '').strip().strip('\`')
            if os.path.exists(path):
                print(f"  ⚠ CREATE file already exists: {path}")
            else:
                print(f"  ✓ CREATE file will be created: {path}")
        elif line.startswith('- MODIFY:'):
            path = line.replace('- MODIFY:', '').strip().strip('\`')
            if os.path.exists(path):
                print(f"  ✓ MODIFY file exists: {path}")
            else:
                print(f"  ✗ MODIFY file NOT FOUND: {path}")
        elif line.startswith('- DELETE:'):
            path = line.replace('- DELETE:', '').strip().strip('\`')
            if os.path.exists(path):
                print(f"  ✓ DELETE file exists: {path}")
            else:
                print(f"  ⚠ DELETE file already gone: {path}")

# Check for test commands
if 'pytest' in content or 'npm run build' in content or 'npm run lint' in content or 'ruff check' in content:
    print("  ✓ Test commands found in spec")
else:
    print("  ✗ No test commands found (pytest, npm run build, etc.)")

# Check acceptance criteria count
criteria = re.findall(r'- \[ \]', content)
if len(criteria) >= 2:
    print(f"  ✓ {len(criteria)} acceptance criteria defined")
else:
    print(f"  ⚠ Only {len(criteria)} acceptance criteria (recommend >= 2)")
PYEOF

echo ""
echo "=== Validation Complete ==="
if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
  echo "✓✓✓ Spec is valid and safe"
elif [[ $ERRORS -eq 0 ]]; then
  echo "✓ Spec is valid with warnings"
else
  echo "✗ Spec has errors — fix before delegating"
fi

exit $ERRORS
