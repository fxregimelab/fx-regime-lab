# NSDL FPI HTML parser repair

Date: 27 September 2026. Scope: leaf 21.3 only. This work added a pure parser,
authored public tests and an offline verifier for the private original captures.
It did not add network access, database writes, durable first-seen handling or
model activation.

## Accepted parser boundary

`parse_nsdl_fpi_html` accepts original response bytes, one of the two accepted
NSDL report URLs and a timezone-aware retrieval time. It requires one `div#rpt`
with exactly two unnested `table.tbls01` tables. It identifies the investment
table by its dated heading and all eight logical headers, and separately checks
that one derivative table is present. It never uses table position to select
investment rows.

The eight required headers are exactly:

1. `Reporting Date`
2. `Debt/Debt-VRR/Equity/Hybrid`
3. `Investment Route`
4. `Gross Purchases(Rs. Crore)`
5. `Gross Sales (Rs. Crore)`
6. `Net Investment (Rs. Crore)`
7. `Net Investment US($) million`
8. `Conversion (1 USD TO INR)*`

Every date must expand to 25 logical rows: 17 details, seven subtotals and one
grand total. The exact category order and route labels are:

| Category | Detail routes |
|---|---|
| Equity | Stock Exchange; Primary market & others |
| Debt-General Limit | Stock Exchange; Primary market & others |
| Debt-VRR | Stock Exchange; Primary market & others |
| Debt-FAR | Stock Exchange; Primary market & others |
| Hybrid | Stock Exchange; Primary market & others |
| Mutual Funds | Equity schemes; Debt schemes; Hybrid schemes; Solution oriented schemes; Other schemes |
| AIFs | Stock Exchange; Primary market & others |

The parser handles the observed AIF four-row span without treating the inherited
AIF label on the grand-total row as another category row. It accepts the source's
malformed nested footer only when it resolves to two eight-column footer rows and
the last row is `Note`. Decorative title widths of eight or nine columns do not
control the eight-column data width.

INR values feed the existing `build_fpi_observation` contract. Published USD net
values for every detail, subtotal and total, plus the printed four-place INR per
USD rate, are retained in a separate canonical JSON document with its own hash.
USD details reconcile to their published USD subtotals and total under the same
displayed-precision bound used for component sums. The parser deliberately does
not recompute USD from INR and the printed rate because the original report's
rounded fields do not always satisfy that identity.

The observed numeric forms are unsigned two-place decimals, parentheses for
negative net values, genuine `0.00`, and `Rs.` followed by a positive four-place
rate. Missing values never become zero. Commas, leading minus signs, negative
zero, other precision and oversized values are rejected. The only deliberate
format extension is optional whitespace between `Rs.` and the rate, covered by
an authored test. Normal HTML whitespace between words is collapsed when labels
are compared.

## Original-capture result

The verifier reads local files only. It pins both response-body hashes, both
receipt hashes, the exact receipt URLs, HTTP 200 status and exact retrieval-time
strings. The known original response bytes have no UTF-8 byte-order mark.

| Capture | Retrieved at UTC | Bytes | SHA-256 |
|---|---|---:|---|
| `latest-direct.html` | `2026-09-27T12:32:50.1044666Z` | 59,129 | `5283f52784fd0cc9a7d41968cb6a34f69700923f4adb20ffe6d509a38ca8ca81` |
| `monthly-direct.html` | `2026-09-27T12:32:32.0884114Z` | 291,533 | `632537a467a15ff386104b3fa7a4a6b983b062d752ac1757eb8974954cdcd752` |

Python datetimes retain six fractional digits while these receipts retain seven.
The verifier therefore uses conservative effective candidate times of
`2026-09-27T12:32:50.104467Z` for Latest and
`2026-09-27T12:32:32.088412Z` for Monthly. It rounds a discarded non-zero
fraction up, so the observation cannot become eligible before the recorded
completion. The table above keeps the exact receipt strings.

The captures contain 19 parsed date blocks: one Latest block and 18 Monthly
blocks. Monthly dates are 1, 2, 3, 4, 7, 8, 9, 10, 11, 15, 16, 17, 18, 21, 22,
23, 24 and 25 September 2026. The selected 25 September reference has gross
purchases of INR 14,990.76 crore, gross sales of INR 21,543.47 crore and net
investment of INR -6,552.71 crore. Its published net USD amount is -683.20
million and its printed conversion rate is 95.9099 INR per USD. Complete
day-by-day arithmetic remains private in
`C:/Users/sakha/.agent-reach/fxregimelab-fpi-evidence/arithmetic-summary.json`;
it is not reproduced in this repository.

Latest and Monthly's final block match across every INR component, every USD
component and the printed rate. With the Monthly receipt completion used only as
the candidate parse time, all 18 observations are excluded one microsecond
before capture. At capture, 25 September is current at -655,271 INR hundredths
and the other 17 dates are prior history. This proves the pure bridge is causal;
it does not claim durable production first-seen provenance.

## Rejected cases and checks

Authored fixtures cover reordered, duplicate and missing categories; duplicate
and out-of-order dates; wrong routes and units; malformed date, category and AIF
spans; partial totals; invalid, blank and oversized numbers; USD reconciliation;
zero or malformed rates; unknown and incomplete footers; nested and duplicate
tables; derivatives-only pages; request-rejection pages; unsupported URLs; and
naive timestamps. No original NSDL table was copied into the repository.

The exact parser gate passed with 86 tests and `REPAIR_PYTEST_VERIFIED`. The
private original-capture command returned `FPI_ORIGINAL_CAPTURE_VERIFIED`.
Scoped Ruff and MyPy checks also passed. Storage, atomic durable first-seen
assignment, acquisition scheduling, live/staged/replay integration and feature
activation remain outside this leaf.
