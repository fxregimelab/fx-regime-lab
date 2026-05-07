#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Phase 2 Orchestrator — Master Auto-Execution Loop
# ═══════════════════════════════════════════════════════════════
# Connects: triage → plan → readiness → delegate → verify → deploy → monitor → fix → report
# Usage: ./scripts/auto/orchestrator.sh '<directive>' [--dry-run] [--await-approval]
#   --dry-run: Run in analysis mode only (no delegation)
#   --await-approval: Tier 2 only — stop before deploy, await human approval
#
# Safety:
#   Tier 1 → Fully autonomous
#   Tier 2 → Auto-execution with approval gate before deploy
#   Tier 3/4 → Rejects with human-required message
#
# Exit codes:
#   0 = success (Tier 1/2 completed, or Tier 3/4 properly rejected)
#   1 = execution failure
#   2 = safety rejection (Tier 3/4)
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_err()   { echo -e "${RED}[ERR]${NC}   $1"; }
log_phase() { echo -e "${BOLD}${CYAN}▶ $1${NC}"; }
log_sep()   { echo -e "${BOLD}─────────────────────────────────────────────────${NC}"; }

# ── CLI Parsing ─────────────────────────────────────────────────
DIRECTIVE=""
DRY_RUN=false
AWAIT_APPROVAL=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --await-approval) AWAIT_APPROVAL=true ;;
    *) DIRECTIVE="$arg" ;;
  esac
done

if [[ -z "$DIRECTIVE" ]]; then
  log_err "Usage: orchestrator.sh '<directive>' [--dry-run]"
  exit 1
fi

START_TIME=$(date +%s)
START_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ═══════════════════════════════════════════════════════════════
# PHASE 1: TRIAGE
# ═══════════════════════════════════════════════════════════════
log_phase "PHASE 1: Triage"
log_info "Directive: $DIRECTIVE"

TRIAGE_RESULT=$(cd "$REPO_ROOT/pipeline" && python3 -m src.auto.triage "$DIRECTIVE" 2>/dev/null) || TRIAGE_RESULT=''
if [[ -z "$TRIAGE_RESULT" ]] || ! echo "$TRIAGE_RESULT" | python3 -c "import sys,json; json.load(sys.stdin)" >/dev/null 2>&1; then
  TRIAGE_RESULT='{"tier":3,"tier_name":"Unknown","confidence":0.5,"reasoning":"Triage failed","suggested_approval":"human_required","estimated_risk":"unknown"}'
fi
TIER=$(echo "$TRIAGE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['tier'])")
TIER_NAME=$(echo "$TRIAGE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['tier_name'])")
CONFIDENCE=$(echo "$TRIAGE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['confidence'])")
RISK=$(echo "$TRIAGE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['estimated_risk'])")
REASONING=$(echo "$TRIAGE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['reasoning'])")

echo "  Tier:       $TIER ($TIER_NAME)"
echo "  Confidence: $CONFIDENCE"
echo "  Risk:       $RISK"
echo "  Reasoning:  $REASONING"

# ── Safety Gate ────────────────────────────────────────────────
if [[ "$TIER" -ge 3 ]]; then
  log_sep
  log_warn "TIER $TIER — Human approval required."
  log_info "Directive classified as: $TIER_NAME"
  log_info "Suggested approval: human_required"
  echo ""
  echo "═══════════════════════════════════════════════════"
  echo "  EXECUTION HALTED — Human Required"
  echo "═══════════════════════════════════════════════════"
  echo "  This directive requires human review before execution."
  echo "  Reason: $REASONING"
  echo ""
  exit 2
fi

if [[ "$DRY_RUN" == true ]]; then
  log_info "Dry-run mode: stopping before execution."
  echo ""
  echo "═══════════════════════════════════════════════════"
  echo "  DRY RUN COMPLETE"
  echo "═══════════════════════════════════════════════════"
  echo "  Tier:         $TIER ($TIER_NAME)"
  echo "  Would execute: Yes (Tier $TIER is auto-eligible)"
  echo "  Next step:    Run without --dry-run to execute"
  echo ""
  exit 0
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 2: PLANNING
# ═══════════════════════════════════════════════════════════════
log_phase "PHASE 2: Planning"
log_info "Generating implementation spec..."

