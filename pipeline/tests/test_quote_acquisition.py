"""Adversarial synthetic checks for bounded quote HTTP acquisition."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any

import aiohttp
import pytest

from src.research import quote_acquisition as acquisition
from src.research.quote_attempt import quote_runtime_manifest
from src.research.quote_reference import build_quote_reference

ATTEMPT_ID = "12345678-1234-5678-9234-567812345678"
DAY = date(2026, 9, 26)
NOW = datetime(2026, 9, 27, 1, tzinfo=UTC)
START_NS = 1_790_380_800_000_000_000


def _body(
    *,
    cursor: str | None = None,
    next_host: str = "api.massive.com",
    rows: list[Any] | None = None,
) -> bytes:
    payload: dict[str, Any] = {"status": "OK", "results": rows if rows is not None else []}
    if cursor is not None:
        payload["next_url"] = (
            f"https://{next_host}/v3/quotes/C:EUR-USD?cursor={cursor}"
        )
    return json.dumps(payload, separators=(",", ":")).encode()


class Response:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        error: Exception | None = None,
        block: asyncio.Event | None = None,
    ) -> None:
        self.status = status
        self.headers: Mapping[str, str] = {"Content-Type": "application/json"}
        self.body = body
        self.error = error
        self.block = block
        self.closed = False

    async def iter_chunks(self) -> AsyncIterator[bytes]:
        if self.block is not None:
            await self.block.wait()
        if self.error is not None:
            raise self.error
        midpoint = max(1, len(self.body) // 2)
        yield self.body[:midpoint]
        yield self.body[midpoint:]

    async def close(self) -> None:
        self.closed = True


class Transport:
    def __init__(self, responses: list[Response], *, error: Exception | None = None) -> None:
        self.responses = responses
        self.error = error
        self.requests: list[tuple[str, dict[str, str], float]] = []

    async def open_page(
        self, url: str, *, params: Mapping[str, str], timeout_seconds: float
    ) -> Response:
        self.requests.append((url, dict(params), timeout_seconds))
        if self.error is not None:
            raise self.error
        return self.responses[len(self.requests) - 1]


class Clock:
    def __init__(self, *, start: datetime = NOW, step: float = 0.001) -> None:
        self.current = start
        self.tick = 0.0
        self.step = step

    def now(self) -> datetime:
        result = self.current
        self.current += timedelta(milliseconds=1)
        return result

    def monotonic(self) -> float:
        result = self.tick
        self.tick += self.step
        return result


class Persistence:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.captures: list[dict[str, Any]] = []
        self.snapshots: list[list[Mapping[str, Any]]] = []
        self.order: list[str] = []
        self.duplicate_start = False
        self.fail_capture = False
        self.fail_page_event = False
        self.fail_snapshot = False
        self.bad_snapshot_receipt = False
        self.fail_terminal = False
        self.fail_started = False
        self.bad_capture_receipt = False
        self.bad_page_receipt = False
        self.bad_terminal_receipt = False

    def event(self, event: Mapping[str, Any]) -> Mapping[str, Any]:
        copied = dict(event)
        self.order.append(f"event:{copied['kind']}:{copied['sequence']}")
        if self.fail_started and copied["kind"] == "started":
            raise OSError("database detail must stay private")
        if self.fail_page_event and copied["kind"] == "page_saved":
            raise OSError("database detail must stay private")
        if self.fail_terminal and copied["kind"] == "finished":
            raise OSError("database detail must stay private")
        self.events.append(copied)
        receipt = {
            "event_sha256": copied["event_sha256"],
            "attempt_id": copied["attempt_id"],
            "sequence": copied["sequence"],
            "inserted": not (self.duplicate_start and copied["kind"] == "started"),
        }
        if self.bad_page_receipt and copied["kind"] == "page_saved":
            receipt["event_sha256"] = "0" * 64
        if self.bad_terminal_receipt and copied["kind"] == "finished":
            receipt["event_sha256"] = "0" * 64
        return receipt

    def capture(self, page: Mapping[str, Any]) -> Mapping[str, Any]:
        self.order.append(f"capture:{page['page_index']}")
        if self.fail_capture:
            raise OSError("database detail must stay private")
        copied = dict(page)
        self.captures.append(copied)
        return {
            "capture_sha256": "0" * 64 if self.bad_capture_receipt else page["capture_sha256"],
            "inserted": True,
        }

    def snapshot(self, pages: list[Mapping[str, Any]], **kwargs: Any) -> Mapping[str, Any]:
        self.order.append("snapshot")
        if self.fail_snapshot:
            raise OSError("database detail must stay private")
        self.snapshots.append(list(pages))
        reference = build_quote_reference(pages, as_of=kwargs["as_of"])
        fingerprint = acquisition._snapshot_sha256(
            reference,
            implementation_sha256=kwargs["implementation_sha256"],
        )
        if self.bad_snapshot_receipt:
            fingerprint = "b" * 64
        return {"snapshot_sha256": fingerprint, "inserted": True, "capture_count": len(pages)}


@pytest.fixture
def stable_manifest(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    manifest = quote_runtime_manifest()
    monkeypatch.setattr(acquisition, "quote_runtime_manifest", lambda: manifest)
    return manifest


def _run(
    transport: Transport | None,
    persistence: Persistence,
    *,
    clock: Clock | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    selected_clock = clock or Clock()
    return asyncio.run(
        acquisition.acquire_quotes(
            pair="EURUSD",
            day=DAY,
            api_key="top-secret-key",
            attempt_id=ATTEMPT_ID,
            transport=transport,
            now=selected_clock.now,
            monotonic=selected_clock.monotonic,
            persist_event=persistence.event,
            persist_capture=persistence.capture,
            persist_snapshot=persistence.snapshot,
            **kwargs,
        )
    )


def test_multi_page_order_fixed_host_and_credential_privacy(
    stable_manifest: tuple[str, str],
) -> None:
    first = Response(_body(cursor="opaque-one", next_host="api.polygon.io"))
    second = Response(
        _body(rows=[{"participant_timestamp": START_NS + 1, "bid_price": 1.1, "ask_price": 1.2}])
    )
    transport = Transport([first, second])
    persistence = Persistence()

    terminal = _run(transport, persistence)

    assert terminal["status"] == "complete"
    assert terminal["reason"] == "completed"
    assert terminal["sequence"] == 3
    assert persistence.order == [
        "event:started:0",
        "capture:0",
        "event:page_saved:1",
        "capture:1",
        "event:page_saved:2",
        "snapshot",
        "event:finished:3",
    ]
    assert [request[0] for request in transport.requests] == [
        "https://api.massive.com/v3/quotes/C:EUR-USD",
        "https://api.massive.com/v3/quotes/C:EUR-USD",
    ]
    assert set(transport.requests[0][1]) == {
        "timestamp.gte", "timestamp.lt", "sort", "order", "limit", "apiKey"
    }
    assert transport.requests[1][1] == {"cursor": "opaque-one", "apiKey": "top-secret-key"}
    assert all(response.closed for response in (first, second))
    retained = json.dumps({"events": persistence.events, "captures": persistence.captures})
    assert "top-secret-key" not in retained
    assert "opaque-one" not in retained


@pytest.mark.parametrize(
    ("body", "status", "reason"),
    [
        (_body(), 503, "http_status"),
        (b"not-json", 200, "invalid_response"),
        (_body(cursor="one", next_host="evil.example"), 200, "invalid_response"),
    ],
)
def test_failed_responses_are_captured_before_terminal(
    stable_manifest: tuple[str, str], body: bytes, status: int, reason: str
) -> None:
    response = Response(body, status=status)
    persistence = Persistence()
    terminal = _run(Transport([response]), persistence)
    assert terminal["status"] == "failed"
    assert terminal["reason"] == reason
    assert len(persistence.captures) == 1
    assert terminal["snapshot_sha256"] is not None
    assert response.closed


def test_repeated_cursor_stops_without_third_request(stable_manifest: tuple[str, str]) -> None:
    transport = Transport([Response(_body(cursor="same")), Response(_body(cursor="same"))])
    persistence = Persistence()
    terminal = _run(transport, persistence)
    assert terminal["reason"] == "cursor_cycle"
    assert len(transport.requests) == 2
    assert len(persistence.captures) == 2


def test_duplicate_started_receipt_prevents_network(stable_manifest: tuple[str, str]) -> None:
    transport = Transport([Response(_body())])
    persistence = Persistence()
    persistence.duplicate_start = True
    with pytest.raises(RuntimeError, match="not newly acknowledged"):
        _run(transport, persistence)
    assert transport.requests == []


@pytest.mark.parametrize(
    ("body", "limits", "reason"),
    [
        (b"x" * 81, {"max_page_bytes": 80, "max_total_bytes": 80}, "body_limit"),
        (_body(cursor="more"), {"max_pages": 1}, "page_limit"),
    ],
)
def test_page_and_body_budgets(
    stable_manifest: tuple[str, str], body: bytes, limits: Mapping[str, int], reason: str
) -> None:
    persistence = Persistence()
    terminal = _run(Transport([Response(body)]), persistence, limits=limits)
    assert terminal["reason"] == reason
    assert terminal["status"] == "failed"


def test_total_byte_budget_preserves_only_acknowledged_prefix(
    stable_manifest: tuple[str, str],
) -> None:
    first_body = _body(cursor="two", rows=[{"padding": "x" * 50}])
    second_body = _body(rows=[{"padding": "y" * 50}])
    limit = len(first_body) + len(second_body) - 1
    persistence = Persistence()
    terminal = _run(
        Transport([Response(first_body), Response(second_body)]),
        persistence,
        limits={"max_page_bytes": max(len(first_body), len(second_body)), "max_total_bytes": limit},
    )
    assert terminal["reason"] == "byte_budget"
    assert len(persistence.captures) == 1
    assert len(persistence.snapshots[0]) == 1


def test_request_and_read_failures_are_sanitized(stable_manifest: tuple[str, str]) -> None:
    for transport, expected in (
        (Transport([], error=OSError("top-secret-key provider detail")), "request_failed"),
        (Transport([Response(b"", error=OSError("top-secret-key stream detail"))]), "read_failed"),
    ):
        persistence = Persistence()
        terminal = _run(transport, persistence)
        assert terminal["reason"] == expected
        assert "top-secret-key" not in json.dumps(terminal)


def test_actual_open_and_read_timeouts_are_bounded(stable_manifest: tuple[str, str]) -> None:
    class BlockingTransport(Transport):
        async def open_page(
            self, url: str, *, params: Mapping[str, str], timeout_seconds: float
        ) -> Response:
            self.requests.append((url, dict(params), timeout_seconds))
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    cases: list[tuple[Transport, str]] = [
        (BlockingTransport([]), "request_failed"),
        (Transport([Response(b"", block=asyncio.Event())]), "read_failed"),
    ]
    for transport, reason in cases:
        persistence = Persistence()
        before = time.monotonic()
        terminal = _run(
            transport,
            persistence,
            limits={"request_timeout_seconds": 1, "deadline_seconds": 10},
        )
        assert time.monotonic() - before < 2.0
        assert terminal["reason"] == reason


def test_short_remaining_budget_does_not_relabel_immediate_errors(
    stable_manifest: tuple[str, str],
) -> None:
    for transport, ticks, reason in (
        (Transport([], error=OSError("open")), iter((0.0, 0.9, 0.9, 0.9)), "request_failed"),
        (
            Transport([Response(b"", error=OSError("read"))]),
            iter((0.0, 0.9, 0.9, 0.9, 0.9)),
            "read_failed",
        ),
    ):
        persistence = Persistence()
        terminal = asyncio.run(
            acquisition.acquire_quotes(
                pair="EURUSD",
                day=DAY,
                api_key="secret",
                attempt_id=ATTEMPT_ID,
                limits={"deadline_seconds": 1, "request_timeout_seconds": 30},
                transport=transport,
                now=Clock().now,
                monotonic=lambda: next(ticks, 0.9),
                persist_event=persistence.event,
                persist_capture=persistence.capture,
                persist_snapshot=persistence.snapshot,
            )
        )
        assert terminal["reason"] == reason


def test_partial_stream_failure_is_not_captured(stable_manifest: tuple[str, str]) -> None:
    class Partial(Response):
        async def iter_chunks(self) -> AsyncIterator[bytes]:
            yield b'{"status":"OK",'
            raise OSError("interrupted")

    persistence = Persistence()
    terminal = _run(Transport([Partial(b"")]), persistence)
    assert terminal["reason"] == "read_failed"
    assert persistence.captures == []


def test_capture_and_snapshot_failures_have_fixed_codes(stable_manifest: tuple[str, str]) -> None:
    capture_persistence = Persistence()
    capture_persistence.fail_capture = True
    terminal = _run(Transport([Response(_body())]), capture_persistence)
    assert terminal["reason"] == "capture_write_failed"
    assert terminal["sequence"] == 1

    snapshot_persistence = Persistence()
    snapshot_persistence.fail_snapshot = True
    terminal = _run(Transport([Response(_body())]), snapshot_persistence)
    assert terminal["reason"] == "snapshot_write_failed"
    assert terminal["snapshot_sha256"] is None

    wrong_receipt = Persistence()
    wrong_receipt.bad_snapshot_receipt = True
    terminal = _run(Transport([Response(_body())]), wrong_receipt)
    assert terminal["reason"] == "snapshot_write_failed"
    assert terminal["snapshot_sha256"] is None


def test_uncertain_page_event_stops_without_terminal(stable_manifest: tuple[str, str]) -> None:
    persistence = Persistence()
    persistence.fail_page_event = True
    transport = Transport([Response(_body(cursor="must-not-follow"))])
    with pytest.raises(RuntimeError, match="progress is uncertain") as raised:
        _run(transport, persistence)
    assert raised.value.__cause__ is None
    assert len(transport.requests) == 1
    assert [event["kind"] for event in persistence.events] == ["started"]

    bad_receipt = Persistence()
    bad_receipt.bad_page_receipt = True
    with pytest.raises(RuntimeError, match="progress is uncertain"):
        _run(Transport([Response(_body())]), bad_receipt)
    assert [event["kind"] for event in bad_receipt.events] == ["started", "page_saved"]


def test_started_capture_and_terminal_receipts_are_strict(stable_manifest: tuple[str, str]) -> None:
    started = Persistence()
    started.fail_started = True
    transport = Transport([Response(_body())])
    with pytest.raises(RuntimeError, match="could not record its start") as raised:
        _run(transport, started)
    assert raised.value.__cause__ is None
    assert transport.requests == []

    capture = Persistence()
    capture.bad_capture_receipt = True
    terminal = _run(Transport([Response(_body())]), capture)
    assert terminal["reason"] == "capture_write_failed"

    terminal_store = Persistence()
    terminal_store.bad_terminal_receipt = True
    with pytest.raises(RuntimeError, match="not acknowledged") as raised:
        _run(Transport([Response(_body())]), terminal_store)
    assert raised.value.__cause__ is None


def test_clock_regression_records_clock_invalid(stable_manifest: tuple[str, str]) -> None:
    values = iter((NOW, NOW - timedelta(seconds=1), NOW, NOW))
    persistence = Persistence()
    terminal = asyncio.run(
        acquisition.acquire_quotes(
            pair="EURUSD",
            day=DAY,
            api_key="secret",
            attempt_id=ATTEMPT_ID,
            transport=Transport([Response(_body())]),
            now=lambda: next(values),
            monotonic=Clock().monotonic,
            persist_event=persistence.event,
            persist_capture=persistence.capture,
            persist_snapshot=persistence.snapshot,
        )
    )
    assert terminal["reason"] == "clock_invalid"
    assert terminal["sequence"] == 1


def test_source_manifest_change_prevents_complete_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = quote_runtime_manifest()
    calls = 0

    def changed() -> tuple[str, str]:
        nonlocal calls
        calls += 1
        return original if calls == 1 else (original[0], "0" * 64)

    monkeypatch.setattr(acquisition, "quote_runtime_manifest", changed)
    persistence = Persistence()
    terminal = _run(Transport([Response(_body())]), persistence)
    assert terminal["reason"] == "implementation_changed"
    assert terminal["status"] == "failed"


def test_source_change_during_snapshot_callback_prevents_complete_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = quote_runtime_manifest()
    changed = False
    persistence = Persistence()
    ordinary_snapshot = persistence.snapshot

    def runtime() -> tuple[str, str]:
        return (original[0], "0" * 64) if changed else original

    def snapshot(pages: list[Mapping[str, Any]], **kwargs: Any) -> Mapping[str, Any]:
        nonlocal changed
        receipt = ordinary_snapshot(pages, **kwargs)
        changed = True
        return receipt

    monkeypatch.setattr(acquisition, "quote_runtime_manifest", runtime)
    monkeypatch.setattr(persistence, "snapshot", snapshot)
    terminal = _run(Transport([Response(_body())]), persistence)
    assert terminal["reason"] == "implementation_changed"


def test_invalid_input_precedes_persistence_and_network(stable_manifest: tuple[str, str]) -> None:
    persistence = Persistence()
    transport = Transport([Response(_body())])
    with pytest.raises(ValueError):
        asyncio.run(
            acquisition.acquire_quotes(
                pair="GBPUSD",
                day=DAY,
                api_key="secret",
                attempt_id=ATTEMPT_ID,
                transport=transport,
                persist_event=persistence.event,
                persist_capture=persistence.capture,
                persist_snapshot=persistence.snapshot,
            )
        )
    assert persistence.events == []
    assert transport.requests == []
    with pytest.raises(ValueError):
        asyncio.run(
            acquisition.acquire_quotes(
                pair=[],  # type: ignore[arg-type]
                day=DAY,
                api_key="secret",
                attempt_id=ATTEMPT_ID,
                transport=transport,
                persist_event=persistence.event,
                persist_capture=persistence.capture,
                persist_snapshot=persistence.snapshot,
            )
        )
    for api_key, attempt_id in (("", ATTEMPT_ID), ("secret", "NOT-A-UUID")):
        with pytest.raises(ValueError):
            asyncio.run(
                acquisition.acquire_quotes(
                    pair="EURUSD",
                    day=DAY,
                    api_key=api_key,
                    attempt_id=attempt_id,
                    transport=transport,
                    now=lambda: NOW,
                    monotonic=lambda: 0.0,
                    persist_event=persistence.event,
                    persist_capture=persistence.capture,
                    persist_snapshot=persistence.snapshot,
                )
            )
    assert persistence.events == []
    assert transport.requests == []


@pytest.mark.parametrize(
    "bad_day",
    [datetime(2026, 9, 26, tzinfo=UTC), date(1969, 12, 31), NOW.date()],
)
def test_invalid_days_precede_io(stable_manifest: tuple[str, str], bad_day: Any) -> None:
    persistence = Persistence()
    transport = Transport([Response(_body())])
    with pytest.raises(ValueError):
        asyncio.run(
            acquisition.acquire_quotes(
                pair="EURUSD",
                day=bad_day,
                api_key="secret",
                attempt_id=ATTEMPT_ID,
                transport=transport,
                now=lambda: NOW,
                monotonic=lambda: 0.0,
                persist_event=persistence.event,
                persist_capture=persistence.capture,
                persist_snapshot=persistence.snapshot,
            )
        )
    assert persistence.events == []
    assert transport.requests == []


@pytest.mark.parametrize(
    "bad_limits",
    [
        {"max_pages": True},
        {"unknown": 1},
        {"max_page_bytes": 100, "max_total_bytes": 99},
        {"request_timeout_seconds": 61},
    ],
)
def test_invalid_limits_precede_io(
    stable_manifest: tuple[str, str], bad_limits: Mapping[str, int]
) -> None:
    persistence = Persistence()
    transport = Transport([Response(_body())])
    with pytest.raises(ValueError):
        _run(transport, persistence, limits=bad_limits)
    assert persistence.events == []
    assert transport.requests == []


def test_invalid_initial_clocks_precede_io(stable_manifest: tuple[str, str]) -> None:
    persistence = Persistence()
    transport = Transport([Response(_body())])
    for now, monotonic in (
        (lambda: datetime(2026, 9, 27), lambda: 0.0),
        (lambda: NOW, lambda: float("nan")),
    ):
        with pytest.raises(ValueError):
            asyncio.run(
                acquisition.acquire_quotes(
                    pair="EURUSD",
                    day=DAY,
                    api_key="secret",
                    attempt_id=ATTEMPT_ID,
                    transport=transport,
                    now=now,
                    monotonic=monotonic,
                    persist_event=persistence.event,
                    persist_capture=persistence.capture,
                    persist_snapshot=persistence.snapshot,
                )
            )
    assert persistence.events == []
    assert transport.requests == []


def test_receipt_timestamp_is_taken_before_response_close(stable_manifest: tuple[str, str]) -> None:
    clock = Clock()

    class DelayedClose(Response):
        async def close(self) -> None:
            clock.current += timedelta(hours=1)
            await super().close()

    persistence = Persistence()
    _run(Transport([DelayedClose(_body())]), persistence, clock=clock)
    received = datetime.fromisoformat(persistence.captures[0]["received_at"])
    page_event = next(event for event in persistence.events if event["kind"] == "page_saved")
    assert datetime.fromisoformat(page_event["occurred_at"]) - received >= timedelta(hours=1)


def test_hanging_response_cleanup_is_bounded(stable_manifest: tuple[str, str]) -> None:
    class HangingClose(Response):
        async def close(self) -> None:
            await asyncio.Event().wait()

    persistence = Persistence()
    before = time.monotonic()
    terminal = _run(
        Transport([HangingClose(_body())]),
        persistence,
        limits={"request_timeout_seconds": 1, "deadline_seconds": 10},
    )
    assert time.monotonic() - before < 2.0
    assert terminal["reason"] == "read_failed"
    assert persistence.captures == []


@pytest.mark.parametrize("cleanup_sample", [float("nan"), 0.35])
def test_invalid_clock_sample_during_cleanup_remains_terminal(
    stable_manifest: tuple[str, str], cleanup_sample: float,
) -> None:
    samples = iter((0.0, 0.1, 0.2, 0.3, 0.4, cleanup_sample))
    healthy = 0.5
    persistence = Persistence()
    terminal = asyncio.run(
        acquisition.acquire_quotes(
            pair="EURUSD",
            day=DAY,
            api_key="secret",
            attempt_id=ATTEMPT_ID,
            transport=Transport([Response(_body())]),
            now=Clock().now,
            monotonic=lambda: next(samples, healthy),
            persist_event=persistence.event,
            persist_capture=persistence.capture,
            persist_snapshot=persistence.snapshot,
        )
    )
    assert terminal["reason"] == "clock_invalid"
    assert terminal["status"] == "failed"


def test_invalid_response_metadata_and_iterator_are_sanitized(
    stable_manifest: tuple[str, str],
) -> None:
    class BrokenHeaders(Response):
        @property
        def headers(self) -> Mapping[str, str]:
            raise OSError("top-secret-key header detail")

        @headers.setter
        def headers(self, _: Mapping[str, str]) -> None:
            pass

    class BrokenIterator(Response):
        def iter_chunks(self) -> AsyncIterator[bytes]:
            raise OSError("top-secret-key iterator detail")

    for response, reason in (
        (BrokenHeaders(_body()), "invalid_response"),
        (BrokenIterator(_body()), "read_failed"),
    ):
        persistence = Persistence()
        terminal = _run(Transport([response]), persistence)
        assert terminal["reason"] == reason
        assert "top-secret-key" not in json.dumps(terminal)
        assert response.closed


def test_exhausted_deadline_records_time_budget(stable_manifest: tuple[str, str]) -> None:
    persistence = Persistence()
    terminal = _run(
        Transport([Response(_body())]),
        persistence,
        clock=Clock(step=1.0),
        limits={"deadline_seconds": 1},
    )
    assert terminal["reason"] == "time_budget"
    assert persistence.captures == []


def test_mixed_invalid_rows_remain_complete_but_provisional(
    stable_manifest: tuple[str, str],
) -> None:
    body = _body(
        rows=[
            {"participant_timestamp": START_NS + 1, "bid_price": 1.1, "ask_price": 1.2},
            {"participant_timestamp": START_NS + 2, "bid_price": -1, "ask_price": 1.2},
        ]
    )
    persistence = Persistence()
    terminal = _run(Transport([Response(body)]), persistence)
    assert terminal["reason"] == "completed"
    assert terminal["status"] == "complete"


def test_cancellation_closes_response_and_propagates(stable_manifest: tuple[str, str]) -> None:
    async def scenario() -> tuple[Response, Persistence]:
        gate = asyncio.Event()
        response = Response(b"", block=gate)
        persistence = Persistence()
        task = asyncio.create_task(
            acquisition.acquire_quotes(
                pair="EURUSD",
                day=DAY,
                api_key="secret",
                attempt_id=ATTEMPT_ID,
                transport=Transport([response]),
                now=Clock().now,
                monotonic=Clock().monotonic,
                persist_event=persistence.event,
                persist_capture=persistence.capture,
                persist_snapshot=persistence.snapshot,
            )
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return response, persistence

    response, persistence = asyncio.run(scenario())
    assert response.closed
    assert [event["kind"] for event in persistence.events] == ["started"]


@pytest.mark.parametrize("hanging_close", [False, True])
def test_cancellation_survives_failed_or_hanging_cleanup(
    stable_manifest: tuple[str, str], hanging_close: bool
) -> None:
    async def scenario() -> Persistence:
        class HostileClose(Response):
            async def close(self) -> None:
                if hanging_close:
                    await asyncio.Event().wait()
                raise OSError("cleanup detail")

        response = HostileClose(b"", block=asyncio.Event())
        persistence = Persistence()
        task = asyncio.create_task(
            acquisition.acquire_quotes(
                pair="EURUSD",
                day=DAY,
                api_key="secret",
                attempt_id=ATTEMPT_ID,
                limits={"request_timeout_seconds": 1, "deadline_seconds": 10},
                transport=Transport([response]),
                now=Clock().now,
                monotonic=Clock().monotonic,
                persist_event=persistence.event,
                persist_capture=persistence.capture,
                persist_snapshot=persistence.snapshot,
            )
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return persistence

    before = time.monotonic()
    persistence = asyncio.run(scenario())
    assert time.monotonic() - before < 2.0
    assert [event["kind"] for event in persistence.events] == ["started"]


def test_default_aiohttp_adapter_disables_ambient_state_and_redirects(
    stable_manifest: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions: list[Any] = []

    class Content:
        async def iter_chunked(self, _: int) -> AsyncIterator[bytes]:
            yield _body()

    class RawResponse:
        status = 200
        headers = {"Content-Type": "application/json"}
        content = Content()

        def release(self) -> None:
            pass

        async def wait_for_close(self) -> None:
            pass

    class Session:
        def __init__(self, **kwargs: Any) -> None:
            self.init_kwargs = kwargs
            self.get_calls: list[tuple[str, dict[str, Any]]] = []
            self.closed = False
            sessions.append(self)

        async def get(self, url: str, **kwargs: Any) -> RawResponse:
            self.get_calls.append((url, kwargs))
            return RawResponse()

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(aiohttp, "ClientSession", Session)
    persistence = Persistence()
    terminal = _run(None, persistence)
    session = sessions[0]
    assert terminal["reason"] == "completed"
    assert session.init_kwargs["trust_env"] is False
    assert session.init_kwargs["raise_for_status"] is False
    assert session.get_calls[0][1]["allow_redirects"] is False
    assert session.get_calls[0][1]["ssl"] is True
    assert session.get_calls[0][1]["proxy"] is None
    assert session._retry_connection is False
    assert session.closed
