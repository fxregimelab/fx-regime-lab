# D03 rate observation and freshness — local packet report

29 September 2026. Checkout `codex/frontend`, HEAD `9fa150538d08ab5a2a6c587976552944f47a724d`. The checkout had substantial uncommitted repair work before this packet. No reset, clone, commit, push, deployment, production request, production data write, SQL migration, or edit to `IDENTITY.md` was made. No database or heavy runtime was needed or started.

## Result and decisive control

**D03 remains IN PROGRESS.** Source timing now travels beside scalar yields through the async master buffer, core `IngestionSnapshot`, staged snapshot and signal path. The synchronous fetcher can emit the same observation records through an optional sink. Each record carries the actual provider series/ticker, documented instrument where known, source observation date, retrieval time, value, unit, explicit missing reason, and separately the FRED real-time fields. The verified availability time and true historical vintage remain `None` when the current source path cannot establish them. Scalar callers remain compatible but unqualified for a timed rate feature. Live, staged and replay rate paths use the same qualification function; replay's old `historical_yields` scalars fail closed by default. The accepted base-minus-quote pair orientation and matched two-year instrument rules are unchanged.

The **red control** was run before changing `_rates_bucket_freshness`:

```text
python -m pytest -q tests/test_d03_rate_observation.py -k stale_spot
FAILED: assert 1.0 == 0.1
```

The fixture had a fresh 29 September EUR/USD spot and a 1 September yield. The old scalar spread still returned `-2.0` percentage points and the old rate-quality bucket scored `1.0` from the spot date. On the repaired boundary, that bucket scores `0.1` and the rate spread is unavailable. A same-day, explicitly released and versioned pair of matched synthetic observations scores `1.0` and yields `-2.0` in the live, staged and replay qualification seams. The test also covers zero versus missing, an old monthly observation, unknown release or vintage, post-decision release, and FRED-to-Yahoo fallback preserving the actual ticker identity. No synthetic fixture is published as live data.

## Checks

All commands below ran from `pipeline/` unless stated otherwise. Final run, after the last source change:

| Check | Result |
| --- | --- |
| `python -m pytest -q tests/test_d03_rate_observation.py` | 5 passed |
| `python -m pytest -q` | 2,041 passed in 56.55 s |
| `ruff check .` | All checks passed |
| `mypy .` | Success, 231 source files |
| `git diff --check` (repository root) | Exit 0; only a pre-existing CRLF notice for `pipeline/tests/test_writer.py` |
| `node C:/Users/sakha/.codex/skills/unlazy/scripts/gate-lint.mjs .unlazy/d03/GATES.md` | LINT OK, five warnings about broad test success strings and a manual report gate |

GitNexus impact was run before the rate-feature and DQS edits. The index rates `two_year_spread` and `_rates_bucket_freshness` CRITICAL, with seven affected indexed flows, including daily, staged and backfill paths. Direct references were noisy; compatibility and full-suite checks were used. The MCP impact call could not open LadybugDB due storage version 42 versus runtime 40, so the CLI impact result is the recorded one. No commit was made, so the pre-commit `detect_changes` rule was not triggered.

## Owned files and SHA-256

The hashes identify the complete current files, including accepted repair content that was already uncommitted where applicable. They are not a claim that every line of a dirty tracked file belongs to D03.

| File | SHA-256 |
| --- | --- |
| `.unlazy/d03/GATES.md` | `e8760d222df437bf4c5b7ddeed4d3ce46fdf7068f4031a6bd0969bfd21247dcb` |
| `pipeline/src/signals/rate_observation.py` | `7957d0f09715ddf8e7d49aee3da73d26efc4fc4fccd0cee88daa8abc9eac546b` |
| `pipeline/src/fetchers/yields.py` | `006aa032fffdc4da947d0e7d2dc2c63d8cce5018bd6ac6e1d16c06f2fc304d11` |
| `pipeline/src/fetchers/async_engine.py` | `8c6b8e7b15b26d36fdf626c0238d0de6c4e284be13831dde8767952a3941f28a` |
| `pipeline/src/fetchers/buffer_keys.py` | `3d264c2670e9a3ca95c98aecd6b8fcf3ed6906f499faa47310c9dddb467fc1c6` |
| `pipeline/src/core/ingestion_snapshot.py` | `b717a7f84fc810aa62dd625d15ebf39c5b49a64c67fd0350f5374115a6a83d0e` |
| `pipeline/src/validation/ingestion_buffer.py` | `4a3dd15581e315f2c42a69670c6212df100727e7a4cde16ec2b0391e7ca60a7f` |
| `pipeline/src/scheduler/orchestrator.py` | `704260803ec12713fa19f77f5cf1b5f50aa94b8906d9f14b19f553ea7867dc07` |
| `pipeline/src/staged/contracts.py` | `ce8bf1bdd7945fcceff7d7baff7c264039765b9ff1506b1a4087f153e2810d54` |
| `pipeline/src/staged/adapters/fetcher.py` | `15385f08237318e22f2f7a7219cc6fab46c63b7383bd50ed528cc5fe617977ba` |
| `pipeline/src/staged/stages/ingestion_stage.py` | `d209e620e40543e729d26849540544376c95f28d3e541c955c8a7233558505f0` |
| `pipeline/src/staged/stages/regime_stage.py` | `473ef03632109bc33918ab103f61f96b676426d3abebca498f627c5c6b2cec93` |
| `pipeline/src/staged/stages/signal_stage.py` | `3157b95ff6caa3f554126932db938d08d1646ef3fd1fffba684183bc8ee97b39` |
| `pipeline/src/backfill/simulation_engine.py` | `c7e1015e56390360fe0ff9c61e8e29917270747c2f8d1ceb1aafe6085afc0c73` |
| `pipeline/tests/test_d03_rate_observation.py` | `8d2f4074a0e6889ea040b1fed482427847868a0fea7c8f90698be5043d506ad9` |
| `reports/repair-d03-provider-source-research.md` | `4b10368a82aa2b876c668f4a98a604a0601571b080d5dd9904c2d89142adf2a2` |

## Remaining limits for independent review

The current FRED observation response has an observation date and real-time period dates, but the default real-time period is today's query context; it does not prove the actual release instant or revision vintage of that selected observation. The code preserves the raw `realtime_start`/`realtime_end` separately and leaves `vintage` and `available_at` unknown. The synchronous `fredapi` scalar series and Yahoo close rows do not supply those facts either. Source definitions and exact links are in [the provider review](repair-d03-provider-source-research.md). Current configured foreign legs also remain economically unmatched under D01, so no live two-year spread is claimed.

`historical_yields` still holds only source ID, date and value. Replay cannot certify a past-known rate or reconstruct its revision from those rows. No migration was added: a durable, qualified observation/vintage design and source-by-source acquisition evidence are still required before a stored rate can become a historical point-in-time feature. Live/staged scalar outputs and old replay rows remain explicitly unqualified. D03 cannot be marked VERIFIED LOCAL or used to claim a forecasting improvement. The [D03 leaf gates](../.unlazy/d03/GATES.md) are left for independent review; the commands above were run directly, and no Unlazy checker approval or automatic evidence was manufactured.

If released unchanged, current live provider feeds would score the rates bucket as stale because they do not prove the required release and vintage facts; the DQS critical penalty can therefore lower confidence. This is an intentional fail-closed result and requires a separate release decision after source evidence and operational review.
