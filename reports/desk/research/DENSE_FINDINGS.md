# Dense-trading research findings (2026-10-19)

**Historical simulation — not live results.** Every number below comes from
completed bars, with entry at the next bar's open, stop-before-target on
ambiguous bars, gaps filled at the open, and canonical costs subtracted.

## The question

The owner asked for **10–15 settled trades per week** so that selection can be
optimised on a statistically usable sample. The structural-setup path produced
**39 trades in four years (~0.19/week)**, which cannot support optimisation.

Two things had to be separated:

1. **Can the desk generate the frequency?** (mechanical)
2. **Is there an edge at that frequency?** (economic)

The answer to (1) is yes. The answer to (2), on all data and features currently
available, is **no demonstrated edge**.

## What was measured

| Instrument | File | What it answers |
|---|---|---|
| Dense walk-forward harness | `src/paper/backtest/dense.py` | OOS expectancy of a feature-scored selector |
| Geometry sweep | `reports/desk/research/sweep*.json` | Does stop/target/hold change the sign? |
| Interpretable rules | `src/paper/backtest/rules.py`, `rules*.json` | Can a one-line rule beat the model? |
| Univariate edge scan | `scripts/edge_scan.py`, `edge_scan*.json` | Is any feature predictive at all? |
| Protocol scan | `dense_protocol_scan.py`, `protocol_scan.json` | Do retrain window / selectivity help? |
| Structural sensitivity | `sensitivity.json` | Can relaxing setup gates reach the target frequency? |

Protocol: expanding-window walk-forward, no shuffling, fixed hyper-parameters,
training strictly before each test window. Model: ridge on 30 causal features,
one symmetric model over long and short directional views.

## Result 1 — frequency is achievable

The interpretable rules trade at the requested rate:

| Rule | Pair | Trades | Per week | Expectancy |
|---|---|---:|---:|---:|
| London breakout | EURUSD | 1731 | 8.34 | −0.097R |
| London breakout | USDJPY | 1289 | 6.22 | −0.079R |
| Mean reversion | EURUSD | 1534 | 7.39 | −0.079R |
| Mean reversion | USDJPY | 1413 | 6.82 | −0.086R |
| Momentum pullback | EURUSD | 3224 | 15.53 | −0.096R |
| Momentum pullback | USDJPY | 2890 | 13.94 | −0.126R |

M15, 2022-10-27 → 2026-10-19. Frequency is not the binding constraint.

## Result 2 — the edge is approximately the size of costs

Best cells only, across every sweep:

| Family | Best net R/week | Trades/week | Verdict |
|---|---:|---:|---|
| Dense model, M15 | +0.062 | 5.2 | neighbours negative → noise |
| Dense model, H1 | +0.035 | 2.8 | noise |
| Interpretable rules, H1 | −0.018 | 3.4 | negative |
| Protocol scan (train window × selectivity) | +0.060 | 1.6 | sign flips across cells |

A positive cell is not an edge when the adjacent cells are negative and the
magnitude is smaller than one trade's cost.

## Result 3 — the apparent signal is not stable

Univariate scan, H1, stop 2.5×ATR, target 1.5R, hold 48 bars. Top-decile mean
net R by calendar year:

| Feature | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| USDJPY `upper_wick` | +0.167 | +0.036 | +0.051 | −0.037 | +0.044 |
| USDJPY `dist_pdl` | +0.183 | +0.109 | −0.041 | −0.150 | −0.177 |
| USDJPY `vwap_dist` | +0.120 | +0.010 | −0.020 | −0.060 | −0.030 |
| EURUSD `dist_pdl` | −0.232 | −0.068 | −0.113 | +0.065 | −0.333 |

The 2022 column is the high-volatility, strongly trending USD regime. The signal
decays and flips as the regime changes. A model trained on 2022–2023 is
therefore wrong for 2025–2026, which is exactly what the walk-forward produced.

## Result 4 — relaxing the structural gates cannot reach 10–15/week

From `sensitivity.json` (M15, diagnostic relaxations, production rules untouched):

| Scenario | Trades | Per week | Expectancy |
|---|---:|---:|---:|
| Baseline | 39 | 0.188 | +0.001R |
| H4 neutral allowed | 79 | 0.381 | −0.055R |
| Stop floor 0.8×ATR | 40 | 0.193 | +0.035R |
| Cost share cap 20% | 44 | 0.212 | −0.014R |
| Session window removed | 149 | 0.718 | +0.007R |

Even the most permissive relaxation reaches **0.72 trades/week**, still two
orders of magnitude short of 10–15. The setup conjunctions simply do not occur
that often; the gates are not what is suppressing frequency.

## Result 5 — canonical costs are conservative but not decisive

Median broker spread in the dump: EURUSD 0.8 pips, USDJPY 1.0 pip. The canonical
table implies 1.65 and 2.55 pips respectively, so it overstates cost by 18%
(EURUSD) and 31% (USDJPY). Using the observed spread would raise the best dense
cells by roughly 0.01–0.03R per trade. It does not change the sign of the
unstable years, and it is not a substitute for an edge. Changing the cost model
would be an owner-level spec amendment, not an agent decision.

## Conclusion

- The desk **can** trade 10–15 times per week. The rules already do.
- With the data and features currently available, that frequency has **no
  demonstrated positive expectancy**. The best observed cells are indistinguishable
  from noise and decay across regimes.
- Promoting a dense configuration now would knowingly run a zero/negative
  expectancy strategy on demo. That is a legitimate *experiment*, but it is not
  a profitable trading system and must not be described as one.

## What would change the answer (pre-registered, not yet tested)

1. **Event-driven entries with an authoritative calendar** (actual vs consensus,
   surprise-scaled). This is the most plausible source of intraday edge and the
   only one with a clear economic mechanism. Blocked: feed entitlement is
   unverified; scraped substitutes are not allowed by the spec.
2. **Cross-asset / positioning context** (yields, DXY, COT) as a *regime gate*
   on mean reversion, tested walk-forward with per-year stability.
3. **Limit/maker execution** to capture the spread instead of paying it. Owner
   decision; needs broker pending-order support and a new execution contract.
4. **Higher-quality intraday features** (session VWAP bands, liquidity sweeps
   with volume confirmation) tested one hypothesis at a time with a stability
   table, not added in bulk.

Each requires its own data entitlement or owner decision. None is a reason to
relax the acceptance criteria in
`docs/specs/autonomous-desk/AMENDMENT_2026-10-19_HF_MANDATE.md`.

## Reproduction

```powershell
cd pipeline
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\backtest_dense.py
.\.venv\Scripts\python.exe scripts\backtest_dense_sweep.py --timeframe h1 --start 2022-01-01
.\.venv\Scripts\python.exe scripts\edge_scan.py --timeframe h1 --start 2022-01-01
.\.venv\Scripts\python.exe scripts\backtest_rules.py --timeframe h1 --start 2022-01-01
.\.venv\Scripts\python.exe scripts\dense_protocol_scan.py
```
