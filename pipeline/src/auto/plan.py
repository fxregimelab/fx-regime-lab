"""Research & planning engine for autonomous spec generation.

Generates implementation specs from natural language directives
by analyzing templates and codebase maps.

@agent_context: Auto-plan for FX Regime Lab CEO Mode
@allowed_imports: [json, os, sys, dataclasses, pathlib]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlanResult:
    directive: str
    tier: int
    spec_path: str
    files_to_read: list[str]
    files_to_modify: list[str]
    files_to_create: list[str]
    acceptance_criteria: list[str]
    reasoning: str


def _load_codemap(repo_root: Path) -> dict:
    """Load CODEMAP.json for file discovery."""
    codemap_path = repo_root / ".agent" / "maps" / "CODEMAP.json"
    if codemap_path.exists():
        return json.loads(codemap_path.read_text())
    return {}


def _find_relevant_files(codemap: dict, directive: str, tier: int) -> list[str]:
    """Find files relevant to the directive using keyword matching."""
    directive_lower = directive.lower()
    keywords = set(directive_lower.split())
    # Remove common words
    keywords -= {
        "a", "an", "the", "to", "from", "in", "on", "at", "for", "with",
        "and", "or", "of", "is", "are", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "add", "new", "create", "make", "build", "write",
    }

    matches = []
    for section_name, section in codemap.items():
        if not isinstance(section, dict):
            continue
        for category, files in section.items():
            if not isinstance(files, list):
                continue
            for item in files:
                # CODEMAP items are dicts with 'file' key
                if isinstance(item, dict):
                    file_path = item.get("file", "")
                else:
                    file_path = str(item)
                file_lower = file_path.lower()
                # Score how many keywords match
                score = sum(1 for kw in keywords if kw in file_lower)
                if score > 0:
                    matches.append((score, file_path))

    # Sort by score descending, take top 10
    matches.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in matches[:10]]


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use in file paths."""
    return re.sub(r"[^a-z0-9_-]", "", name.lower())[:40]


def _generate_tier_1_spec(directive: str, relevant_files: list[str]) -> str:
    """Generate a Tier 1 (UI) spec from directive."""
    # Extract page/component name from directive
    words = directive.lower().split()
    page_name = "new-page"
    for i, word in enumerate(words):
        if word in ("page", "component", "chart", "table") and i > 0:
            page_name = _sanitize_name(words[i - 1])
            break

    files_to_read = [f for f in relevant_files if "page" in f or "component" in f][:5]

    spec = f"""# Spec: {directive}

## Task
{directive}

## Files to Read
"""
    for f in files_to_read:
        spec += f"- `{f}` — reference for patterns\n"

    spec += f"""
## Files to Modify
- None (new page)

## Files to Create
- `web/src/app/{page_name}/page.tsx` — main page component
- `web/src/app/{page_name}/layout.tsx` — page layout (if needed)

## Acceptance Criteria
- [ ] Page renders without errors
- [ ] npm run build passes
- [ ] npm run lint passes (0 errors)
- [ ] Uses Swiss Monochrome design tokens (no rounded corners, 1px borders)
- [ ] All financial numbers use `tabular-nums`
- [ ] Mobile responsive (min-width breakpoints)
- [ ] No `console.log` statements in production code
- [ ] Uses generated Supabase types from `database.types.ts`

## Context
- Look at existing pages in `web/src/app/` for patterns
- Use Tailwind CSS 4 with the existing design system
- All data fetching should use server components where possible
"""
    return spec


