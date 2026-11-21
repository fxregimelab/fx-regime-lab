"""Regression tests for the default pytest network boundary."""

from __future__ import annotations

import asyncio
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import aiohttp
import pytest
import requests

from tests.network_guard import OutboundNetworkBlockedError, isolated_network


class _LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, _format: str, *args: object) -> None:
        return


def test_guard_blocks_urls_and_literal_ips_before_underlying_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reached: list[str] = []

    def unexpected_resolver(*_args: object, **_kwargs: object) -> list[tuple[Any, ...]]:
        reached.append("resolver")
        raise AssertionError("guard reached the underlying DNS resolver")

    def unexpected_connect(*_args: object, **_kwargs: object) -> None:
        reached.append("connector")
        raise AssertionError("guard reached the underlying socket connector")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected_resolver)
    monkeypatch.setattr(socket, "gethostbyname", unexpected_resolver)
    monkeypatch.setattr(socket, "gethostbyname_ex", unexpected_resolver)
    monkeypatch.setattr(socket, "gethostbyaddr", unexpected_resolver)
    monkeypatch.setattr(socket.socket, "connect", unexpected_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", unexpected_connect)
    monkeypatch.setattr(socket.socket, "sendto", unexpected_connect)
    if hasattr(socket.socket, "sendmsg"):
        monkeypatch.setattr(socket.socket, "sendmsg", unexpected_connect)

    with pytest.raises(AssertionError, match="outbound network attempts were blocked"):
        with isolated_network() as guard:
            session = requests.Session()
            session.trust_env = False
            with pytest.raises(requests.RequestException):
                session.get("https://outside.example.invalid/data", timeout=0.01)
            with pytest.raises(requests.RequestException):
                session.get("http://198.51.100.23/data", timeout=0.01)
            with pytest.raises(OutboundNetworkBlockedError):
                socket.gethostbyname("dns.example.invalid")
            with pytest.raises(OutboundNetworkBlockedError):
                socket.gethostbyname_ex("dns-ex.example.invalid")
            with pytest.raises(OutboundNetworkBlockedError):
                socket.gethostbyaddr("198.51.100.24")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as datagram:
                with pytest.raises(OutboundNetworkBlockedError):
                    datagram.sendto(b"blocked", ("198.51.100.25", 53))

            assert {attempt.host for attempt in guard.blocked_attempts} == {
                "outside.example.invalid",
                "198.51.100.23",
                "dns.example.invalid",
                "dns-ex.example.invalid",
                "198.51.100.24",
                "198.51.100.25",
            }

    assert reached == []


def test_guard_applies_to_threads_and_caught_blocks_fail_exit() -> None:
    caught: list[type[BaseException]] = []

    with pytest.raises(AssertionError, match="worker.example.invalid"):
        with isolated_network():
            def attempt_from_worker() -> None:
                try:
                    socket.getaddrinfo("worker.example.invalid", 443)
                except OutboundNetworkBlockedError as exc:
                    caught.append(type(exc))

            worker = threading.Thread(target=attempt_from_worker)
            worker.start()
            worker.join(timeout=2)
            assert not worker.is_alive()
            assert caught == [OutboundNetworkBlockedError]


def test_localhost_is_rejected_when_resolution_contains_a_foreign_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def poisoned_localhost(*_args: object, **_kwargs: object) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.51.100.30", 80))]

    monkeypatch.setattr(socket, "getaddrinfo", poisoned_localhost)

    with pytest.raises(AssertionError, match="localhost"):
        with isolated_network():
            with pytest.raises(OutboundNetworkBlockedError):
                socket.getaddrinfo("localhost", 80)


def test_guard_restores_socket_functions_after_control_context() -> None:
    getaddrinfo_before = socket.getaddrinfo
    connect_before = socket.socket.connect
    connect_ex_before = socket.socket.connect_ex

    with isolated_network():
        assert socket.getaddrinfo is not getaddrinfo_before
        assert socket.socket.connect is not connect_before
        assert socket.socket.connect_ex is not connect_ex_before

    assert socket.getaddrinfo is getaddrinfo_before
    assert socket.socket.connect is connect_before
    assert socket.socket.connect_ex is connect_ex_before


def test_loopback_ipv4_and_validated_localhost_work_with_aiohttp() -> None:
    assert socket.getaddrinfo("::1", 0, socket.AF_INET6)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    async def exercise_loopback() -> None:
        port = server.server_address[1]
        async with aiohttp.ClientSession(trust_env=False) as session:
            for host in ("127.0.0.1", "localhost"):
                async with session.get(f"http://{host}:{port}/") as response:
                    assert response.status == 200
                    assert await response.text() == "ok"

    try:
        asyncio.run(exercise_loopback())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert not thread.is_alive()
