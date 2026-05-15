#!/usr/bin/env bash
#
# init-agent-system.sh — One-command setup for the entire agent ecosystem
# Run this once after cloning the repo.
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════"
echo "  FX Regime Lab — Agent System Initialization"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. Verify dependencies
echo "[1/7] Checking dependencies..."
MISSING=()

command -v python3 >/dev/null 2>&1 || MISSING+=("python3")
command -v node >/dev/null 2>&1 || MISSING+=("node")
command -v npm >/dev/null 2>&1 || MISSING+=("npm")
command -v agent >/dev/null 2>&1 || MISSING+=("cursor-agent-cli")
command -v git >/dev/null 2>&1 || MISSING+=("git")

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "  ✗ Missing: ${MISSING[*]}"
  echo "  Please install missing dependencies and re-run."
  exit 1
fi
echo "  ✓ All core dependencies present"

# Optional deps
command -v jq >/dev/null 2>&1 && echo "  ✓ jq installed" || echo "  ⚠ jq not installed (optional, recommended)"
command -v inotifywait >/dev/null 2>&1 && echo "  ✓ inotify-tools installed" || echo "  ⚠ inotify-tools not installed (optional)"

# 2. Install project dependencies
echo ""
echo "[2/7] Installing project dependencies..."
(cd pipeline && pip install -e . >/dev/null 2>&1 && echo "  ✓ Pipeline dependencies") || echo "  ⚠ Pipeline install failed (may need manual fix)"
(cd web && npm install >/dev/null 2>&1 && echo "  ✓ Web dependencies") || echo "  ⚠ Web install failed (may need manual fix)"

# 3. Set up git hooks
echo ""
echo "[3/7] Setting up git hooks..."
HOOKS_DIR=".git/hooks"
mkdir -p "$HOOKS_DIR"

cat > "$HOOKS_DIR/post-commit" << 'EOF'
#!/usr/bin/env bash
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
"${REPO_ROOT}/.agent/scripts/regenerate-maps.sh" git-hook &
EOF
chmod +x "$HOOKS_DIR/post-commit"
echo "  ✓ post-commit hook"

cat > "$HOOKS_DIR/post-merge" << 'EOF'
#!/usr/bin/env bash
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
"${REPO_ROOT}/.agent/scripts/regenerate-maps.sh" git-hook &
EOF
chmod +x "$HOOKS_DIR/post-merge"
echo "  ✓ post-merge hook"

cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../.."
if git diff --cached --name-only | grep -qE '^pipeline/|^web/'; then
  echo "[pre-commit] Running tests..."
  if git diff --cached --name-only | grep -q '^pipeline/'; then
    cd pipeline && pytest -q --tb=short || { echo "✗ pytest failed"; exit 1; }
    cd ..
  fi
  if git diff --cached --name-only | grep -q '^web/'; then
    cd web && npm run build 2>/dev/null || { echo "✗ npm build failed"; exit 1; }
    cd ..
  fi
fi
EOF
chmod +x "$HOOKS_DIR/pre-commit"
echo "  ✓ pre-commit hook"

# 4. Make all scripts executable
echo ""
echo "[4/7] Making scripts executable..."
chmod +x scripts/*.sh .agent/scripts/*.sh 2>/dev/null || true
echo "  ✓ Scripts ready"

# 5. Generate initial maps
echo ""
echo "[5/7] Generating initial agent maps..."
./.agent/scripts/regenerate-maps.sh init
echo "  ✓ Maps generated"

# 6. Health check
echo ""
echo "[6/7] Running health check..."
./scripts/agent-health-check.sh || true

# 7. Start file watcher
echo ""
echo "[7/7] Starting background file watcher..."
./.agent/scripts/file-watcher.sh start || echo "  ⚠ Watcher start failed (optional)"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Initialization Complete"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Quick start:"
echo "  ./scripts/agent-health-check.sh     # Verify system"
echo "  ./.agent/scripts/file-watcher.sh status  # Check watcher"
echo "  cat .agent/index.json               # Read manifest"
echo ""
echo "Kimi workflow:"
echo "  1. Read .agent/index.json"
echo "  2. Read .agent/maps/CODEMAP.json"
echo "  3. Write spec → delegate to Cursor"
echo ""
echo "Cursor workflow:"
echo "  1. Read .cursorrules"
echo "  2. Read Implementation Spec"
echo "  3. Execute → run tests → report"
echo ""
