#!/usr/bin/env bash
#
# predict-failures.sh — Analyze a spec BEFORE delegation and predict failure modes
# Usage: ./.agent/scripts/predict-failures.sh <spec.md>
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC="${1:-}"

if [[ -z "$SPEC" || ! -f "$SPEC" ]]; then
  echo "Usage: $0 <spec.md>"
  exit 1
fi

cd "$REPO_ROOT"

echo "=== Predictive Failure Detection ==="
echo "Analyzing: $SPEC"
echo ""

python3 << PYEOF
import json, os, re

with open('$SPEC') as f:
    spec = f.read()

with open('.agent/learning/patterns.json') as f:
    patterns = json.load(f)

predictions = []
confidence = 0

# Check 1: Spec length
lines = spec.count('\n')
if lines < 20:
    predictions.append({"risk": "HIGH", "reason": "Spec is very short (<20 lines). Cursor may not have enough context.", "fix": "Add more detail to Context, Technical Requirements, and Execution Plan."})
    confidence += 30

# Check 2: Files listed
files_section = re.search(r'## Files\s*\n(.*?)(?=\n##|\Z)', spec, re.DOTALL)
if files_section:
    files_text = files_section.group(1)
    create_count = files_text.count('CREATE:')
    modify_count = files_text.count('MODIFY:')
    
    if create_count == 0 and modify_count == 0:
        predictions.append({"risk": "HIGH", "reason": "No files listed in spec.", "fix": "Add CREATE/MODIFY/DELETE file list."})
        confidence += 40
    elif create_count > 5:
        predictions.append({"risk": "MEDIUM", "reason": f"Spec creates {create_count} new files. High complexity.", "fix": "Consider splitting into multiple specs."})
        confidence += 20

# Check 3: Acceptance criteria
 criteria = re.findall(r'- \[ \]', spec)
if len(criteria) < 2:
    predictions.append({"risk": "MEDIUM", "reason": f"Only {len(criteria)} acceptance criteria. Hard to verify success.", "fix": "Add at least 3 testable acceptance criteria."})
    confidence += 15

# Check 4: Test commands
if 'pytest' not in spec and 'npm run build' not in spec:
    predictions.append({"risk": "HIGH", "reason": "No test commands in spec. Cannot verify success.", "fix": "Add test commands (pytest, npm run build, etc.)."})
    confidence += 25

# Check 5: Historical patterns
spec_lower = spec.lower()
domain = "unknown"
if 'pipeline' in spec_lower or 'signal' in spec_lower:
    domain = "pipeline"
elif 'web' in spec_lower or 'component' in spec_lower or 'page' in spec_lower:
    domain = "web"
elif 'migration' in spec_lower or 'schema' in spec_lower:
    domain = "database"

if domain in patterns.get('per_domain', {}):
    stats = patterns['per_domain'][domain]
    total = stats['success'] + stats['failure']
    if total > 0:
        rate = stats['success'] / total
        if rate < 0.5:
            predictions.append({"risk": "HIGH", "reason": f"Historical success rate for {domain} tasks is {rate:.0%}.", "fix": "Review past failures in .agent/learning/patterns.json"})
            confidence += 20

# Check 6: Cross-module touches
modules_touched = set()
for line in spec.split('\n'):
    if 'pipeline/src/fetchers' in line:
        modules_touched.add('fetchers')
    if 'pipeline/src/signals' in line:
        modules_touched.add('signals')
    if 'pipeline/src/regime' in line:
        modules_touched.add('regime')
    if 'pipeline/src/logic' in line:
        modules_touched.add('logic')
    if 'web/src/' in line:
        modules_touched.add('web')

if len(modules_touched) > 2:
    predictions.append({"risk": "MEDIUM", "reason": f"Spec touches {len(modules_touched)} modules: {', '.join(modules_touched)}. Cross-module changes are riskier.", "fix": "Consider sequential specs instead of parallel."})
    confidence += 15

# Report
print(f"Failure Prediction Confidence: {min(confidence, 100)}%")
print(f"Predicted Risks: {len(predictions)}")
print("")

if predictions:
    for i, p in enumerate(predictions, 1):
        print(f"{i}. [{p['risk']}] {p['reason']}")
        print(f"   Fix: {p['fix']}")
        print("")
else:
    print("✓ No significant failure risks detected.")
    print("This spec looks solid for delegation.")

print("")
if confidence > 60:
    print("⚠⚠⚠ HIGH RISK — Consider revising spec before delegation")
elif confidence > 30:
    print("⚠ MEDIUM RISK — Proceed with caution")
else:
    print("✓ LOW RISK — Safe to delegate")

PYEOF
