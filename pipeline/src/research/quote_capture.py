"""Pure, credential-redacted capture manifests for a candidate FX quote series."""

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, quote, quote_plus, unquote, urlsplit

_DAY_NS = 86_400_000_000_000
_MAX_BODY = 16 * 1024 * 1024
_INSTRUMENTS = {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}
_FIXED = {"timestamp.gte", "timestamp.lt", "sort", "order", "limit"}
_SENSITIVE = {
    "apikey", "authorization", "cookie", "setcookie", "password", "token",
    "accesstoken", "refreshtoken", "secret", "clientsecret", "crumb",
}
_ISSUES = ("invalid_utf8", "invalid_json", "invalid_cursor", "non_integer_quote_timestamp",
           "text_storage_escaped")
_FIELDS = {
    "version", "provider", "pair", "instrument", "window_start_ns", "window_end_ns",
    "page_index", "request_parameters", "request_cursor_sha256", "requested_at",
    "received_at", "http_status", "response_headers", "body_text", "raw_body_sha256",
    "body_sha256", "raw_size_bytes", "next_cursor_sha256", "issues", "capture_sha256",
}


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("JSON numbers must be finite")
    if not value:
        return "0"
    sign, digits, exponent = value.as_tuple()
    assert isinstance(exponent, int)
    coefficient = "".join(map(str, digits))
    trimmed = coefficient.rstrip("0")
    exponent += len(coefficient) - len(trimmed)
    coefficient = trimmed
    adjusted = len(coefficient) + exponent - 1
    prefix = "-" if sign else ""
    if adjusted < -6 or adjusted > 20:
        mantissa = coefficient[0] + ("." + coefficient[1:] if len(coefficient) > 1 else "")
        return f"{prefix}{mantissa}e{adjusted}"
    position = len(coefficient) + exponent
    if position <= 0:
        return prefix + "0." + "0" * -position + coefficient
    if position >= len(coefficient):
        return prefix + coefficient + "0" * (position - len(coefficient))
    return prefix + coefficient[:position] + "." + coefficient[position:]


def canonical_json(value: Any) -> str:
    """Serialize strict JSON, normalizing numbers without Decimal-context rounding."""
    def encode(item: Any, depth: int) -> str:
        if depth > 100:
            raise ValueError("JSON nesting exceeds capture limit")
        if item is None:
            return "null"
        if isinstance(item, bool):
            return "true" if item else "false"
        if isinstance(item, str):
            # ASCII escaping also makes lone JSON surrogates safe to fingerprint.
            return json.dumps(item, ensure_ascii=True)
        if isinstance(item, (int, Decimal)):
            return _decimal_text(Decimal(item))
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("JSON numbers must be finite")
            return _decimal_text(Decimal(str(item)))
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("JSON object keys must be strings")
            return "{" + ",".join(
                encode(key, depth + 1) + ":" + encode(item[key], depth + 1)
                for key in sorted(item)
            ) + "}"
        if isinstance(item, list):
            return "[" + ",".join(encode(child, depth + 1) for child in item) + "]"
        raise ValueError("Unsupported JSON value")

    return encode(value, 0)


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _storable_text(value: str) -> str:
    """Escape characters PostgreSQL TEXT cannot represent; preserve other text."""
    return re.sub(r"[\x00\ud800-\udfff]", lambda match: f"\\u{ord(match[0]):04x}", value)


def _json_storage_safe(value: Any) -> bool:
    if isinstance(value, str):
        return _storable_text(value) == value
    if isinstance(value, dict):
        return all(_storable_text(key) == key and _json_storage_safe(child)
                   for key, child in value.items())
    if isinstance(value, list):
        return all(_json_storage_safe(child) for child in value)
    return True


def _sensitive(key: str) -> bool:
    return key.replace("_", "").replace("-", "").casefold() in _SENSITIVE


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Capture timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _integer(value: Any, minimum: int, maximum: int | None = None) -> bool:
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def _metadata(pair: Any, instrument: Any, start: Any, end: Any, index: Any) -> None:
    if not isinstance(pair, str) or pair not in _INSTRUMENTS:
        raise ValueError("Unsupported FX pair")
    if instrument != _INSTRUMENTS[pair]:
        raise ValueError("Instrument does not match pair")
    if not _integer(start, 0) or not _integer(end, 1):
        raise ValueError("Window bounds must be integer nanoseconds")
    if end - start != _DAY_NS or start % _DAY_NS:
        raise ValueError("Capture window must be one aligned UTC day")
    if not _integer(index, 0):
        raise ValueError("Page index must be a nonnegative integer")


