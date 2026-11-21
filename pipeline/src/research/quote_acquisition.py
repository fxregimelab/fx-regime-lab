"""Bounded HTTP acquisition with durable, credential-free attempt evidence."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
import uuid
from collections.abc import AsyncIterator, Callable, Mapping
from datetime import UTC, date, datetime
from datetime import time as datetime_time
from decimal import Decimal
from typing import Any, Protocol, cast
from urllib.parse import parse_qsl, unquote, urlsplit

import aiohttp

from src.research.quote_attempt import (
    CLIENT_VERSION,
    DEFAULT_LIMITS,
    make_quote_acquisition_event,
    quote_runtime_manifest,
)
from src.research.quote_capture import canonical_json, capture_quote_page
from src.research.quote_reference import build_quote_reference

_DAY_NS = 86_400_000_000_000
_INSTRUMENTS = {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}
_LIMIT_RANGES = {
    "max_pages": (1, 10_000),
    "max_page_bytes": (1, 16_777_216),
    "max_total_bytes": (1, 268_435_456),
    "deadline_seconds": (1, 3_600),
    "request_timeout_seconds": (1, 60),
}


class QuoteResponse(Protocol):
    """Minimal streaming response required by the acquisition engine."""

    status: int
    headers: Mapping[str, str]

    def iter_chunks(self) -> AsyncIterator[bytes]: ...

    async def close(self) -> None: ...


class QuoteTransport(Protocol):
    """Injected page-opening boundary; transports never choose the request target."""

    async def open_page(
        self, url: str, *, params: Mapping[str, str], timeout_seconds: float
    ) -> QuoteResponse: ...


class _AiohttpResponse:
    def __init__(self, response: aiohttp.ClientResponse) -> None:
        self._response = response
        self.status = response.status
        self.headers: Mapping[str, str] = dict(response.headers)

    async def iter_chunks(self) -> AsyncIterator[bytes]:
        async for chunk in self._response.content.iter_chunked(64 * 1024):
            yield bytes(chunk)

    async def close(self) -> None:
        self._response.release()
        await self._response.wait_for_close()


class _AiohttpTransport:
    def __init__(self) -> None:
        self._session = aiohttp.ClientSession(
            trust_env=False,
            cookie_jar=aiohttp.DummyCookieJar(),
            raise_for_status=False,
        )
        # aiohttp 3.13 retries one idempotent request after a persistent-connection
        # disconnect by default. This acquisition contract records one request only.
        self._session._retry_connection = False

    async def open_page(
        self, url: str, *, params: Mapping[str, str], timeout_seconds: float
    ) -> QuoteResponse:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        response = await self._session.get(
            url,
            params=dict(params),
            timeout=timeout,
            allow_redirects=False,
            ssl=True,
            proxy=None,
        )
        return _AiohttpResponse(response)

    async def close(self) -> None:
        await self._session.close()


class _StopAcquisitionError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


def _limits(value: Mapping[str, int] | None) -> dict[str, int]:
    if value is None:
        result = dict(DEFAULT_LIMITS)
    else:
        if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
            raise ValueError("Quote limits must be a mapping")
        if not set(value) <= set(DEFAULT_LIMITS):
            raise ValueError("Quote limits contain unknown fields")
        result = {**DEFAULT_LIMITS, **value}
    for name, (minimum, maximum) in _LIMIT_RANGES.items():
        selected = result[name]
        if type(selected) is not int or not minimum <= selected <= maximum:
            raise ValueError(f"Invalid quote limit: {name}")
    if result["max_total_bytes"] < result["max_page_bytes"]:
        raise ValueError("max_total_bytes must be at least max_page_bytes")
    return result


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Quote acquisition clocks must return aware datetimes")
    return value.astimezone(UTC)


def _strict_json(body: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def invalid_constant(_: str) -> Any:
        raise ValueError("non-finite number")

    return json.loads(
        body.decode("utf-8"),
        parse_float=Decimal,
        object_pairs_hook=pairs,
        parse_constant=invalid_constant,
    )


def _next_cursor(body: bytes, capture: Mapping[str, Any], instrument: str) -> str | None:
    try:
        payload = _strict_json(body)
    except (
        UnicodeError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        RecursionError,
        OverflowError,
    ):
        raise _StopAcquisitionError("invalid_response") from None
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise _StopAcquisitionError("invalid_response")
    if "results" not in payload or not isinstance(payload["results"], list):
        raise _StopAcquisitionError("invalid_response")
    next_url = payload.get("next_url")
    if next_url is None:
        if capture["next_cursor_sha256"] is not None:
            raise _StopAcquisitionError("invalid_response")
        return None
    if not isinstance(next_url, str):
        raise _StopAcquisitionError("invalid_response")
    try:
        parsed = urlsplit(next_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc not in {"api.massive.com", "api.polygon.io"}
            or parsed.fragment
            or unquote(parsed.path) != f"/v3/quotes/{instrument}"
        ):
            raise ValueError
        query = parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            encoding="utf-8",
            errors="strict",
        )
        if len({key for key, _ in query}) != len(query):
            raise ValueError
        cursor = dict(query).get("cursor")
        if not cursor or not cursor.strip():
            raise ValueError
        fingerprint = hashlib.sha256(cursor.encode("utf-8")).hexdigest()
        if fingerprint != capture["next_cursor_sha256"]:
            raise ValueError
    except (UnicodeError, ValueError):
        raise _StopAcquisitionError("invalid_response") from None
    return cursor


def _event_receipt(event: Mapping[str, Any], receipt: Any) -> bool:
    return bool(
        isinstance(receipt, Mapping)
        and set(receipt) == {"event_sha256", "attempt_id", "sequence", "inserted"}
        and receipt["event_sha256"] == event["event_sha256"]
        and receipt["attempt_id"] == event["attempt_id"]
        and type(receipt["sequence"]) is int
        and receipt["sequence"] == event["sequence"]
        and type(receipt["inserted"]) is bool
    )


def _capture_receipt(capture: Mapping[str, Any], receipt: Any) -> bool:
    return bool(
        isinstance(receipt, Mapping)
        and set(receipt) == {"capture_sha256", "inserted"}
        and receipt["capture_sha256"] == capture["capture_sha256"]
        and type(receipt["inserted"]) is bool
    )


def _snapshot_receipt(page_count: int, expected_sha256: str, receipt: Any) -> str | None:
    if not (
        isinstance(receipt, Mapping)
        and set(receipt) == {"snapshot_sha256", "inserted", "capture_count"}
        and isinstance(receipt["snapshot_sha256"], str)
        and receipt["snapshot_sha256"] == expected_sha256
        and type(receipt["inserted"]) is bool
        and type(receipt["capture_count"]) is int
        and receipt["capture_count"] == page_count
    ):
        return None
    return receipt["snapshot_sha256"]


def _snapshot_sha256(
    reference: Mapping[str, Any], *, implementation_sha256: str
) -> str:
    unsigned = canonical_json(
        {
            "version": "quote-snapshot-v1",
            "implementation_sha256": implementation_sha256,
            "client_version": CLIENT_VERSION,
            "reference": reference,
        }
    )
    return hashlib.sha256(unsigned.encode("utf-8")).hexdigest()


async def acquire_quotes(
    *,
    pair: str,
    day: date,
    api_key: str,
    attempt_id: str,
    limits: Mapping[str, int] | None = None,
    transport: QuoteTransport | None = None,
    now: Callable[[], datetime] | None = None,
    monotonic: Callable[[], float] | None = None,
    persist_event: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    persist_capture: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    persist_snapshot: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Acquire one closed UTC day and return only a receipt-verified terminal event."""
    clock = now or (lambda: datetime.now(UTC))
    monotonic_clock = monotonic or time.monotonic
    first_now = _utc(clock())
    try:
        first_tick = float(monotonic_clock())
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Quote monotonic clock must return a finite number") from None
    if not math.isfinite(first_tick):
        raise ValueError("Quote monotonic clock must return a finite number")
    if not isinstance(pair, str) or pair not in _INSTRUMENTS:
        raise ValueError("Unsupported FX pair")
    if type(day) is not date or day < date(1970, 1, 1) or day >= first_now.date():
        raise ValueError("Quote day must be a closed UTC date")
    if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 512:
        raise ValueError("A nonblank bounded API key is required")
    try:
        canonical_attempt = str(uuid.UUID(attempt_id))
    except (AttributeError, TypeError, ValueError):
        raise ValueError("attempt_id must be a canonical lowercase UUID") from None
    if canonical_attempt != attempt_id:
        raise ValueError("attempt_id must be a canonical lowercase UUID")
    selected_limits = _limits(limits)
    manifest_json, implementation_sha256 = quote_runtime_manifest()

    if persist_event is None or persist_capture is None or persist_snapshot is None:
        from src.db.writer import (
            archive_quote_acquisition_event,
            archive_quote_capture,
            archive_quote_snapshot,
        )

        persist_event = persist_event or archive_quote_acquisition_event
        persist_capture = persist_capture or archive_quote_capture
        persist_snapshot = persist_snapshot or archive_quote_snapshot

    instrument = _INSTRUMENTS[pair]
    start_datetime = datetime.combine(day, datetime_time(), tzinfo=UTC)
    window_start_ns = int(start_datetime.timestamp()) * 1_000_000_000
    window_end_ns = window_start_ns + _DAY_NS
    common = {
        "attempt_id": attempt_id,
        "pair": pair,
        "instrument": instrument,
        "window_start_ns": str(window_start_ns),
        "window_end_ns": str(window_end_ns),
        "implementation_sha256": implementation_sha256,
        "client_version": CLIENT_VERSION,
        "runtime_manifest_json": manifest_json,
        "limits": selected_limits,
    }
    started = make_quote_acquisition_event(
        common,
        sequence=0,
        previous_event_sha256=None,
        kind="started",
        occurred_at=first_now,
    )
    try:
        started_receipt = persist_event(started)
    except Exception:
        raise RuntimeError("Quote acquisition could not record its start") from None
    if not _event_receipt(started, started_receipt) or not started_receipt["inserted"]:
        raise RuntimeError("Quote acquisition start was not newly acknowledged") from None

    created_transport = transport is None
    active_transport: QuoteTransport | None = transport
    response: QuoteResponse | None = None
    pages: list[Mapping[str, Any]] = []
    total_bytes = 0
    previous_hash = cast(str, started["event_sha256"])
    previous_time = first_now
    last_tick = first_tick
    cursor: str | None = None
    reason = "completed"
    snapshot_sha256: str | None = None
    page_event_uncertain = False
    transport_cleanup_failed = False
    cleanup_clock_invalid = False

    def tick() -> tuple[float, float]:
        nonlocal last_tick
        try:
            current = float(monotonic_clock())
        except (TypeError, ValueError, OverflowError):
            raise _StopAcquisitionError("clock_invalid") from None
        if not math.isfinite(current) or current < last_tick:
            raise _StopAcquisitionError("clock_invalid")
        last_tick = current
        remaining = selected_limits["deadline_seconds"] - (current - first_tick)
        if remaining <= 0:
            raise _StopAcquisitionError("time_budget")
        return current, remaining

    def wall_time() -> datetime:
        nonlocal previous_time
        try:
            current = _utc(clock())
        except (TypeError, ValueError, OverflowError):
            raise _StopAcquisitionError("clock_invalid") from None
        if current < previous_time:
            raise _StopAcquisitionError("clock_invalid")
        previous_time = current
        return current

    def failure_reason(default: str) -> str:
        """Classify observed clock exhaustion without relabeling immediate I/O failures."""
        nonlocal last_tick
        try:
            current = float(monotonic_clock())
        except (TypeError, ValueError, OverflowError):
            return "clock_invalid"
        if not math.isfinite(current) or current < last_tick:
            return "clock_invalid"
        last_tick = current
        if current - first_tick >= selected_limits["deadline_seconds"]:
            return "time_budget"
        return default

    def cleanup_timeout() -> float:
        nonlocal cleanup_clock_invalid, last_tick
        try:
            current = float(monotonic_clock())
            if not math.isfinite(current) or current < last_tick:
                cleanup_clock_invalid = True
                remaining = 0.0
            else:
                last_tick = current
                remaining = selected_limits["deadline_seconds"] - (current - first_tick)
        except (TypeError, ValueError, OverflowError):
            cleanup_clock_invalid = True
            remaining = 0.0
        # One millisecond is reserved for best-effort cleanup after exhaustion; this
        # keeps a hostile close await bounded without hiding the original result.
        return max(0.001, min(float(selected_limits["request_timeout_seconds"]), remaining))

    try:
        if active_transport is None:
            try:
                active_transport = _AiohttpTransport()
            except Exception:
                raise _StopAcquisitionError("request_failed") from None
        for page_index in range(selected_limits["max_pages"]):
            _, remaining = tick()
            requested_at = wall_time()
            params = (
                {
                    "timestamp.gte": str(window_start_ns),
                    "timestamp.lt": str(window_end_ns),
                    "sort": "timestamp",
                    "order": "asc",
                    "limit": "50000",
                    "apiKey": api_key,
                }
                if cursor is None
                else {"cursor": cursor, "apiKey": api_key}
            )
            timeout_seconds = min(float(selected_limits["request_timeout_seconds"]), remaining)
            try:
                response = await asyncio.wait_for(
                    active_transport.open_page(
                        f"https://api.massive.com/v3/quotes/{instrument}",
                        params=params,
                        timeout_seconds=timeout_seconds,
                    ),
                    timeout=timeout_seconds,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                raise _StopAcquisitionError(failure_reason("request_failed")) from None
            try:
                response_status = response.status
                response_headers = dict(response.headers)
            except Exception:
                raise _StopAcquisitionError("invalid_response") from None
            if type(response_status) is not int or not 100 <= response_status <= 599:
                raise _StopAcquisitionError("invalid_response")
            if any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in response_headers.items()
            ):
                raise _StopAcquisitionError("invalid_response")
            body = bytearray()
            try:
                iterator = response.iter_chunks().__aiter__()
            except Exception:
                raise _StopAcquisitionError("read_failed") from None
            stream_cancelled = False
            try:
                while True:
                    _, remaining = tick()
                    chunk_timeout = min(
                        float(selected_limits["request_timeout_seconds"]), remaining
                    )
                    try:
                        chunk = await asyncio.wait_for(iterator.__anext__(), timeout=chunk_timeout)
                    except StopAsyncIteration:
                        break
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        raise _StopAcquisitionError(failure_reason("read_failed")) from None
                    if not isinstance(chunk, bytes):
                        raise _StopAcquisitionError("read_failed")
                    if len(body) + len(chunk) > selected_limits["max_page_bytes"]:
                        raise _StopAcquisitionError("body_limit")
                    if total_bytes + len(body) + len(chunk) > selected_limits["max_total_bytes"]:
                        raise _StopAcquisitionError("byte_budget")
                    body.extend(chunk)
                # Receipt time belongs immediately after the full body reaches EOF. Closing
                # the response and all parsing/persistence happen after this observation.
                received_at = wall_time()
            except asyncio.CancelledError:
                stream_cancelled = True
                raise
            finally:
                try:
                    await asyncio.wait_for(response.close(), timeout=cleanup_timeout())
                except asyncio.CancelledError:
                    if not stream_cancelled:
                        raise
                except Exception:
                    if not stream_cancelled:
                        raise _StopAcquisitionError("read_failed") from None
                finally:
                    response = None
            total_bytes += len(body)
            tick()
            try:
                capture = capture_quote_page(
                    pair=pair,
                    instrument=instrument,
                    window_start_ns=window_start_ns,
                    window_end_ns=window_end_ns,
                    page_index=page_index,
                    requested_at=requested_at,
                    received_at=received_at,
                    status_code=response_status,
                    body=bytes(body),
                    request_params=params,
                    response_headers=response_headers,
                    secrets=(api_key,),
                )
            except Exception:
                raise _StopAcquisitionError("capture_invalid") from None
            try:
                capture_receipt = persist_capture(capture)
            except Exception:
                raise _StopAcquisitionError("capture_write_failed") from None
            if not _capture_receipt(capture, capture_receipt):
                raise _StopAcquisitionError("capture_write_failed")
            tick()
            page_time = wall_time()
            page_event = make_quote_acquisition_event(
                common,
                sequence=page_index + 1,
                previous_event_sha256=previous_hash,
                kind="page_saved",
                occurred_at=page_time,
                capture_sha256=cast(str, capture["capture_sha256"]),
            )
            try:
                event_receipt = persist_event(page_event)
            except Exception:
                page_event_uncertain = True
                raise RuntimeError("Quote acquisition page progress is uncertain") from None
            if not _event_receipt(page_event, event_receipt):
                page_event_uncertain = True
                raise RuntimeError("Quote acquisition page progress is uncertain") from None
            pages.append(capture)
            previous_hash = cast(str, page_event["event_sha256"])
            previous_time = page_time
            tick()
            if response_status != 200:
                raise _StopAcquisitionError("http_status")
            if capture["issues"]:
                raise _StopAcquisitionError("invalid_response")
            cursor = _next_cursor(bytes(body), capture, instrument)
            if cursor is None:
                break
            cursor_hashes = {page["request_cursor_sha256"] for page in pages}
            if capture["next_cursor_sha256"] in cursor_hashes:
                raise _StopAcquisitionError("cursor_cycle")
        else:
            if cursor is not None:
                raise _StopAcquisitionError("page_limit")
    except asyncio.CancelledError:
        raise
    except _StopAcquisitionError as stopped:
        reason = stopped.reason
    finally:
        if response is not None:
            try:
                await asyncio.wait_for(response.close(), timeout=cleanup_timeout())
            except Exception:
                transport_cleanup_failed = True
        if created_transport and active_transport is not None:
            try:
                await asyncio.wait_for(
                    cast(_AiohttpTransport, active_transport).close(),
                    timeout=cleanup_timeout(),
                )
            except Exception:
                transport_cleanup_failed = True

    if page_event_uncertain:
        raise RuntimeError("Quote acquisition page progress is uncertain") from None
    if cleanup_clock_invalid:
        reason = "clock_invalid"
    elif transport_cleanup_failed and reason == "completed":
        reason = "read_failed"

    try:
        tick()
    except _StopAcquisitionError as stopped:
        if reason == "completed":
            reason = stopped.reason

    if pages:
        try:
            snapshot_time = wall_time()
            reference = build_quote_reference(pages, as_of=snapshot_time)
            if reason == "completed" and reference.get("acquisition_complete") is not True:
                reason = "invalid_response"
            expected_snapshot_sha256 = _snapshot_sha256(
                reference,
                implementation_sha256=implementation_sha256,
            )
            snapshot_receipt = persist_snapshot(
                pages,
                as_of=snapshot_time,
                implementation_sha256=implementation_sha256,
                client_version=CLIENT_VERSION,
            )
            snapshot_sha256 = _snapshot_receipt(
                len(pages), expected_snapshot_sha256, snapshot_receipt
            )
            if snapshot_sha256 is None:
                reason = "snapshot_write_failed"
        except _StopAcquisitionError as stopped:
            reason = stopped.reason
        except Exception:
            reason = "snapshot_write_failed"

    # Re-read provenance after all snapshot work: a callback can take long enough for
    # source bytes or installed dependency metadata to change underneath the attempt.
    if reason == "completed":
        try:
            _, current_implementation = quote_runtime_manifest()
        except Exception:
            reason = "implementation_changed"
        else:
            if current_implementation != implementation_sha256:
                reason = "implementation_changed"
    try:
        tick()
    except _StopAcquisitionError as stopped:
        if reason == "completed":
            reason = stopped.reason

    try:
        terminal_time = wall_time()
    except _StopAcquisitionError:
        reason = "clock_invalid"
        terminal_time = previous_time
    terminal = make_quote_acquisition_event(
        common,
        sequence=len(pages) + 1,
        previous_event_sha256=previous_hash,
        kind="finished",
        occurred_at=terminal_time,
        snapshot_sha256=snapshot_sha256,
        status="complete" if reason == "completed" else "failed",
        reason=reason,
    )
    try:
        terminal_receipt = persist_event(terminal)
    except Exception:
        raise RuntimeError("Quote acquisition terminal state was not recorded") from None
    if not _event_receipt(terminal, terminal_receipt):
        raise RuntimeError("Quote acquisition terminal state was not acknowledged") from None
    return terminal
