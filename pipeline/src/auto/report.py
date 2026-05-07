"""Human-readable reporting for autonomous execution.

Generates formatted reports from execution context, tier, results,
and file changes.

@agent_context: Auto-report for FX Regime Lab CEO Mode
@allowed_imports: [json, sys, dataclasses, datetime]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class ExecutionContext:
    directive: str
    tier: int
    tier_name: str
    start_time: str
    end_time: str
    files_changed: list[dict[str, str]] = field(default_factory=list)
    test_results: dict[str, str] = field(default_factory=dict)
    deploy_target: str = ""
    deploy_url: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def generate_report(ctx: ExecutionContext) -> str:
    """Generate a human-readable execution report."""
    lines: list[str] = []

    # Header
    lines.append("═══════════════════════════════════════════════════")
    lines.append("  FX Regime Lab — Autonomous Execution Report")
    lines.append("═══════════════════════════════════════════════════")
    lines.append("")

    # Directive
    lines.append(f"Directive:    {ctx.directive}")
    lines.append(f"Tier:         {ctx.tier} ({ctx.tier_name})")
    lines.append(f"Status:       {_status_emoji(ctx)} {_status_text(ctx)}")
    lines.append("")

    # Timing
    lines.append("Execution:")
    lines.append(f"  Started:     {ctx.start_time}")
    lines.append(f"  Finished:    {ctx.end_time}")
    duration = _parse_duration(ctx.start_time, ctx.end_time)
    lines.append(f"  Duration:    {duration}")
    lines.append("")

    # Results
    lines.append("Results:")
    lines.append(f"  Tests:       {ctx.test_results.get('pytest', 'N/A')}")
    lines.append(f"  Ruff:        {ctx.test_results.get('ruff', 'N/A')}")
    lines.append(f"  Build:       {ctx.test_results.get('build', 'N/A')}")
    lines.append(f"  Lint:        {ctx.test_results.get('lint', 'N/A')}")
    lines.append("")

    # Files changed
    if ctx.files_changed:
        lines.append("Files Changed:")
        for f in ctx.files_changed:
            status = f.get("status", "?")
            path = f.get("path", "unknown")
            delta = f.get("delta", "")
            lines.append(f"  {status:1}  {path:<50} {delta}")
        lines.append("")

    # Warnings
    if ctx.warnings:
        lines.append("Warnings:")
        for w in ctx.warnings:
            lines.append(f"  ⚠  {w}")
        lines.append("")

    # Errors
    if ctx.errors:
        lines.append("Errors:")
        for e in ctx.errors:
            lines.append(f"  ✗  {e}")
        lines.append("")

    # Deploy info
    if ctx.deploy_target:
        lines.append("Deployment:")
        lines.append(f"  Target:      {ctx.deploy_target}")
        if ctx.deploy_url:
            lines.append(f"  URL:         {ctx.deploy_url}")
        lines.append("")

    # Next steps based on tier
    lines.append(_next_steps(ctx))
    lines.append("")

    # Footer
    lines.append("═══════════════════════════════════════════════════")

    return "\n".join(lines)


def _status_emoji(ctx: ExecutionContext) -> str:
    if ctx.errors:
        return "❌"
    if ctx.warnings:
        return "⚠️"
    return "✅"


def _status_text(ctx: ExecutionContext) -> str:
    if ctx.errors:
        return "FAILED — manual intervention required"
    if ctx.warnings:
        return "COMPLETE WITH WARNINGS"
    if ctx.tier == 2:
        return "COMPLETE — Awaiting your approval for merge"
    return "COMPLETE — No action needed"


def _parse_duration(start: str, end: str) -> str:
    """Parse ISO timestamps and return human-readable duration."""
    try:
        t1 = datetime.fromisoformat(start.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(end.replace("Z", "+00:00"))
        delta = t2 - t1
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        if total_seconds < 3600:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
        return f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
    except Exception:
        return "unknown"


def _next_steps(ctx: ExecutionContext) -> str:
    if ctx.errors:
        return (
            "Next Step:\n"
            "  Review errors above. Fix manually or write a debug spec.\n"
            "  fx-agent spec create signal  # for debug spec"
        )

    if ctx.tier == 1:
        if ctx.deploy_url:
            return (
                "Next Step:\n"
                f"  Deployed to: {ctx.deploy_url}\n"
                "  No action needed from you."
            )
        return (
            "Next Step:\n"
            "  Run: fx-agent approve <spec-id>  # to deploy\n"
            "  Or:  fx-agent deploy <spec-id>   # auto-deploy"
        )

    if ctx.tier == 2:
        return (
            "Next Step:\n"
            "  Review the diff above.\n"
            "  Run: fx-agent approve <spec-id>  # to merge and deploy\n"
            "  Or:  fx-agent reject <spec-id> --reason '...'"
        )

    if ctx.tier == 3:
        return (
            "Next Step:\n"
            "  This is a Tier 3 change. Human approval required.\n"
            "  Review the spec and implementation carefully.\n"
            "  Run: fx-agent approve --tier-3 <spec-id>  # with explicit confirmation"
        )

    if ctx.tier == 4:
        return (
            "Next Step:\n"
            "  This is a TIER 4 change touching immutable ledger data.\n"
            "  This requires signed confirmation and audit trail.\n"
            "  Run: fx-agent approve --tier-4 <spec-id> --audit-note '...'"
        )

    return "Next Step:\n  Review and approve as appropriate."


def generate_json_report(ctx: ExecutionContext) -> str:
    """Generate a JSON report for machine consumption."""
    return json.dumps(asdict(ctx), indent=2, default=str)


def main() -> None:
    """CLI entrypoint for report generation."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.auto.report <context.json>", file=sys.stderr)
        sys.exit(1)

    context_path = sys.argv[1]
    try:
        with open(context_path, encoding="utf-8") as f:
            data = json.load(f)
        ctx = ExecutionContext(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing context: {e}", file=sys.stderr)
        sys.exit(1)

    report = generate_report(ctx)
    print(report)


if __name__ == "__main__":
    main()
