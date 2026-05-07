#!/usr/bin/env bash
#
# build-knowledge-graph.sh — Build a network graph of codebase relationships
# Files, functions, imports, calls — all connected in a graph
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Building Knowledge Graph ==="

python3 << 'PYEOF'
import os, json, ast
from collections import defaultdict

graph = {
    "meta": {
        "description": "Knowledge graph of FX Regime Lab. Nodes = files/functions. Edges = imports/calls/dependencies.",
        "generated": "$(date -Iseconds)"
    },
    "nodes": [],
    "edges": []
}

node_ids = {}
node_counter = [0]

def add_node(node_type, name, path="", metadata=None):
    node_id = node_counter[0]
    node_counter[0] += 1
    node = {
        "id": node_id,
        "type": node_type,
        "name": name,
        "path": path,
        "metadata": metadata or {}
    }
    graph["nodes"].append(node)
    return node_id

def add_edge(source, target, edge_type, metadata=None):
    graph["edges"].append({
        "source": source,
        "target": target,
        "type": edge_type,
        "metadata": metadata or {}
    })

# Build file nodes
file_nodes = {}
for root, dirs, files in os.walk('pipeline/src'):
    dirs[:] = [d for d in dirs if d not in ['__pycache__', 'legacy']]
    for f in files:
        if f.endswith('.py') and not f.startswith('__'):
            path = os.path.join(root, f)
            nid = add_node("file", f, path)
            file_nodes[path] = nid

# Build function nodes and edges
for path, file_id in file_nodes.items():
    try:
        with open(path) as fh:
            tree = ast.parse(fh.read())
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                # Map to file if possible
                module_path = module.replace('.', '/') + '.py'
                for fp, fid in file_nodes.items():
                    if module_path in fp or os.path.basename(fp).replace('.py', '') in module:
                        add_edge(file_id, fid, "imports")
        
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_id = add_node("function", node.name, path, {"line": node.lineno})
                add_edge(file_id, func_id, "contains")
                
                # Extract calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            # Find which file defines this function
                            for other_path, other_id in file_nodes.items():
                                if other_path != path:
                                    try:
                                        with open(other_path) as of:
                                            other_tree = ast.parse(of.read())
                                        for on in ast.walk(other_tree):
                                            if isinstance(on, ast.FunctionDef) and on.name == child.func.id:
                                                add_edge(func_id, other_id, "calls", {"function": child.func.id})
                                                break
                                    except:
                                        pass
    except:
        pass

# Build web component relationships
for root, dirs, files in os.walk('web/src'):
    dirs[:] = [d for d in dirs if d not in ['node_modules']]
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            path = os.path.join(root, f)
            nid = add_node("component", f, path)
            file_nodes[path] = nid

# Add schema relationships
for root, dirs, files in os.walk('supabase/migrations'):
    for f in sorted(files):
        if f.endswith('.sql'):
            path = os.path.join(root, f)
            nid = add_node("migration", f, path)
            file_nodes[path] = nid

# Write graph
with open('.agent/graph/knowledge-graph.json', 'w') as f:
    json.dump(graph, f, indent=2)

print(f"  Nodes: {len(graph['nodes'])} (files, functions, components, migrations)")
print(f"  Edges: {len(graph['edges'])} (imports, calls, contains)")

# Generate simple graphviz dot file for visualization
dot = "digraph FXRegimeLab {\n"
dot += "  rankdir=TB;\n"
dot += "  node [shape=box, style=filled, fillcolor=lightblue];\n"

for node in graph["nodes"]:
    if node["type"] == "file":
        dot += f'  "{node["name"]}" [fillcolor=lightblue];\n'
    elif node["type"] == "function":
        dot += f'  "{node["name"]}" [fillcolor=lightgreen, fontsize=10];\n'
    elif node["type"] == "component":
        dot += f'  "{node["name"]}" [fillcolor=lightyellow];\n'
    elif node["type"] == "migration":
        dot += f'  "{node["name"]}" [fillcolor=lightcoral];\n'

for edge in graph["edges"][:200]:  # Limit edges for readability
    src = graph["nodes"][edge["source"]]["name"]
    tgt = graph["nodes"][edge["target"]]["name"]
    if edge["type"] == "imports":
        dot += f'  "{src}" -> "{tgt}" [color=blue, fontsize=9];\n'
    elif edge["type"] == "calls":
        dot += f'  "{src}" -> "{tgt}" [color=green, fontsize=9];\n'
    elif edge["type"] == "contains":
        dot += f'  "{src}" -> "{tgt}" [color=gray, style=dashed, fontsize=9];\n'

dot += "}\n"

with open('.agent/graph/codebase.dot', 'w') as f:
    f.write(dot)

print(f"  Graphviz DOT: .agent/graph/codebase.dot")
PYEOF

echo "[$(date -Iseconds)] Knowledge graph built."
