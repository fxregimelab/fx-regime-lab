"""Task classification engine for autonomous execution.

Classifies natural language directives into safety tiers based on
keyword matching and risk heuristics.

@agent_context: Auto-triage for FX Regime Lab CEO Mode
@allowed_imports: [json, re, sys, dataclasses]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TriageResult:
    tier: int
    tier_name: str
    confidence: float
    reasoning: str
    suggested_approval: str
    immutable_tables_touched: list[str]
    estimated_risk: str


# Tier 1 — Terminal UI only
TIER_1_KEYWORDS = {
    "page",
    "component",
    "style",
    "css",
    "color",
    "layout",
    "mobile",
    "responsive",
    "copy",
    "text",
    "font",
    "spacing",
    "margin",
    "padding",
    "border",
    "button",
    "chart",
    "graph",
    "visualization",
    "tooltip",
    "modal",
    "dialog",
    "form",
    "input",
    "link",
    "nav",
    "footer",
    "header",
    "card",
    "table",
    "row",
    "cell",
    "column",
    "animation",
    "hover",
    "focus",
    "dark mode",
    "light mode",
    "theme",
    "icon",
    "logo",
    "image",
    "svg",
}

# Tier 2 — Signal & Logic (non-breaking pipeline changes)
TIER_2_KEYWORDS = {
    "signal",
    "fetcher",
    "analysis",
    "indicator",
    "layer 2",
    "layer2",
    "layer 3",
    "layer3",
    "composite",
    "conviction",
    "directional",
    "timing",
    "entry",
    "stop",
    "position size",
    "sizing",
    "volatility",
    "rvol",
    "implied vol",
    "skew",
    "risk reversal",
    "cot",
    "positioning",
    "crowding",
    "percentile",
    "normalization",
    "z-score",
    "macd",
    "rsi",
    "momentum",
    "carry",
    "spread",
    "differential",
    "yield",
    "rate",
    "test",
    "pytest",
    "unit test",
    "docstring",
    "document",
    "comment",
    "refactor",
    "extract",
    "rename",
    "move",
}

# Tier 3 — Schema & Thresholds (breaking or critical changes)
TIER_3_KEYWORDS = {
    "migration",
    "schema",
    "rls",
    "row level security",
    "table",
    "column",
    "index",
    "constraint",
    "foreign key",
    "primary key",
    "threshold",
    "layer 1",
    "layer1",
    "regime gate",
    "gate",
    "bullish",
    "bearish",
    "neutral",
    "weight",
    "parameter",
    "config",
    "setting",
    "constant",
    "env",
    "environment variable",
    "credential",
    "api key",
    "secret",
    "token",
    "deploy",
    "deployment",
    "production",
    "prefect",
    "vercel",
    "worker",
    "cloudflare",
    "edge",
    "lambda",
    "serverless",
    "infra",
    "infrastructure",
    "docker",
    "container",
    "kubernetes",
    "k8s",
}

# Tier 4 — Immutable Ledger (sacred data)
TIER_4_KEYWORDS = {
    "backfill",
    "retroactive",
    "reprocess",
    "edit history",
    "fix past",
    "regenerate old",
    "delete call",
    "remove call",
    "modify call",
    "update regime",
    "change regime",
    "alter validation",
    "edit brief",
    "rewrite memo",
    "correct historical",
    "fix ledger",
    "amend record",
    "historical data",
    "past signal",
    "old call",
    "batch update",
    "mass update",
    "bulk",
}

# Immutable tables in Supabase
IMMUTABLE_TABLES = {
    "regime_calls",
    "validation_log",
    "brief_log",
    "signals",
}


def _keyword_score(request: str, keywords: set[str]) -> int:
    """Count how many keywords from the set appear in the request."""
    request_lower = request.lower()
    return sum(1 for kw in keywords if kw in request_lower)


# Keywords that imply SCHEMA changes (Tier 3) rather than DATA changes (Tier 4)
SCHEMA_KEYWORDS = {
    "migration",
    "add column",
    "add a column",
    "new column",
    "drop column",
    "create table",
    "alter table",
    "schema",
    "index",
    "constraint",
    "foreign key",
    "primary key",
}


def _is_schema_change(request: str) -> bool:
    """Check if the request describes a schema change, not data change."""
    request_lower = request.lower()
    return any(kw in request_lower for kw in SCHEMA_KEYWORDS)


def _detect_immutable_tables(request: str) -> list[str]:
    """Detect which immutable tables might be touched.

    Only flags data modifications, not schema changes.
    """
    request_lower = request.lower()
    if _is_schema_change(request):
        return []

    touched = []
    for table in IMMUTABLE_TABLES:
        if table.replace("_", " ") in request_lower or table in request_lower:
            touched.append(table)
    return touched


def classify(request: str) -> TriageResult:
    """Classify a natural language directive into a safety tier.

    Returns a TriageResult with tier, confidence, reasoning, and risk.
    """
    if not request or not request.strip():
        return TriageResult(
            tier=3,
            tier_name="Schema & Thresholds",
            confidence=1.0,
            reasoning="Empty request — cannot classify, defaulting to safest tier.",
            suggested_approval="human_required",
            immutable_tables_touched=[],
            estimated_risk="unknown",
        )

    # Detect immutable tables first (sacred data)
    touched = _detect_immutable_tables(request)

    # Check Tier 4 first (highest risk)
    tier_4_score = _keyword_score(request, TIER_4_KEYWORDS)
    if tier_4_score > 0 or touched:
        return TriageResult(
            tier=4,
            tier_name="Immutable Ledger",
            confidence=min(0.5 + tier_4_score * 0.15, 0.95) if tier_4_score > 0 else 0.85,
            reasoning=(
                f"Detected Tier 4 keywords ({tier_4_score} matches)."
                " Request touches or implies modification of immutable research data."
            ) if tier_4_score > 0 else (
                f"Detected immutable table references: {', '.join(touched)}."
                " Any modification to these tables requires audit approval."
            ),
            suggested_approval="human_required_audit",
            immutable_tables_touched=touched,
            estimated_risk="critical",
        )

    # Check Tier 3
    tier_3_score = _keyword_score(request, TIER_3_KEYWORDS)
    if tier_3_score > 0:
        return TriageResult(
            tier=3,
            tier_name="Schema & Thresholds",
            confidence=min(0.5 + tier_3_score * 0.12, 0.92),
            reasoning=(
                f"Detected Tier 3 keywords ({tier_3_score} matches)."
                " Request involves schema, thresholds, deployment, or infrastructure."
            ),
            suggested_approval="human_required",
            immutable_tables_touched=[],
            estimated_risk="high",
        )

    # Check Tier 1
    tier_1_score = _keyword_score(request, TIER_1_KEYWORDS)

    # Check Tier 2
    tier_2_score = _keyword_score(request, TIER_2_KEYWORDS)

    # Determine tier based on scores
    if tier_1_score > 0 and tier_2_score == 0:
        return TriageResult(
            tier=1,
            tier_name="Terminal Polish",
            confidence=min(0.6 + tier_1_score * 0.1, 0.95),
            reasoning=(
                f"Pure UI/UX request ({tier_1_score} Tier-1 keywords,"
                " 0 Tier-2/3/4). No pipeline or data layer involvement."
            ),
            suggested_approval="fully_autonomous",
            immutable_tables_touched=[],
            estimated_risk="low",
        )

    if tier_2_score > 0 and tier_1_score == 0:
        return TriageResult(
            tier=2,
            tier_name="Signal & Logic",
            confidence=min(0.6 + tier_2_score * 0.1, 0.93),
            reasoning=(
                f"Pipeline logic request ({tier_2_score} Tier-2 keywords,"
                " 0 Tier-1/3/4). Non-breaking signal or analysis addition."
            ),
            suggested_approval="auto_up_to_merge",
            immutable_tables_touched=[],
            estimated_risk="medium",
        )

    if tier_1_score > 0 and tier_2_score > 0:
        # Mixed signal — default to safer tier
        return TriageResult(
            tier=2,
            tier_name="Signal & Logic",
            confidence=0.65,
            reasoning=(
                f"Mixed request ({tier_1_score} UI keywords,"
                f" {tier_2_score} pipeline keywords)."
                " Defaulting to Tier 2 for safety."
            ),
            suggested_approval="auto_up_to_merge",
            immutable_tables_touched=[],
            estimated_risk="medium",
        )

    # No keywords matched — default to Tier 3 (safe)
    return TriageResult(
        tier=3,
        tier_name="Schema & Thresholds",
        confidence=0.5,
        reasoning=(
            "No clear keywords matched."
            " Request is ambiguous — defaulting to human-required tier for safety."
        ),
        suggested_approval="human_required",
        immutable_tables_touched=[],
        estimated_risk="unknown",
    )


def main() -> None:
    """CLI entrypoint for triage."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.auto.triage '<directive>'", file=sys.stderr)
        sys.exit(1)

    request = sys.argv[1]
    result = classify(request)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
