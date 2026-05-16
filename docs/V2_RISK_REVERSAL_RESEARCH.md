# V2.0 Risk Reversal Data Source Research

> **Research Date:** 2026-05-15  
> **Analyst:** Kimi Code CLI (Financial Data Research)  
> **Scope:** EUR/USD, USD/JPY, USD/INR — 25-delta OTC risk reversal (skew) data  
> **Status:** PROXY currently used; this document evaluates real-data alternatives for v2.0 credibility

---

## Executive Summary

**Best option for institutional credibility: Bloomberg API (B-PIPE) or LSEG Refinitiv Data Platform (RDP) APIs.** Both provide native 25-delta risk reversal quotes for OTC FX options as standard market conventions. Bloomberg is the industry gold standard with explicit RR tickers; LSEG offers comparable coverage via Instrument Pricing Analytics (IPA) and Data Platform APIs.

**Best affordable alternative: Exchange Data International (EDI) or FinPricing FX Volatility Surface APIs.** These specialized vendors provide daily FX implied volatility surfaces (ATM + 25Δ Risk Reversal + 25Δ Butterfly) for 30+ currency pairs starting at ~$5,000/year.

**Best hybrid / fallback approach: CME Group CVOL Indexes + proxy construction.** CME publishes daily CVOL implied volatility indexes for EUR/USD and JPY/USD (not INR) with a Skew metric (Up Variance minus Down Variance). While not a direct 25Δ RR, the Skew index correlates closely with risk reversal. This can be combined with the well-known academic formulas to approximate 25Δ RR from ATM vol + butterfly if listed option strike-level IVs are available.

**Verdict for FX Regime Lab v2.0:**
1. **Short-term (credibility MVP):** Subscribe to CME CVOL Skew data (~$200–500/mo via CME DataMine) for EUR/USD and USD/JPY; keep proxy for USD/INR.
2. **Medium-term:** Integrate EDI or FinPricing API (~$5k–15k/year) for true 25Δ RR across all three pairs.
3. **Long-term:** Migrate to Bloomberg B-PIPE or LSEG RDP if institutional funding allows ($30k–$100k+/year).

---

## Option 1: Bloomberg API

### Availability: ✅ YES

Bloomberg natively provides 25-delta risk reversal and butterfly data for OTC FX options via the Bloomberg API (B-PIPE / Server API) and Excel functions (BDP/BDH).

**Ticker Convention (from Bloomberg Core User Guide):**
- `GBPUSD25B6M BVAL Curncy` — GBP FX option **Butterfly 25D 6M** volatility
- `GBPUSD10B6M BVAL Curncy` — GBP FX option **Risk Reversal 25D 6M** volatility *(note: Bloomberg uses "10B" mnemonic for RR; "25B" for BF in this example)*
- General pattern: `{CCY1}{CCY2}{CODE}{TENOR} BVAL Curncy`

For our target pairs, analogous tickers would be:
- `EURUSD10B1M BVAL Curncy` — EUR/USD 25D RR 1M
- `USDJPY10B1M BVAL Curncy` — USD/JPY 25D RR 1M
- `USDINR10B1M BVAL Curncy` — USD/INR 25D RR 1M *(availability depends on BVAL coverage for INR)*

**API Access:**
- **BDP** (Bloomberg Data Point) for snapshot quotes
- **BDH** (Bloomberg Data History) for time-series history
- **FLDS <GO>** on terminal to discover exact field codes

### Cost
- **Bloomberg Terminal:** ~$24,000 – $31,980/year per seat (2026 pricing)
- **B-PIPE (real-time API feed):** ~$2,000 – $3,000/month add-on
- **Enterprise / Data License:** $10,000 – $100,000+/year depending on redistribution rights
- **Academic pricing:** ~$200 – $500/student/year (heavily subsidized)

### Coverage
- **Pairs:** All G10 majors + most EM pairs (INR coverage may be limited to onshore NDF tenors)
- **Tenors:** OTC standard tenors (1W, 2W, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y, etc.)
- **History:** Extensive historical data available via BDH

### API Format
- Bloomberg Server API (blpapi) — C++, Java, Python, .NET bindings
- Excel Add-in (BDP, BDH, BDS)
- REST-like request/response over proprietary protocol

### Pros / Cons
| Pros | Cons |
|------|------|
| Industry standard — universally accepted | Very expensive for small teams |
| Explicit RR and BF tickers as market convention | Requires terminal or B-PIPE license |
| Deep historical data | INR OTC options may have gaps vs G10 |
| Excellent documentation (FLDS, HELP) | 2-year minimum contracts typical |
| Real-time updates | Not suitable for lightweight web apps |

