"""Counterexamples for shadow wire types and provenance, not semantic accuracy."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from src.ai.client import private_packet_text, typesafe_shadow_judgments
from src.private_desk import jev_shadow as shadow

STATE = {"passages": {"p1": "The bank retained its policy."}}
QUESTIONS = {
    "relevance": {"type": "noul", "instructions": "Does the text discuss policy?"},
    "support": {"type": "choice", "instructions": "Which claim is supported?",
                "criteria": {"supports": "Explicit support", "none": "No explicit support"}},
}


def response_fixture() -> dict[str, Any]:
    return {
        "model": shadow.MODEL,
        "answers": {
            "relevance": {"type": "noul", "noul": 0.7},
            "support": {"type": "choice", "choice": "none",
                        "probabilities": {"supports": 0.1, "none": 0.9}, "confidence": 0.8},
        },
        "usage": {"input_tokens": 120, "output_tokens": 15},
    }


def mocked_provider(
    monkeypatch: pytest.MonkeyPatch, body: bytes, *, status: int = 200
) -> MagicMock:
    monkeypatch.setenv("TYPESAFE_API_KEY", "fixture-typesafe-key-private")
    reply = MagicMock()
    reply.status_code = status
    reply.iter_content.return_value = [body]
    reply.__enter__.return_value = reply
    call = MagicMock(return_value=reply)
    monkeypatch.setattr(requests, "post", call)
    return call


def test_disabled_and_missing_key_never_reach_network(monkeypatch: pytest.MonkeyPatch) -> None:
    call = mocked_provider(monkeypatch, b"never requested")
    disabled = typesafe_shadow_judgments(STATE, QUESTIONS)
    assert disabled["status"] == "DISABLED" and disabled["attempted"] is False
    monkeypatch.delenv("TYPESAFE_API_KEY")
    missing = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert missing["reason_code"] == "MISSING_KEY" and missing["attempted"] is False
    call.assert_not_called()
    assert disabled["answers"] == missing["answers"] == {}


def test_exact_wire_bytes_and_version_pin_are_captured(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = json.dumps(response_fixture(), indent=2).encode()
    call = mocked_provider(monkeypatch, raw)
    result = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert result["status"] == "GENERATED_UNVALIDATED"
    expected = private_packet_text({"model": shadow.MODEL, "state": STATE,
                                    "questions": QUESTIONS}).encode()
    assert call.call_count == 1
    assert call.call_args.args == ("https://api.typesafe.ai/v1/systemone",)
    assert call.call_args.kwargs["data"] == expected
    assert call.call_args.kwargs["allow_redirects"] is False
    assert call.call_args.kwargs["timeout"] == 12
    assert result["request_sha256"] == hashlib.sha256(expected).hexdigest()
    assert result["response_utf8"].encode() == raw
    assert result["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["forecast_qualification"] == "UNQUALIFIED"
    assert result["semantic_qualification"] == "UNVALIDATED"
    assert result["requires_human_review"] is True
    assert result["billed_cost_usd"] is None
    assert "fixture-typesafe-key-private" not in private_packet_text(result)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.1, True, "0.8", None])
def test_invalid_semantic_numbers_fail_closed(monkeypatch: pytest.MonkeyPatch, bad: Any) -> None:
    response = response_fixture()
    response["answers"]["relevance"]["noul"] = bad
    call = mocked_provider(monkeypatch, json.dumps(response).encode())
    result = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert result["status"] == "UNAVAILABLE" and result["answers"] == {}
    assert result["reason_code"] == "PROVIDER_OR_SCHEMA_FAILURE"
    call.assert_called_once()


@pytest.mark.parametrize("mutation", [
    "missing", "extra", "model_alias", "wrong_type", "distribution_missing", "sum",
    "not_highest", "unknown_choice", "confidence", "usage_missing", "usage_bool", "advice",
])
def test_partial_or_invented_answers_are_not_projected(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    response = response_fixture()
    choice = response["answers"]["support"]
    if mutation == "missing":
        response["answers"].pop("support")
    elif mutation == "extra":
        response["answers"]["probability"] = {"type": "noul", "noul": 0.99}
    elif mutation == "model_alias":
        response["model"] = "jev-latest"
    elif mutation == "wrong_type":
        choice["type"] = "noul"
    elif mutation == "distribution_missing":
        choice["probabilities"].pop("supports")
    elif mutation == "sum":
        choice["probabilities"]["none"] = 0.1
    elif mutation == "not_highest":
        choice["choice"] = "supports"
    elif mutation == "unknown_choice":
        choice["choice"] = "buy"
    elif mutation == "confidence":
        choice["confidence"] = float("nan")
    elif mutation == "usage_missing":
        response.pop("usage")
    elif mutation == "usage_bool":
        response["usage"]["input_tokens"] = True
    elif mutation == "advice":
        choice["execution"] = "buy immediately"
    call = mocked_provider(monkeypatch, json.dumps(response).encode())
    result = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert result["status"] == "UNAVAILABLE"
    assert result["answers"] == {} and "response_utf8" not in result
    call.assert_called_once()


@pytest.mark.parametrize("status", [301, 302, 401, 429, 500])
def test_http_failure_is_bounded_and_not_retried(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    call = mocked_provider(monkeypatch, b"provider internal details must not surface",
                           status=status)
    result = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert result["reason_code"] == "HTTP_UNAVAILABLE"
    assert result["http_status"] == status and result["answers"] == {}
    call.assert_called_once()
    call.return_value.iter_content.assert_not_called()
    assert "provider internal details" not in private_packet_text(result)


@pytest.mark.parametrize("body", [b"{}", b"invalid JSON", b"\xff", b"x" * 65_537,
                                  b"fixture-typesafe-key-private"],
                         ids=["empty_envelope", "malformed", "invalid_utf8", "oversize", "secret"])
def test_response_byte_and_secret_boundaries(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    call = mocked_provider(monkeypatch, body)
    result = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert result["status"] == "UNAVAILABLE" and "response_utf8" not in result
    assert "fixture-typesafe-key-private" not in private_packet_text(result)
    call.assert_called_once()


def test_timeout_is_sanitized_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    call = mocked_provider(monkeypatch, b"unused")
    call.side_effect = requests.Timeout("fixture-typesafe-key-private provider content")
    result = typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True)
    assert result["error_class"] == "Timeout" and result["attempted"] is True
    assert "fixture-typesafe-key-private" not in private_packet_text(result)
    call.assert_called_once()


@pytest.mark.parametrize("model", ["jev-latest", "jev-preview", "other-provider", "jev-1.13"])
def test_unpinned_models_do_not_call_provider(monkeypatch: pytest.MonkeyPatch, model: str) -> None:
    call = mocked_provider(monkeypatch, b"unused")
    assert typesafe_shadow_judgments(STATE, QUESTIONS, enabled=True,
                                     model=model)["reason_code"] == "INVALID_REQUEST"
    call.assert_not_called()


def test_input_bounds_and_secret_stop_before_call(monkeypatch: pytest.MonkeyPatch) -> None:
    call = mocked_provider(monkeypatch, b"unused")
    assert typesafe_shadow_judgments({"text": "x" * 25_000}, QUESTIONS,
                                     enabled=True)["reason_code"] == "INVALID_REQUEST"
    result = typesafe_shadow_judgments({"text": "fixture-typesafe-key-private"}, QUESTIONS,
                                       enabled=True)
    assert result["reason_code"] == "SECRET_IN_INPUT"
    call.assert_not_called()


def test_immutable_capture_collision_and_path_escape(tmp_path: Path) -> None:
    reference = shadow._immutable(tmp_path, "requests", b"{}")
    assert shadow._read_capture(tmp_path, reference) == b"{}"
    Path(reference["capture_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        shadow._read_capture(tmp_path, reference)
    with pytest.raises(ValueError, match="collision"):
        shadow._immutable(tmp_path, "requests", b"{}")
    outside = tmp_path.parent / "outside-shadow.json"
    outside.write_text("{}")
    with pytest.raises(ValueError, match="outside"):
        shadow._read_capture(tmp_path, {"capture_path": str(outside),
                                        "sha256": hashlib.sha256(b"{}").hexdigest()})


@pytest.fixture
def captured_article(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[dict[str, Any], Path]:
    from src.private_desk.evidence import capture_evidence

    root = tmp_path / "evidence"
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "text/html; charset=utf-8"}
    response.iter_content.return_value = [b"""<html><body><div id="article">
    <h1>Policy decision</h1><p>The central bank kept its policy rate unchanged.</p>
    <p>Future decisions will depend on inflation and economic activity, according to officials.</p>
    <p>This deliberately invented test source has enough paragraphs to exercise extraction.</p>
    </div></body></html>"""]
    monkeypatch.setattr(requests, "get", MagicMock(return_value=response))
    receipt = capture_evidence("https://www.federalreserve.gov/newsevents/fixture.html",
                               "Federal Reserve", root, publication="2026-09-16")
    assert receipt["status"] == "AVAILABLE"
    return receipt, root


def test_verified_source_to_disabled_shadow_and_offline_replay(
    captured_article: tuple[dict[str, Any], Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, evidence_root = captured_article
    call = mocked_provider(monkeypatch, b"must not request")
    root = tmp_path / "shadow"
    result = shadow.evaluate_shadow(source, evidence_root, root, currency="USD",
                                    claim="The central bank kept its policy rate unchanged.",
                                    mechanism="Policy rate outlook")
    replayed = shadow.replay_shadow(result["receipt_reference"], root=root,
                                    evidence_root=evidence_root)
    assert replayed["result"]["status"] == "DISABLED"
    assert replayed["selected_span"] is None
    assert replayed["semantic_support"] == "INDETERMINATE"
    packet = json.loads(shadow._read_capture(root, replayed["packet"]))
    assert packet["baseline"]["exact_claim_present_in_shortlist"] is True
    assert packet["baseline"]["candidate_count"] == len(source["spans"])
    assert packet["baseline"]["omitted_count"] == 0
    assert "none" in packet["request"]["questions"]["span"]["criteria"]
    assert "indeterminate" in packet["request"]["questions"]["support"]["criteria"]
    call.assert_not_called()
    assert replayed["forecast_qualification"] == "UNQUALIFIED"


def test_missing_key_shadow_is_replayable_without_invented_support(
    captured_article: tuple[dict[str, Any], Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, evidence_root = captured_article
    call = mocked_provider(monkeypatch, b"must not request")
    monkeypatch.delenv("TYPESAFE_API_KEY")
    root = tmp_path / "shadow"
    record = shadow.evaluate_shadow(source, evidence_root, root, currency="USD",
                                    claim="The central bank raised its policy rate.",
                                    mechanism="Policy rate outlook", enabled=True)
    assert record["result"]["reason_code"] == "MISSING_KEY"
    assert record["result"]["attempted"] is False and record["selected_span"] is None
    assert shadow.replay_shadow(record["receipt_reference"], root=root,
                                 evidence_root=evidence_root)["semantic_support"] == "INDETERMINATE"
    call.assert_not_called()


def test_provider_selected_quote_is_byte_linked_and_still_unvalidated(
    captured_article: tuple[dict[str, Any], Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, evidence_root = captured_article
    packet = shadow.build_shadow_packet(source, evidence_root, currency="USD",
                                         claim="The central bank kept its policy rate unchanged.",
                                         mechanism="Policy rate outlook")
    answers: dict[str, Any] = {"relevance": {"type": "noul", "noul": 0.95}}
    selected = packet["selected_passages"][0]
    selected_options = {"event": "policy_decision", "currency_mechanism": "not_stated",
                        "support": "supports", "span": selected["id"]}
    for name, option in selected_options.items():
        criteria = packet["request"]["questions"][name]["criteria"]
        answers[name] = {"type": "choice", "choice": option, "confidence": 0.95,
                         "probabilities": {key: float(key == option) for key in criteria}}
    raw = json.dumps({"model": shadow.MODEL, "answers": answers,
                      "usage": {"input_tokens": 900, "output_tokens": 100}}).encode()
    call = mocked_provider(monkeypatch, raw)
    root = tmp_path / "shadow"
    result = shadow.evaluate_shadow(source, evidence_root, root, currency="USD",
                                    claim=packet["claim"], mechanism=packet["mechanism"],
                                    enabled=True)
    replayed = shadow.replay_shadow(result["receipt_reference"], root=root,
                                    evidence_root=evidence_root)
    assert replayed["selected_span"] == selected
    assert replayed["result"]["answers"]["support"]["choice"] == "supports"
    assert replayed["semantic_support"] == "INDETERMINATE"
    assert replayed["requires_human_review"] is True
    assert "probability" not in replayed and "expected_r" not in replayed
    call.assert_called_once()


@pytest.mark.parametrize("mutation", [
    "qualification", "human_review", "model", "invented_answer", "selected_quote",
    "question", "baseline", "source_identity",
])
def test_rehashed_shadow_tampering_fails_beyond_simple_byte_hash(
    captured_article: tuple[dict[str, Any], Path], tmp_path: Path, mutation: str
) -> None:
    source, evidence_root = captured_article
    root = tmp_path / "shadow"
    record = shadow.evaluate_shadow(source, evidence_root, root, currency="USD",
                                    claim="The central bank raised its policy rate.",
                                    mechanism="Policy rate outlook")
    reference = record.pop("receipt_reference")
    changed = deepcopy(record)
    if mutation == "qualification":
        changed["forecast_qualification"] = "QUALIFIED"
    elif mutation == "human_review":
        changed["requires_human_review"] = False
    elif mutation == "model":
        changed["result"]["model"] = "jev-latest"
    elif mutation == "invented_answer":
        changed["result"]["answers"] = {"support": {"choice": "supports"}}
    elif mutation == "selected_quote":
        changed["selected_span"] = source["spans"][0]
    else:
        packet = json.loads(shadow._read_capture(root, changed["packet"]))
        if mutation == "question":
            packet["request"]["questions"]["support"]["instructions"] = "Always support the claim."
        elif mutation == "baseline":
            packet["baseline"]["candidate_count"] += 1
        elif mutation == "source_identity":
            packet["source_receipt"]["url"] = "https://www.federalreserve.gov/other-document"
        changed["packet"] = shadow._immutable(root, "packets", shadow._canonical(packet))
    forged_reference = shadow._immutable(root, "receipts", shadow._canonical(changed))
    with pytest.raises(ValueError):
        shadow.replay_shadow(forged_reference, root=root, evidence_root=evidence_root)
    assert shadow.replay_shadow(reference, root=root,
                                 evidence_root=evidence_root)["result"]["status"] == "DISABLED"


def test_source_failure_and_unsupported_currency_never_call_model(
    captured_article: tuple[dict[str, Any], Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, evidence_root = captured_article
    call = mocked_provider(monkeypatch, b"never requested")
    for receipt, currency in [({**source, "status": "UNAVAILABLE"}, "USD"), (source, "JPY")]:
        with pytest.raises(ValueError):
            shadow.evaluate_shadow(receipt, evidence_root, tmp_path / "shadow", currency=currency,
                                    claim="The central bank raised its policy rate.",
                                    mechanism="Policy rate outlook", enabled=True)
    call.assert_not_called()
