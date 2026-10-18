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
        """Bulk-upsert backfill (signal, call) tuples for a single pair.

        The write is scoped to the reconstruction ``model_version`` value(s)
        present in ``results``. Existing ``regime_calls`` rows for this pair
        carrying any other ``model_version`` (including NULL legacy rows) are
        treated as protected live/legacy data: incoming rows dated on those
        protected dates are skipped with a warning, are never deleted and are
        never updated. Skipping is fail-safe — a run never fails because of
        it.

        Both tables use ``INSERT ... ON CONFLICT (pair, date) DO UPDATE SET``
        against their ``(pair, date)`` unique indexes, updating only the
        columns listed below. Re-runs therefore update reconstructed rows in
        place, and auxiliary ``signals`` columns (COT splits, ``z_blended``,
        ``bund_btp_spread``, FPI/BoJ/India fields, ...) keep their values.

        The two ``regime_calls`` triggers are disabled for the write and are
        always re-enabled in a ``finally`` block, even when a batch fails
        mid-write (best effort if the connection itself died; failures are
        logged).

        ``validation_log`` is never touched.
        """
        if not results:
            return

        raw_versions = {call.model_version for _, call in results}
        if not raw_versions or any(not version for version in raw_versions):
            raise ValueError(
                "bulk_write_backfill_results requires a truthy model_version on every "
                f"result for pair {pair}; got {sorted(repr(v) for v in raw_versions)}"
            )
        recon_versions: set[str] = {version for version in raw_versions if version}

        triggers_disabled = False
        conn = _pg_conn()
        try:
            placeholders = ", ".join(f":mv{i}" for i in range(len(recon_versions)))
            version_params: dict[str, Any] = {"pair": pair}
            for i, version in enumerate(sorted(recon_versions)):
                version_params[f"mv{i}"] = version
            protected_rows = conn.run(
                "SELECT DISTINCT date FROM regime_calls WHERE pair = :pair "
                f"AND (model_version IS NULL OR model_version NOT IN ({placeholders}))",
                **version_params,
            )
            protected_dates = {str(row[0])[:10] for row in protected_rows}

            write_rows: list[tuple[SignalRow, RegimeCall]] = []
            skipped_dates: list[str] = []
            for signal_row, call in results:
                row_dates = (date_iso(signal_row.date), date_iso(call.date))
                protected_hits = [d for d in row_dates if d in protected_dates]
                if protected_hits:
                    skipped_dates.append(min(protected_hits))
                    continue
                write_rows.append((signal_row, call))

            if skipped_dates:
                logger.warning(
                    "Backfill %s: skipped %d of %d incoming rows overlapping protected "
                    "live/legacy dates (%s..%s); protected rows are never deleted or updated",
                    pair,
                    len(skipped_dates),
                    len(results),
                    min(skipped_dates),
                    max(skipped_dates),
                )
            if not write_rows:
                return

            signal_rows: list[tuple[Any, ...]] = []
            regime_rows: list[tuple[Any, ...]] = []
            for signal_row, call in write_rows:
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

            conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls")
            triggers_disabled = True
            conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_log_regime_call_audit")

            batch_size = 500
            for i in range(0, len(signal_rows), batch_size):
                batch = signal_rows[i:i + batch_size]
                values_sql = []
                params: dict[str, Any] = {}
                for j, row in enumerate(batch):
                    prefix = f"r{j}_"
                    values_sql.append(
                        f"(:{prefix}pair, :{prefix}date, :{prefix}r2y, :{prefix}r10y, "
                        f":{prefix}cot, "
                        f":{prefix}rv20, :{prefix}rv5, :{prefix}iv, :{prefix}spot, "
                        f":{prefix}dc, :{prefix}dcp, "
                        f":{prefix}vix, :{prefix}dxy, :{prefix}oil, "
                        f":{prefix}us10y, :{prefix}gold, "
                        f":{prefix}copper, :{prefix}stoxx, :{prefix}oi, "
                        f":{prefix}rvol, :{prefix}si, "
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
                    + " ON CONFLICT (pair, date) DO UPDATE SET "
                    "rate_diff_2y = EXCLUDED.rate_diff_2y, "
                    "rate_diff_10y = EXCLUDED.rate_diff_10y, "
                    "cot_percentile = EXCLUDED.cot_percentile, "
                    "realized_vol_20d = EXCLUDED.realized_vol_20d, "
                    "realized_vol_5d = EXCLUDED.realized_vol_5d, "
                    "implied_vol_30d = EXCLUDED.implied_vol_30d, "
                    "spot = EXCLUDED.spot, "
                    "day_change = EXCLUDED.day_change, "
                    "day_change_pct = EXCLUDED.day_change_pct, "
                    "cross_asset_vix = EXCLUDED.cross_asset_vix, "
                    "cross_asset_dxy = EXCLUDED.cross_asset_dxy, "
                    "cross_asset_oil = EXCLUDED.cross_asset_oil, "
                    "cross_asset_us10y = EXCLUDED.cross_asset_us10y, "
                    "cross_asset_gold = EXCLUDED.cross_asset_gold, "
                    "cross_asset_copper = EXCLUDED.cross_asset_copper, "
                    "cross_asset_stoxx = EXCLUDED.cross_asset_stoxx, "
                    "oi_delta = EXCLUDED.oi_delta, "
                    "volume_rvol = EXCLUDED.volume_rvol, "
                    "structural_instability = EXCLUDED.structural_instability, "
                    "breakeven_inflation_10y = EXCLUDED.breakeven_inflation_10y, "
                    "rate_diff_10y_real = EXCLUDED.rate_diff_10y_real, "
                    "rate_z_tactical = EXCLUDED.rate_z_tactical, "
                    "rate_z_structural = EXCLUDED.rate_z_structural, "
                    "realized_vol_rank = EXCLUDED.realized_vol_rank, "
                    "skew_alignment = EXCLUDED.skew_alignment"
                )
                conn.run(sql, **params)
                logger.info("Signals batch %d-%d upserted", i, i + len(batch) - 1)

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
                    "conviction, cot_signal, vol_signal, oi_signal, rr_signal, "
                    "special_signal_value, "
                    "special_signal_label, model_version, strategy_version, data_source) VALUES "
                    + ",".join(values_sql)
                    + " ON CONFLICT (pair, date) DO UPDATE SET "
                    "regime = EXCLUDED.regime, "
                    "confidence = EXCLUDED.confidence, "
                    "signal_composite = EXCLUDED.signal_composite, "
                    "rate_signal = EXCLUDED.rate_signal, "
                    "primary_driver = EXCLUDED.primary_driver, "
                    "entry_timing = EXCLUDED.entry_timing, "
                    "position_size = EXCLUDED.position_size, "
                    "stop_level = EXCLUDED.stop_level, "
                    "data_quality_score = EXCLUDED.data_quality_score, "
                    "stress_level = EXCLUDED.stress_level, "
                    "predicted_direction = EXCLUDED.predicted_direction, "
                    "directional_bias = EXCLUDED.directional_bias, "
                    "conviction = EXCLUDED.conviction, "
                    "cot_signal = EXCLUDED.cot_signal, "
                    "vol_signal = EXCLUDED.vol_signal, "
                    "oi_signal = EXCLUDED.oi_signal, "
                    "rr_signal = EXCLUDED.rr_signal, "
                    "special_signal_value = EXCLUDED.special_signal_value, "
                    "special_signal_label = EXCLUDED.special_signal_label, "
                    "model_version = EXCLUDED.model_version, "
                    "strategy_version = EXCLUDED.strategy_version, "
                    "data_source = EXCLUDED.data_source"
                )
                conn.run(sql, **regime_params)
                logger.info("Regime batch %d-%d upserted", i, i + len(batch) - 1)

            logger.info(
                "Backfill %s: upserted %d signals and %d regime_calls (%d skipped)",
                pair,
                len(signal_rows),
                len(regime_rows),
                len(skipped_dates),
            )
        finally:
            if triggers_disabled:
                for stmt in (
                    "ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls",
                    "ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit",
                ):
                    try:
                        conn.run(stmt)
                    except Exception:
                        logger.warning(
                            "Backfill %s: failed to re-enable trigger (%s); check the "
                            "connection and re-enable it manually",
                            pair,
                            stmt,
                            exc_info=True,
                        )
            try:
                conn.close()
            except Exception:
                logger.warning(
                    "Backfill %s: failed to close connection", pair, exc_info=True
                )
