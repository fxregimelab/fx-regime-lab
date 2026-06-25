## Parent

#13

## What to build

Add a feature flag, shadow-run harness, and migration procedure so the new pipeline can be proven equivalent to the old one before going live.

Work:
- Introduce a `USE_V2_PIPELINE` feature flag (default false).
- Build a shadow-run mode where v2 runs alongside v1 without writing to the live ledger.
- Add output comparison between v1 and v2 (RegimeCall fields, brief artifacts).
- Run shadow mode for 20 trading days to cover T+5/T+20 validation horizons.
- Document and execute the flip procedure: EUR/USD first, then USD/JPY, then USD/INR.
- Ensure the daily Substack brief continues to publish throughout migration.

## Acceptance criteria

- [ ] Feature flag controls whether v2 is active.
- [ ] Shadow-run mode compares v1 and v2 outputs without affecting live ledger.
- [ ] 20-trading-day equivalence window is tracked and documented.
- [ ] Flip procedure is documented and executed pair by pair.
- [ ] Daily brief is not interrupted during migration.
- [ ] Old orchestrator path is deprecated only after 10+ successful live v2 runs.

## Blocked by

- #17

## User stories covered

7, 9