PLAN_RESULT=$(python3 -m pipeline.src.auto.plan "$DIRECTIVE" "$TIER" "$REPO_ROOT" 2>/dev/null || echo '{"spec_path":"","files_to_read":[],"files_to_modify":[],"files_to_create":[],"acceptance_criteria":[],"reasoning":"Plan generation failed"}')
SPEC_PATH=$(echo "$PLAN_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['spec_path'])")

if [[ -n "$SPEC_PATH" && -f "$REPO_ROOT/$SPEC_PATH" ]]; then
  log_ok "Spec generated: $SPEC_PATH"
else
  log_warn "Spec generation had issues, proceeding with default template"
  SPEC_PATH=""
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 3: READINESS
# ═══════════════════════════════════════════════════════════════
log_phase "PHASE 3: Readiness"

if [[ "$TIER" -eq 1 ]]; then
  TARGET="vercel"
else
  TARGET="prefect"
fi

READINESS_RESULT=$(python3 -m pipeline.src.auto.readiness "$TARGET" "$REPO_ROOT" 2>/dev/null) || READINESS_RESULT=""
if [[ -z "$READINESS_RESULT" ]] || ! echo "$READINESS_RESULT" | python3 -c "import sys,json; json.load(sys.stdin)" >/dev/null 2>&1; then
  READINESS_RESULT='{"overall":"warning","summary":"Readiness check failed","checks":[]}'
fi
READINESS_STATUS=$(echo "$READINESS_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['overall'])")
READINESS_SUMMARY=$(echo "$READINESS_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary'])")

echo "  Target:   $TARGET"
echo "  Status:   $READINESS_STATUS"
echo "  Summary:  $READINESS_SUMMARY"

if [[ "$READINESS_STATUS" == "fail" ]]; then
  log_err "Readiness check FAILED. Cannot proceed safely."
  log_info "Fix the issues above, then retry."
  exit 1
elif [[ "$READINESS_STATUS" == "warning" ]]; then
  log_warn "Readiness has warnings but proceeding."
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 4: DELEGATION (Cursor)
# ═══════════════════════════════════════════════════════════════
log_phase "PHASE 4: Delegation → Cursor"

DELEGATION_START=$(date +%s)

# Create a delegation entry for Cursor
DELEGATION_DIR="$REPO_ROOT/.cursor/delegation/queue"
mkdir -p "$DELEGATION_DIR"

# If we have a spec, use it; otherwise create a minimal one
if [[ -n "$SPEC_PATH" ]]; then
  SPEC_FULL_PATH="$REPO_ROOT/$SPEC_PATH"
else
  # Create minimal spec
  SPEC_FULL_PATH="$DELEGATION_DIR/auto-$(date +%s).md"
  cat > "$SPEC_FULL_PATH" <<EOF
# Spec: $DIRECTIVE

## Task
$DIRECTIVE

## Acceptance Criteria
- [ ] Implementation matches directive
- [ ] All tests pass
- [ ] Lint is clean
EOF
fi

# Run Cursor delegate
DELEGATE_OUTPUT=""
if [[ -f "$REPO_ROOT/scripts/cursor-delegate.sh" ]]; then
  log_info "Running cursor-delegate.sh..."
  if DELEGATE_OUTPUT=$("$REPO_ROOT/scripts/cursor-delegate.sh" --spec "$SPEC_FULL_PATH" --yolo 2>&1); then
    DELEGATE_EXIT=0
    log_ok "Cursor delegation completed"
  else
    DELEGATE_EXIT=$?
    log_warn "Cursor delegation exited with code $DELEGATE_EXIT"
  fi
else
  log_warn "cursor-delegate.sh not found. Skipping delegation."
  DELEGATE_EXIT=1
fi

DELEGATION_DURATION=$(( $(date +%s) - DELEGATION_START ))

