"""Current AI provenance controls; fixtures never imply factual/predictive validity."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.ai import client as ai
from src.private_desk.current_review import quantitative_fingerprint, verify_current_review
from src.private_desk.report import PAIRS, apply_current_review, atomic_json, refresh_current_report

CLOCK = "2026-10-01T13:00:00Z"


def headline(**changes: Any) -> dict[str, Any]:
    return {
        "title": "Dated evidence",
        "sha256": "0" * 64,
        "content_scope": "attributed_headline_only",
        "url": "https://www.federalreserve.gov/newsevents/fixture",
        "source": "Federal Reserve",
        "published_at": "2026-10-01T10:00:00Z",
        "retrieved_at": "2026-10-01T12:00:00Z",
        **changes,
    }


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"published_at": "2026-09-16"}, "PUBLICATION_OUTSIDE_WINDOW"),
        ({"published_at": "2026-10-02"}, "PUBLICATION_AFTER_RECEIPT"),
        (
            {"published_at": "2026-10-01", "retrieved_at": "2026-09-30T23:00:00Z"},
            "PUBLICATION_AFTER_RECEIPT",
        ),
        ({"published_at": "2026-10-01T12:30:00Z"}, "PUBLICATION_AFTER_RECEIPT"),
        ({"published_at": "2026-10-01T10:00:00"}, "INVALID_NEWS_METADATA"),
        (
            {"published_at": "2026-09-29", "retrieved_at": "2026-09-29T12:59:59Z"},
            "RETRIEVAL_RECEIPT_OUTSIDE_WINDOW",
        ),
        ({"retrieved_at": "2026-10-01T13:00:01Z"}, "RETRIEVAL_RECEIPT_OUTSIDE_WINDOW"),
        ({"retrieved_at": "2026-10-01T12:00:00+01:00"}, "RETRIEVAL_RECEIPT_OUTSIDE_WINDOW"),
        ({"url": "javascript:alert(1)"}, "INVALID_NEWS_METADATA"),
        ({"title": "  "}, "INVALID_NEWS_METADATA"),
    ],
)
def test_current_news_rejects_bad_clocks_and_metadata(changes: dict[str, Any], reason: str) -> None:
    payload = ai.private_brief_input([{"pair": "EURUSD"}], [headline(**changes)], {}, as_of=CLOCK)
    assert payload["headlines"] == []
    assert payload["input_admission"]["rejected_news"][0]["reason"] == reason


def test_date_only_calendar_boundary_and_utc_receipt_boundary_are_preserved() -> None:
    news = [
        headline(published_at="2026-09-17T00:00:00Z"),
        headline(
            url="https://www.federalreserve.gov/newsevents/fixture-date",
            published_at="2026-09-29",
            retrieved_at="2026-09-29T13:00:00Z",
        ),
    ]
    payload = ai.private_brief_input([{"pair": "EURUSD"}], news, {}, as_of=CLOCK)
    assert len(payload["headlines"]) == 2
    assert payload["headlines"][1]["published_at"] == "2026-09-29"
    assert payload["input_admission"]["news_currencies"] == ["USD"]
    assert "NZD" in payload["input_admission"]["missing_news_currencies"]
    with pytest.raises(ValueError, match="UTC"):
        ai.private_brief_input([], [], {}, as_of="2026-10-01T13:00:00")


def scenario(pair: str) -> dict[str, Any]:
    return {
        "pair": pair,
        "thesis": "If evidence improves, the base currency could strengthen.",
        "opposing": "If evidence reverses, the base currency could weaken.",
        "risks": "Surprises and source relevance are unverified.",
        "sources": ["https://www.federalreserve.gov/newsevents/fixture"],
        "probability": 0.99,
    }


def provider(monkeypatch: pytest.MonkeyPatch, items: Any, finish: str = "stop") -> MagicMock:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-only")
    monkeypatch.delenv("PRIVATE_FX_AI_MODEL", raising=False)
    mocked = MagicMock()
    mocked.models.list.return_value.data = [SimpleNamespace(id="deepseek-v4-pro")]
    mocked.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps({"pairs": items})), finish_reason=finish
            )
        ],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=30, prompt_cache_hit_tokens=0),
    )
    monkeypatch.setattr(ai, "OpenAI", MagicMock(return_value=mocked))
    return mocked


def test_exact_input_sent_once_and_quantitative_extra_field_cannot_become_probability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocked = provider(monkeypatch, [scenario(pair) for pair in PAIRS])
    pairs = [{"pair": pair} for pair in PAIRS]
    result = ai.generate_private_fundamental_brief(pairs, [headline()], {}, as_of=CLOCK)
    assert result["status"] == "GENERATED_UNVALIDATED"
    mocked.chat.completions.create.assert_called_once()
    sent = mocked.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert sent == ai.private_packet_text(
        ai.private_brief_input(pairs, [headline()], {}, as_of=CLOCK)
    )
    assert result["payload_sha256"] == hashlib.sha256(sent.encode()).hexdigest()
    assert len(result["pairs"]) == len(PAIRS)
    assert all("probability" not in item for item in result["pairs"])


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "duplicate",
        "unknown",
        "unsupported_cite",
        "empty_cite",
        "missing_text",
        "oversized",
        "length",
    ],
)
def test_partial_malformed_or_unattributed_response_rejects_whole_review(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    items = [scenario("EURUSD"), scenario("GBPUSD")]
    finish = "stop"
    if kind == "missing":
        items.pop()
    if kind == "duplicate":
        items.append(scenario("EURUSD"))
    if kind == "unknown":
        items[1]["pair"] = "USDJPY"
    if kind == "unsupported_cite":
        items[0]["sources"] += ["https://invented.test"]
    if kind == "empty_cite":
        items[0]["sources"] = []
    if kind == "missing_text":
        items[0]["opposing"] = ""
    if kind == "oversized":
        items[0]["thesis"] = "If " + "x" * 1200
    if kind == "length":
        finish = "length"
    mocked = provider(monkeypatch, items, finish)
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}, {"pair": "GBPUSD"}],
        [headline()],
        {},
        as_of=CLOCK,
    )
    mocked.chat.completions.create.assert_called_once()
    assert result["status"] == "UNAVAILABLE" and result["pairs"] == []
    assert result["usage"]["output_tokens"] == 30
    assert "invented.test" not in json.dumps(result)


def test_no_current_news_never_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    mocked = provider(monkeypatch, [scenario("EURUSD")])
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}],
        [headline(published_at="2026-09-01")],
        {},
        as_of=CLOCK,
    )
    assert result["status"] == "UNAVAILABLE"
    mocked.models.list.assert_not_called()
    mocked.chat.completions.create.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"url": "https://evil.test/federalreserve.gov"},
        {"url": "https://federalreserve.gov.evil.test/news"},
        {"url": "https://user:password@www.federalreserve.gov/news"},
        {"source": "Unknown publisher"},
        {"source": ["Federal Reserve"]},
        {"sha256": None},
        {"sha256": "invalid"},
        {"content_scope": "article_body"},
    ],
)
def test_supported_publisher_requires_matching_host_scope_and_digest(
    changes: dict[str, Any],
) -> None:
    payload = ai.private_brief_input([{"pair": "EURUSD"}], [headline(**changes)], {}, as_of=CLOCK)
    assert payload["headlines"] == []
    assert payload["input_admission"]["news_currencies"] == []


@pytest.mark.parametrize(
    "field,text",
    [
        ("thesis", "If evidence improves, the euro could strengthen. Buy EUR now."),
        ("thesis", "If evidence improves, buy EUR now."),
        ("opposing", "If evidence weakens, sell GBP now."),
        ("risks", "Enter the market now."),
        ("thesis", "If evidence improves, the euro strengthens; the data proves it."),
    ],
)
def test_conditional_prefix_cannot_hide_second_sentence_or_execution_advice(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    text: str,
) -> None:
    item = scenario("EURUSD")
    item[field] = text
    mocked = provider(monkeypatch, [item])
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}], [headline()], {}, as_of=CLOCK
    )
    mocked.chat.completions.create.assert_called_once()
    assert result["status"] == "UNAVAILABLE"
    assert result["pairs"] == []


def test_risk_notes_are_computed_from_inputs_not_model_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = scenario("EURUSD")
    item["risks"] = "No Federal Reserve headlines exist."
    provider(monkeypatch, [item])
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}], [headline()], {}, as_of=CLOCK
    )
    assert result["status"] == "GENERATED_UNVALIDATED"
    risk = result["pairs"][0]
    assert risk["risk_note_origin"] == "INPUT_AUDIT"
    assert "No Federal Reserve headlines exist" not in risk["risks"]
    assert "headline coverage for this pair: EUR" in risk["risks"]


def parent_report() -> dict[str, Any]:
    return {
        "schema_version": "private-fx-v1",
        "generated_at": "2026-09-30T00:00:00Z",
        "universe": list(PAIRS),
        "policy": {"full_target_gross_r": 2.0},
        "sources": [],
        "historical_policy": {"status": "PINNED_POLICY"},
        "historical_releases": {"events": []},
        "portfolio_audit": {"status": "PINNED_PORTFOLIO"},
        "news": [],
        "ai_summary": {"status": "UNAVAILABLE"},
        "pair_reports": [
            {
                "pair": pair,
                "backtest": {"method_version": "test-only"},
                "candidate": {"status": "ABSTAIN", "probability": None},
                "bidask_evidence": {"status": "PINNED_BIDASK"},
                "fundamentals": {},
                "ai_analysis": {"status": "UNAVAILABLE"},
            }
            for pair in PAIRS
        ],
    }


def test_offline_binding_rejects_changed_prose_even_with_unchanged_input_hash(
    tmp_path: Path,
) -> None:
    report = parent_report()
    apply_current_review(report, tmp_path, use_ai=False)
    verify_current_review(report, tmp_path / "current-review")
    digest = report["current_review"]["input_packet"]["sha256"]
    quant = quantitative_fingerprint(report)
    report["ai_summary"]["reason"] = "Tampered model output"
    assert digest == report["current_review"]["input_packet"]["sha256"]
    assert quant == quantitative_fingerprint(report)
    with pytest.raises(ValueError, match="output no longer matches"):
        verify_current_review(report, tmp_path / "current-review")


@pytest.mark.parametrize(
    "kind", ["packet", "output", "parent", "pair_text", "candidate", "policy_audit", "methods"]
)
def test_capture_and_parent_preservation_tampering_is_rejected(tmp_path: Path, kind: str) -> None:
    parent = parent_report()
    report = deepcopy(parent)
    apply_current_review(report, tmp_path, use_ai=False, parent_bytes=json.dumps(parent).encode())
    verify_current_review(report, tmp_path / "current-review")
    receipt = report["current_review"]
    if kind in ("packet", "output", "parent"):
        key = {"packet": "input_packet", "output": "output_packet", "parent": "parent_report"}[kind]
        Path(receipt[key]["capture_path"]).write_bytes(b"tampered")
    elif kind == "pair_text":
        report["pair_reports"][0]["ai_analysis"]["reason"] = "tampered"
    elif kind == "candidate":
        report["pair_reports"][0]["candidate"]["probability"] = 0.9
    elif kind == "policy_audit":
        report["historical_policy"]["status"] = "tampered"
    elif kind == "methods":
        receipt["quantitative_methods"]["EURUSD"] = "tampered"
    with pytest.raises(ValueError):
        verify_current_review(report, tmp_path / "current-review")


@pytest.mark.parametrize("kind", ["vintage", "release", "policy", "bidask", "policy_features"])
def test_full_research_binding_protects_all_evidence_without_parent(
    tmp_path: Path, kind: str
) -> None:
    report = parent_report()
    apply_current_review(report, tmp_path, use_ai=False)
    assert report["current_review"]["parent_report"] is None
    if kind in ("vintage", "release", "policy"):
        name = {
            "vintage": "historical_fundamentals",
            "release": "historical_releases",
            "policy": "historical_policy",
        }[kind]
        report[name] = {"status": "tampered"}
    else:
        name = "bidask_evidence" if kind == "bidask" else "historical_policy_features"
        report["pair_reports"][0][name] = {"status": "tampered"}
    with pytest.raises(ValueError, match="quantitative binding changed"):
        verify_current_review(report, tmp_path / "current-review")


@pytest.mark.parametrize("kind", ["summary", "receipt", "pair"])
def test_surfaced_predecessors_must_match_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    from src.private_desk import data

    report = parent_report()
    report["ai_summary"] = {"status": "PREVIOUS_REVIEW", "text": "Pinned previous review"}
    report["pair_reports"][0]["ai_analysis"] = {"status": "PREVIOUS_REVIEW"}
    report["current_review"] = {"status": "PREVIOUS_RECEIPT"}
    atomic_json(tmp_path / "report.json", report)
    monkeypatch.setattr(data, "fetch_fundamentals", lambda _path: {})
    monkeypatch.setattr(data, "fetch_news", lambda: [])
    refreshed = refresh_current_report(tmp_path, use_ai=False)
    if kind == "summary":
        refreshed["prior_ai_summary"] = {"status": "tampered"}
    elif kind == "receipt":
        refreshed["prior_current_review"] = {"status": "tampered"}
    else:
        refreshed["pair_reports"][0]["prior_ai_analysis"] = {"status": "tampered"}
    with pytest.raises(ValueError, match="predecessor"):
        verify_current_review(refreshed, tmp_path / "current-review")


def test_context_refresh_preserves_all_research_and_archives_bound_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.private_desk import data

    original = parent_report()
    atomic_json(tmp_path / "report.json", original)
    before = (tmp_path / "report.json").read_bytes()
    monkeypatch.setattr(data, "fetch_fundamentals", lambda _path: {"warnings": ["Fixture only"]})
    monkeypatch.setattr(data, "fetch_news", lambda: [])
    refreshed = refresh_current_report(tmp_path, use_ai=False)
    verify_current_review(refreshed, tmp_path / "current-review")
    assert Path(refreshed["current_review"]["parent_report"]["capture_path"]).read_bytes() == before
    for name in ("historical_policy", "historical_releases", "portfolio_audit", "generated_at"):
        assert original[name] == refreshed[name]
    assert quantitative_fingerprint(original) == quantitative_fingerprint(refreshed)
    repeated = refresh_current_report(tmp_path, use_ai=False)
    assert repeated["prior_current_review"] == refreshed["current_review"]
    assert len(list((tmp_path / "reports").glob("*-review-*.json"))) == 2


def test_concurrent_report_change_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.private_desk import data

    atomic_json(tmp_path / "report.json", parent_report())
    changed = b'{"concurrent":"writer"}'

    def fetch(_path: Path) -> dict[str, Any]:
        (tmp_path / "report.json").write_bytes(changed)
        return {}

    monkeypatch.setattr(data, "fetch_fundamentals", fetch)
    monkeypatch.setattr(data, "fetch_news", lambda: [])
    with pytest.raises(ValueError, match="Report changed"):
        refresh_current_report(tmp_path, use_ai=False)
    assert (tmp_path / "report.json").read_bytes() == changed
    assert not (tmp_path / "reports").exists()
