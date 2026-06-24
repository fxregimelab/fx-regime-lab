"""Production adapters for the staged pipeline v2 external ports."""

from __future__ import annotations

from .alert import ProductionAlertPort
from .fetcher import ProductionFetcherPort
from .writer import ProductionWriterPort

__all__ = [
    "ProductionAlertPort",
    "ProductionFetcherPort",
    "ProductionWriterPort",
]
