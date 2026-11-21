"""Adversarial checks for capture integrity, privacy and source precision."""

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Any
from urllib.parse import quote

import pytest

from src.research.quote_capture import canonical_json, capture_quote_page, validate_quote_page

START = 1_788_134_400_000_000_000  # 2026-08-31 UTC; integer arithmetic only.
END = START + 86_400_000_000_000
RECEIPT = datetime(2026, 9, 27, 12, tzinfo=UTC)


def capture(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "pair": "EURUSD", "instrument": "C:EUR-USD", "window_start_ns": START,
        "window_end_ns": END, "page_index": 0,
        "requested_at": RECEIPT - timedelta(seconds=1), "received_at": RECEIPT,
        "status_code": 200, "body": b'{"status":"OK","results":[]}',
        "request_params": {"timestamp.gte": str(START), "timestamp.lt": str(END),
                           "sort": "timestamp", "order": "asc", "limit": "50000"},
        "response_headers": {"Content-Type": "application/json", "Server": "discard"},
    }
    arguments.update(overrides)
    return capture_quote_page(**arguments)


def resign(page: dict[str, Any]) -> dict[str, Any]:
    page["body_sha256"] = hashlib.sha256(page["body_text"].encode()).hexdigest()
    unsigned = {k: v for k, v in page.items() if k != "capture_sha256"}
    page["capture_sha256"] = hashlib.sha256(canonical_json(unsigned).encode()).hexdigest()
    return page


def test_exact_numeric_canonicalization_is_independent_of_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 3
        assert canonical_json({"z": Decimal("1.234567890123456789000"), "n": START}) == (
            '{"n":1788134400000000000,"z":1.234567890123456789}'
        )
        assert canonical_json([1, 1.0, Decimal("1.000"), -0.0]) == "[1,1,1,0]"
        assert canonical_json(Decimal("1e1000000")) == "1e1000000"
        assert canonical_json(10**25) == canonical_json(Decimal("1e25"))
        assert canonical_json("1") != canonical_json(1)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), Decimal("NaN"),
                                  {1: "key"}, {"tuple": (1,)}, object()])
def test_canonicalization_rejects_non_json_values(value: Any) -> None:
    with pytest.raises(ValueError):
        canonical_json(value)


def test_capture_preserves_exact_source_numbers_and_original_byte_fingerprint() -> None:
    raw = ('{"results":[{"participant_timestamp":' + str(START + 1)
           + ',"bid_price":1.234567890123456789}],"status":"OK"}').encode()
    page = capture(body=raw)
    assert str(START + 1) in page["body_text"]
    assert "1.234567890123456789" in page["body_text"]
    assert page["raw_body_sha256"] == hashlib.sha256(raw).hexdigest()
    assert page["raw_size_bytes"] == len(raw)
    assert page["issues"] == []
    validate_quote_page(page)


def test_credentials_and_literal_encoded_secrets_are_removed_from_retained_content() -> None:
    secret = "key /?+=&value"
    params = capture()["request_parameters"] | {"API-Key": secret}
    raw = json.dumps({"status": "OK", "results": [], "nested": {
        "access_token": "other-secret", "Authorization": "Bearer other-secret"},
        "message": f"raw {secret} encoded {quote(secret, safe='')}",
    }).encode()
    page = capture(body=raw, request_params=params, response_headers={
        "X-Request-ID": secret, "Set-Cookie": "cookie-value", "Other": "ignored",
    })
    retained = canonical_json(page)
    for excluded in (secret, quote(secret, safe=""), "other-secret", "cookie-value"):
        assert excluded not in retained
    assert page["response_headers"] == {"x-request-id": "[REDACTED]"}
    assert set(page["request_parameters"]) == set(capture()["request_parameters"])
    assert page["raw_body_sha256"] == hashlib.sha256(raw).hexdigest()


def test_encoded_secret_hex_case_and_overlapping_redactions() -> None:
    page = capture(body=b'{"message":"secret%2fvalue REDACTED"}',
                   secrets=["secret/value", "REDACTED"])
    assert json.loads(page["body_text"])["message"] == "[REDACTED] [REDACTED]"


def test_redaction_key_collision_fails_instead_of_losing_source_fields() -> None:
    with pytest.raises(ValueError, match="merge distinct"):
        capture(body=b'{"secret-one":1,"secret-two":2}', secrets=["secret-one", "secret-two"])


