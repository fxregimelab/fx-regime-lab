#!/usr/bin/env bash
#
# predictive-loader.sh — Given a task description, predict which files/skills/rules to load
# Usage: ./.agent/scripts/predictive-loader.sh "Build a new EURUSD volatility signal"
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TASK="${1:-}"
if [[ -z "$TASK" ]]; then
  echo "Usage: $0 'task description'"
  exit 1
fi

echo "=== Predictive Loader ==="
echo "Task: $TASK"
echo ""

python3 << PYEOF
import json, re

task_lower = "$TASK".lower()

# Load maps
with open('.agent/maps/CODEMAP.json') as f:
    codemap = json.load(f)
with open('.agent/maps/SKILLMAP.json') as f:
    skillmap = json.load(f)
with open('.agent/maps/RULEMAP.json') as f:
    rulemap = json.load(f)
with open('.agent/maps/SEMANTICMAP.json') as f:
    semantic = json.load(f)

# Keyword matching
keywords = {
    "pipeline": ["signal", "fetcher", "pipeline", "python", "math", "percentile", "regime", "cot", "volatility", "yield"],
    "web": ["page", "component", "ui", "frontend", "nextjs", "react", "tailwind", "layout", "dashboard"],
    "database": ["migration", "schema", "table", "column", "supabase", "postgres", "rls", "index"],
    "deployment": ["deploy", "prefect", "cloudflare", "vercel", "worker", "orchestration"],
    "test": ["test", "pytest", "spec", "assertion", "fixture", "mock"]
}

scores = {"pipeline": 0, "web": 0, "database": 0, "deployment": 0, "test": 0}
for domain, words in keywords.items():
    for word in words:
        if word in task_lower:
            scores[domain] += 1

# Determine primary domain
primary = max(scores, key=scores.get)
if scores[primary] == 0:
    primary = "general"

print(f"Predicted domain: {primary.upper()}")
print("")

# Recommend files
print("RECOMMENDED FILES:")
if primary == "pipeline":
    for category in ["fetchers", "signals", "regime", "logic", "db"]:
        if category in codemap.get("pipeline", {}):
            files = codemap["pipeline"][category][:3]
            for f in files:
                print(f"  - {f['file']}")
elif primary == "web":
    for category in ["components", "pages", "hooks", "lib"]:
        if category in codemap.get("web", {}):
            files = codemap["web"][category][:3]
            for f in files:
                print(f"  - {f['file']}")
elif primary == "database":
    for category in ["migrations", "schema"]:
        if category in codemap.get("database", {}):
            files = codemap["database"][category][:3]
            for f in files:
                print(f"  - {f['file']}")

# Recommend skills
print("")
print("RECOMMENDED SKILLS:")
skill_keywords = {
    "fx-regime-signal-pipeline": ["signal", "pipeline", "math", "percentile"],
    "pipeline-data-fetch": ["fetch", "api", "fred", "yahoo"],
    "fx-regime-supabase-writes": ["database", "supabase", "write", "persist"],
    "regime-validation-logging": ["validation", "accuracy", "backtest"],
    "nextjs-frontend": ["frontend", "ui", "component", "page", "nextjs"],
    "quant-math": ["math", "percentile", "zscore", "statistical"],
    "prefect-deploy": ["deploy", "prefect", "orchestration"],
    "cloudflare-worker": ["worker", "api", "cloudflare"],
    "cursor-delegation": ["delegate", "orchestrate", "workflow"],
    "cursor-orchestration": ["orchestrate", "parallel", "multi-task"]
}

for skill in skillmap.get("skills", []):
    name = skill["name"]
    desc = skill.get("description", "").lower()
    matched = False
    for kw in skill_keywords.get(name, []):
        if kw in task_lower or kw in desc:
            matched = True
            break
    if matched:
        print(f"  - {name} ({skill['agent']})")

# Recommend rules
print("")
print("RECOMMENDED RULES:")
if primary == "pipeline":
    print("  - Pipeline-Rules.mdc (pipeline/src/**/*.py)")
elif primary == "web":
    print("  - Frontend-Rules.mdc (web/src/**/*.{ts,tsx,css})")
elif primary == "database":
    print("  - Database-Rules.mdc (migrations + db code)")

print("")
print("RECOMMENDED TEMPLATE:")
if primary == "pipeline":
    print("  - .agent/templates/pipeline-signal.md")
elif primary == "web":
    print("  - .agent/templates/nextjs-page.md")
elif primary == "database":
    print("  - .agent/templates/db-migration.md")

# Semantic search for relevant functions
print("")
print("SEMANTIC MATCHES (functions related to task):")
matches = []
for file_info in semantic.get("files", []):
    for func in file_info.get("functions", []):
        summary = func.get("summary", "").lower()
        name = func.get("name", "").lower()
        score = 0
        for word in task_lower.split():
            if len(word) > 3:
                if word in summary or word in name:
                    score += 1
        if score > 0:
            matches.append((score, file_info["file"], func["name"], func.get("summary", "")[:80]))

matches.sort(reverse=True)
for score, path, name, summary in matches[:5]:
    print(f"  - {path}::{name}() — {summary}")

PYEOF
