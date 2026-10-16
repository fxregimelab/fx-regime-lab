"""COT positioning signal family adapter."""

from __future__ import annotations

from datetime import date

from src.fetchers.open_interest import compute_oi_delta_from_cot, compute_oi_from_cot
from src.signals.cot import compute_cot_percentile, normalize_cot_signal
from src.staged.contracts import IngestionSnapshot
from src.staged.signals.types import CotFamilyOutput, FamilyOutput
from src.types import CotRow


def _cot_rows_for_pair(rows: list[CotRow], pair: str) -> list[CotRow]:
    return sorted([r for r in rows if r.pair == pair], key=lambda r: r.date)


def _latest_cot_net_pos(rows: list[CotRow], pair: str) -> int | None:
    pair_rows = _cot_rows_for_pair(rows, pair)
    if not pair_rows:
        return None
    return int(pair_rows[-1].net_long)


def _latest_cot_breakdown(rows: list[CotRow], pair: str) -> tuple[int | None, int | None]:
    pair_rows = _cot_rows_for_pair(rows, pair)
    if not pair_rows:
        return None, None
    latest = pair_rows[-1]
    return latest.asset_mgr_net, latest.lev_money_net


def _days_since_cot(rows: list[CotRow], pair: str, as_of: date) -> int:
    pair_rows = _cot_rows_for_pair(rows, pair)
    if not pair_rows:
        return 999
    latest = pair_rows[-1].date
    return (as_of - latest).days


class CotFamily:
    """Compute COT percentile, OI normalization, and positioning breakdown."""

    def compute(self, pair: str, snapshot: IngestionSnapshot) -> FamilyOutput:
        as_of = snapshot.date
        cot_pct = compute_cot_percentile(snapshot.cot_rows, pair, as_of=as_of)
        cot_norm = normalize_cot_signal(cot_pct)
        oi_pct = compute_oi_from_cot(snapshot.cot_rows, pair)
        oi_norm = (
            float(max(-1.0, min(1.0, -(oi_pct - 50.0) / 50.0)))
            if oi_pct is not None
            else None
        )
        oi_delta = compute_oi_delta_from_cot(snapshot.cot_rows, pair)
        cot_net_pos = _latest_cot_net_pos(snapshot.cot_rows, pair)
        cot_asset_mgr_net, cot_lev_money_net = _latest_cot_breakdown(snapshot.cot_rows, pair)
        days_since_cot = _days_since_cot(snapshot.cot_rows, pair, as_of)

        return FamilyOutput(
            rate=None,
            cot=CotFamilyOutput(
                percentile=cot_pct,
                norm=cot_norm,
                oi_norm=oi_norm,
                oi_delta=oi_delta,
                net_pos=cot_net_pos,
                asset_mgr_net=cot_asset_mgr_net,
                lev_money_net=cot_lev_money_net,
                days_since_cot=days_since_cot,
            ),
            vol=None,
            special=None,
        )
