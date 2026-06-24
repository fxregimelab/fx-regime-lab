"""Pipeline feature flags and runtime configuration.

All flags are intentionally environment-driven so operators can shadow-run or
flip the staged v2 pipeline without code changes.
"""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a truthy environment variable value."""

    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"} if value else default


# Use the staged v2 pipeline as the live execution path.
USE_V2_PIPELINE: bool = _env_bool("USE_V2_PIPELINE", default=False)

# Run v2 in shadow mode alongside v1 and compare outputs without touching the
# live ledger. Only meaningful when USE_V2_PIPELINE is False.
SHADOW_V2: bool = _env_bool("SHADOW_V2", default=False)

# Number of trading days required to prove v1/v2 equivalence before a pair is
# allowed to flip to live v2. Matches the 20-day T+5/T+20 validation horizon.
SHADOW_V2_EQUIVALENCE_DAYS: int = int(
    os.environ.get("SHADOW_V2_EQUIVALENCE_DAYS", "20")
)

# Number of successful live v2 runs required before the legacy orchestrator path
# can be deprecated.
V2_LIVE_RUNS_BEFORE_DEPRECATION: int = int(
    os.environ.get("V2_LIVE_RUNS_BEFORE_DEPRECATION", "10")
)