### Code Example (Python blpapi)
```python
import blpapi

session = blpapi.Session()
session.start()
session.openService("//blp/refdata")
service = session.getService("//blp/refdata")
request = service.createRequest("ReferenceDataRequest")
request.append("securities", "EURUSD10B1M BVAL Curncy")
request.append("fields", "PX_LAST")
session.sendRequest(request)
# Parse response for 25D Risk Reversal value
```

---

## Option 2: Refinitiv / LSEG (London Stock Exchange Group)

### Availability: ✅ YES

LSEG (formerly Refinitiv) provides comprehensive FX options data via multiple API channels:

1. **Refinitiv Data Platform (RDP) APIs** — RESTful web services
2. **Instrument Pricing Analytics (IPA)** — quantitative analytics including FX Options and Volatility Surface
3. **Eikon / Workspace** — desktop with Excel add-in (`=TR()` function)

**Relevant API endpoints:**
- `/data/quantitative-analytics/v1/` — FX option pricing, Greeks, vol surfaces
- `/data/historical-pricing/v1/` — time-series for vol data
- IPA supports: *Fx Spot, Fx Forwards, FX Swaps, Non Deliverable FX Forwards, FX Options, Volatility Surface*

### Cost
- **LSEG Workspace:** ~$1,500 – $3,000/user/month + data entitlements
- **Datastream (historical):** ~$1,000 – $2,500/user/month
- **Real-time data feeds (API):** ~$1,000 – $10,000+/month depending on asset classes
- **Mid-market deployment (10–25 users):** ~$150,000 – $400,000/year
- **Enterprise (50+ users):** $1M+/year

### Coverage
- **Pairs:** 500+ currency pairs including EUR/USD, USD/JPY, USD/INR
- **Tenors:** Full OTC tenor structure
- **History:** Decades of history via Datastream

### API Format
- RESTful HTTP (JSON) via RDP
- Python/TypeScript SDKs (`refinitiv.data`, `lseg.data`)
- WebSocket streaming available

### Pros / Cons
| Pros | Cons |
|------|------|
| Broad EM coverage including INR | Complex pricing (platform + entitlements + feeds) |
| Modern REST APIs with good SDKs | Still expensive for lean teams |
| IPA provides calculated vol surfaces | Requires negotiation for exact pricing |
| Competitive leverage vs Bloomberg | Implementation fees ($5k–$25k+) |
| Workspace desktop for validation | |

### Code Example (Python RDP)
```python
import refinitiv.data as rd
rd.open_session()
# Symbology uses RICs (Reuters Instrument Codes)
# Example fields for FX vol: "IMPLVOL", "DELTA", etc.
df = rd.get_data(
    universe=["EURUSD1MO="],  # Example RIC for 1M EUR/USD
    fields=["IMPLVOL", "DELTA"]
)
```

---

## Option 3: CME Group

### Availability: ⚠️ PARTIAL

CME Group provides **listed FX options on futures**, not pure OTC FX options. However, they publish:

1. **CVOL™ Implied Volatility Indexes** — daily benchmark indexes
2. **Options Analytics API** — Greeks and IV for listed options (5-min snapshots)

**CVOL FX Indexes (relevant to our pairs):**
- **EUR/USD CVOL Index**
- **JPY/USD CVOL Index** *(note: CME quotes JPY/USD, not USD/JPY)*
- **G5 FX CVOL Index** (aggregate)

Each CVOL index includes:
- `Up Variance` — call-only implied variance
- `Down Variance` — put-only implied variance
- `Skew` = Up Variance − Down Variance *(this is the closest proxy to risk reversal)*

**Important limitation:** CME does **not** publish a USD/INR CVOL index. They do list cleared OTC FX options for some pairs, but strike-level 25Δ RR is not natively published as a standalone metric.

**Options Analytics API:**
- Provides strike-level Greeks and IV for listed options
- 5-minute snapshots
- 20 requests/second rate limit
- Data available for current trading week only (historical via DataMine)

### Cost
- **CME DataMine:** ~$200 – $500/month for historical data
- **Real-time API access:** Requires entitlement; typically $500 – $2,000/month
- **CVOL data:** Often bundled with CME market data subscriptions

### Coverage
- **Pairs:** EUR/USD, JPY/USD (and GBP/USD, AUD/USD, CAD/USD)
- **Missing:** USD/INR
- **Tenors:** Listed option expiries (monthly, quarterly)
- **History:** CVOL back to ~2020; Options Analytics back to 2020

### API Format
- REST JSON (`https://markets.api.cmegroup.com/greeks/v1`)
- OAuth
