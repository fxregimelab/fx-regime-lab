# Crowding integration repair

27 September 2026. Packet 19, based on `9fa1505`, shared branch `codex/frontend`. This receipt records accepted local checks. Research and release acceptance remain open.

## What changed and why

The old pain number combined position ranks, a mean of closes labelled VWAP, and a carry adjustment. Those inputs do not identify participants' entry prices or losses. The [research review](repair-crowding-diagnostic-research.md) traces that problem to primary CFTC and CME definitions; the [implementation contract](../docs/CROWDING_DIAGNOSTIC_CONTRACT.md) defines the replacement.

The real daily scheduler now binds the versioned descriptor to `persisted_call_id`, `call.date`, and the frozen `call.predicted_direction`. Descriptive regime text cannot substitute for that direction. It stores separate provisional position and price components. Diagnostic failure produces the same versioned schema with explicit unavailable components. Unknown loss, report freshness and cluster status remain null, not false.

The scheduler no longer constructs a carry-adjusted participant entry price, reads yesterday's ranking to compute Apex, writes ranking-event logs, or produces a new rank. New desk cards store null pain, Apex and global rank. The actual trading-date reference used by the later daily summary is retained independently of ranking.

The AI prompt no longer receives a pain number or asks for controlled/elevated squeeze labels. The deterministic fallback and the parsed model response both use `Participant losses and squeeze probability unavailable`. Valid bias and catalyst fields are retained. Missing publication inputs still prevent the model request. Two unused Apex LinkedIn generators now raise before model access; the existing deterministic public share note remains available. No message was posted or sent.

The public reader suppresses stored historical pain, Apex and rank-jump estimates, and the actual React desk component renders qualified position and signed price descriptions. Original database records are preserved. Other retained free-text bias/catalyst claims, heuristic confidence, Markov estimates and methodological material remain subject to the wider research/publication review.

## Independent review

Parent review traced the scheduler, storage constructor, batch AI and fallback routes, query mapper, DeskCard and comparison consumer. It found a frontend contract mismatch: a valid position component was discarded when price history contained fewer than 40 observations. It also found type-insensitive duplicate COT comparison, where Python regards integer 1, boolean True and floating-point 1.0 as equal. The workers were asked to repair those findings and add failure cases before acceptance.

The parent consumer tests execute the real scheduler helper and descriptor for all three pairs, with a deliberately contradictory regime label. They also execute the actual production `DeskOpenCardRow` constructor expression and assert the stored null fields and call identity. An AST check confirms the daily flow routes the frozen call and spreads the returned telemetry. This is bounded integration evidence, not an execution of the full live scheduler or a database write.

Mocked AI tests cover normal response, founder-thesis context, timeout fallback, zero/high/invalid legacy pain, and both retired sharing entrypoints. A model that returns invented participant-loss language cannot populate `squeeze_risk`. All provider/model access is mocked.

GitNexus impact checks were run before changed symbols. `run_daily`, the AI consumers and retired sharing entrypoints returned CRITICAL with generic unrelated flows. The storage/runtime index mismatch and graph contamination prevent treating those counts as reliable. The owner was warned; direct source caller inspection supplemented the tool. No index was rebuilt while workers were active, and no commit was made.

## Verification

- Parent reverified the 21-case core/ranking gate, 55-case consumer integration gate and 10-test React render gate.
- The full pipeline regression gate passes; final collection reports 1,196 tests. Full Ruff passes; MyPy passes 206 source files.
- All frontend tests passed: 43 tests across TypeScript and JavaScript suites. The final focused render gate passed again after parent boundary fixes.
- The actual Python-to-TypeScript bridge passed 243 payloads across all three pairs, all four forecast states, absent/short/full histories, signed/zero/missing/invalid counts and arithmetic underflow. This uses the actual Python calculator and actual TypeScript reader, not two hand-copied fixtures.
- Final TypeScript and full Biome checks pass (204 files). The local production build passes, including 32 static pages. It used a loopback-only Supabase URL and placeholder anonymous key, with Next telemetry disabled. Canonical Linux/Vercel release and browser visual checks remain separate.
- Git whitespace check passes; the existing test-writer CRLF warning is unchanged.

The frontend gate initially had an unwrapped regex expectation and correctly remained unmet despite a successful test process. The expectation was corrected to actual regex syntax and rerun. A TypeScript invocation overlapped Next's regeneration of `.next/types` and failed on missing generated files; it was not accepted. The final TypeScript check ran after the build and passed. Future builds and standalone TypeScript checks must run sequentially.

Parent review also fixed nonfinite intermediate arithmetic in the frontend reader and accepted the core's explicit price-arithmetic failure shape without discarding valid COT. Each affected render check and build was rerun. Unlazy reports 137 met gates, six unmet root requirements and no abandonment. No accepted local result is a forecasting-performance or release result.

## Remaining evidence

These descriptors remain provisional: current COT rows lack release/vintage/category identity, and a date-fenced price history does not prove when it was available. Neither unit tests nor display repairs establish predictive skill, participant loss, or squeeze probability. Qualified acquisition, frozen research, complete security/migration checks, historical reconciliation, public methodology consistency and deployed observation remain required under the full repair goal. Docker and heavier Hermes services were not needed or started for this packet.