def test_opaque_cursor_is_hashed_and_never_retained() -> None:
    token = "opaque /token+123"
    url = f"https://api.massive.com/v3/quotes/C%3AEUR-USD?cursor={quote(token, safe='')}"
    page = capture(body=json.dumps({"status": "OK", "results": [], "next_url": url}).encode())
    assert page["next_cursor_sha256"] == hashlib.sha256(token.encode()).hexdigest()
    assert token not in canonical_json(page)
    assert quote(token, safe="") not in canonical_json(page)
    continuation = capture(page_index=1, request_params={"cursor": token})
    assert continuation["request_cursor_sha256"] == page["next_cursor_sha256"]
    assert continuation["request_parameters"] == {}
    assert page["issues"] == continuation["issues"] == []


def test_cursor_token_overlapping_schema_name_preserves_structure() -> None:
    page = capture(body=b'{"status":"OK","results":[],"next_url":'
                        b'"https://api.massive.com/v3/quotes/C:EUR-USD?cursor=next"}')
    body = json.loads(page["body_text"])
    assert "next_url" in body
    assert page["next_cursor_sha256"] == hashlib.sha256(b"next").hexdigest()
    assert page["issues"] == []


@pytest.mark.parametrize("timestamp", ["1788134400000000001.0", "1.788134400000000001e18",
                                       '"1788134400000000001"', "true"])
def test_numeric_normalization_cannot_disguise_invalid_timestamp_type(timestamp: str) -> None:
    raw = ('{"status":"OK","results":[{"participant_timestamp":' + timestamp
           + ',"bid_price":1,"ask_price":2}]}').encode()
    page = capture(body=raw)
    assert page["issues"] == ["non_integer_quote_timestamp"]


@pytest.mark.parametrize("url", [
    "http://api.massive.com/v3/quotes/C:EUR-USD?cursor=x",
    "https://evil.test/v3/quotes/C:EUR-USD?cursor=x",
    "https://user:password@api.massive.com/v3/quotes/C:EUR-USD?cursor=x",
    "https://api.massive.com:443/v3/quotes/C:EUR-USD?cursor=x",
    "https://api.massive.com/v3/quotes/C:USD-JPY?cursor=x",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=x#fragment",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=x&cursor=y",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=x&order=desc",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=x&unknown=key",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=%xx",
    "https://api.massive.com/v3/quotes/C:EUR-USD?cursor=x\n",
    42,
])
def test_hostile_next_urls_are_evidence_of_incomplete_acquisition(url: Any) -> None:
    page = capture(body=json.dumps({"status": "OK", "results": [], "next_url": url}).encode())
    assert page["issues"] == ["invalid_cursor"]
    assert page["next_cursor_sha256"] is None
    assert json.loads(page["body_text"])["next_url"] == "[INVALID_CURSOR]"
    validate_quote_page(page)


@pytest.mark.parametrize(("body", "issues"), [
    (b'{"status":"OK","results":[],"results":[]}', ["invalid_json"]),
    (b'{"value":NaN}', ["invalid_json"]),
    (b'{"value":Infinity}', ["invalid_json"]),
    (b'{"value":"\xff"}', ["invalid_utf8"]),
    (b'bad\xffkey-secret', ["invalid_utf8", "invalid_json"]),
    (b'<html>key-secret</html>', ["invalid_json"]),
])
def test_malformed_responses_preserve_redacted_evidence(body: bytes, issues: list[str]) -> None:
    page = capture(body=body, secrets=["key-secret"])
    assert page["issues"] == issues
    assert "key-secret" not in page["body_text"]
    validate_quote_page(page)