def _generate_tier_2_spec(directive: str, relevant_files: list[str]) -> str:
    """Generate a Tier 2 (Signal/Logic) spec from directive."""
    # Extract signal name from directive
    words = directive.lower().split()
    signal_name = "new_signal"
    for i, word in enumerate(words):
        if word in ("signal", "indicator", "fetcher") and i > 0:
            signal_name = _sanitize_name(words[i - 1]).replace("-", "_")
            break

    files_to_read = [
        f for f in relevant_files
        if "signal" in f or "fetcher" in f or "logic" in f
    ][:5]
    files_to_modify = []

    # Check if Layer 2/3 is mentioned
    if "layer 2" in directive.lower() or "layer2" in directive.lower():
        files_to_modify.append("pipeline/src/logic/layer2_directional.py")
    if "layer 3" in directive.lower() or "layer3" in directive.lower():
        files_to_modify.append("pipeline/src/logic/layer3_execution.py")

    spec = f"""# Spec: {directive}

## Task
{directive}

## Files to Read
"""
    for f in files_to_read:
        spec += f"- `{f}` — reference for patterns\n"

    spec += """
## Files to Modify
"""
    for f in files_to_modify:
        spec += f"- `{f}` — integrate signal into composite\n"

    spec += f"""
## Files to Create
- `pipeline/src/signals/{signal_name}.py` — signal implementation
- `pipeline/tests/test_{signal_name}.py` — unit tests

## Acceptance Criteria
- [ ] Causal computation only (today scored against t-1 history)
- [ ] Uses `np.float64` explicitly, no rounding
- [ ] Normalized to [-1, 1] using rolling percentile
- [ ] Integrated into appropriate Layer composite with documented weight
- [ ] All 121+ tests pass: `cd pipeline && pytest`
- [ ] Ruff clean: `cd pipeline && ruff check .`
- [ ] Mypy clean: `cd pipeline && mypy .`
- [ ] Docstrings for all public functions
- [ ] No forbidden imports (src.db in signals, src.ai in fetchers)

## Context
- Look at `src/signals/volatility.py` for causal rolling pattern
- Look at `src/logic/layer2_directional.py` for composite integration
- Weight must be documented and justified in SIGNAL_DEFINITIONS.md
"""
    return spec


def create_plan(directive: str, tier: int, repo_root: Path | str) -> PlanResult:
    """Generate an implementation plan and spec from a directive.

    Args:
        directive: Natural language directive
        tier: Safety tier (1 or 2)
        repo_root: Repository root path

    Returns:
        PlanResult with spec path and file recommendations
    """
    repo_root = Path(repo_root)
    codemap = _load_codemap(repo_root)
    relevant_files = _find_relevant_files(codemap, directive, tier)

    # Generate spec
    if tier == 1:
        spec_content = _generate_tier_1_spec(directive, relevant_files)
        acceptance_criteria = [
            "Page renders without errors",
            "npm run build passes",
            "npm run lint passes (0 errors)",
            "Uses Swiss Monochrome design tokens",
            "Mobile responsive",
        ]
    elif tier == 2:
        spec_content = _generate_tier_2_spec(directive, relevant_files)
        acceptance_criteria = [
            "Causal computation only",
            "np.float64 explicitly",
            "Normalized to [-1, 1]",
            "pytest passes",
            "ruff clean",
        ]
    else:
        raise ValueError(f"Tier {tier} not supported for auto-planning")

    # Write spec to queue (UUID filename avoids collisions)
    queue_dir = repo_root / ".cursor" / "delegation" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    spec_path = queue_dir / f"auto-{uuid.uuid4().hex[:12]}.md"
    spec_path.write_text(spec_content)

    # Determine files
    if tier == 1:
        files_to_modify = []
        files_to_create = ["web/src/app/.../page.tsx"]
    else:
        files_to_modify = [f for f in relevant_files if "logic" in f][:2]
        files_to_create = ["pipeline/src/signals/....py"]

    return PlanResult(
        directive=directive,
        tier=tier,
        spec_path=str(spec_path.relative_to(repo_root)),
        files_to_read=relevant_files[:5],
        files_to_modify=files_to_modify,
        files_to_create=files_to_create,
        acceptance_criteria=acceptance_criteria,
        reasoning=(
            f"Generated spec from Tier {tier} template with "
            f"{len(relevant_files)} relevant files identified"
        ),
    )


def main() -> None:
    """CLI entrypoint for planning."""
    if len(sys.argv) < 3:
        print("Usage: python -m src.auto.plan '<directive>' <tier> [repo_root]", file=sys.stderr)
        sys.exit(1)

    directive = sys.argv[1]
    tier = int(sys.argv[2])
    repo_root = Path(sys.argv[3]) if len(sys.argv) > 3 else Path.cwd()

    if tier not in (1, 2):
        print(f"Tier {tier} not supported for auto-planning. Use Tier 1 or 2.", file=sys.stderr)
        sys.exit(1)

    result = create_plan(directive, tier, repo_root)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
