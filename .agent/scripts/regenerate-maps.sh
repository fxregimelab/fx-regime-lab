#!/usr/bin/env bash
#
# regenerate-maps.sh — Auto-regenerate all agent maps from live codebase
# Called by git hooks, file watcher, or manually.
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[$(date -Iseconds)] Regenerating agent maps..."

# 1. Regenerate CODEMAP.json
python3 << 'PYEOF'
import os, json, ast

def find_files(ext, exclude_dirs=None):
    result = []
    exclude = set(exclude_dirs or [
        '.git', 'node_modules', '.next', '__pycache__', '.venv', 'venv',
        '.mypy_cache', '.ruff_cache', '.pytest_cache', '.cursor', '.kimi',
        '.obsidian', '_archive', '_legacy_archive', '_docs', 'data', 'briefs',
        'runs', 'dist'
    ])
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            if f.endswith(ext):
                result.append(os.path.join(root, f))
    return sorted(result)

def extract_docstring(path, max_lines=3):
    try:
        with open(path) as f:
            lines = f.readlines()[:max_lines]
        for line in lines:
            line = line.strip()
            if line.startswith('"""') or line.startswith("'''"):
                return line.strip('"\'').strip()[:120]
            if line.startswith('#') and len(line) > 3:
                return line.lstrip('#').strip()[:120]
            if line.startswith('//') and len(line) > 3:
                return line.lstrip('/').strip()[:120]
    except:
        pass
    return ""

def extract_python_symbols(path):
    symbols = {"functions": [], "classes": [], "constants": []}
    try:
        with open(path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args][:5]
                })
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                symbols["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods[:10]
                })
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        symbols["constants"].append(target.id)
    except:
        pass
    return symbols

codemap = {
    "meta": {
        "generated": "$(date -Iseconds)",
        "description": "FX Regime Lab codebase. Read this first before exploring.",
        "total_files": 0
    },
    "pipeline": {},
    "web": {},
    "database": {},
    "deployment": {},
    "docs": {},
    "config": {}
}

codemap["pipeline"]["fetchers"] = [{"file": p, "desc": extract_docstring(p), "symbols": extract_python_symbols(p)} for p in find_files('.py') if 'pipeline/src/fetchers' in p]
codemap["pipeline"]["signals"] = [{"file": p, "desc": extract_docstring(p), "symbols": extract_python_symbols(p)} for p in find_files('.py') if 'pipeline/src/signals' in p]
codemap["pipeline"]["regime"] = [{"file": p, "desc": extract_docstring(p), "symbols": extract_python_symbols(p)} for p in find_files('.py') if 'pipeline/src/regime' in p]
codemap["pipeline"]["logic"] = [{"file": p, "desc": extract_docstring(p), "symbols": extract_python_symbols(p)} for p in find_files('.py') if 'pipeline/src/logic' in p]
codemap["pipeline"]["db"] = [{"file": p, "desc": extract_docstring(p), "symbols": extract_python_symbols(p)} for p in find_files('.py') if 'pipeline/src/db' in p]
codemap["pipeline"]["scheduler"] = [{"file": p, "desc": extract_docstring(p), "symbols": extract_python_symbols(p)} for p in find_files('.py') if 'pipeline/src/scheduler' in p]
codemap["pipeline"]["tests"] = [{"file": p, "desc": extract_docstring(p)} for p in find_files('.py') if 'pipeline/tests' in p]

codemap["web"]["pages"] = [{"file": p} for p in find_files('.tsx') if 'web/src/app' in p and 'page.tsx' in p]
codemap["web"]["layouts"] = [{"file": p} for p in find_files('.tsx') if 'web/src/app' in p and 'layout.tsx' in p]
codemap["web"]["components"] = [{"file": p} for p in find_files('.tsx') if 'web/src/components' in p]
codemap["web"]["hooks"] = [{"file": p} for p in find_files('.ts') if 'web/src/hooks' in p]
codemap["web"]["lib"] = [{"file": p} for p in find_files('.ts') if 'web/src/lib' in p]

codemap["database"]["migrations"] = [{"file": p} for p in find_files('.sql') if 'supabase/migrations' in p]
codemap["database"]["schema"] = [{"file": p} for p in find_files('.sql') if 'sql/' in p]

codemap["deployment"]["prefect"] = [{"file": "pipeline/prefect.yaml", "desc": "Prefect Cloud deployment"}]
codemap["deployment"]["cloudflare"] = [{"file": "workers/site-entry.js", "desc": "Cloudflare Worker API"}]

codemap["config"]["pipeline"] = [{"file": "pipeline/pyproject.toml", "desc": "Python build config"}]
codemap["config"]["web"] = [{"file": "web/package.json", "desc": "Node dependencies"}, {"file": "web/tsconfig.json", "desc": "TypeScript config"}]

total = 0
for section_name, section in codemap.items():
    if section_name == "meta":
        continue
    if isinstance(section, dict):
        for category, files in section.items():
            total += len(files)
codemap["meta"]["total_files"] = total

