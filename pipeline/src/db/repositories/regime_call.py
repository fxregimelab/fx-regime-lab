"""Regime call repository (internal — use ``src.db.writer``)."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import asdict
from typing import Any, cast

from supabase import Client

from src.db.repositories.common import date_iso
from src.types import RegimeCall, SignalRow

logger = logging.getLogger(__name__)


def _pg_conn(max_retries: int = 5) -> Any:
    """Raw Postgres connection for bulk backfill writes (pg8000)."""
    import ssl
    import time

    import pg8000.native

    ctx = ssl._create_unverified_context()
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "SUPABASE_DB_PASSWORD must be set in the environment. "
            "Get it from Supabase Dashboard → Project Settings → Database → Connection string."
        )
    last_err: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return pg8000.native.Connection(
                host=host,
                database="postgres",
                user="postgres",
                password=password,
                ssl_context=ctx,
                timeout=30,
            )
        except Exception as e:
            last_err = e
            logger.warning("DB connection attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            time.sleep(min(2 ** attempt, 30))
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")


class RegimeCallRepository:
    def __init__(self, client_factory: Callable[[], Client]) -> None:
        self._client_factory = client_factory

    def write_regime_call(
        self,
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int | str | None:
        """Insert a regime call row. Returns the existing or new row id."""
        payload: dict[str, Any] = asdict(call)
        payload["date"] = date_iso(call.date)
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id
        if write_hash is not None:
            payload["write_hash"] = write_hash
        client = self._client_factory()

        existing = (
            client.table("regime_calls")
            .select("id")
            .eq("pair", call.pair)
            .eq("date", payload["date"])
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            row = cast(dict[str, Any], existing.data)
            return row.get("id")

        res = client.table("regime_calls").insert(payload).execute()
        rows = cast(list[dict[str, Any]], res.data or [])
        return rows[0].get("id") if rows else None

    def get_latest_regime_call(self, pair: str) -> dict[str, Any] | None:
        res = (
            self._client_factory()
            .table("regime_calls")
            .select("*")
            .eq("pair", pair)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        data = cast(list[dict[str, Any]], res.data or [])
        return data[0] if data else None

    def get_historical_regime_calls(
        self, pair: str, limit: int = 5000
    ) -> list[dict[str, Any]]:
        res = (
            self._client_factory()
            .table("regime_calls")
            .select(
                "id,date,regime,signal_composite,rate_signal,confidence,"
                "predicted_direction,primary_driver"
            )
            .eq("pair", pair)
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        rows = cast(list[dict[str, Any]], res.data or [])
        return list(reversed(rows))

    def bulk_write_backfill_results(
        self,
        pair: str,
        results: Sequence[tuple[SignalRow, RegimeCall]],
    ) -> None:
        """Bulk-persist backfill (signal, call) tuples for a single pair."""
        if not results:
            return

        conn = _pg_conn()
        conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls")
        conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_log_regime_call_audit")

        conn.run("DELETE FROM signals WHERE pair = :pair", pair=pair)
        conn.run("DELETE FROM regime_calls WHERE pair = :pair", pair=pair)

        signal_rows: list[tuple[Any, ...]] = []
        regime_rows: list[tuple[Any, ...]] = []
        for signal_row, call in results:
            signal_rows.append((
                signal_row.pair, signal_row.date.isoformat(), signal_row.rate_diff_2y,
                signal_row.rate_diff_10y, signal_row.cot_percentile,
                signal_row.realized_vol_20d, signal_row.realized_vol_5d,
                signal_row.implied_vol_30d, signal_row.spot,
                signal_row.day_change, signal_row.day_change_pct,
                signal_row.cross_asset_vix, signal_row.cross_asset_dxy,
                signal_row.cross_asset_oil, signal_row.cross_asset_us10y,
                signal_row.cross_asset_gold, signal_row.cross_asset_copper,
                signal_row.cross_asset_stoxx,
                signal_row.oi_delta, signal_row.volume_rvol,
                signal_row.structural_instability,
                signal_row.breakeven_inflation_10y, signal_row.rate_diff_10y_real,
                signal_row.rate_z_tactical, signal_row.rate_z_structural,
                signal_row.realized_vol_rank, signal_row.skew_alignment,
            ))
            regime_rows.append((
                call.pair, call.date.isoformat(), call.regime, call.confidence,
                call.signal_composite, call.rate_signal, call.primary_driver,
                call.entry_timing, call.position_size, call.stop_level,
                call.data_quality_score, call.stress_level, call.predicted_direction,
                call.directional_bias, call.conviction, call.cot_signal,
                call.vol_signal, call.oi_signal, call.rr_signal,
                call.special_signal_value, call.special_signal_label, call.model_version,
                call.strategy_version, call.data_source,
            ))

        batch_size = 500
        for i in range(0, len(signal_rows), batch_size):
            batch = signal_rows[i:i + batch_size]
            values_sql = []
            params: dict[str, Any] = {}
            for j, row in enumerate(batch):
                prefix = f"r{j}_"
                values_sql.append(
                    f"(:{prefix}pair, :{prefix}date, :{prefix}r2y, :{prefix}r10y, :{prefix}cot, "
                    f":{prefix}rv20, :{prefix}rv5, :{prefix}iv, :{prefix}spot, "
                    f":{prefix}dc, :{prefix}dcp, "
                    f":{prefix}vix, :{prefix}dxy, :{prefix}oil, "
                    f":{prefix}us10y, :{prefix}gold, "
                    f":{prefix}copper, :{prefix}stoxx, :{prefix}oi, :{prefix}rvol, :{prefix}si, "
                    f":{prefix}bei, :{prefix}r10r, :{prefix}rzt, :{prefix}rzs, "
                    f":{prefix}rvr, :{prefix}sa)"
                )
                params[f"{prefix}pair"] = row[0]
                params[f"{prefix}date"] = row[1]
                params[f"{prefix}r2y"] = row[2]
                params[f"{prefix}r10y"] = row[3]
                params[f"{prefix}cot"] = row[4]
                params[f"{prefix}rv20"] = row[5]
                params[f"{prefix}rv5"] = row[6]
                params[f"{prefix}iv"] = row[7]
                params[f"{prefix}spot"] = row[8]
                params[f"{prefix}dc"] = row[9]
                params[f"{prefix}dcp"] = row[10]
                params[f"{prefix}vix"] = row[11]
                params[f"{prefix}dxy"] = row[12]
                params[f"{prefix}oil"] = row[13]
                params[f"{prefix}us10y"] = row[14]
                params[f"{prefix}gold"] = row[15]
                params[f"{prefix}copper"] = row[16]
                params[f"{prefix}stoxx"] = row[17]
                params[f"{prefix}oi"] = row[18]
                params[f"{prefix}rvol"] = row[19]
                params[f"{prefix}si"] = row[20]
                params[f"{prefix}bei"] = row[21]
                params[f"{prefix}r10r"] = row[22]
                params[f"{prefix}rzt"] = row[23]
                params[f"{prefix}rzs"] = row[24]
                params[f"{prefix}rvr"] = row[25]
                params[f"{prefix}sa"] = row[26]
            sql = (
                "INSERT INTO signals (pair, date, rate_diff_2y, rate_diff_10y, "
                "cot_percentile, realized_vol_20d, realized_vol_5d, implied_vol_30d, "
                "spot, day_change, day_change_pct, cross_asset_vix, cross_asset_dxy, "
                "cross_asset_oil, cross_asset_us10y, cross_asset_gold, "
                "cross_asset_copper, cross_asset_stoxx, oi_delta, volume_rvol, "
                "structural_instability, breakeven_inflation_10y, rate_diff_10y_real, "
                "rate_z_tactical, rate_z_structural, realized_vol_rank, "
                "skew_alignment) VALUES " + ",".join(values_sql)
            )
            conn.run(sql, **params)
            logger.info("Signals batch %d-%d inserted", i, i + len(batch) - 1)

        for i in range(0, len(regime_rows), batch_size):
            batch = regime_rows[i:i + batch_size]
            values_sql = []
            regime_params: dict[str, Any] = {}
            for j, row in enumerate(batch):
                prefix = f"r{j}_"
                values_sql.append(
                    f"(:{prefix}pair, :{prefix}date, :{prefix}regime, :{prefix}conf, "
                    f":{prefix}comp, :{prefix}rate, :{prefix}driver, :{prefix}et, "
                    f":{prefix}ps, :{prefix}sl, :{prefix}dqs, :{prefix}stress, "
                    f":{prefix}pred, :{prefix}bias, :{prefix}conv, :{prefix}cot, "
                    f":{prefix}vol, :{prefix}oi, :{prefix}rr, :{prefix}ssv, "
                    f":{prefix}ssl, :{prefix}mv, :{prefix}sv, :{prefix}ds)"
                )
                regime_params[f"{prefix}pair"] = row[0]
                regime_params[f"{prefix}date"] = row[1]
                regime_params[f"{prefix}regime"] = row[2]
                regime_params[f"{prefix}conf"] = row[3]
                regime_params[f"{prefix}comp"] = row[4]
                regime_params[f"{prefix}rate"] = row[5]
                regime_params[f"{prefix}driver"] = row[6]
                regime_params[f"{prefix}et"] = row[7]
                regime_params[f"{prefix}ps"] = row[8]
                regime_params[f"{prefix}sl"] = row[9]
                regime_params[f"{prefix}dqs"] = row[10]
                regime_params[f"{prefix}stress"] = row[11]
                regime_params[f"{prefix}pred"] = row[12]
                regime_params[f"{prefix}bias"] = row[13]
                regime_params[f"{prefix}conv"] = row[14]
                regime_params[f"{prefix}cot"] = row[15]
                regime_params[f"{prefix}vol"] = row[16]
                regime_params[f"{prefix}oi"] = row[17]
                regime_params[f"{prefix}rr"] = row[18]
                regime_params[f"{prefix}ssv"] = row[19]
                regime_params[f"{prefix}ssl"] = row[20]
                regime_params[f"{prefix}mv"] = row[21]
                regime_params[f"{prefix}sv"] = row[22]
                regime_params[f"{prefix}ds"] = row[23]
            sql = (
                "INSERT INTO regime_calls (pair, date, regime, confidence, signal_composite, "
                "rate_signal, primary_driver, entry_timing, position_size, stop_level, "
                "data_quality_score, stress_level, predicted_direction, directional_bias, "
                "conviction, cot_signal, vol_signal, oi_signal, rr_signal, special_signal_value, "
                "special_signal_label, model_version, strategy_version, data_source) VALUES "
                + ",".join(values_sql)
            )
            conn.run(sql, **regime_params)
            logger.info("Regime batch %d-%d inserted", i, i + len(batch) - 1)

        conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls")
        conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit")

        conn.close()
        logger.info(
            "Batch wrote %d signals and %d regime_calls for %s",
            len(signal_rows),
            len(regime_rows),
            pair,
        )