def _parameters(parameters: Any, start: int, end: int, *, initial: bool) -> None:
    if not isinstance(parameters, Mapping) or any(
        not isinstance(k, str) or not isinstance(v, str) for k, v in parameters.items()
    ):
        raise ValueError("Request parameters must be string pairs")
    if not set(parameters) <= _FIXED or (initial and set(parameters) != _FIXED):
        raise ValueError("Unexpected or missing request parameters")
    expected = {"timestamp.gte": str(start), "timestamp.lt": str(end),
                "sort": "timestamp", "order": "asc"}
    for key, value in parameters.items():
        if key == "limit":
            if not re.fullmatch(r"[1-9][0-9]{0,4}", value) or int(value) > 50000:
                raise ValueError("Invalid quote page limit")
        elif value != expected[key]:
            raise ValueError("Request parameters disagree with capture window")


def _parse_json(body: str) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> Any:
        raise ValueError("Non-finite JSON number")

    return json.loads(body, parse_float=Decimal, object_pairs_hook=object_pairs,
                      parse_constant=invalid_constant)


def _cursor(url: Any, instrument: str, start: int, end: int) -> tuple[str, str]:
    if not isinstance(url, str) or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise ValueError("Invalid next cursor URL")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or parsed.netloc not in {"api.massive.com", "api.polygon.io"}
        or parsed.fragment or unquote(parsed.path) != f"/v3/quotes/{instrument}"
        or re.search(r"%(?![0-9a-fA-F]{2})", parsed.query)
    ):
        raise ValueError("Invalid next cursor URL")
    pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True,
                      encoding="utf-8", errors="strict")
    if len({k for k, _ in pairs}) != len(pairs):
        raise ValueError("Duplicate cursor query parameter")
    parameters = {k: v for k, v in pairs if not _sensitive(k)}
    token = parameters.pop("cursor", None)
    if not token or not token.strip():
        raise ValueError("Missing cursor")
    _parameters(parameters, start, end, initial=False)
    safe = f"https://{parsed.netloc}/v3/quotes/{instrument}?cursor=[REDACTED]"
    return token, safe


