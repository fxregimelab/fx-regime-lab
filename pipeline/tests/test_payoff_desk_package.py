"""Static installation checks, not proof of trading/runtime permission enforcement."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = (
    "desk-researcher",
    "desk-pair-analyst",
    "desk-challenger",
    "desk-payoff-researcher",
    "desk-builder",
    "desk-auditor",
    "desk-postmortem",
)
SKILLS = ("desk-evidence", "desk-payoff", "desk-worker", "desk-postmortem")


def _header(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    return text.split("---\n", 2)[1]


def _rules(header: str) -> list[tuple[str, str, str]]:
    """Check the deliberately restricted three-line YAML rule format we ship."""
    raw = re.findall(
        r"  - action: (.+)\n    resource: (.+)\n    effect: (allow|ask|deny)",
        header,
    )
    return [(a.strip("'\""), r.strip("'\""), e) for a, r, e in raw]


@pytest.mark.parametrize("name", AGENTS)
def test_agents_are_fail_closed_and_do_not_select_deepseek(name: str) -> None:
    header = _header(ROOT / ".opencode" / "agents" / f"{name}.md")
    assert "mode: subagent\n" in header
    assert "description: " in header
    assert "deepseek" not in header.lower()
    rules = _rules(header)
    assert rules[0] == ("*", "*", "deny")
    assert not any(a == "*" and e == "allow" for a, _, e in rules)
    assert not any(a == "shell" and e == "allow" for a, _, e in rules)
    assert not any(a == "subagent" and e != "deny" for a, _, e in rules)
    if name not in {"desk-builder", "desk-auditor"}:
        assert not any(a in {"edit", "shell"} and e != "deny" for a, _, e in rules)
    for secret in ("**/.env*", "**/.mcp.json", "**/opencode.json*", "**/.codex/**"):
        assert ("read", secret, "deny") in rules


def test_builder_has_only_bound_packet_edit_scope() -> None:
    rules = _rules(_header(ROOT / ".opencode" / "agents" / "desk-builder.md"))
    edits = {(r, e) for a, r, e in rules if a == "edit"}
    assert edits == {
        ("pipeline/src/paper/backtest/payoff.py", "ask"),
        ("pipeline/tests/test_payoff.py", "ask"),
        ("pipeline/src/paper/calendar.py", "ask"),
        ("pipeline/tests/test_ad_calendar.py", "ask"),
        ("pipeline/src/paper/backtest/engine.py", "ask"),
        ("pipeline/tests/test_payoff_engine_regressions.py", "ask"),
        ("pipeline/src/paper/backtest/portfolio.py", "ask"),
        ("pipeline/tests/test_payoff_portfolio_regressions.py", "ask"),
        ("pipeline/src/paper/backtest/report.py", "ask"),
        ("pipeline/src/paper/backtest/__init__.py", "ask"),
        ("pipeline/scripts/backtest_desk.py", "ask"),
        ("pipeline/scripts/backtest_sensitivity.py", "ask"),
    }


@pytest.mark.parametrize("name", SKILLS)
def test_skills_have_discoverable_description_and_repository_reference(name: str) -> None:
    path = ROOT / ".opencode" / "skills" / name / "SKILL.md"
    header = _header(path)
    assert f"name: {name}\n" in header
    assert "description: " in header
    assert "docs/specs/payoff-desk/" in path.read_text(encoding="utf-8")


def test_package_relative_markdown_links_resolve() -> None:
    docs = ROOT / "docs" / "specs" / "payoff-desk"
    for path in docs.glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if target.startswith(("https://", "http://", "#")):
                continue
            assert (path.parent / target.split("#", 1)[0]).resolve().is_file(), (path, target)


def test_mandate_preserves_all_in_denominator_and_protected_graduation() -> None:
    text = (ROOT / "docs/specs/payoff-desk/01-mandate.md").read_text(encoding="utf-8")
    assert "D=G+A" in text
    assert "5 + 6*k + 2*c" in text
    assert "5 + 8*c" in text
    assert "separate owner-approved graduation contract" in text
    assert "risk may be reduced only" in text.lower()


def test_handoff_does_not_present_future_payoff_module_as_installed() -> None:
    text = (ROOT / "docs/specs/payoff-desk/05-delivery.md").read_text(encoding="utf-8")
    assert "NEW `pipeline/src/paper/backtest/payoff.py`" in text
    assert "Runtime integration is NOT" in text
    assert "PD-00B" in text and "PD-00C" in text


@pytest.mark.parametrize("name", AGENTS)
def test_agent_reads_are_scoped_and_content_search_is_disabled(name: str) -> None:
    rules = _rules(_header(ROOT / ".opencode" / "agents" / f"{name}.md"))
    approved = {
        "docs/**", "pipeline/src/**", "pipeline/tests/**",
        "reports/desk/research/**", ".opencode/skills/**", ".opencode/agents/**",
        "IDENTITY.md", "MASTERPLAN.md", "TASK.md",
    }
    positive_reads = {r for a, r, e in rules if a == "read" and e != "deny"}
    assert positive_reads <= approved
    assert not any(a in {"grep", "glob"} and e != "deny" for a, _, e in rules)


def test_required_agent_and_skill_document_paths_resolve_without_shorthand() -> None:
    paths = list((ROOT / ".opencode/agents").glob("*.md"))
    paths.extend((ROOT / ".opencode/skills").glob("*/SKILL.md"))
    for path in paths:
        text = path.read_text(encoding="utf-8").split("---", 2)[2]
        refs = re.findall(r"(?<![/\w-])(?:[\w.-]+/)*[\w.-]+\.md", text)
        for ref in refs:
            assert (ROOT / ref).is_file(), (path, ref)