@pytest.mark.parametrize("override", [
    {"pair": "GBPUSD"}, {"instrument": "C:USD-JPY"}, {"window_start_ns": True},
    {"window_start_ns": START + 1}, {"window_end_ns": END - 1}, {"page_index": True},
    {"page_index": -1}, {"status_code": True}, {"status_code": 600},
    {"requested_at": RECEIPT.replace(tzinfo=None)},
    {"received_at": RECEIPT - timedelta(seconds=2)},
    {"body": "text"}, {"body": b"x" * (16 * 1024 * 1024 + 1)},
    {"request_params": {}}, {"page_index": 1, "request_params": {}},
    {"page_index": 1, "request_params": {"cursor": " "}},
    {"request_params": {"cursor": "initial-cursor"}}, {"secrets": "not-a-list"},
])
def test_capture_rejects_invalid_request_metadata(override: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        capture(**override)


@pytest.mark.parametrize("limit", ["0", "01", "50001", "-1", "1.0", "1e2"])
def test_page_limit_requires_canonical_bounded_integer(limit: str) -> None:
    params = capture()["request_parameters"] | {"limit": limit}
    with pytest.raises(ValueError):
        capture(request_params=params)


def test_input_mutation_does_not_mutate_capture_and_timezone_normalizes() -> None:
    params = capture()["request_parameters"]
    headers = {"content-type": "application/json"}
    page = capture(request_params=params, response_headers=headers, received_at=RECEIPT.astimezone(
        timezone(timedelta(hours=5, minutes=30))))
    before = copy.deepcopy(page)
    params["limit"] = "1"
    headers["content-type"] = "modified"
    assert page == before
    assert page["received_at"] == RECEIPT.isoformat()


@pytest.mark.parametrize(("field", "value"), [
    ("body_text", '{"results":[1],"status":"OK"}'), ("raw_size_bytes", 1),
    ("http_status", 500), ("pair", "USDJPY"), ("requested_at", "2026-09-27T00:00:00+00:00"),
    ("capture_sha256", ""), ("body_sha256", "0" * 64), ("raw_body_sha256", "0" * 64),
])
def test_tampering_is_rejected(field: str, value: Any) -> None:
    page = capture()
    page[field] = value
    with pytest.raises(ValueError):
        validate_quote_page(page)


@pytest.mark.parametrize(("field", "value"), [
    ("version", "unsupported"), ("page_index", True), ("http_status", True),
    ("request_cursor_sha256", "0" * 64), ("next_cursor_sha256", "0" * 64),
    ("issues", ["unknown"]), ("issues", ["invalid_json", "invalid_json"]),
    ("response_headers", {"set-cookie": "leak"}), ("raw_size_bytes", -1),
    ("window_start_ns", "0" + str(START)), ("received_at", "2026-09-27T12:00:00Z"),
    ("request_parameters", {"apiKey": "leak"}),
])
def test_structural_corruption_is_rejected_even_with_recomputed_hashes(
    field: str, value: Any,
) -> None:
    page = capture()
    page[field] = value
    with pytest.raises(ValueError):
        validate_quote_page(resign(page))


def test_hashes_are_integrity_not_provider_authentication() -> None:
    page = capture()
    page["body_text"] = '{"results":[],"status":"CHANGED"}'
    # A party able to replace the entire record can recompute it; storage must be immutable.
    validate_quote_page(resign(page))


def test_malformed_nul_diagnostics_remain_storable_with_original_byte_identity() -> None:
    raw = b'upstream failure\x00diagnostic'
    page = capture(body=raw, response_headers={"x-request-id": "request\x00id\ud800"})
    assert page["body_text"] == r"upstream failure\u0000diagnostic"
    assert page["response_headers"]["x-request-id"] == r"request\u0000id\ud800"
    assert page["raw_body_sha256"] == hashlib.sha256(raw).hexdigest()
    assert page["raw_size_bytes"] == len(raw)
    assert page["issues"] == ["invalid_json", "text_storage_escaped"]
    validate_quote_page(page)


def test_valid_json_controls_are_explicitly_sanitized_without_changing_numeric_values() -> None:
    page = capture(body=b'{"status":"OK","results":[],"note":"\\u0000\\ud800"}')
    assert json.loads(page["body_text"])["note"] == r"\u0000\ud800"
    assert "\x00" not in page["body_text"]
    assert page["issues"] == ["text_storage_escaped"]
    validate_quote_page(page)


def test_exceptional_json_keys_are_sanitized_and_collisions_are_rejected() -> None:
    raw = b'{"status":"OK","results":[],"\\u0000":1.1234567890123456789,"\\ud800":2}'
    page = capture(body=raw)
    parsed = json.loads(page["body_text"], parse_float=Decimal)
    assert parsed[r"\u0000"] == Decimal("1.1234567890123456789")
    assert parsed[r"\ud800"] == 2
    assert page["raw_body_sha256"] == hashlib.sha256(raw).hexdigest()
    assert page["issues"] == ["text_storage_escaped"]
    with pytest.raises(ValueError, match="merge distinct"):
        capture(body=b'{"\\u0000":1,"\\\\u0000":2}')


def test_unsanitized_nested_json_controls_are_rejected_even_with_recomputed_hash() -> None:
    page = capture()
    page["body_text"] = '{"note":"\\u0000","results":[],"status":"OK"}'
    with pytest.raises(ValueError, match="Unsupported character"):
        validate_quote_page(resign(page))


@pytest.mark.parametrize("field", ["body_text", "response_headers"])
def test_forged_unrepresentable_text_rejected_even_with_recomputed_hash(field: str) -> None:
    page = capture()
    if field == "body_text":
        page[field] = "invalid\x00json"
        page["issues"] = ["invalid_json"]
    else:
        page[field] = {"x-request-id": "invalid\x00header"}
    with pytest.raises(ValueError, match="Unsupported"):
        validate_quote_page(resign(page))