def capture_quote_page(
    *, pair: str, instrument: str, window_start_ns: int, window_end_ns: int,
    page_index: int, requested_at: datetime, received_at: datetime, status_code: int,
    body: bytes, request_params: Mapping[str, str], response_headers: Mapping[str, str],
    secrets: Sequence[str] = (),
) -> dict[str, Any]:
    """Capture one supplied response; never fetch, follow URLs, or qualify a price."""
    _metadata(pair, instrument, window_start_ns, window_end_ns, page_index)
    requested, received = _aware(requested_at), _aware(received_at)
    if received < requested or not _integer(status_code, 100, 599):
        raise ValueError("Invalid capture receipt or HTTP status")
    if not isinstance(body, bytes) or len(body) > _MAX_BODY:
        raise ValueError("Capture body must be bytes within the size limit")
    if (not isinstance(secrets, Sequence) or isinstance(secrets, (str, bytes))
            or any(not isinstance(s, str) for s in secrets)):
        raise ValueError("Secrets must be a sequence of strings")
    for mapping in (request_params, response_headers):
        if not isinstance(mapping, Mapping) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()
        ):
            raise ValueError("Headers and parameters must be string pairs")
    known_secrets = list(secrets) + [
        v for mapping in (request_params, response_headers)
        for k, v in mapping.items() if _sensitive(k)
    ]
    parameters = {k: v for k, v in request_params.items() if not _sensitive(k)}
    token = parameters.pop("cursor", None)
    if page_index == 0 and token is not None:
        raise ValueError("Initial page cannot have a cursor")
    if page_index > 0 and (token is None or not token.strip()):
        raise ValueError("Continuation page requires a cursor")
    cursor_tokens = [token] if token else []
    _parameters(parameters, window_start_ns, window_end_ns, initial=page_index == 0)
    issues: list[str] = []
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        decoded = body.decode("utf-8", errors="replace")
        issues.append("invalid_utf8")
    parsed: Any = None
    is_json = True
    try:
        parsed = _parse_json(decoded)
        canonical_json(parsed)
    except (ValueError, RecursionError, OverflowError):
        issues.append("invalid_json")
        is_json = False
    next_hash = None
    safe_next = None
    if is_json and isinstance(parsed, dict) and parsed.get("next_url") is not None:
        try:
            next_token, safe_next = _cursor(
                parsed["next_url"], instrument, window_start_ns, window_end_ns,
            )
            cursor_tokens.append(next_token)
            next_hash = _hash(next_token.encode("utf-8"))
        except (ValueError, UnicodeError):
            issues.append("invalid_cursor")
            safe_next = "[INVALID_CURSOR]"
    if is_json and isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
        if any(isinstance(row, dict) and "participant_timestamp" in row
               and type(row["participant_timestamp"]) is not int for row in parsed["results"]):
            issues.append("non_integer_quote_timestamp")

    def secret_forms(values: Sequence[str]) -> list[str]:
        return sorted({form for secret in values if secret for form in (
            secret, quote(secret, safe=""), quote_plus(secret, safe=""),
        )}, key=lambda text: (-len(text), text))

    forms = secret_forms(known_secrets)
    value_forms = secret_forms(known_secrets + cursor_tokens)

    def pattern(items: list[str]) -> re.Pattern[str] | None:
        # Percent escape hex digits are case-insensitive; the secret itself is not.
        def escape_hex(match: re.Match[str]) -> str:
            return "%" + "".join(
                f"[{c.lower()}{c.upper()}]" if c.isalpha() else c for c in match[1]
            )
        expressions = [re.sub(r"%([0-9a-fA-F]{2})", escape_hex, re.escape(item)) for item in items]
        return re.compile("|".join(expressions)) if expressions else None

    key_pattern, value_pattern = pattern(forms), pattern(value_forms)
    storage_escaped = False

    def storage_text(value: str) -> str:
        nonlocal storage_escaped
        retained = _storable_text(value)
        storage_escaped = storage_escaped or retained != value
        return retained

    def redact(text: str, *, key: bool = False) -> str:
        selected = key_pattern if key else value_pattern
        return selected.sub("[REDACTED]", text) if selected is not None else text

    def sanitize(value: Any, *, root: bool = False) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, child in value.items():
                clean_key = storage_text(redact(key, key=True))
                if clean_key in result:
                    raise ValueError("Redaction would merge distinct JSON keys")
                if _sensitive(key):
                    result[clean_key] = "[REDACTED]"
                elif key == "next_url" and child is not None:
                    result[clean_key] = safe_next if root else "[REDACTED]"
                else:
                    result[clean_key] = sanitize(child)
            return result
        if isinstance(value, list):
            return [sanitize(child) for child in value]
        return storage_text(redact(value)) if isinstance(value, str) else value

    body_text = storage_text(
        canonical_json(sanitize(parsed, root=True)) if is_json else redact(decoded)
    )
    headers: dict[str, str] = {}
    for key, value in response_headers.items():
        normalized = key.casefold()
        if normalized in {"content-type", "x-request-id"}:
            if normalized in headers:
                raise ValueError("Duplicate retained response header")
            headers[normalized] = storage_text(redact(value))
    if storage_escaped:
        issues.append("text_storage_escaped")
    manifest: dict[str, Any] = {
        "version": "quote-page-v1", "provider": "massive", "pair": pair,
        "instrument": instrument, "window_start_ns": str(window_start_ns),
        "window_end_ns": str(window_end_ns), "page_index": page_index,
        "request_parameters": parameters,
        "request_cursor_sha256": _hash(token.encode("utf-8")) if token else None,
        "requested_at": requested.isoformat(), "received_at": received.isoformat(),
        "http_status": status_code, "response_headers": headers, "body_text": body_text,
        "raw_body_sha256": _hash(body), "body_sha256": _hash(body_text.encode("utf-8")),
        "raw_size_bytes": len(body), "next_cursor_sha256": next_hash, "issues": issues,
    }
    manifest["capture_sha256"] = _hash(canonical_json(manifest).encode("utf-8"))
    validate_quote_page(manifest)
    return manifest


