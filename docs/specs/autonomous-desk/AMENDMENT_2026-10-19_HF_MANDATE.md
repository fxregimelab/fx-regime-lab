# Amendment 2026-10-19 — Dense-trading mandate (owner directive)

Status: **owner-directed requirement change, effective immediately for research.**
Authority: owner instruction, 2026-10-19. Recorded by the executing agent; not a
self-granted weakening of any gate.

## Directive

The demo desk must be able to produce **10–15 settled trades per week** so that
selection can be optimised on a statistically usable sample. The measured
structural-setup path produced **39 trades in four years (~0.19/week)**, which
cannot distinguish an edge from noise and cannot support optimisation.

## What changes

1. **Primary research path**: a dense, walk-forward, feature-scored trade
   selector (`pipeline/src/paper/backtest/dense.py`) replaces the rare-setup
   path as the candidate generator *for research purposes*.
2. **Sample density is a product requirement**, not an excuse to lower the
   quality bar. A dense system that loses money after costs is a failed system,
   not a success because it traded often.
3. **Optimisation is allowed on the dense sample**, but only inside a
   walk-forward protocol: every reported number must come from bars that the
   model never trained on.

## What does not change

- Demo/paper only. No real-money authority is created by this amendment.
- Hard risk limits, daily/weekly stops, slot ceilings, and the evaluator remain
  in force and remain owner-gated. The agent may not rewrite them.
- Canonical cost table (`src/paper/config.py`) is used unchanged. Costs are
  subtracted from every label and every reported trade.
- No lookahead: features use completed bars only; entry is the next M15 open;
  a bar spanning stop and target books the stop; gaps through a stop fill at
  the open.
- The research pipeline keeps its 3-pair lock; the desk still executes only
  EURUSD and USDJPY.
- Forward shadow and canary calendar-time gates are untouched and cannot be
  accelerated by this amendment.
- The immutable ledger rule is untouched.

## Supersession, not deletion

SU1/SU2/SU3 remain implemented, tested, and documented. They are no longer the
primary trade generator while the dense path is evaluated. The SU2 stop-floor
contradiction (spec-exact stop ≈0.55×ATR against a ≥1.2×ATR floor) remains an
open owner decision; it is **not** silently fixed by this amendment.

## Acceptance criteria for the dense path

A dense configuration may be proposed as the production candidate only when all
of the following hold on out-of-sample walk-forward data:

| Criterion | Threshold |
|---|---|
| Sustained trade rate | ≥ 8 settled trades/week over ≥ 12 months OOS |
| Net expectancy after canonical costs | > 0 |
| Edge over unconditional entry | ≥ +0.05R per trade |
| Profit factor | ≥ 1.15 |
| Fold concentration | no single fold > 40% of total net R |
| Drawdown | inside the existing daily −10% / weekly −25% stops |
| Parameter stability | sign of net R stable across the final three folds |

If no configuration meets these criteria, the correct outcome is to report that
no dense edge was found, not to relax the criteria.

## Known measurement risk

M15 stop distances are small relative to the canonical round-trip cost. At
1.5×ATR_M15 the measured cost drag reached ~0.27R per USDJPY trade. Geometry
must therefore be wide enough that cost ≤ ~0.10R per trade, or the system is
mathematically unprofitable before any signal is considered. The geometry sweep
is the instrument that measures this trade-off.