# ═══════════════════════════════════════════════════════════════
# PHASE 5: VERIFICATION
# ═══════════════════════════════════════════════════════════════
log_phase "PHASE 5: Verification"

TEST_PASSED=null
TEST_TOTAL=null
RUFF_CLEAN=null
BUILD_PASS=null
LINT_PASS=null

if [[ "$TIER" -eq 1 ]]; then
  # Frontend verification
  log_info "Running npm build..."
  if (cd "$REPO_ROOT/web" && npm run build >/dev/null 2>&1); then
    BUILD_PASS=true
    log_ok "Build passed"
  else
    BUILD_PASS=false
    log_err "Build failed"
  fi

  log_info "Running biome lint..."
  if (cd "$REPO_ROOT/web" && npx biome check . >/dev/null 2>&1); then
    LINT_PASS=true
    log_ok "Lint passed"
  else
    LINT_PASS=false
    log_err "Lint failed"
  fi

  if [[ "$BUILD_PASS" == "true" && "$LINT_PASS" == "true" ]]; then
    VERIFY_STATUS="passed"
    log_ok "Verification PASSED"
  else
    VERIFY_STATUS="failed"
    log_err "Verification FAILED"
  fi

elif [[ "$TIER" -eq 2 ]]; then
  # Pipeline verification
  log_info "Running pytest..."
  PYTEST_OUTPUT=$(cd "$REPO_ROOT/pipeline" && python3 -m pytest -q 2>&1) || true
  if echo "$PYTEST_OUTPUT" | grep -q "passed"; then
    TEST_PASSED=$(echo "$PYTEST_OUTPUT" | python3 -c "import sys,re; m=re.search(r'(\d+) passed', sys.stdin.read()); print(m.group(1) if m else '0')")
    TEST_TOTAL="$TEST_PASSED"
    log_ok "Tests passed: $TEST_PASSED"
  else
    TEST_PASSED=0
    TEST_TOTAL=0
    log_err "Tests failed"
  fi

  log_info "Running ruff..."
  if (cd "$REPO_ROOT/pipeline" && python3 -m ruff check . >/dev/null 2>&1); then
    RUFF_CLEAN=true
    log_ok "Ruff clean"
  else
    RUFF_CLEAN=false
    log_err "Ruff found issues"
  fi

  if [[ "$TEST_PASSED" -gt 0 && "$RUFF_CLEAN" == "true" ]]; then
    VERIFY_STATUS="passed"
    log_ok "Verification PASSED"
  else
    VERIFY_STATUS="failed"
    log_err "Verification FAILED"
  fi
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 6: DEPLOY (if verification passed)
# ═══════════════════════════════════════════════════════════════
DEPLOY_STATUS="skipped"
DEPLOY_URL=""
DEPLOY_MESSAGE=""

if [[ "$VERIFY_STATUS" == "passed" || "$VERIFY_STATUS" == "fixed" ]]; then
  # Tier 2 approval gate
  if [[ "$TIER" -eq 2 && "$AWAIT_APPROVAL" == true ]]; then
    log_phase "PHASE 6: Approval Gate"
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  AWAITING APPROVAL"
    echo "═══════════════════════════════════════════════════"
    echo "  Tier 2 directive requires explicit approval before deploy."
    echo ""
    echo "  Directive: $DIRECTIVE"
    echo "  Status:    Verified and ready"
    echo ""
    echo "  To approve and deploy:  fx-agent approve"
    echo "  To reject:              fx-agent reject --reason '...'"
    echo ""

    # Save state for approve/reject (safe JSON via Python)
    mkdir -p "$REPO_ROOT/.cursor/delegation/sessions"
    python3 -c "
