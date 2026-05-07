#!/usr/bin/env bash
#
# self-test.sh — The agent system tests itself
# Verifies: maps are readable, scripts work, rules are valid, skills are loadable
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0

echo "=== Agent System Self-Test ==="
echo ""

# Test 1: Maps are valid JSON
echo "[1/8] Testing map integrity..."
for map in CODEMAP SKILLMAP RULEMAP SEMANTICMAP; do
  file=".agent/maps/${map}.json"
  if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
    echo "  ✓ $map.json is valid JSON"
  else
    echo "  ✗ $map.json is invalid JSON"
    ERRORS=$((ERRORS + 1))
  fi
done

# Test 2: CODEMAP has required sections
echo ""
echo "[2/8] Testing CODEMAP structure..."
python3 << 'PYEOF'
import json
with open('.agent/maps/CODEMAP.json') as f:
    cm = json.load(f)

required = ['pipeline', 'web', 'database', 'deployment']
for section in required:
    if section in cm:
        print(f"  ✓ Section '{section}' present")
    else:
        print(f"  ✗ Section '{section}' missing")
        exit(1)

if cm['meta']['total_files'] > 0:
    print(f"  ✓ {cm['meta']['total_files']} files mapped")
else:
    print(f"  ✗ No files mapped")
    exit(1)
PYEOF

# Test 3: Scripts are executable
echo ""
echo "[3/8] Testing script executability..."
for script in .agent/scripts/*.sh scripts/*.sh; do
  if [[ -x "$script" ]]; then
    echo "  ✓ $(basename $script) is executable"
  else
    echo "  ✗ $(basename $script) is not executable"
    ERRORS=$((ERRORS + 1))
  fi
done

# Test 4: Rules are valid .mdc
echo ""
echo "[4/8] Testing rule validity..."
for rule in .cursor/rules/*.mdc; do
  if grep -q "^---" "$rule"; then
    echo "  ✓ $(basename $rule) has frontmatter"
  else
    echo "  ✗ $(basename $rule) missing frontmatter"
    ERRORS=$((ERRORS + 1))
  fi
done

# Test 5: Skills are valid SKILL.md
echo ""
echo "[5/8] Testing skill validity..."
for skill_dir in .cursor/skills/* .kimi/skills/*; do
  if [[ -d "$skill_dir" ]]; then
    skill_file="$skill_dir/SKILL.md"
    if [[ -f "$skill_file" ]]; then
      if grep -q "^---" "$skill_file"; then
        echo "  ✓ $(basename $skill_dir)/SKILL.md has frontmatter"
      else
        echo "  ✗ $(basename $skill_dir)/SKILL.md missing frontmatter"
        ERRORS=$((ERRORS + 1))
      fi
    fi
  fi
done

# Test 6: Git hooks are executable
echo ""
echo "[6/8] Testing git hooks..."
for hook in post-commit post-merge pre-commit; do
  if [[ -x ".git/hooks/$hook" ]]; then
    echo "  ✓ $hook hook is executable"
  else
    echo "  ✗ $hook hook missing or not executable"
    ERRORS=$((ERRORS + 1))
  fi
done

# Test 7: Can regenerate maps
echo ""
echo "[7/8] Testing map regeneration..."
if ./.agent/scripts/regenerate-maps.sh self-test >/dev/null 2>&1; then
  echo "  ✓ Map regeneration works"
else
  echo "  ✗ Map regeneration failed"
  ERRORS=$((ERRORS + 1))
fi

# Test 8: Predictive loader works
echo ""
echo "[8/8] Testing predictive loader..."
if ./.agent/scripts/predictive-loader.sh "build signal" >/dev/null 2>&1; then
  echo "  ✓ Predictive loader works"
else
  echo "  ✗ Predictive loader failed"
  ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=== Self-Test Complete ==="
if [[ $ERRORS -eq 0 ]]; then
  echo "✓✓✓ All system components healthy"
  exit 0
else
  echo "✗ $ERRORS component(s) failed"
  exit 1
fi
