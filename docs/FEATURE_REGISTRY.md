# Feature registry

Status vocabulary:

- **LIVE:** existed in v1 public surface (static `site/` under archive) and is still operationally produced by the pipeline today.
- **SCAFFOLDED:** a `web/` file exists with real wiring partial or placeholder UI.
- **PLANNED:** no implementation file in `web/` at doc time.

Supabase column in the table is the **primary** table for that feature, or `—` if not data-backed yet.

| Feature | Phase | Status | Description | Supabase table | Component or path | Dependencies |
|---------|-------|--------|-------------|------------------|-------------------|----------------|
| RegimeCard | 1 | SCAFFOLDED | Pair regime summary card with confidence bar | `regime_calls` | `web/components/regime/RegimeCard.tsx` | `useRegimeCalls`, `Badge`, `ConfidenceBar` |
| ValidationTable | 1 | SCAFFOLDED | Tabular validation history | `validation_log` | `web/components/regime/ValidationTable.tsx` | Parent must pass `rows` (no default fetch wired in a page yet) |
| BriefRenderer | 1 | SCAFFOLDED | Renders latest `brief_text` | `brief_log` | `web/components/brief/BriefRenderer.tsx` | `useBrief` |
| ConfidenceBar | 1 | SCAFFOLDED | Horizontal confidence meter | derived from `regime_calls.confidence` | `web/components/regime/ConfidenceBar.tsx` | Used by `RegimeCard` |
| SignalStack | 1 | SCAFFOLDED | Per-signal direction rows from a regime call | `regime_calls` | `web/components/regime/SignalStack.tsx` | Expects `RegimeCall` |
| DivergenceAlert | 2 | PLANNED | Banner for model vs market divergence | — | — | Not implemented |
| DivergenceFeed | 3 | PLANNED | Feed page for divergences | `divergence_log` (PLANNED table) | — | Schema missing |
| HypothesisLog | 2 | PLANNED | Hypothesis ledger | `hypothesis_log` (PLANNED) | — | Schema missing |
| ThesisGraveyard | 2 | PLANNED | Archived theses view | — | — | Not implemented |
| RegimeTransitionMap | 2 | PLANNED | Visual map of regime changes | `regime_calls` | — | Chart not built |
| SignalAttributionDashboard | 2 | PLANNED | Attribution dashboard | `signals` | — | Not implemented |
| ScenarioStressTester | 4 | PLANNED | Scenario tool | — | — | Not implemented |
| MethodologyVersionHistory | 2 | PLANNED | Versioned methodology | `methodology_versions` (PLANNED) | — | Schema missing |
| MacroCalendarOverlay | 2 | PLANNED | Calendar overlay on charts | `brief_log.macro_context` partial today | — | Macro JSON on disk |
| CentralBankTracker | 3 | PLANNED | CB communication tracker | — | — | Not implemented |
| IPFSCallArchive | 4 | PLANNED | Hashed call archive | — | — | Not implemented |
| PeerComparison | 4 | PLANNED | Peer stats | — | — | Not implemented |
| PaperPositionLog | 4 | PLANNED | Paper trades UI | `paper_positions` (schema exists, no writer) | — | Pipeline writer missing |
| PerformancePage | 1 | SCAFFOLDED | Aggregate performance page | `validation_log` | `web/app/(shell)/performance/page.tsx` | Not wired to hooks yet |
| TrackRecordStrip | 1 | PLANNED | Compact rolling accuracy strip | `validation_log` | — | Not implemented as component |
| CanvasBg | 1 | SCAFFOLDED | Animated background canvas | — | `web/components/shell/CanvasBg.tsx` | Shell layout |
| Nav | 1 | SCAFFOLDED | Shell navigation | — | `web/components/shell/Nav.tsx` | Client dropdown |
| TerminalNav | 1 | SCAFFOLDED | Terminal top strip | — | `web/components/terminal/TerminalNav.tsx` | Client |
| TimeSeriesChart | 1 | SCAFFOLDED | Lightweight Charts line chart | optional `signals` history | `web/components/charts/TimeSeriesChart.tsx` | `lightweight-charts` v5 |
| RegimeChart | 1 | SCAFFOLDED | Title + chart wrapper | — | `web/components/charts/RegimeChart.tsx` | Uses `TimeSeriesChart` |
| Badge | 1 | SCAFFOLDED | Regime chip | — | `web/components/ui/Badge.tsx` | `REGIME_COLORS` |
| Skeleton | 1 | SCAFFOLDED | Loading skeleton | — | `web/components/ui/Skeleton.tsx` | Not used yet |
| PairDesk | 1 | SCAFFOLDED | Pair terminal desk | `regime_calls`, `signals` | `web/components/terminal/PairDesk.tsx` | Hooks |
| SignalDepth | 1 | SCAFFOLDED | Compact signal column display | `signals` | `web/components/terminal/SignalDepth.tsx` | `PairDesk` |
| Morning HTML brief | 0 | LIVE | Pipeline-built HTML brief | — | `_archive/v1/create_html_brief.py` output | Still produced nightly |
| Static site shell | 0 | LIVE (archived copy) | Legacy Cloudflare static site | — | `_archive/v1/site/` | Worker deploy in CI today |
| API health | 0 | LIVE | Worker heartbeat | — | `workers/site-entry.js` `/api/health` | Cloudflare Worker |
| Yahoo proxy | 0 | LIVE | Worker Yahoo proxy routes | — | `workers/site-entry.js` | Cloudflare Worker |

## Related docs

- [[FRONTEND_ARCHITECTURE]]
- [[DATABASE_SCHEMA]]
- [[PHASES]]