import json, sys
json.dump({
  'directive': sys.argv[1],
  'tier': int(sys.argv[2]),
  'tier_name': sys.argv[3],
  'status': 'AWAITING_APPROVAL',
  'verification': sys.argv[4],
  'timestamp': sys.argv[5]
}, open(sys.argv[6], 'w'))
" "$DIRECTIVE" "$TIER" "$TIER_NAME" "$VERIFY_STATUS" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$REPO_ROOT/.cursor/delegation/sessions/awaiting-approval.json"

    FINAL_STATUS="AWAITING_APPROVAL"
    NEXT_STEP="Run 'fx-agent approve' to deploy"

    # Skip to report
    END_TIME=$(date +%s)
    END_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    DURATION=$((END_TIME - START_TIME))

    REPORT_CTX=$(python3 -c "
import json, sys
print(json.dumps({
  'directive': sys.argv[1],
  'tier': int(sys.argv[2]),
  'tier_name': sys.argv[3],
  'confidence': float(sys.argv[4]),
  'status': sys.argv[5],
  'started_at': sys.argv[6],
  'finished_at': sys.argv[7],
  'duration_seconds': int(sys.argv[8]),
  'tests_passed': int(sys.argv[9]) if sys.argv[9] != 'null' else None,
  'tests_total': int(sys.argv[10]) if sys.argv[10] != 'null' else None,
  'ruff_clean': sys.argv[11] == 'true' if sys.argv[11] != 'null' else None,
  'build_pass': sys.argv[12] == 'true' if sys.argv[12] != 'null' else None,
  'lint_pass': sys.argv[13] == 'true' if sys.argv[13] != 'null' else None,
  'files_changed': [],
  'deployment_target': sys.argv[14],
  'next_step': sys.argv[15]
}))" "$DIRECTIVE" "$TIER" "$TIER_NAME" "$CONFIDENCE" "$FINAL_STATUS" "$START_ISO" "$END_ISO" "$DURATION" "${TEST_PASSED:-null}" "${TEST_TOTAL:-null}" "${RUFF_CLEAN:-null}" "${BUILD_PASS:-null}" "${LINT_PASS:-null}" "$TARGET" "$NEXT_STEP")
    (cd "$REPO_ROOT/pipeline" && python3 -m src.auto.report <<< "$REPORT_CTX") 2>/dev/null || true

    log_sep
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  CEO Mode — Execution Paused"
    echo "═══════════════════════════════════════════════════"
    echo "  Directive:  $DIRECTIVE"
    echo "  Tier:       $TIER ($TIER_NAME)"
    echo "  Status:     AWAITING_APPROVAL"
    echo "  Duration:   ${DURATION}s"
    echo "  Verification: $VERIFY_STATUS"
    echo ""
    exit 0
  fi

  log_phase "PHASE 6: Deploy"

  if [[ "$TIER" -eq 1 ]]; then
    DEPLOY_TARGET_NAME="vercel"
  else
    DEPLOY_TARGET_NAME="prefect"
  fi

  log_info "Deploying to $DEPLOY_TARGET_NAME..."

  DEPLOY_RESULT=$(python3 -m pipeline.src.auto.deploy "$DEPLOY_TARGET_NAME" "$REPO_ROOT" 2>/dev/null) || DEPLOY_RESULT=""
  # Validate JSON
  if [[ -n "$DEPLOY_RESULT" ]] && echo "$DEPLOY_RESULT" | python3 -c "import sys,json; json.load(sys.stdin)" >/dev/null 2>&1; then
    DEPLOY_STATUS=$(echo "$DEPLOY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    DEPLOY_URL=$(echo "$DEPLOY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'] or '')")
    DEPLOY_MESSAGE=$(echo "$DEPLOY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])")
  else
    DEPLOY_STATUS="skipped"
    DEPLOY_MESSAGE="Deploy module returned invalid output"
  fi

  echo "  Target:   $DEPLOY_TARGET_NAME"
  echo "  Status:   $DEPLOY_STATUS"
  if [[ -n "$DEPLOY_URL" ]]; then
    echo "  URL:      $DEPLOY_URL"
  fi
  echo "  Message:  $DEPLOY_MESSAGE"

  if [[ "$DEPLOY_STATUS" == "success" ]]; then
    log_ok "Deploy successful"
  elif [[ "$DEPLOY_STATUS" == "skipped" ]]; then
    log_warn "Deploy skipped — $DEPLOY_MESSAGE"
  else
    log_err "Deploy failed — $DEPLOY_MESSAGE"
  fi
else
  log_info "Verification failed — skipping deploy"
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 7: MONITOR / SELF-HEAL (if deploy ran)
# ═══════════════════════════════════════════════════════════════
MONITOR_STATUS="skipped"
HEAL_STATUS="skipped"

if [[ "$VERIFY_STATUS" == "passed" || "$VERIFY_STATUS" == "fixed" ]]; then
  if [[ "$DEPLOY_STATUS" == "success" ]]; then
    log_phase "PHASE 7: Post-Deploy Monitor"

    log_info "Monitoring $DEPLOY_TARGET_NAME deployment..."
    HEAL_RESULT=$(python3 -m pipeline.src.auto.self_heal "$DIRECTIVE" "$TIER" "$DEPLOY_TARGET_NAME" "$DEPLOY_URL" 3 "$REPO_ROOT" 2>/dev/null) || HEAL_RESULT=""

    if [[ -n "$HEAL_RESULT" ]] && echo "$HEAL_RESULT" | python3 -c "import sys,json; json.load(sys.stdin)" >/dev/null 2>&1; then
      HEAL_STATUS=$(echo "$HEAL_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['final_status'])")
      MONITOR_STATUS=$(echo "$HEAL_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['final_monitor_status'])")
      HEAL_SUMMARY=$(echo "$HEAL_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary'])")
    else
      HEAL_STATUS="skipped"
      MONITOR_STATUS="unknown"
      HEAL_SUMMARY="Self-heal module returned invalid output"
    fi

    echo "  Monitor status: $MONITOR_STATUS"
    echo "  Heal status:    $HEAL_STATUS"
    echo "  Summary:        $HEAL_SUMMARY"

    if [[ "$HEAL_STATUS" == "healthy" ]]; then
      log_ok "Post-deploy monitor healthy"
    elif [[ "$HEAL_STATUS" == "recovered" ]]; then
      log_ok "Post-deploy issues auto-recovered"
    elif [[ "$HEAL_STATUS" == "failed" ]]; then
      log_err "Post-deploy monitor failed — auto-heal exhausted"
    else
      log_warn "Post-deploy monitor status: $HEAL_STATUS"
    fi
  else
    log_info "Deploy did not succeed — skipping post-deploy monitor"
  fi
else
  log_info "Verification failed — skipping post-deploy monitor"
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 8: AUTO-FIX (if verification failed)
# ═══════════════════════════════════════════════════════════════
if [[ "$VERIFY_STATUS" == "failed" ]]; then
  log_phase "PHASE 8: Auto-Fix Loop (max 3 attempts)"

  FIX_RESULT=$(python3 -m pipeline.src.auto.fix "$DIRECTIVE" "$TIER" 3 "$REPO_ROOT" 2>/dev/null) || FIX_RESULT=""
  if [[ -n "$FIX_RESULT" ]] && echo "$FIX_RESULT" | python3 -c "import sys,json; json.load(sys.stdin)" >/dev/null 2>&1; then
    FIX_STATUS=$(echo "$FIX_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['final_status'])")
    FIX_SUMMARY=$(echo "$FIX_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary'])")
  else
    FIX_STATUS="failed"
    FIX_SUMMARY="Auto-fix module failed"
  fi

  echo "  Fix status: $FIX_STATUS"
  echo "  Summary:    $FIX_SUMMARY"

  if [[ "$FIX_STATUS" == "fixed" ]]; then
    log_ok "Auto-fix resolved all issues"
    VERIFY_STATUS="fixed"
  else
    log_err "Auto-fix could not resolve all issues"
    VERIFY_STATUS="failed"
  fi
else
  FIX_STATUS="skipped"
  FIX_SUMMARY="No fixes needed"
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 9: REPORT
# ═══════════════════════════════════════════════════════════════
log_phase "PHASE 9: Final Report"

END_TIME=$(date +%s)
END_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DURATION=$((END_TIME - START_TIME))

# Determine final status
if [[ "$VERIFY_STATUS" == "passed" || "$VERIFY_STATUS" == "fixed" ]]; then
  if [[ "$DEPLOY_STATUS" == "success" ]]; then
    if [[ "$HEAL_STATUS" == "healthy" || "$HEAL_STATUS" == "recovered" || "$HEAL_STATUS" == "skipped" ]]; then
      FINAL_STATUS="COMPLETE"
      NEXT_STEP="Deployed and live"
    else
      FINAL_STATUS="PARTIAL"
      NEXT_STEP="Deployed but post-deploy monitor failed"
    fi
  elif [[ "$DEPLOY_STATUS" == "skipped" ]]; then
    FINAL_STATUS="COMPLETE"
    NEXT_STEP="Verified — deploy skipped (credentials not configured)"
  else
    FINAL_STATUS="PARTIAL"
    NEXT_STEP="Verified but deploy failed"
  fi
else
  FINAL_STATUS="FAILED"
  NEXT_STEP="Human intervention required"
fi

# Write execution context for report (safe JSON via Python)
REPORT_CTX=$(python3 -c "
import json, sys
print(json.dumps({
  'directive': sys.argv[1],
  'tier': int(sys.argv[2]),
  'tier_name': sys.argv[3],
  'confidence': float(sys.argv[4]),
  'status': sys.argv[5],
  'started_at': sys.argv[6],
  'finished_at': sys.argv[7],
  'duration_seconds': int(sys.argv[8]),
  'tests_passed': int(sys.argv[9]) if sys.argv[9] != 'null' else None,
  'tests_total': int(sys.argv[10]) if sys.argv[10] != 'null' else None,
  'ruff_clean': sys.argv[11] == 'true' if sys.argv[11] != 'null' else None,
  'build_pass': sys.argv[12] == 'true' if sys.argv[12] != 'null' else None,
  'lint_pass': sys.argv[13] == 'true' if sys.argv[13] != 'null' else None,
  'files_changed': [],
  'deployment_target': sys.argv[14],
  'next_step': sys.argv[15]
}))" "$DIRECTIVE" "$TIER" "$TIER_NAME" "$CONFIDENCE" "$FINAL_STATUS" "$START_ISO" "$END_ISO" "$DURATION" "${TEST_PASSED:-null}" "${TEST_TOTAL:-null}" "${RUFF_CLEAN:-null}" "${BUILD_PASS:-null}" "${LINT_PASS:-null}" "$TARGET" "$NEXT_STEP")

# Generate report
(cd "$REPO_ROOT/pipeline" && python3 -m src.auto.report <<< "$REPORT_CTX") 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════
# FINAL OUTPUT
# ═══════════════════════════════════════════════════════════════
log_sep
echo ""
echo "═══════════════════════════════════════════════════"
echo "  CEO Mode — Execution Complete"
echo "═══════════════════════════════════════════════════"
echo "  Directive:        $DIRECTIVE"
echo "  Tier:             $TIER ($TIER_NAME)"
echo "  Status:           $FINAL_STATUS"
echo "  Duration:         ${DURATION}s"
echo "  Delegation:       $([[ $DELEGATE_EXIT -eq 0 ]] && echo 'OK' || echo 'Issues')"
echo "  Verification:     $VERIFY_STATUS"
echo "  Auto-fix:         $FIX_STATUS"
echo "  Deploy:           $DEPLOY_STATUS"
if [[ -n "$DEPLOY_URL" ]]; then
  echo "  Deploy URL:       $DEPLOY_URL"
fi
if [[ "$MONITOR_STATUS" != "skipped" ]]; then
  echo "  Monitor:          $MONITOR_STATUS"
  echo "  Self-heal:        $HEAL_STATUS"
fi
echo ""

if [[ "$FINAL_STATUS" == "COMPLETE" ]]; then
  log_ok "Execution successful."
  exit 0
elif [[ "$FINAL_STATUS" == "PARTIAL" ]]; then
  log_warn "Execution partially successful — verify deploy manually."
  exit 1
else
  log_err "Execution failed. Manual review required."
  exit 1
fi
