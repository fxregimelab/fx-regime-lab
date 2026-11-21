# Private daily holding-risk study

Revision 1, 2 October 2026 IST. This is a separate development study under the private desk contract. It preserves the original correlation replay and every frozen forward suggestion or abstention. R1–R5 remain open.

The owner wants at most five concurrent trades, three to five new trades per week and at most two trades in one correlated directional group. The original entry rule leaves five later breach days in the examined history. This study tests a daily response; it does not establish continuous or intraday control, executable exits, a profitable strategy or a qualified hedge.

## Fixed rules before implementation

- Use all eight private pairs, exact-date daily returns, the existing 60-observation window, 40-match floor, seven-day freshness rule and signed-correlation threshold of 0.70. Connected groups may contain at most two positions. These settings are research choices, not established optimums.
- At each business-day open, use returns strictly before that day for both holding review and new admissions. The older replay used the earlier signal-date cutoff at admission and stays unchanged. Any comparison must disclose this timing change.
- Review positions that survived the preceding day's simulated path. Do not use a future exit date, future profit or current candle extremes to decide which position survives. Keep earlier entries first; within the same entry date, keep the original predicted probability first, null last, then fixed universe order. No ranking by eventual returns.
- Greedily retain a position only if its edges are available and adding it leaves every connected group within two. Request a modelled open exit for any other held position. An unavailable edge is a reason to reduce the simulated set, never evidence of independence. Record the pre-action and post-action groups and every removed position.
- Consider today's candidates after that review. Reserve all admitted slots and pair occupancy through their original planned horizon, including early natural or risk exits. Reject excess weekly entries, occupied pairs, unavailable correlations and oversized groups. Never create a trade to fill the weekly target.
- Execute a requested exit only in the daily-OHLC simulator. Preserve prior partial exits and opening-stop gaps. Evaluate the open before the candle's high, low or close. A previously hit +1R target leaves half the trade, and moving the stop to entry can still lose after a gap and costs.
- Preserve the existing generic spread, two-sided slippage and calendar-day financing assumptions. Predeclare additional risk-exit slippage scenarios of zero, one and three pips per remaining unit. Use the one-pip scenario as the displayed study, with all three sensitivity results. Do not choose a scenario or ranking from its returns.
- Returns are MODELLED_DAILY_OHLC_AFTER_ASSUMED_COSTS. They are neither account returns nor verified executable fills. Executable forced-exit and hedge returns remain unavailable. Daily decision-boundary limits do not certify the risk between reviews.
- Verify original trade paths against their hash-bound daily sources and original cost assumptions. Missing, malformed, conflicting or changed evidence rejects the entire study; do not publish a partial successful audit.
- Record admitted and rejected research candidates, daily reviews, requested exits, modelled outcomes, weekly frequency and shortfalls, source hashes, method version and limits. Preserve the original report and append a journal publication without turning repeated candidates into independent observations. Detach the prior AI binding when quantitative inputs change.

## Acceptance

The old drift control must remain red. The new study must demonstrate rejection or modelled reduction at the next daily boundary, strict lagging, conservative capacity, unknown-edge handling, partial-exit and JPY cost arithmetic, gap priority and fixed cost sensitivity. Original simulator calls and the saved original replay must reproduce unchanged.

Independent source and code review, focused and full pipeline checks, saved-source replay and the actual authenticated dashboard must support the bounded result. The forward journal must preserve prior events and show repeat counts honestly. Strategy calibration, historical source availability, account notionals, executable costs, intraday control, hedges and genuinely untouched or forward evaluation remain separate acceptance requirements.
