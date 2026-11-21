# Private bid/ask history: first-party source review

Reviewed 1 October 2026. Read-only research; no data purchase, bulk history download, installation, code change or strategy qualification. Provider documentation was read through agent-reach's GitHub CLI, Exa search and Jina reader routes. Live FXCM archive results below came from the coordinator's bounded probes, not this research worker.

FXCM is the smallest justified first ingestion source: the coordinator witnessed all seven private pairs for one week with the same nine-column bid/ask schema, and FXCM's documentation states UTC and personal use. Archive completeness, candle timestamp meaning and actual executable fills remain unproved. Dukascopy's current browser source establishes a separate, single-side CSV export shape; no exported price file was downloaded here. Its S3 route is Requester Pays and has legacy-format warnings.

## FXCM: documented contract and witnessed files

The official repository was read at commit `924393dd545fab187527d95ef8b1178284b274b6` (9 July 2026). Its candle endpoint is `https://candledata.fxcorporate.com/{m1|H1}/{instrument}/{year}/{week}.csv.gz`; D1 uses `.../D1/{instrument}/{year}.csv.gz`. The supplied pandas script uses `date.isocalendar()` for request year and week. This does not prove that every row belongs to that ISO week: the 2017 and 2025 probes include the preceding Sunday evening. Year-boundary membership still needs a bounded probe. [Official script](https://github.com/fxcm/MarketData/blob/924393dd545fab187527d95ef8b1178284b274b6/CandleData/CandleData%28pandas%29.py).

The candle README says history begins on 1 January 2012, weekly m1/H1 files are updated on Mondays, and D1 is updated yearly. It states UTC timestamps and indicative prices based on the lowest spreads reserved for Active Trader accounts. The root README's year list is 2017–2020; the candle README lists 2012–2018. These are inconsistent documentation lists, not verified live bounds. Both candle instrument lists omit AUDUSD; the coordinator's later probe establishes one AUDUSD file despite that omission. [Candle README](https://github.com/fxcm/MarketData/blob/924393dd545fab187527d95ef8b1178284b274b6/CandleData/README.md), [root README](https://github.com/fxcm/MarketData/blob/924393dd545fab187527d95ef8b1178284b274b6/README.md).

Coordinator probes at about 11:30 UTC on 1 October 2026 witnessed this exact header:

```csv
DateTime,BidOpen,BidHigh,BidLow,BidClose,AskOpen,AskHigh,AskLow,AskClose
```

There is no volume column in these files. `DateTime` is `MM/DD/YYYY HH:MM:SS.mmm` (the 2017 file contains `07/16/2017`, resolving date-order ambiguity). UTC comes from the provider documentation. No inspected archive document or script states whether this timestamp is the candle's opening time, closing time, or how exact boundary ticks are allocated. Open and close column names alone do not establish that contract.

| EURUSD minute URL suffix | Result | Rows | First / last raw timestamp | SHA-256 of received body |
|---|---:|---:|---|---|
| `2012/1.csv.gz` | 200 | 6,815 | `01/02/2012 03:06:00.000` / `01/06/2012 21:59:00.000` | `783378a59efcfecba7dddc2e8b3a4f2b2c6185f9f77b1142779792d4fd6005de` |
| `2017/29.csv.gz` | 200 | 7,184 | `07/16/2017 21:02` / `07/21/2017 20:57` | `44526c83e1760f323cc177fc7b83b28efbed31459f68e2b4375c3d6c4b59fa4a` |
| `2025/40.csv.gz` | 200 | 7,168 | `09/28/2025 21:05` / `10/03/2025 20:58` | `3bcd78e5ab293e32c3a54d61a2aadc9a72e5b520438d6bac232f217e2f321db8` |
| `2026/39.csv.gz` | 404 | — | 196-byte error body | `80c3fe2ae1062abf56456f52518bd670f9ec3917b7f85e152b347ac6b6faf880` |

Follow-up coordinator probes at 11:33:42–11:33:48 UTC received HTTP 200 for every private pair's `m1/{PAIR}/2025/40.csv.gz`: EURUSD 7,168 rows; GBPUSD 7,121; AUDUSD 7,148; NZDUSD 7,111; USDCAD 7,134; USDCHF 7,068; EURGBP 7,183. Every header matched. Their receipt times, first/last timestamps, response sizes and hashes are preserved in `.private-fx/bidask-probes/{PAIR}-2025-40.json`; this worker verified that all seven metadata files exist.

The coordinator preserved bodies and metadata under `.private-fx/bidask-probes/`. These observations establish selected file availability through a 2025 example and one failed 2026 request. They establish neither continuous 2012–2025 coverage nor a general 2026 cutoff. No complete gap inventory, correction log, immutable publication guarantee or historical availability timestamps were found in the inspected FXCM documents.

FXCM expressly permits personal use subject to its EULA. The linked current EULA page redirects users to an Adobe Sign form and does not expose the full agreement in the readable page. Private research is consistent with the README's stated purpose; public redistribution, resale or publication rights have not been established. [EULA page](https://www.fxcm.com/uk/forms/eula/).

## Dukascopy: separate export and tick contracts

The official historical-export page offers free CSV downloads from tick to monthly periods and links its own widget at `https://widgets.dukascopy.com/en/historical-data-export`. It also documents JForex's Historical Data Manager. [Historical export](https://www.dukascopy.com/swiss/english/marketwatch/historical/), [official widget](https://widgets.dukascopy.com/en/historical-data-export).

Source inspection of the currently served `HdfComponent` establishes `selectedTimezone,Open,High,Low,Close,Volume`. With the default UTC selection, the header is `UTC,Open,High,Low,Close,Volume`. `exportAndDownload` requests BID or ASK separately, defaulting to BID; it does not produce combined bid/ask columns. `formatTimestampInTimezone` emits `YYYY-MM-DDTHH:MM:SS±HH:MM`, with no millisecond field. Its CSV filename includes side and timezone. No downloaded CSV or tick-level timestamp-precision check was witnessed; the CSV volume unit and exact bar boundary semantics remain unverified for this widget. [Official widget export source served on 1 October 2026](https://widgets.dukascopy.com/en/chunk-DvIpafn_.js).

The newer official developer guide documents `s3://cfg-public-proper-wallaby/` in `eu-west-1`, using AWS credentials and `RequestPayer='requester'`. This is a separately billed route; it was not accessed. Current daily paths are `SYMBOL/YEAR/MONTH/DAY_ticks.bi5`, with January numbered `00`. Its documented LZMA binary record is big-endian `>IIIff`: UTC milliseconds since day start, integer ask price, integer bid price, float ask volume, float bid volume. Most FX prices are divided by 100,000. Volume is in millions of base-currency units. The guide's own decoder exports `timestamp,ask,bid,ask_volume,bid_volume`; this is an example decoder's output, not a witnessed UI CSV. [Historical Price Data guide](https://www.dukascopy.com/wiki/en/development/data-export/).

That guide warns that legacy files can use milliseconds since hour start, while its current decoders assume daily files. A missing daily object means no recorded ticks according to the guide; this does not independently prove that a missing weekday is a harmless holiday. No pair-specific first/last-date guarantee, full gap inventory or revision ledger was established. Preserve missing days and unknown availability rather than silently fill them. [Historical Price Data guide](https://www.dukascopy.com/wiki/en/development/data-export/).

JForex's API describes tick volume as quantity available at the best bid or ask; historical ticks expose one price level. Bar volume sums those best-price tick volumes. This is quote liquidity aggregated over ticks, not centralised FX traded turnover. Its historical data uses LIVE-environment data even in DEMO, while DEMO real-time ticks differ. Currently forming bars can be returned with `shift=0`. None of these statements proves an order would fill at the displayed price for this owner's broker, size or account. [ITick reference](https://www.dukascopy.com/client/javadoc3/com/dukascopy/api/ITick.html), [IBar reference](https://www.dukascopy.com/client/javadoc3/com/dukascopy/api/IBar.html), [history overview](https://www.dukascopy.com/wiki/en/development/strategy-api/historical-data/overview-historical-data/).

Dukascopy Bank SA's general website terms permit personal, non-commercial downloads with notices retained. They also restrict automated website acquisition without express written consent, redistribution and constructing databases from website information. The advertised export UI and programmatic S3 guide are more specific access instructions, but no inspected document resolves their exact relationship to those restrictions. Mark route-specific automated-ingestion and reuse permission **OPEN**; free export is not an established unrestricted licence. The XML-data licence is a separate product and cannot be applied to historical CSV or S3 data. [Bank SA website terms](https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/), [XML-only licence](https://www.dukascopy.com/plugins/cont.php?ref_id=1273).

## Smallest justified ingestion contract

1. Start with FXCM EURUSD `m1` and only explicitly requested ISO weeks. Preserve the compressed response, URL, status, receipt UTC, SHA-256, schema version, row count and first/last raw timestamp. Store failures too. Keep provider publication time unknown; receipt time does not prove historical publication availability.
2. Require the exact nine-column header; parse the witnessed date format and declared UTC; reject non-finite/non-positive prices, duplicates/conflicts, invalid side-specific OHLC ranges and crossed same-time open/close quotes. Do not fabricate volume.
3. Retain provider timestamp and record `timestamp_semantics=UNVERIFIED` until first-party evidence or an independent tick-to-candle comparison resolves it. Do not qualify next-bar execution or session timing from the archive yet.
4. Check actual file coverage and within-week gaps. Keep missing minutes and weekdays explicit; use no carry-forward bars or silently merged replacement sources. New hashes for a URL become new captures, preserving the former bytes.
5. Label bid/ask results as indicative FXCM-source research. Long entries can be studied on ask and exits on bid, with the reverse for shorts, once timing is resolved. OHLC still leaves within-minute order unknown; apply the desk's adverse-order rule. Broker-specific slippage, commissions, rollover, order acceptance and fills remain separate evidence.

Source access and a parsable schema are sufficient for a bounded ingestion review. They do not qualify a profitable policy, calibrated probability, session advantage or executable fill.
