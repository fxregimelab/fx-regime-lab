#!/usr/bin/env bash
#
# learn-from-outcomes.sh — Meta-learning: analyze delegation outcomes and improve system
# Tracks success/failure patterns, updates rules, evolves templates
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

METRICS_FILE=".agent/metrics/build-log.jsonl"
LEARNING_DB=".agent/learning/outcomes.jsonl"
PATTERNS_FILE=".agent/learning/patterns.json"
mkdir -p "$(dirname "$LEARNING_DB")"

echo "=== Meta-Learning System ==="

python3 << 'PYEOF'
import json, os
from collections import defaultdict

metrics_file = '.agent/metrics/build-log.jsonl'
learning_db = '.agent/learning/outcomes.jsonl'
patterns_file = '.agent/learning/patterns.json'

# Load all historical outcomes
outcomes = []
if os.path.exists(learning_db):
    with open(learning_db) as f:
        for line in f:
            if line.strip():
                outcomes.append(json.loads(line))

# Load recent metrics
if os.path.exists(metrics_file):
    with open(metrics_file) as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get('event') in ['spec_completed', 'spec_failed', 'spec_retried']:
                    outcomes.append(entry)

# Analyze patterns
patterns = {
    "total_attempts": len(outcomes),
    "success_rate": 0,
    "avg_retries": 0,
    "common_failures": defaultdict(int),
    "success_patterns": defaultdict(int),
    "per_domain": defaultdict(lambda: {"success": 0, "failure": 0, "retries": 0}),
    "per_skill": defaultdict(lambda: {"success": 0, "failure": 0}),
    "recommendations": []
}

successes = [o for o in outcomes if o.get('status') == 'success']
failures = [o for o in outcomes if o.get('status') == 'failed']

if outcomes:
    patterns["success_rate"] = len(successes) / len(outcomes)
    patterns["avg_retries"] = sum(o.get('retries', 0) for o in outcomes) / len(outcomes)

# Domain analysis
for o in outcomes:
    domain = o.get('domain', 'unknown')
    if o.get('status') == 'success':
        patterns["per_domain"][domain]["success"] += 1
    else:
        patterns["per_domain"][domain]["failure"] += 1
    patterns["per_domain"][domain]["retries"] += o.get('retries', 0)

# Failure analysis
for f in failures:
    error_type = f.get('error_type', 'unknown')
    patterns["common_failures"][error_type] += 1

# Skill analysis
for o in outcomes:
    skill = o.get('skill_used', 'unknown')
    if o.get('status') == 'success':
        patterns["per_skill"][skill]["success"] += 1
    else:
        patterns["per_skill"][skill]["failure"] += 1

# Generate recommendations
for domain, stats in patterns["per_domain"].items():
    total = stats["success"] + stats["failure"]
    if total > 0:
        rate = stats["success"] / total
        if rate < 0.5 and total >= 3:
            patterns["recommendations"].append({
                "type": "domain_struggle",
                "domain": domain,
                "success_rate": round(rate, 2),
                "recommendation": f"Consider more detailed specs for {domain} tasks. Current success rate is {rate:.0%}."
            })
        if stats["retries"] / total > 1.5:
            patterns["recommendations"].append({
                "type": "high_retries",
                "domain": domain,
                "avg_retries": round(stats["retries"] / total, 2),
                "recommendation": f"{domain} tasks require many retries. Add more detailed acceptance criteria."
            })

for skill, stats in patterns["per_skill"].items():
    total = stats["success"] + stats["failure"]
    if total > 0:
        rate = stats["success"] / total
        if rate < 0.5 and total >= 2:
            patterns["recommendations"].append({
                "type": "skill_underperforming",
                "skill": skill,
                "success_rate": round(rate, 2),
                "recommendation": f"Skill '{skill}' has low success rate ({rate:.0%}). Consider updating the SKILL.md."
            })

# Write patterns
with open(patterns_file, 'w') as f:
    json.dump(patterns, f, indent=2)

print(f"  Analyzed {len(outcomes)} historical outcomes")
print(f"  Success rate: {patterns['success_rate']:.1%}")
print(f"  Avg retries: {patterns['avg_retries']:.2f}")
print(f"  Recommendations: {len(patterns['recommendations'])}")

for rec in patterns['recommendations']:
    print(f"    ⚠ {rec['recommendation']}")

# Auto-evolve templates based on success patterns
print("\n  Auto-evolving templates...")
template_dir = '.agent/templates'
for template_file in os.listdir(template_dir):
    if template_file.endswith('.md'):
        template_name = template_file.replace('.md', '')
        template_success = sum(1 for o in outcomes if o.get('template') == template_name and o.get('status') == 'success')
        template_total = sum(1 for o in outcomes if o.get('template') == template_name)
        if template_total > 0:
            rate = template_success / template_total
            if rate < 0.6:
                print(f"    ⚠ Template '{template_name}' underperforming ({rate:.0%}) — needs review")
            else:
                print(f"    ✓ Template '{template_name}' performing well ({rate:.0%})")

PYEOF

echo "[$(date -Iseconds)] Meta-learning complete."
