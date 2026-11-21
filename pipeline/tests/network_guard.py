"""Process-wide outbound network guard for pytest.

The guard patches Python's DNS and socket connection entry points.  Because
those entry points are process-wide, the same policy applies to worker threads
started by a test.
"""

from __future__ import annotations

import ipaddress
import socket
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

import pytest


class OutboundNetworkBlockedError(OSError):
    """Raised before a test can resolve or connect to a non-loopback host."""


@dataclass(frozen=True)
class BlockedAttempt:
    """One denied DNS lookup or socket connection."""

    operation: str
    host: str
    port: object | None


class OutboundNetworkGuard:
    """Patch DNS and socket calls while allowing validated loopback traffic."""

    def __init__(
        self,
        *,
        getaddrinfo: Callable[..., list[tuple[Any, ...]]] | None = None,
        connect: Callable[..., Any] | None = None,
        connect_ex: Callable[..., int] | None = None,
        gethostbyname: Callable[..., str] | None = None,
        gethostbyname_ex: Callable[..., tuple[str, list[str], list[str]]] | None = None,
        gethostbyaddr: Callable[..., tuple[str, list[str], list[str]]] | None = None,
        sendto: Callable[..., int] | None = None,
        sendmsg: Callable[..., int] | None = None,
    ) -> None:
        self._getaddrinfo = cast(
            Callable[..., list[tuple[Any, ...]]], getaddrinfo or socket.getaddrinfo
        )
        self._connect = cast(Callable[..., Any], connect or socket.socket.connect)
        self._connect_ex = cast(Callable[..., int], connect_ex or socket.socket.connect_ex)
        self._gethostbyname = cast(
            Callable[..., str], gethostbyname or socket.gethostbyname
        )
        self._gethostbyname_ex = cast(
            Callable[..., tuple[str, list[str], list[str]]],
            gethostbyname_ex or socket.gethostbyname_ex,
        )
        self._gethostbyaddr = cast(
            Callable[..., tuple[str, list[str], list[str]]],
            gethostbyaddr or socket.gethostbyaddr,
        )
        self._sendto = cast(Callable[..., int], sendto or socket.socket.sendto)
        socket_sendmsg = getattr(socket.socket, "sendmsg", None)
        self._sendmsg = cast(Callable[..., int] | None, sendmsg or socket_sendmsg)
        self._attempts: list[BlockedAttempt] = []
        self._lock = threading.Lock()

    @property
    def blocked_attempts(self) -> tuple[BlockedAttempt, ...]:
        """Return a stable snapshot of attempts recorded across all threads."""
        with self._lock:
            return tuple(self._attempts)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Install the guard for the lifetime of ``monkeypatch``."""
        def guarded_connect(sock: socket.socket, address: object) -> Any:
            return self._guarded_connect(sock, address)

        def guarded_connect_ex(sock: socket.socket, address: object) -> int:
            return self._guarded_connect_ex(sock, address)

        def guarded_sendto(sock: socket.socket, data: object, *args: object) -> int:
            return self._guarded_sendto(sock, data, *args)

        def guarded_sendmsg(sock: socket.socket, buffers: object, *args: object) -> int:
            return self._guarded_sendmsg(sock, buffers, *args)

        monkeypatch.setattr(socket, "getaddrinfo", self._guarded_getaddrinfo)
        monkeypatch.setattr(socket, "gethostbyname", self._guarded_gethostbyname)
        monkeypatch.setattr(socket, "gethostbyname_ex", self._guarded_gethostbyname_ex)
        monkeypatch.setattr(socket, "gethostbyaddr", self._guarded_gethostbyaddr)
        monkeypatch.setattr(socket.socket, "connect", guarded_connect)
        monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
        monkeypatch.setattr(socket.socket, "sendto", guarded_sendto)
        if self._sendmsg is not None:
            monkeypatch.setattr(socket.socket, "sendmsg", guarded_sendmsg)

    def assert_no_blocked_attempts(self) -> None:
        """Fail even when code under test caught the immediate block exception."""
        attempts = self.blocked_attempts
        if not attempts:
            return
        details = ", ".join(
            f"{attempt.operation}({attempt.host!r}, {attempt.port!r})"
            for attempt in attempts
        )
        raise AssertionError(f"outbound network attempts were blocked: {details}")

    def _record_and_raise(self, operation: str, host: object, port: object | None) -> None:
        attempt = BlockedAttempt(operation=operation, host=str(host), port=port)
        with self._lock:
            self._attempts.append(attempt)
        raise OutboundNetworkBlockedError(
            f"pytest blocked outbound network access via {operation}: "
            f"host={host!r}, port={port!r}"
        )

    @staticmethod
    def _numeric_loopback(host: object) -> bool:
        if isinstance(host, bytes):
            try:
                host = host.decode("ascii")
            except UnicodeDecodeError:
                return False
        if not isinstance(host, str):
            return False
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @staticmethod
    def _is_localhost(host: object) -> bool:
        if isinstance(host, bytes):
            try:
                host = host.decode("ascii")
            except UnicodeDecodeError:
                return False
        return isinstance(host, str) and host.rstrip(".").lower() == "localhost"

    def _guarded_getaddrinfo(
        self,
        host: object,
        port: object,
        *args: object,
        **kwargs: object,
    ) -> list[tuple[Any, ...]]:
        if host is None or self._numeric_loopback(host):
            return self._getaddrinfo(host, port, *args, **kwargs)
        if not self._is_localhost(host):
            self._record_and_raise("getaddrinfo", host, port)

        resolved = self._getaddrinfo(host, port, *args, **kwargs)
        addresses = [entry[4][0] for entry in resolved if len(entry) >= 5 and entry[4]]
        if not addresses or any(not self._numeric_loopback(address) for address in addresses):
            self._record_and_raise("getaddrinfo", host, port)
        return resolved

    def _guarded_gethostbyname(self, host: object) -> str:
        if not (self._numeric_loopback(host) or self._is_localhost(host)):
            self._record_and_raise("gethostbyname", host, None)
        resolved = self._gethostbyname(host)
        if not self._numeric_loopback(resolved):
            self._record_and_raise("gethostbyname", host, None)
        return resolved

    def _guarded_gethostbyname_ex(self, host: object) -> tuple[str, list[str], list[str]]:
        if not (self._numeric_loopback(host) or self._is_localhost(host)):
            self._record_and_raise("gethostbyname_ex", host, None)
        resolved = self._gethostbyname_ex(host)
        if not resolved[2] or any(not self._numeric_loopback(item) for item in resolved[2]):
            self._record_and_raise("gethostbyname_ex", host, None)
        return resolved

    def _guarded_gethostbyaddr(self, host: object) -> tuple[str, list[str], list[str]]:
        if not self._numeric_loopback(host):
            self._record_and_raise("gethostbyaddr", host, None)
        resolved = self._gethostbyaddr(host)
        if not resolved[2] or any(not self._numeric_loopback(item) for item in resolved[2]):
            self._record_and_raise("gethostbyaddr", host, None)
        return resolved

    @staticmethod
    def _address_parts(address: object) -> tuple[object, object | None]:
        if isinstance(address, tuple) and address:
            return address[0], address[1] if len(address) > 1 else None
        return address, None

    def _allow_socket_address(self, sock: socket.socket, address: object, operation: str) -> None:
        if sock.family == getattr(socket, "AF_UNIX", object()):
            return
        host, port = self._address_parts(address)
        if self._numeric_loopback(host):
            return
        if self._is_localhost(host):
            self._guarded_getaddrinfo(host, port, sock.family, sock.type, sock.proto)
            return
        self._record_and_raise(operation, host, port)

    def _guarded_connect(self, sock: socket.socket, address: object) -> Any:
        self._allow_socket_address(sock, address, "connect")
        return self._connect(sock, address)

    def _guarded_connect_ex(self, sock: socket.socket, address: object) -> int:
        self._allow_socket_address(sock, address, "connect_ex")
        return self._connect_ex(sock, address)

    def _guarded_sendto(self, sock: socket.socket, data: object, *args: object) -> int:
        if not args:
            raise TypeError("sendto expected a destination address")
        address = args[-1]
        self._allow_socket_address(sock, address, "sendto")
        return self._sendto(sock, data, *args)

    def _guarded_sendmsg(self, sock: socket.socket, buffers: object, *args: object) -> int:
        if self._sendmsg is None:
            raise AttributeError("socket.sendmsg is unavailable")
        if args and isinstance(args[-1], tuple):
            self._allow_socket_address(sock, args[-1], "sendmsg")
        return self._sendmsg(sock, buffers, *args)


@contextmanager
def isolated_network() -> Iterator[OutboundNetworkGuard]:
    """Install an independently testable guard and enforce its exit assertion."""
    monkeypatch = pytest.MonkeyPatch()
    guard = OutboundNetworkGuard()
    guard.install(monkeypatch)
    try:
        yield guard
    finally:
        try:
            guard.assert_no_blocked_attempts()
        finally:
            monkeypatch.undo()