with open('.agent/maps/CODEMAP.json', 'w') as f:
    json.dump(codemap, f, indent=2)

print(f"  CODEMAP.json: {total} files")
PYEOF

# 2. Regenerate SKILLMAP
python3 << 'PYEOF'
import os, json
skillmap = {"meta": {"description": "All agent skills."}, "skills": []}
for base_dir in ['.cursor/skills', '.kimi/skills']:
    if not os.path.exists(base_dir):
        continue
    for d in sorted(os.listdir(base_dir)):
        skill_file = os.path.join(base_dir, d, 'SKILL.md')
        if os.path.exists(skill_file):
            with open(skill_file) as f:
                content = f.read()
            name = d
            desc = ""
            if content.startswith('---'):
                fm_end = content.find('---', 3)
                if fm_end > 0:
                    fm = content[3:fm_end]
                    for line in fm.split('\n'):
                        if line.startswith('name:'):
                            name = line.split(':', 1)[1].strip()
                        if line.startswith('description:'):
                            desc = line.split(':', 1)[1].strip().strip('"\'')
            skillmap["skills"].append({"name": name, "path": skill_file, "description": desc[:200], "agent": "cursor" if '.cursor/' in skill_file else "kimi"})
with open('.agent/maps/SKILLMAP.json', 'w') as f:
    json.dump(skillmap, f, indent=2)
print(f"  SKILLMAP.json: {len(skillmap['skills'])} skills")
PYEOF

# 3. Regenerate RULEMAP
python3 << 'PYEOF'
import os, json
rulemap = {"meta": {"description": "All Cursor rules."}, "rules": []}
rules_dir = '.cursor/rules'
if os.path.exists(rules_dir):
    for f in sorted(os.listdir(rules_dir)):
        if f.endswith('.mdc'):
            path = os.path.join(rules_dir, f)
            with open(path) as fh:
                content = fh.read()
            always_apply = False
            globs = ""
            desc = ""
            if content.startswith('---'):
                fm_end = content.find('---', 3)
                if fm_end > 0:
                    fm = content[3:fm_end]
                    for line in fm.split('\n'):
                        if 'alwaysApply:' in line and 'true' in line:
                            always_apply = True
                        if 'globs:' in line:
                            globs = line.split(':', 1)[1].strip()
                        if 'description:' in line:
                            desc = line.split(':', 1)[1].strip().strip('"\'')
            if not desc:
                for line in content.split('\n'):
                    if line.startswith('# '):
                        desc = line[2:].strip()
                        break
            rulemap["rules"].append({"file": f, "alwaysApply": always_apply, "globs": globs, "description": desc[:200]})
with open('.agent/maps/RULEMAP.json', 'w') as f:
    json.dump(rulemap, f, indent=2)
print(f"  RULEMAP.json: {len(rulemap['rules'])} rules")
PYEOF

# 4. Regenerate HOTFILES
python3 << 'PYEOF'
import subprocess, os
from datetime import datetime
result = subprocess.run(['git', 'log', '--name-only', '--pretty=format:', '-20'], capture_output=True, text=True)
files = set(line.strip() for line in result.stdout.split('\n') if line.strip() and not line.strip().startswith('.git/'))
hotfiles = []
for f in sorted(files):
    if os.path.exists(f) and os.path.isfile(f):
        try:
            hotfiles.append((f, os.path.getmtime(f)))
        except:
            pass
hotfiles.sort(key=lambda x: x[1], reverse=True)
content = "# HOTFILES — Recently Modified\n\n> Auto-generated from git history.\n\n| File | Last Modified |\n|------|---------------|\n"
for f, mtime in hotfiles[:25]:
    content += f"| `{f}` | {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')} |\n"
with open('.agent/context/HOTFILES.md', 'w') as f:
    f.write(content)
print(f"  HOTFILES.md: {len(hotfiles)} files")
PYEOF

# 5. Log metrics
python3 << 'PYEOF'
import json, os
metrics_file = '.agent/metrics/build-log.jsonl'
total_chars = sum(len(open(f).read()) for f in ['.agent/maps/CODEMAP.json', '.agent/maps/SKILLMAP.json', '.agent/maps/RULEMAP.json', '.agent/context/HOTFILES.md'] if os.path.exists(f))
try:
    with open('.agent/maps/CODEMAP.json') as f:
        cm = json.load(f)
    total = 0
    for section_name, section in cm.items():
        if section_name == "meta":
            continue
        if isinstance(section, dict):
            for category, files in section.items():
                total += len(files)
except:
    total = 0
entry = {"timestamp": "$(date -Iseconds)", "event": "maps_regenerated", "total_files_mapped": total, "map_tokens_estimate": total_chars // 4, "trigger": "${1:-manual}"}
with open(metrics_file, 'a') as f:
    f.write(json.dumps(entry) + '\n')
print(f"  Metrics: {entry['map_tokens_estimate']} tokens")
PYEOF

echo "[$(date -Iseconds)] Maps regenerated."
