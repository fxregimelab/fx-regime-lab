"""Staged pipeline v2 contracts, ports, fakes, adapters, and orchestrator."""

from __future__ import annotations

from src.staged.adapters import (
    ProductionAlertPort,
    ProductionFetcherPort,
    ProductionWriterPort,
)
from src.staged.contracts import (
    IngestionSnapshot,
    MultiPairRunOutput,
    PublishOutput,
    SignalPipelineResult,
    StageHealth,
)
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.staged.orchestrator import run_multi_pair_flow, run_single_pair_flow
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.staged.shadow_runner import (
    ShadowComparison,
    ShadowRunResult,
    compare_regime_calls,
    count_consecutive_equivalent_days,
    make_comparison,
    run_shadow_comparison,
)
from src.staged.stages import (
    IngestionStage,
    PublishStage,
    RegimeStage,
    SignalStage,
    ValidateStage,
)

__all__ = [
    "AlertPort",
    "FakeAlertPort",
    "FakeFetcherPort",
    "FakeWriterPort",
    "FetcherPort",
    "IngestionSnapshot",
    "IngestionStage",
    "MultiPairRunOutput",
    "ProductionAlertPort",
    "ProductionFetcherPort",
    "ProductionWriterPort",
    "PublishOutput",
    "PublishStage",
    "RegimeStage",
    "ShadowComparison",
    "ShadowRunResult",
    "SignalPipelineResult",
    "SignalStage",
    "StageHealth",
    "ValidateStage",
    "WriterPort",
    "compare_regime_calls",
    "count_consecutive_equivalent_days",
    "make_comparison",
    "run_multi_pair_flow",
    "run_shadow_comparison",
    "run_single_pair_flow",
]
