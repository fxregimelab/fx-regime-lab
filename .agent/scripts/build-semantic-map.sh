#!/usr/bin/env bash
#
# build-semantic-map.sh — Extract semantic meaning from all Python code
# Creates SEMANTICMAP.json with: function purpose, inputs, outputs, dependencies
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

python3 << 'PYEOF'
import os, json, ast, re

def extract_semantics(path):
    """Extract semantic info from a Python file."""
    try:
        with open(path) as f:
            source = f.read()
        tree = ast.parse(source)
    except:
        return None
    
    file_info = {
        "file": path,
        "module_docstring": ast.get_docstring(tree) or "",
        "imports": [],
        "functions": [],
        "classes": []
    }
    
    # Extract imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                file_info["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [a.name for a in node.names]
            file_info["imports"].append(f"{module}: {', '.join(names)}")
    
    # Extract functions with semantic analysis
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node) or ""
            # Extract first sentence as semantic summary
            summary = doc.split('.')[0].strip() if doc else ""
            
            # Extract parameter types from annotations
            params = []
            for arg in node.args.args:
                param_type = ""
                if arg.annotation:
                    try:
                        param_type = ast.unparse(arg.annotation)
                    except:
                        pass
                params.append({"name": arg.arg, "type": param_type})
            
            # Extract return type
            return_type = ""
            if node.returns:
                try:
                    return_type = ast.unparse(node.returns)
                except:
                    pass
            
            # Find all function calls inside this function
            calls = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.append(child.func.attr)
            
            file_info["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "summary": summary[:200],
                "params": params,
                "returns": return_type,
                "calls": list(set(calls))[:20],
                "is_async": isinstance(node, ast.AsyncFunctionDef)
            })
        
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            summary = doc.split('.')[0].strip() if doc else ""
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
            file_info["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "summary": summary[:200],
                "methods": methods,
                "bases": [ast.unparse(b) for b in node.bases]
            })
    
    return file_info

# Find all Python files in pipeline/src
semantic_map = {
    "meta": {
        "generated": "$(date -Iseconds)",
        "description": "Semantic understanding of codebase. Each function/class has a human-readable summary, params, return types, and internal calls."
    },
    "files": []
}

for root, dirs, files in os.walk('pipeline/src'):
    dirs[:] = [d for d in dirs if d not in ['__pycache__', 'legacy']]
    for f in files:
        if f.endswith('.py') and not f.startswith('__'):
            path = os.path.join(root, f)
            info = extract_semantics(path)
            if info and (info["functions"] or info["classes"]):
                semantic_map["files"].append(info)

# Also scan web/src for TypeScript (basic extraction)
for root, dirs, files in os.walk('web/src'):
    dirs[:] = [d for d in dirs if d not in ['node_modules']]
    for f in files:
        if f.endswith(('.ts', '.tsx')) and not f.startswith('__'):
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    content = fh.read()
                # Simple regex-based extraction for TS
                functions = re.findall(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', content)
                components = re.findall(r'(?:export\s+default\s+)?function\s+(\w+)', content)
                interfaces = re.findall(r'interface\s+(\w+)', content)
                if functions or components or interfaces:
                    semantic_map["files"].append({
                        "file": path,
                        "module_docstring": "",
                        "imports": [],
                        "functions": [{"name": fn, "summary": "", "params": [], "returns": "", "calls": []} for fn in set(functions + components)],
                        "classes": [{"name": i, "summary": "", "methods": []} for i in interfaces],
                        "is_typescript": True
                    })
            except:
                pass

with open('.agent/maps/SEMANTICMAP.json', 'w') as f:
    json.dump(semantic_map, f, indent=2)

print(f"SEMANTICMAP.json: {len(semantic_map['files'])} files with semantic analysis")
PYEOF
