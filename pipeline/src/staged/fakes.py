"""Fake implementations of the staged pipeline external ports.

These fakes record every call and return minimal canned data so that stage
logic can be unit tested without touching real external services.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

from src.types import RegimeCall, SignalRow
from src.validation.calculator import EVALUATION_VERSION

from .contracts import IngestionSnapshot, StageHealth
from .ports import AlertPort, FetcherPort, WriterPort


class FakeFetcherPort(FetcherPort):
    """In-memory fetcher that returns a configured snapshot or an empty one."""

    def __init__(self, snapshot: IngestionSnapshot | None = None) -> None:
        self.snapshot = snapshot
        self.calls: list[date] = []

    async def fetch(self, as_of: date) -> IngestionSnapshot:
        """Return the configured snapshot, or an empty OK snapshot."""

        self.calls.append(as_of)
        if self.snapshot is not None:
            return self.snapshot
        return IngestionSnapshot(
            date=as_of,
            spots={},
            yields={},
            cot_rows=[],
            cross_asset={},
        )


class FakeWriterPort(WriterPort):
    """In-memory writer that records regime calls and validation rows.

    Atomic publications are idempotent by pair, date, source, strategy, and
    model. ``write_regime_call`` remains only as a legacy test-seeding helper.
    """

    def __init__(self) -> None:
        self.price_observations: list[dict[str, Any]] = []
        self._price_observation_ids: list[int] = []
        self._price_observation_keys: list[Any] = []
        self.archive_calls: list[list[dict[str, Any]]] = []
        self._next_price_observation_id = 1
        self.regime_calls: list[tuple[RegimeCall, dict[str, Any]]] = []
        self.signal_rows: list[SignalRow] = []
        self.validation_rows: list[Mapping[str, Any]] = []
        self._regime_call_ids: list[int] = []
        self._publication_signal_rows: list[SignalRow | None] = []
        self._historical_prices: dict[tuple[str, date], dict[str, Any]] = {}
        self.publication_signal_reads: list[int] = []
        self.historical_price_reads: list[tuple[str, date]] = []
        self._next_regime_call_id = 1

    @staticmethod
    def _archive_value_key(value: Any) -> Any:
        if isinstance(value, Mapping):
            return tuple(
                (key, FakeWriterPort._archive_value_key(item))
                for key, item in sorted(value.items())
            )
        if isinstance(value, list | tuple):
            return tuple(FakeWriterPort._archive_value_key(item) for item in value)
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return value
        if isinstance(value, int | float | Decimal):
            return ("number", Decimal(str(value)).normalize())
        raise TypeError(f"Unsupported archive value: {type(value).__name__}")

    def archive_price_observations(
        self,
        observations: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        """Append detached observations with retry-idempotent receipt ids."""

        if len(observations) > 5000:
            raise ValueError("Price observation batches cannot exceed 5000 rows")
        detached = [deepcopy(dict(observation)) for observation in observations]
        self.archive_calls.append(deepcopy(detached))
        ids: list[int] = []
        inserted = existing = 0
        for observation in detached:
            key = self._archive_value_key(observation)
            try:
                index = self._price_observation_keys.index(key)
            except ValueError:
                observation_id = self._next_price_observation_id
                self._next_price_observation_id += 1
                self._price_observation_keys.append(key)
                self._price_observation_ids.append(observation_id)
                self.price_observations.append(deepcopy(observation))
                inserted += 1
            else:
                observation_id = self._price_observation_ids[index]
                existing += 1
            ids.append(observation_id)
        return {
            "observation_ids": ids,
            "inserted_count": inserted,
            "existing_count": existing,
        }

    @staticmethod
    def _publication_identity(call: RegimeCall) -> tuple[str, date, str, str, str]:
        if call.pair not in {"EURUSD", "USDJPY", "USDINR"}:
            raise ValueError("Publication pair is outside the locked universe")
        data_source = call.data_source
        strategy_version = call.strategy_version
        model_version = call.model_version
        provenance = (data_source, strategy_version, model_version)
        if any(not isinstance(value, str) or not value.strip() for value in provenance):
            raise ValueError(
                "Publication requires nonempty data_source, strategy_version, and model_version"
            )
        if data_source not in {"live", "backtest"}:
            raise ValueError("Publication source must be live or backtest")
        assert isinstance(model_version, str)
        return (
            call.pair,
            call.date,
            data_source,
            strategy_version,
            model_version,
        )

    def publish_regime_call(
        self,
        call: RegimeCall,
        signal_row: SignalRow,
        *,
        correlation_id: str | None = None,
    ) -> int | str | None:
        """Atomically record detached call and signal snapshots."""

        if (call.pair, call.date) != (signal_row.pair, signal_row.date):
            raise ValueError("Publication call and signal identity must match")
        identity = self._publication_identity(call)
        call_snapshot = deepcopy(call)
        signal_snapshot = deepcopy(signal_row)

        for index, (existing_call, _meta) in enumerate(self.regime_calls):
            existing_identity = (
                existing_call.pair,
                existing_call.date,
                existing_call.data_source,
                existing_call.strategy_version,
                existing_call.model_version,
            )
            if existing_identity != identity:
                continue
            existing_signal = self._publication_signal_rows[index]
            if existing_signal is None:
                raise ValueError("Existing call has no publication evidence")
            if existing_call == call_snapshot and existing_signal == signal_snapshot:
                return self._regime_call_ids[index]
            raise ValueError("Conflicting publication at existing identity")

        call_id = self._next_regime_call_id
        self._next_regime_call_id += 1
        self.regime_calls.append((call_snapshot, {"correlation_id": correlation_id}))
        self.signal_rows.append(signal_snapshot)
        self._regime_call_ids.append(call_id)
        self._publication_signal_rows.append(signal_snapshot)
        return call_id

    def _existing_index(self, call: RegimeCall) -> int | None:
        for idx, (existing, _meta) in enumerate(self.regime_calls):
            if existing.pair == call.pair and existing.date == call.date:
                return idx
        return None

    def read_published_calls(
        self,
        pair: str,
        *,
        limit: int | None,
    ) -> Sequence[Mapping[str, Any]]:
        """Return persisted fake calls through the same contract as production."""

        rows = [
            {
                "call_id": self._regime_call_ids[idx],
                "date": call.date,
                "pair": call.pair,
                "regime": call.regime,
                "predicted_direction": call.predicted_direction,
                "confidence": call.confidence,
                "strategy_version": call.strategy_version,
                "model_version": call.model_version,
                "data_source": call.data_source,
            }
            for idx, (call, _meta) in enumerate(self.regime_calls)
            if call.pair == pair
        ]
        if limit is None:
            return rows
        if limit == 0:
            return []
        return rows[-limit:]

    def read_validation_entry(
        self,
        call_id: int | str,
    ) -> Mapping[str, Any] | None:
        """Return the latest recorded fake evaluation for a durable call id."""

        for row in reversed(self.validation_rows):
            if (
                row.get("call_id") == call_id
                and row.get("evaluation_version") == EVALUATION_VERSION
                and row.get("is_superseded") is not True
            ):
                return deepcopy(row)
        return None

    def get_publication_signal_for_call(
        self,
        call_id: int,
    ) -> Mapping[str, Any] | None:
        """Return detached evidence only when it was atomically published."""

        self.publication_signal_reads.append(call_id)
        for index, existing_id in enumerate(self._regime_call_ids):
            if existing_id != call_id:
                continue
            signal = self._publication_signal_rows[index]
            return None if signal is None else asdict(deepcopy(signal))
        return None

    def seed_historical_price(
        self,
        pair: str,
        price_date: date,
        close: float,
    ) -> None:
        """Seed exact historical evidence for a staged validation test."""

        self._historical_prices[(pair, price_date)] = {
            "pair": pair,
            "date": price_date.isoformat(),
            "close": close,
        }

    def get_exact_historical_price_for_date(
        self,
        pair: str,
        date_str: str,
    ) -> Mapping[str, Any] | None:
        """Return only explicitly seeded evidence for the exact requested date."""

        price_date = date.fromisoformat(date_str)
        self.historical_price_reads.append((pair, price_date))
        row = self._historical_prices.get((pair, price_date))
        return None if row is None else deepcopy(row)

    def write_regime_call(
        self,
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int | str | None:
        """Record the call and return a synthetic integer id."""

        existing = self._existing_index(call)
        if existing is not None:
            return self._regime_call_ids[existing]
        call_id = self._next_regime_call_id
        self._next_regime_call_id += 1
        self.regime_calls.append(
            (call, {"correlation_id": correlation_id, "write_hash": write_hash})
        )
        self._regime_call_ids.append(call_id)
        self._publication_signal_rows.append(None)
        return call_id

    def write_signal_row(self, row: SignalRow) -> None:
        """Upsert a detached signal-row snapshot by pair and date."""

        snapshot = deepcopy(row)
        for index, existing in enumerate(self.signal_rows):
            if existing.pair == row.pair and existing.date == row.date:
                self.signal_rows[index] = snapshot
                return
        self.signal_rows.append(snapshot)

    def write_validation_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        """Record validation rows in order."""

        self.validation_rows.extend(rows)


class FakeAlertPort(AlertPort):
    """In-memory alert port that records every alert for inspection."""

    def __init__(self) -> None:
        self.heartbeats: list[dict[str, Any]] = []
        self.successes: list[RegimeCall] = []
        self.low_dqs_alerts: list[dict[str, Any]] = []
        self.statuses: list[dict[str, Any]] = []

    def send_heartbeat(
        self,
        as_of: date,
        *,
        pairs_processed: int,
        regime_calls_count: int,
        dqs_score: float,
    ) -> None:
        """Record a heartbeat."""

        self.heartbeats.append(
            {
                "as_of": as_of,
                "pairs_processed": pairs_processed,
                "regime_calls_count": regime_calls_count,
                "dqs_score": dqs_score,
            }
        )

    def send_success(self, call: RegimeCall) -> None:
        """Record a success alert."""

        self.successes.append(call)

    def send_status(
        self,
        as_of: date,
        health: StageHealth,
        *,
        pair: str | None = None,
    ) -> None:
        """Record a degraded or failed stage notice."""

        if health.status == "OK":
            raise ValueError("send_status accepts only DEGRADED or FAILED health")
        self.statuses.append({"as_of": as_of, "health": health, "pair": pair})

    def send_low_dqs(
        self,
        as_of: date,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        """Record a low-DQS alert."""

        self.low_dqs_alerts.append(
            {
                "as_of": as_of,
                "dqs_score": dqs_score,
                "stale_sources": stale_sources,
            }
        )
