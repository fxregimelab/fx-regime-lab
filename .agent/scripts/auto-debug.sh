#!/usr/bin/env bash
#
# auto-debug.sh — Automatic error parsing and fix spec generation
# Usage: ./.agent/scripts/auto-debug.sh <spec-file> <verify-log-file> <attempt-number>
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC="${1:-}"
VERIFY_LOG="${2:-}"
ATTEMPT="${3:-1}"

if [[ -z "$SPEC" || -z "$VERIFY_LOG" ]]; then
  echo "Usage: $0 <spec.md> <verify.log> [attempt]"
  exit 1
fi

cd "$REPO_ROOT"

BASENAME=$(basename "$SPEC" .md)
FIX_SPEC=".agent/worktrees/${BASENAME}-fix-${ATTEMPT}.md"
mkdir -p "$(dirname "$FIX_SPEC")"

echo "=== Auto-Debug ==="
echo "Original spec: $SPEC"
echo "Verify log: $VERIFY_LOG"
echo "Attempt: $ATTEMPT"
echo ""

# Extract errors from verify log
ERRORS=$(grep -E "FAILED|Error|error:|Traceback|AssertionError|SyntaxError|TypeError|NameError|ImportError" "$VERIFY_LOG" | head -30 || true)

echo "Errors found:"
echo "$ERRORS"
echo ""

# Get git diff
GIT_DIFF=$(git diff --stat 2>/dev/null || true)
GIT_DIFF_FULL=$(git diff 2>/dev/null | head -100 || true)

# Get current test output
TEST_OUTPUT=$(tail -n 50 "$VERIFY_LOG" 2>/dev/null || true)

# Generate fix spec
cat > "$FIX_SPEC" << EOF
# Fix Spec: ${BASENAME} (Auto-Generated, Attempt ${ATTEMPT})

## Original Spec
See: ${SPEC}

## Errors Detected
\`\`\`
${ERRORS}
\`\`\`

## Test Output (last 50 lines)
\`\`\`
${TEST_OUTPUT}
\`\`\`

## Current Git Diff (summary)
\`\`\`
${GIT_DIFF}
\`\`\`

## Root Cause Analysis
[Auto-generated based on error patterns]
EOF

# Auto-detect error type and append targeted fix
python3 << PYEOF
import re

errors = """${ERRORS}"""
verify_log = """${TEST_OUTPUT}"""

fix_spec_path = "$FIX_SPEC"

with open(fix_spec_path, 'a') as f:
    f.write("\n## Detected Error Types\n")
    
    error_types = []
    
    if 'SyntaxError' in errors or 'IndentationError' in errors:
        error_types.append("SYNTAX — Python syntax error. Check indentation, colons, quotes.")
    if 'ImportError' in errors or 'ModuleNotFoundError' in errors:
        error_types.append("IMPORT — Missing import or module. Check imports and dependencies.")
    if 'TypeError' in errors:
        error_types.append("TYPE — Type mismatch. Check function signatures and type annotations.")
    if 'NameError' in errors:
        error_types.append("NAME — Undefined variable. Check variable names and scope.")
    if 'AssertionError' in errors or 'FAILED' in errors:
        error_types.append("ASSERTION — Test failure. Check logic against expected output.")
    if 'npm run build' in verify_log and ('error' in verify_log.lower() or 'failed' in verify_log.lower()):
        error_types.append("BUILD — Next.js build failure. Check TypeScript errors and imports.")
    if 'ruff check' in verify_log and 'failed' in verify_log.lower():
        error_types.append("LINT — Python lint error. Check formatting and imports.")
    if 'mypy' in verify_log and 'failed' in verify_log.lower():
        error_types.append("TYPECHECK — mypy error. Check type annotations.")
    
    if not error_types:
        error_types.append("UNKNOWN — Manual analysis required.")
    
    for et in error_types:
        f.write(f"- {et}\n")
    
    f.write("\n## Fix Strategy\n")
    if "SYNTAX" in str(error_types):
        f.write("1. Re-read the file where SyntaxError occurred\n")
        f.write("2. Fix indentation, missing colons, or mismatched quotes\n")
        f.write("3. Run `python -m py_compile <file>` to verify\n")
    if "IMPORT" in str(error_types):
        f.write("1. Check that all imports exist and are correct\n")
        f.write("2. Verify module paths match the actual file structure\n")
        f.write("3. Add missing __init__.py if needed\n")
    if "TYPE" in str(error_types):
        f.write("1. Check function signatures match call sites\n")
        f.write("2. Verify type annotations are correct\n")
        f.write("3. Ensure `from __future__ import annotations` is present\n")
    if "ASSERTION" in str(error_types):
        f.write("1. Read the failing test to understand expected behavior\n")
        f.write("2. Compare expected vs actual output\n")
        f.write("3. Fix the implementation, not the test (unless test is wrong)\n")
    if "BUILD" in str(error_types):
        f.write("1. Run `cd web && npm run build` to see full error\n")
        f.write("2. Check TypeScript types and imports\n")
        f.write("3. Verify all referenced files exist\n")
    
    f.write("\n## Files to Modify\n")
    f.write("[List only files that need fixing based on error locations]\n")
    
    f.write("\n## Acceptance Criteria\n")
    f.write("- [ ] All previously failing tests now pass\n")
    f.write("- [ ] No new test failures introduced\n")
    f.write("- [ ] Git diff is minimal and focused\n")
    
    f.write("\n## Execution Plan\n")
    f.write("1. Analyze error messages carefully\n")
    f.write("2. Identify root cause\n")
    f.write("3. Apply minimal fix\n")
    f.write("4. Run tests to verify\n")

print(f"Fix spec generated: {fix_spec_path}")
PYEOF

echo ""
echo "Fix spec: $FIX_SPEC"
echo ""
echo "To re-delegate with fix:"
echo "  ./scripts/cursor-delegate.sh --spec $FIX_SPEC --yolo"