def validate_quote_page(page: Mapping[str, Any]) -> None:
    """Check schema and internal fingerprints, not provider authenticity or finality."""
    if not isinstance(page, Mapping) or set(page) != _FIELDS:
        raise ValueError("Invalid quote capture fields")
    if page["version"] != "quote-page-v1" or page["provider"] != "massive":
        raise ValueError("Unsupported capture version or provider")
    bounds = []
    for field in ("window_start_ns", "window_end_ns"):
        value = page[field]
        if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]*", value):
            raise ValueError("Window bounds must be canonical integer strings")
        bounds.append(int(value))
    _metadata(page["pair"], page["instrument"], bounds[0], bounds[1], page["page_index"])
    _parameters(page["request_parameters"], *bounds, initial=page["page_index"] == 0)
    times = []
    for field in ("requested_at", "received_at"):
        value = page[field]
        if not isinstance(value, str):
            raise ValueError("Invalid capture timestamp")
        parsed = _aware(datetime.fromisoformat(value))
        if parsed.isoformat() != value:
            raise ValueError("Capture timestamp must use canonical UTC ISO format")
        times.append(parsed)
    if times[1] < times[0] or not _integer(page["http_status"], 100, 599):
        raise ValueError("Invalid capture receipt or HTTP status")
    if not _integer(page["raw_size_bytes"], 0, _MAX_BODY):
        raise ValueError("Invalid raw response size")
    for field in ("raw_body_sha256", "body_sha256", "capture_sha256",
                  "request_cursor_sha256", "next_cursor_sha256"):
        value = page[field]
        if value is None and field in {"request_cursor_sha256", "next_cursor_sha256"}:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Invalid capture fingerprint")
    if (page["request_cursor_sha256"] is None) != (page["page_index"] == 0):
        raise ValueError("Request cursor disagrees with page index")
    headers = page["response_headers"]
    if not isinstance(headers, Mapping) or not set(headers) <= {"content-type", "x-request-id"}:
        raise ValueError("Unexpected retained header")
    if any(not isinstance(v, str) for v in headers.values()):
        raise ValueError("Invalid retained header")
    if any(_storable_text(value) != value for value in headers.values()):
        raise ValueError("Unsupported retained header character")
    issues = page["issues"]
    if not isinstance(issues, list) or issues != [i for i in _ISSUES if i in issues]:
        raise ValueError("Invalid capture issues")
    body = page["body_text"]
    if not isinstance(body, str):
        raise ValueError("Invalid capture body")
    if _storable_text(body) != body:
        raise ValueError("Unsupported capture body character")
    try:
        parsed_body = _parse_json(body)
        encoded = canonical_json(parsed_body)
    except (ValueError, RecursionError, OverflowError):
        if "invalid_json" not in issues:
            raise ValueError("Unreported invalid capture JSON") from None
        if page["next_cursor_sha256"] is not None or "invalid_cursor" in issues:
            raise ValueError("Invalid JSON cannot establish cursor evidence") from None
    else:
        if "invalid_json" not in issues and encoded != body:
            raise ValueError("Capture JSON is not canonical")
        if "invalid_json" not in issues and not _json_storage_safe(parsed_body):
            raise ValueError("Unsupported character in capture JSON strings")
        next_url = parsed_body.get("next_url") if isinstance(parsed_body, dict) else None
        if "invalid_cursor" in issues:
            if next_url != "[INVALID_CURSOR]" or page["next_cursor_sha256"] is not None:
                raise ValueError("Inconsistent invalid cursor evidence")
        elif next_url is not None:
            safe_urls = {
                f"https://{host}/v3/quotes/{page['instrument']}?cursor=[REDACTED]"
                for host in ("api.massive.com", "api.polygon.io")
            }
            if (not isinstance(next_url, str) or next_url not in safe_urls
                    or page["next_cursor_sha256"] is None):
                raise ValueError("Inconsistent next cursor evidence")
        elif page["next_cursor_sha256"] is not None:
            raise ValueError("Missing next cursor evidence")
    if _hash(body.encode("utf-8")) != page["body_sha256"]:
        raise ValueError("Capture body fingerprint mismatch")
    unsigned = {key: value for key, value in page.items() if key != "capture_sha256"}
    if _hash(canonical_json(unsigned).encode("utf-8")) != page["capture_sha256"]:
        raise ValueError("Capture fingerprint mismatch")
