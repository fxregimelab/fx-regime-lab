"""Shared pytest configuration for the pipeline test suite."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

import pytest

from tests.network_guard import OutboundNetworkGuard

os.environ.setdefault("PREFECT_LOGGING_LEVEL", "CRITICAL")
os.environ["PREFECT_UNIT_TEST_MODE"] = "true"
# A dummy API key plus ephemeral server mode lets Prefect tasks run in the
# test suite without reaching Prefect Cloud. The real profile API URL/key are
# intentionally overridden here.
os.environ["PREFECT_API_KEY"] = "dummy-test-key"
os.environ["PREFECT_SERVER_ALLOW_EPHEMERAL_MODE"] = "true"
os.environ.setdefault("PREFECT_RESULTS_PERSIST_BY_DEFAULT", "false")

# Suppress Prefect's internal concurrency services logger in tests; it may
# attempt to emit after stdout has been closed, producing a logging error.
logging.getLogger("prefect._internal.concurrency.services").setLevel(logging.CRITICAL)


@pytest.fixture(autouse=True)
def _block_outbound_network(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[OutboundNetworkGuard]:
    """Block non-loopback DNS and socket connections in every test."""
    guard = OutboundNetworkGuard()
    guard.install(monkeypatch)
    yield guard
    guard.assert_no_blocked_attempts()
