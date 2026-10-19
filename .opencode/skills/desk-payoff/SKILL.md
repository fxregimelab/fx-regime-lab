---
name: desk-payoff
description: Design or audit blended FX payoff, partial exits, all-in parent risk and matched management experiments.
---

1. Read `docs/specs/payoff-desk/01-mandate.md` and
   `docs/specs/payoff-desk/04-payoff-study.md` from repository root.
2. Identify G (price-stop cash), A (frozen initial reserve), scenario costs and
   quantities. Preserve all-in denominator D=G+A. Report price-R and parent-R.
3. Use hand oracles: half at1/runner3 is2 gross price-R; runner5 is3 gross, not
   net. Net3 parent-R needs runner5+6k+2c where k=A/G, c=cost/G.
4. Check feasible target/horizon, stop validity, executable sides, lot steps,
   ambiguous bars, adverse gaps and duplicate receipts. Missing definitions block.
5. Register fixed comparisons on matched opportunities; record all trials and
   evaluate actual portfolio feasibility separately. Previously inspected history
   is development data. A higher target or win rate is not economic improvement.
6. Return arithmetic, test cases, exact unit definitions and uncertainty. Keep
   protected evaluator/risk and runtime management unchanged; proposed studies
   are not authorised policy activation.
