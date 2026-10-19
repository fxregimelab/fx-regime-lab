# PD mandate — payoff first, not a trade quota

## Owner direction and authority

The owner requests a pair-specific, macro-aware desk prioritising asymmetric
payoffs and net returns, not maximum trade frequency or accuracy. On 2026-10-19
the owner delegated management design and requested at least three times reward
relative to risk. This pack interprets that as **planned blended net payoff >=3R
at the full favourable exit**, after partial exits and modelled costs. It is
not a guarantee, an observed average winner, or an expected return of 3R.

The 10–15/week objective in
`docs/specs/autonomous-desk/AMENDMENT_2026-10-19_HF_MANDATE.md` is superseded as
the private research optimisation objective. Its historical results and test
criteria remain intact. The >=8/week dense eligibility test is NOT silently
removed from the protected evaluator: a lower-frequency strategy needs a
separate owner-approved graduation contract before eligibility. This package
cannot certify one. Do not edit old reports to make them satisfy this mandate.

Public EURUSD 90-day directional accuracy and instrument-expansion rules are
not replaced by private trading expectancy. Execution remains EURUSD/USDJPY;
USDINR stays research-only. Gold, GBP pairs and other majors are not execution
additions. Gold may be proposed as a licensed contextual input, not enabled here.

## Money and risk definitions

Use TWO explicitly named units. G is the initial cash price-to-original-stop
loss on the original quantity. A is the frozen initial cost/gap reserve. The
protected parent denominator is D=G+A (`immutable_initial_risk_usd`), per AD
execution spec sections 2/3/9. It is not G alone. Quantities and valuations use
actual instrument tick/contract rules. Let k=A/G and c=actual scenario costs/G.

For fraction f closed at aR and remaining fraction (1-f) at bR:

`gross_price_R = f*a + (1-f)*b`

`net_price_R = gross_price_R - c`

`net_parent_R = net_price_R / (1+k)`

Here a and b are price-R multiples, not all-in parent-R. Total cost includes all
applicable entry/exit spread/slippage, commission and
financing. Charge only the relevant filled quantity on each leg; do not double
charge entry costs because there are two exit legs. Freeze initial R even after
moving the stop or releasing risk capacity. No martingale, averaging down or
stop widening follows from the payoff target.

At f=0.5, a=1, the following are in PRICE-R:
- runner at original stop -1: gross 0R; net negative after costs;
- runner at entry 0: gross +0.5R, not zero;
- runner at +3: gross +2R;
- runner at +5: gross +3R, net less than 3R;
- net +3 price-R needs runner >= `5 + 2*c`;
- net +3 all-in parent-R needs runner >= `5 + 6*k + 2*c`;
- when k=c, the latter becomes `5 + 8*c`, not `5 + 2*c`.

If costs depend on exit price/time, calculate the net payoff with that scenario's
costs. Do not solve the equation using an unrelated average spread. A no-partial
plan needs price target >= `3*(1+k) + c` for 3 all-in parent-R. Reject unsupported target distances;
never manufacture a distant target or shrink an invalidation stop to pass RR.

The requirement applies to the planned full favourable outcome. Scratches,
protective exits and losses remain valid observed outcomes and stay in the
denominator. Report realised average winner/loser, all-parent net expectancy,
tail losses, drawdown and capital growth separately. No minimum 40–50% accuracy
is assumed. P(hit 1R), P(full target), P(net win) and directional accuracy are
different events and must not share a confidence label.

## Unchanged safety

Existing 5/4/3/3 slot ceilings, 15% open risk, -10% daily and -25% weekly limits,
pair/global caps, same-USD constraints, holding ceiling and graduation gates
remain as defined by the protected authority/config. 5% is a ceiling for the
first slot, not a default risk demand. Risk may be reduced only. Compounding,
overlapping positions and gap losses make nominal risk different from guaranteed
maximum loss. Return aspirations of 300–500% create no permission or forecast.

The current 50%-at-1R -> entry stop -> trail policy remains the runtime policy
until an independently reviewed replacement is explicitly admitted. Alternative
management policies below are research challengers, not a unilateral production
policy edit. Real money, evaluator changes, pair expansion, credentials and
public publication retain their existing owner gates.
