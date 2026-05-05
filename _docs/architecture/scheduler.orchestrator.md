# Module: scheduler/orchestrator.py

## 📝 Description
@agent_context: High-level Prefect workflow orchestrator for daily and weekly FX regime classification and intelligence pipelines.
@allowed_imports: [asyncio, json, logging, os, sys, collections.abc, dataclasses, datetime, typing, dotenv, prefect, src.*]
@forbidden_imports: []
@obsidian_link: [[Orchestration#Pipeline Flow]]

## 🛠️ Functions
- `get_regime_age`
- `write_desk_open_cards_bulk_task`
- `upsert_pair_briefs_task`
- `upsert_macro_event_briefs_task`
- `run_weekly`

## 🔗 Dependencies (Imports)
- `__future__.annotations`
- `asyncio`
- `json`
- `logging`
- `os`
- `sys`
- `collections.abc.Mapping`
- `collections.abc.Sequence`
- `dataclasses.asdict`
- `datetime.date`
- `datetime.timedelta`
- `typing.Any`
- `typing.cast`
- `dotenv.load_dotenv`
- `prefect.flow`
- `prefect.task`
- [[ai.client.desk_card_brief_fallback.md|src.ai.client.desk_card_brief_fallback]]
- [[ai.client.generate_brief.md|src.ai.client.generate_brief]]
- [[ai.client.generate_desk_card_brief_async.md|src.ai.client.generate_desk_card_brief_async]]
- [[ai.client.generate_event_brief.md|src.ai.client.generate_event_brief]]
- [[ai.client.generate_global_macro_summary.md|src.ai.client.generate_global_macro_summary]]
- [[ai.client.summarize_weekly_memo_async.md|src.ai.client.summarize_weekly_memo_async]]
- [[analysis.asymmetry.compute_pain_index.md|src.analysis.asymmetry.compute_pain_index]]
- [[analysis.event_risk.compute_event_risk_matrix.md|src.analysis.event_risk.compute_event_risk_matrix]]
- [[analysis.markov.compute_time_decayed_markov.md|src.analysis.markov.compute_time_decayed_markov]]
- [[analysis.systemic.apply_cluster_to_telemetry.md|src.analysis.systemic.apply_cluster_to_telemetry]]
- [[analysis.systemic.assign_apex_ranking.md|src.analysis.systemic.assign_apex_ranking]]
- [[analysis.systemic.build_yesterday_rank_maps.md|src.analysis.systemic.build_yesterday_rank_maps]]
- [[analysis.systemic.compute_dollar_dominance_score.md|src.analysis.systemic.compute_dollar_dominance_score]]
- [[analysis.systemic.resolve_idiosyncratic_outlier.md|src.analysis.systemic.resolve_idiosyncratic_outlier]]
- [[analysis.systemic.top_three_clustered.md|src.analysis.systemic.top_three_clustered]]
- [[db.writer.md|src.db.writer]]
- [[fetchers.async_engine.build_master_buffer.md|src.fetchers.async_engine.build_master_buffer]]
- [[fetchers.buffer_keys.KEY_COT.md|src.fetchers.buffer_keys.KEY_COT]]
- [[fetchers.buffer_keys.KEY_CROSS_ASSET.md|src.fetchers.buffer_keys.KEY_CROSS_ASSET]]
- [[fetchers.buffer_keys.KEY_FX_SPOT.md|src.fetchers.buffer_keys.KEY_FX_SPOT]]
- [[fetchers.buffer_keys.KEY_YIELDS.md|src.fetchers.buffer_keys.KEY_YIELDS]]
- [[fetchers.macro_calendar.fetch_macro_events.md|src.fetchers.macro_calendar.fetch_macro_events]]
- [[fetchers.open_interest.compute_oi_delta_from_cot.md|src.fetchers.open_interest.compute_oi_delta_from_cot]]
- [[fetchers.open_interest.compute_oi_from_cot.md|src.fetchers.open_interest.compute_oi_from_cot]]
- [[fetchers.substack.fetch_latest_substack_memo.md|src.fetchers.substack.fetch_latest_substack_memo]]
- [[fetchers.volatility.fetch_implied_vol.md|src.fetchers.volatility.fetch_implied_vol]]
- [[fetchers.volatility.fetch_realized_vol.md|src.fetchers.volatility.fetch_realized_vol]]
- [[regime.classifier.VOL_EXPANDING_SUFFIX.md|src.regime.classifier.VOL_EXPANDING_SUFFIX]]
- [[regime.classifier.classify_regime.md|src.regime.classifier.classify_regime]]
- [[regime.composite.TRADING_DAYS_3Y.md|src.regime.composite.TRADING_DAYS_3Y]]
- [[regime.composite.compute_composite.md|src.regime.composite.compute_composite]]
- [[regime.composite.compute_dominance_scores.md|src.regime.composite.compute_dominance_scores]]
- [[regime.composite.compute_dynamic_betas.md|src.regime.composite.compute_dynamic_betas]]
- [[regime.composite.dominance_top_family.md|src.regime.composite.dominance_top_family]]
- [[regime.composite.get_primary_driver.md|src.regime.composite.get_primary_driver]]
- [[regime.confidence.compute_confidence.md|src.regime.confidence.compute_confidence]]
- [[signals.cot.compute_cot_percentile.md|src.signals.cot.compute_cot_percentile]]
- [[signals.cot.normalize_cot_signal.md|src.signals.cot.normalize_cot_signal]]
- [[signals.open_interest.compute_oi_signal.md|src.signals.open_interest.compute_oi_signal]]
- [[signals.rate.build_carry_history_from_rows.md|src.signals.rate.build_carry_history_from_rows]]
- [[signals.rate.build_real_yield_10y_spread_history_from_rows.md|src.signals.rate.build_real_yield_10y_spread_history_from_rows]]
- [[signals.rate.compute_risk_adjusted_carry.md|src.signals.rate.compute_risk_adjusted_carry]]
- [[signals.rate.normalize_rate_signal.md|src.signals.rate.normalize_rate_signal]]
- [[signals.rate.rate_direction_from_spreads.md|src.signals.rate.rate_direction_from_spreads]]
- [[signals.rate.structural_instability_from_carry_history.md|src.signals.rate.structural_instability_from_carry_history]]
- [[signals.volatility.compute_vol_signal.md|src.signals.volatility.compute_vol_signal]]
- [[signals.volatility.is_vol_expanding.md|src.signals.volatility.is_vol_expanding]]
- [[types.PAIRS.md|src.types.PAIRS]]
- [[types.CotRow.md|src.types.CotRow]]
- [[types.DeskOpenCardRow.md|src.types.DeskOpenCardRow]]
- [[types.RegimeCall.md|src.types.RegimeCall]]
- [[types.SignalRow.md|src.types.SignalRow]]
- [[types.SpotBar.md|src.types.SpotBar]]
- [[types.load_universe.md|src.types.load_universe]]
- [[validation.ledger.md|src.validation.ledger]]
- [[validation.backtest.validate_call.md|src.validation.backtest.validate_call]]
- [[validation.ingestion_buffer.validate_ingestion_buffer.md|src.validation.ingestion_buffer.validate_ingestion_buffer]]
- [[fetchers.polymarket.get_active_economics_markets.md|src.fetchers.polymarket.get_active_economics_markets]]
- [[fetchers.polymarket.polymarket_odds_json_for_prompt.md|src.fetchers.polymarket.polymarket_odds_json_for_prompt]]

---
*Auto-generated by FX Regime Lab Obsidian Mapper*