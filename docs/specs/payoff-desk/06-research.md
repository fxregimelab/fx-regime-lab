# PD research evidence ledger

Research date: 2026-10-19. Sources were read by an independent research agent;
read scope and limitations below distinguish evidence from design decisions.
No source proves this desk profitable or provisions licensed historical data.

## Sources and limits

1. Andersen/Bollerslev/Diebold/Vega, 2003 (working paper 2002),
   [Micro Effects of Macro Announcements](https://econ.duke.edu/~boller/Published_Papers/aer_03.pdf).
   Read introduction/data/surprise construction. FX response depends on surprise
   relative to surveyed expectations and timing. Historical association, not a
   latency/cost-adjusted post-news strategy. Training-only surprise scaling is
   required in predictive replay, unlike full-sample descriptive normalization.
2. Bank of Japan, 2000, revised 2018/2023,
   [intervention operations](https://www.boj.or.jp/en/intl_finance/outline/expkainyu.htm).
   Complete operational explanation read. MOF decides and BoJ acts as agent;
   both yen-buying/selling are described. No fixed trigger probability is given.
3. Evans/Lyons, working paper 1999, journal 2002,
   [Order Flow and Exchange Rate Dynamics](https://www.nber.org/system/files/working_papers/w7317/w7317.pdf).
   Introduction, flow definition and forecasting section read. Contemporaneous
   signed interdealer flow has explanatory association. The forecasting exercise
   uses realised future flow/rate changes: not a feasible forecast from known
   inputs. Small historical sample and different instruments limit transfer.
4. OANDA, maintained product page (2024 publication metadata),
   [order/position book scope](https://www.oanda.com/bvi-en/skills-and-insights/oanda-labs/order-book-position-book-tool/).
   Population/definitions/update frequency read. Provider-client pending orders
   and positions are not consolidated executed institutional flow. Marketing
   statements are not predictive validation or a purchase recommendation.
5. Kaminski/Lo, 2014 issue, online 2013,
   [When Do Stop-Loss Rules Stop Losses?](https://doi.org/10.1016/j.finmar.2013.07.001).
   Published PDF via author's site: introduction/assumptions/binary overlay read.
   Value depends on return process; risk reduction differs from expectancy
   improvement. Stock/bond allocation examples do not validate FX partial exits.
   MIT repository retrieval failed; successful author-linked PDF was used.
6. Bailey/Borwein/Lopez de Prado/Zhu, manuscript 2015, journal issue 2017,
   [Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).
   Abstract/introduction/multiple-testing/method framing read. Selection across
   trials alters evidential standards. PBO/CSCV diagnose aspects of selection,
   not leaks, execution errors or guaranteed profitability.
7. St Louis Fed, undated maintained API docs,
   [real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).
   Full page read. Default historical values generally reflect today's known
   data; vintages matter. Date-level vintage parameters alone cannot establish
   exact intraday availability or consensus history.
8. Kim et al., 2025, v3 April 2026,
   [Towards a Science of Scaling Agent Systems](https://arxiv.org/html/2512.08296v3).
   Abstract/architecture/results/limitations read. Gains depend on task and
   coordination; overhead/fragmentation can hurt. Preprint benchmarks are not
   live FX returns, and small subsets/cluster inference limit generalisation.
9. Anthropic, 2024, maintained engineering guidance,
   [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents).
   Workflow/framework/guardrail sections read. Prefer simple composable bounded
   flows until complexity adds measured value. Practitioner guidance, not a
   controlled trading experiment or instruction to adopt its provider.
10. OpenCode V2 maintained docs,
    [agents](https://opencode.ai/v2/docs/agents),
    [skills](https://opencode.ai/v2/docs/skills),
    [MCP](https://opencode.ai/v2/docs/mcp-servers).
    Agent/skill pages read by coordinator, config/MCP by configuration reviewer.
    Project `.opencode/agents` and `.opencode/skills` are supported. Model
    inheritance/permission rules must be inspected; file existence does not prove
    a running service refreshed discovery or OS-level isolation.

## Decisions derived from evidence, not claimed paper results

- Test expectation-aware macro facts against matched price-only decisions.
- Treat institutional flow unavailable unless actual licensed coverage is proved.
- Separate entry edge, management effect and portfolio feasibility.
- Keep a trial ledger and fresh forward endpoint; stop searching old holdouts.
- Reuse existing Python/Prefect/AI boundaries, not a framework installation.
- Restrict agents by responsibility and verified outputs rather than voting.
- Evaluate target feasibility and realised distributions, not just intended RR.

## Unknowns that remain explicit

No validated modern pair-specific surprise coefficients; no entitled historical
consensus archive or live news feed; no measured all-in execution/slippage/swap
dataset; no local model-quality benchmark; no proof partials or macro/agent layers
improve net expectancy. The next studies test these propositions, not assume them.
