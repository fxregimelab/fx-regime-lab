"""Shared pytest configuration for the pipeline test suite."""

from __future__ import annotations

import logging
import os

os.environ.setdefault("PREFECT_LOGGING_LEVEL", "CRITICAL")
os.environ.setdefault("PREFECT_API_URL", "")
os.environ.setdefault("PREFECT_SERVER_ALLOW_EPHEMERAL_MODE", "true")
os.environ.setdefault("PREFECT_RESULTS_PERSIST_BY_DEFAULT", "false")

# Suppress Prefect's internal concurrency services logger in tests; it may
# attempt to emit after stdout has been closed, producing a logging error.
logging.getLogger("prefect._internal.concurrency.services").setLevel(logging.CRITICAL)
