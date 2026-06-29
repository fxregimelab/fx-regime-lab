"""Validation log repository (internal — use ``src.db.writer``)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from typing import Any, cast

from postgrest.exceptions import APIError
from supabase import Client

from src.db.repositories.common import date_iso
from src.db.repositories.ledger import AppendOnlyLedger

_VALIDATION_IGNORED_DIFF_KEYS = {"id", "created_at", "is_superseded"}


class ValidationLogRepository:
    def __init__(self, client_factory: Callable[[], Client]) -> None:
        self._client_factory = client_factory
        self._has_call_date: bool | None = None

    @staticmethod
    def _validation_payload_matches_existing(
        payload: dict[str, Any], existing: dict[str, Any]
    ) -> bool:
        """Return True when every substantive field in *payload* matches *existing*."""
        for key, value in payload.items():
            if key in _VALIDATION_IGNORED_DIFF_KEYS:
                continue
            if existing.get(key) != value:
                return False
        return True

    def _strip_unknown_validation_columns(
        self, payloads: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Insert validation rows, stripping unknown columns one at a time on legacy schemas."""
        client = self._client_factory()
        working = [{k: v for k, v in p.items() if k != "id"} for p in payloads]
        unknown_cols: set[str] = set()

        while True:
            try:
                if working:
                    client.table("validation_log").insert(working).execute()
                return working
            except APIError as exc:
                msg = str(getattr(exc, "message", "")) or str(exc)
                if "Could not find the '" in msg and "' column of 'validation_log'" in msg:
                    col_match = msg.split("Could not find the '")[1].split("'")[0]
                    if col_match in unknown_cols:
                        break
                    unknown_cols.add(col_match)
                    working = [
                        {k: v for k, v in p.items() if k != col_match} for p in working
                    ]
                    continue
                raise

        inserted: list[dict[str, Any]] = []
        for payload in payloads:
            insert_payload = {k: v for k, v in payload.items() if k != "id"}
            for _attempt in range(10):
                try:
                    client.table("validation_log").insert(insert_payload).execute()
                    inserted.append(insert_payload)
                    break
                except APIError as exc:
                    msg = str(getattr(exc, "message", "")) or str(exc)
                    if "Could not find the '" in msg and "' column of 'validation_log'" in msg:
                        col_match = msg.split("Could not find the '")[1].split("'")[0]
                        insert_payload.pop(col_match, None)
                        continue
                    raise
        return inserted

    def _insert_validation_log(self, payload: dict[str, Any]) -> None:
        """Insert a single validation_log row, stripping unknown columns on legacy schemas."""
        self._strip_unknown_validation_columns([payload])

    def get_validation_log_entry(
        self, call_date: date | str, pair: str
    ) -> dict[str, Any] | None:
        """Fetch the current (non-superseded) validation_log row for a call + pair."""
        iso = date_iso(call_date)
        client = self._client_factory()

        if self._has_call_date is not False:
            try:
                res = (
                    client.table("validation_log")
                    .select("*")
                    .eq("call_date", iso)
                    .eq("pair", pair)
                    .eq("is_superseded", False)
                    .order("created_at", desc=True)
                    .limit(1)
                    .maybe_single()
                    .execute()
                )
                if res is not None:
                    raw = res.data
                    if isinstance(raw, dict):
                        self._has_call_date = True
                        return cast(dict[str, Any], raw)
            except APIError as exc:
                msg = str(getattr(exc, "message", "")) or str(exc)
                if "column validation_log.call_date does not exist" in msg:
                    self._has_call_date = False
                elif "column validation_log.is_superseded does not exist" in msg:
                    try:
                        res = (
                            client.table("validation_log")
                            .select("*")
                            .eq("call_date", iso)
                            .eq("pair", pair)
                            .maybe_single()
                            .execute()
                        )
                        if res is not None:
                            raw = res.data
                            if isinstance(raw, dict):
                                self._has_call_date = True
                                return cast(dict[str, Any], raw)
                    except APIError:
                        pass
                else:
                    raise

        if self._has_call_date is not True:
            try:
                res = (
                    client.table("validation_log")
                    .select("*")
                    .eq("date", iso)
                    .eq("pair", pair)
                    .eq("is_superseded", False)
                    .order("created_at", desc=True)
                    .limit(1)
                    .maybe_single()
                    .execute()
                )
                if res is not None:
                    raw = res.data
                    if isinstance(raw, dict):
                        return cast(dict[str, Any], raw)
            except APIError as exc:
                msg = str(getattr(exc, "message", "")) or str(exc)
                if "column validation_log.is_superseded does not exist" in msg:
                    res = (
                        client.table("validation_log")
                        .select("*")
                        .eq("date", iso)
                        .eq("pair", pair)
                        .maybe_single()
                        .execute()
                    )
                    if res is not None:
                        raw = res.data
                        if isinstance(raw, dict):
                            return cast(dict[str, Any], raw)
                else:
                    raise
        return None

    def _find_existing_for_write(
        self, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        client = self._client_factory()
        call_id = payload.get("call_id")
        pair = payload.get("pair")
        date_val = payload.get("call_date") or payload.get("date")

        existing: dict[str, Any] | None = None
        if call_id is not None:
            try:
                res = (
                    client.table("validation_log")
                    .select("*")
                    .eq("call_id", call_id)
                    .eq("is_superseded", False)
                    .order("created_at", desc=True)
                    .limit(1)
                    .maybe_single()
                    .execute()
                )
                if res is not None and res.data is not None:
                    raw = res.data
                    if isinstance(raw, dict):
                        existing = cast(dict[str, Any], raw)
            except APIError as exc:
                msg = str(getattr(exc, "message", "")) or str(exc)
                if "column validation_log.is_superseded does not exist" in msg:
                    res = (
                        client.table("validation_log")
                        .select("*")
                        .eq("call_id", call_id)
                        .maybe_single()
                        .execute()
                    )
                    if res is not None and res.data is not None:
                        raw = res.data
                        if isinstance(raw, dict):
                            existing = cast(dict[str, Any], raw)
                elif "column validation_log.call_id does not exist" not in msg:
                    raise

        if existing is None and pair is not None and date_val is not None:
            existing = self.get_validation_log_entry(date_val, pair)

        return existing

    @staticmethod
    def _should_skip_t5_only_update(
        existing: dict[str, Any], payload: dict[str, Any]
    ) -> bool:
        if existing.get("log_return_t5_bps") is not None:
            existing_has_t20 = existing.get("log_return_t20_bps") is not None
            payload_has_t20 = payload.get("log_return_t20_bps") is not None
            if existing_has_t20 or not payload_has_t20:
                return True
        return False

    def write_validation_row(self, row: Mapping[str, Any]) -> None:
        """Insert a validation_log row, versioning if materially different."""
        payload = cast(dict[str, Any], dict(row))
        client = self._client_factory()
        existing = self._find_existing_for_write(payload)

        def on_supersede(row_id: Any) -> None:
            client.table("validation_log").update({"is_superseded": True}).eq(
                "id", row_id
            ).execute()

        def on_insert(insert_payload: dict[str, Any]) -> None:
            self._insert_validation_log(insert_payload)

        AppendOnlyLedger.append(
            payload,
            existing,
            payload_matches=self._validation_payload_matches_existing,
            on_supersede=on_supersede,
            on_insert=on_insert,
            should_skip=self._should_skip_t5_only_update,
        )

    def supersede_validation_row(self, row_id: str | int) -> None:
        """Mark a single validation_log row as superseded (append-only cleanup)."""
        self._client_factory().table("validation_log").update({"is_superseded": True}).eq(
            "id", row_id
        ).execute()

    def update_validation_log_row(
        self, row_id: str | int, updates: Mapping[str, Any]
    ) -> None:
        """In-place update of derived fields on a validation_log row."""
        self._client_factory().table("validation_log").update(dict(updates)).eq(
            "id", row_id
        ).execute()

    def bulk_rewrite_validation_rows(
        self, old_ids: list[str | int], new_rows: list[dict[str, Any]]
    ) -> None:
        """Versioned bulk correction of validation_log rows."""
        client = self._client_factory()
        for i in range(0, len(old_ids), 500):
            old_chunk = old_ids[i : i + 500]
            client.table("validation_log").update({"is_superseded": True}).in_(
                "id", old_chunk
            ).execute()

        for i in range(0, len(new_rows), 500):
            new_chunk = new_rows[i : i + 500]
            self._strip_unknown_validation_columns(new_chunk)

    def _validation_log_has_t5_for_call(
        self, call_id: Any, call_date: str, pair: str
    ) -> bool:
        """Return True when a current validation_log row exists with brier_score_t5."""
        client = self._client_factory()

        def _by_call_id(include_superseded_filter: bool) -> Any:
            q = (
                client.table("validation_log")
                .select("brier_score_t5")
                .eq("call_id", call_id)
                .not_.is_("brier_score_t5", "null")
            )
            if include_superseded_filter:
                q = q.eq("is_superseded", False)
            return q.maybe_single().execute()

        def _by_date_pair(include_superseded_filter: bool) -> Any:
            q = (
                client.table("validation_log")
                .select("brier_score_t5")
                .eq("date", call_date)
                .eq("pair", pair)
                .not_.is_("brier_score_t5", "null")
            )
            if include_superseded_filter:
                q = q.eq("is_superseded", False)
            return q.maybe_single().execute()

        if call_id is not None:
            try:
                vres = _by_call_id(include_superseded_filter=True)
                if vres is not None and vres.data is not None:
                    return True
            except APIError as exc:
                msg = str(getattr(exc, "message", "")) or str(exc)
                if "column validation_log.is_superseded does not exist" in msg:
                    try:
                        vres = _by_call_id(include_superseded_filter=False)
                        if vres is not None and vres.data is not None:
                            return True
                    except Exception:
                        pass
                elif "column validation_log.call_id does not exist" not in msg:
                    pass
            except Exception:
                pass

        try:
            vres = _by_date_pair(include_superseded_filter=True)
            if vres is not None and vres.data is not None:
                return True
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)
            if "column validation_log.is_superseded does not exist" in msg:
                try:
                    vres = _by_date_pair(include_superseded_filter=False)
                    if vres is not None and vres.data is not None:
                        return True
                except Exception:
                    pass
        except Exception:
            pass

        return False

    def get_unvalidated_regime_calls(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Return regime_calls rows lacking a current validation_log entry with brier_score_t5."""
        query = (
            self._client_factory()
            .table("regime_calls")
            .select("id,date,pair,regime,rate_signal,confidence")
            .order("date", desc=False)
        )
        if limit is not None:
            query = query.limit(limit)

        res = query.execute()
        calls = cast(list[dict[str, Any]], res.data or [])

        unvalidated: list[dict[str, Any]] = []
        for call in calls:
            call_id = call.get("id")
            call_date = str(call.get("date"))[:10]
            pair = str(call.get("pair"))

            if not self._validation_log_has_t5_for_call(call_id, call_date, pair):
                unvalidated.append(call)

        return unvalidated

    @staticmethod
    def _normalize_validation_row(row: dict[str, Any]) -> dict[str, Any]:
        """Normalize a legacy validation_log row to the modern schema."""
        out = dict(row)

        ret_5d = row.get("actual_return_5d")
        if ret_5d is not None and "log_return_t5_bps" not in row:
            out["log_return_t5_bps"] = float(ret_5d) * 10_000.0

        corr_5d = row.get("correct_5d")
        if corr_5d is not None and "correct_t5" not in row:
            out["correct_t5"] = bool(corr_5d)

        if "actual_direction" in row and "actual_direction_t5" not in row:
            out["actual_direction_t5"] = row["actual_direction"]

        conf = row.get("confidence")
        if conf is not None and "brier_score_t5" not in row:
            if out.get("correct_t5") is True:
                out["brier_score_t5"] = (float(conf) - 1.0) ** 2
            elif out.get("correct_t5") is False:
                out["brier_score_t5"] = float(conf) ** 2

        return out

    def get_validation_log_for_stats(
        self,
        pair_filter: str | None = None,
        lookback_days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch validation rows for aggregate statistics."""
        modern_select = (
            "pair,predicted_direction,confidence,date,"
            "actual_direction_t5,log_return_t5_bps,correct_t5,brier_score_t5,"
            "correct_net_t5,cost_bps_t5,"
            "actual_direction_t20,log_return_t20_bps,correct_t20,brier_score_t20,"
            "correct_net_t20,cost_bps_t20"
        )
        legacy_select = (
            "pair,predicted_direction,confidence,date,"
            "actual_direction,actual_return_1d,actual_return_5d,"
            "correct_1d,correct_5d"
        )

        def _build_query(select: str, include_superseded_filter: bool) -> Any:
            q = self._client_factory().table("validation_log").select(select)
            if include_superseded_filter:
                q = q.eq("is_superseded", False)
            if pair_filter:
                q = q.eq("pair", pair_filter)
            if lookback_days is not None and lookback_days > 0:
                cutoff = date.today() - __import__("datetime").timedelta(days=lookback_days)
                q = q.gte("date", cutoff.isoformat())
            return q

        def _fetch_all(q: Any) -> list[dict[str, Any]]:
            all_rows: list[dict[str, Any]] = []
            page_size = 1000
            page = 0
            while True:
                res = q.range(page * page_size, (page + 1) * page_size - 1).execute()
                rows = cast(list[dict[str, Any]], res.data or [])
                if not rows:
                    break
                all_rows.extend(rows)
                if len(rows) < page_size:
                    break
                page += 1
            return all_rows

        try:
            q = _build_query(modern_select, include_superseded_filter=True)
            return _fetch_all(q)
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)
            if "column validation_log." in msg:
                try:
                    q = _build_query(legacy_select, include_superseded_filter=False)
                    rows = _fetch_all(q)
                except APIError as exc2:
                    msg2 = str(getattr(exc2, "message", "")) or str(exc2)
                    if "is_superseded" in msg2:
                        q = _build_query(legacy_select, include_superseded_filter=False)
                        rows = _fetch_all(q)
                    else:
                        raise
                return [self._normalize_validation_row(r) for r in rows]
            raise
