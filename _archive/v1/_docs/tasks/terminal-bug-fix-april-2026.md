# Terminal bug fix pass — April 2026

1. Home regime cards: added 	erm-card--eur / --jpy / --inr on site/terminal/index.html so data-client.js and live-prices.js selectors match the DOM.
2. Stale data hint: replaced #term-data-stale { display: none } with [hidden]-aware layout in 	erminal.css; setStale() in data-client.js unchanged but now effective.
3. Macro ticker: three .term-ticker-item cells each with data-term-ticker + nsureTickerStructure / observer updates in live-prices.js (no single-cell strip bug).
4. Cross-asset row: extended etchLatestPrices select with 
ate_diff_10y; wired US–DE 10Y from EURUSD row; US 10Y and Gold remain — where not on signals.
5. Intel bar: added section.term-intel-bar + empty #term-intel-list on terminal home so home-terminal.js can render signal_changes.
6. Terminal CSS: added .price-flash* animation and .term-intel-bar* strip styles at end of 	erminal.css.
7. Driver line: isDriverSlotOpenForAi() in home-terminal.js so pplyAiArticle does not overwrite Supabase-driven Driver: … from data-client.js.
8. Removed hardcoded Supabase preconnect from index.html; comment notes runtime URL via Worker / supabase-env.js.
9. Removed dead etchFrankfurterPair from live-prices.js (Yahoo/Worker path only).
10. Removed unused FX_FALLBACK and ymd() from live-prices.js after Frankfurter removal.


---

## Optimization pass complete — April 13 2026

- Parser blocking fix
- Lazy panel
- Accuracy delay
- Supabase timeout
- cleanBriefText overhaul

* Yahoo Finance CORS Worker proxy — /proxy/yahoo/ route added to workers/site-entry.js, PRICE_API_FALLBACK updated in live-prices.js
