# Private central-bank evidence capture

Checked on 1 October 2026 against revision 1 of
`docs/PRIVATE_JEV_SHADOW_CONTRACT.md`. This is a source-capture leaf. It does
not qualify a trade, validate a model judgment, establish historical arrival,
or approve either gate.

## Result

Eight first-party URLs were attempted, below the limit of twelve. Six returned
replayable article text. RBA and RBNZ returned direct HTTP 403 responses. Their
response bodies and failure receipts are retained as unavailable evidence.
No proxy body was used. The RBNZ URL came from the documented official homepage
discovery route in `reports/private-current-news-source-research.md`; it was
not inferred from a proxy response.

| Currency | Publisher and role | Status | Selector | Raw SHA-256 | Text SHA-256 | Spans |
|---|---|---:|---|---|---|---:|
| USD | Federal Reserve policy statement | Available | `#article` | `08010b7ed4bf50b44a643174fa2f469bc42c9cb10d8c697bb6500d2169d3c9fe` | `0a2b760a100fb6958709c1c6573cc48ab43b3cd7c27996013896d3ef0d1540e8` | 1 |
| EUR | ECB policy speech | Available | `main` | `f18c6b0ebceed8d73e991fdcc147786cf11fa92dc4a05e5c5b0905916baee2b6` | `0945207b1722fc1fd4ee0d23accc3c699b837e90bf21dcda3fc6c5e642a0ed57` | 21 |
| GBP | Bank of England policy summary and minutes | Available | `main` | `1719d05c09be0d9ce749fff37cfa5fdaf366a4be32fc7745e650e1a9efc1b59c` | `65c92ceb157d0248576adc46badeaa1e0d7d0d0b3ddd1da41563ae85db668db3` | 41 |
| AUD | RBA financial-stability release | Unavailable: HTTP 403 | — | `1d43cf7de4875c689a75d1651980364f7ebc1467b8f1e6293171188c1c85c1b9` | — | 0 |
| CAD | Bank of Canada policy release | Available | `main` | `ba52bd2e92f7e502349830dc8b98e665974f896ee5331ddc8856e85ee002eddb` | `e543f2021103120116a9b722b176226d79dcb0371e48208c7cff2ccdf0168852` | 4 |
| CHF | Swiss National Bank policy assessment | Available | `main` | `aa1dbe9cf0c77479e2224e1d83a88171e1459b9ff77e5bdfe4901dcf47362686` | `3417b1100e5e662f98653840df854db4f9a01f66fff41c25c52e591d8d8a8365` | 4 |
| CAD | Bank of Canada governance negative example | Available | `main` | `8da9e7c4c93c0cb2a1d8d7b96e8387e8c587ce963c694cc77e7447bfae5fb1ae` | `f6dc741cb57cc24e5119db0b9b55a9fb10839fd9a989c80ad76f478a007611f9` | 2 |
| NZD | RBNZ official non-policy discovery article | Unavailable: HTTP 403 | — | `f88f7fbe179d6f6db2d6f303aff890eee440cd529d26062876f2a5fed561a44b` | — | 0 |

The governance item is deliberately retained as a negative example. Its
successful extraction does not make it monetary-policy evidence.

## Interface and replay boundary

`capture_evidence(url, source, root, publication=None)` accepts only the
seven named central-bank publishers and their exact HTTPS hosts. It rejects
userinfo, non-standard ports, redirects, bodies above 2 MiB, unsupported
content or encoding, challenges, login pages, empty pages, and pages without
enough article text. The request has a connect/read timeout and never follows
a redirect. A mid-stream failure preserves bytes already observed and records
the capture as unavailable.

An available receipt has these fields:

```text
schema_version, status, source, publisher_host, url, received_at,
arrival_basis, publication, vintage, request_policy, http,
raw {path, sha256, bytes}, raw_sha256,
text {path, sha256, bytes, encoding, selector}, text_sha256,
spans, extraction_scope, model_calls, failure, capture_id, receipt_path
```

Each span has `id`, `start`, `end`, `text`, `sha256`, and
`offset_basis="UTF8_EXTRACTED_TEXT"`. Start and end are byte offsets into
the saved UTF-8 extracted-text file, not offsets into the raw HTML.

`verify_evidence(receipt, root)` first binds the supplied object exactly to
its immutable receipt file and recomputes its capture identity. It then checks
the URL and publisher boundary, receipt policy fields, status 200 HTML
metadata, body limit, non-future UTC receipt, unknown vintage, prohibited
model-call state, raw hash, publisher selector, replayed text hash, saved text
bytes, and rederived spans. It returns the receipt fields with `text`
replaced by the verified extracted string and `spans` replaced by the
rederived list.

The article selector records extraction coverage only. It is not a claim that
every meaningful byte in the source document was captured. The saved transport
receipt records which URL returned the body; it is not cryptographic proof of
publisher authorship.

## Manifest

The integration entry point is
`.private-fx/evidence/manifest.json`, SHA-256
`4d992195362f051619da4fddafa666db61b53740fc491646cfd60766571157dc`.
Its exact shape is:

```text
{
  schema_version,
  created_at,
  source_report {path, sha256},
  capture_limit,
  attempt_count,
  available_count,
  unavailable_count,
  model_calls,
  captures [{
    currency,
    purpose,
    status,
    receipt_path,
    receipt_sha256,
    failure? {code, status_code}
  }]
}
```

Paths in `receipt_path` are relative to the evidence root. The manifest
binds the witnessed source report at SHA-256
`7b075844f1d1ad7594e13b4284dde06f24d0f2bbb003a2023c3dc747a73638da`.
That report hash was unchanged after capture.

## Checks

- Focused evidence tests: 25 passed.
- Ruff on the evidence module and its test file: passed.
- MyPy on the evidence module and its test file: passed.
- Replay of all six available saved receipts: passed.
- Bounded read-only root review: `test_private_desk_jev_shadow.py`, 38 passed.
- GitNexus impact was attempted before every public function and helper.
  Every attempt returned `UNKNOWN` because the index database is version 42
  while the available runtime expects version 40. The manual call trace is
  limited to the evidence module, its tests, and the root-owned shadow
  consumer.

File hashes:

- `pipeline/src/private_desk/evidence.py`:
  `cbe95156cea6ad4691362499c3bcfb646524d5d5fbb7b9c6a53c3f43df6760a1`
- `pipeline/tests/test_private_desk_evidence.py`:
  `d108e6bc5f7a57ecbb1bc2a356560ef183f09f24925f2c93d9b3bcb34e025e5b`

## Limits

The supplied `publication` value is stored as
`SUPPLIED_PUBLISHER_FEED_CLAIM` with `article_verified=false`. It is not
an article-derived clock, a first-public-availability time, or a historical
vintage. `received_at` is the post-fetch UTC receipt for this capture only.
The parser does not prove completeness, correction history, economic
relevance, or predictive value. Old material may be used only as retrospective
semantic examples. No model call occurs in the capture worker.

The default, no-paid-call integration example is:

```powershell
cd D:\Projects\fxregimelab\pipeline
python -m src.private_desk.jev_shadow evaluate --evidence "D:\Projects\fxregimelab\.private-fx\evidence\receipts\9115290228a62c4505554ca84964a65a.json" --evidence-root "D:\Projects\fxregimelab\.private-fx\evidence" --shadow-root "D:\Projects\fxregimelab\.private-fx\jev-shadow" --currency USD --claim "The Committee decided to raise the target range for the federal funds rate by 1/4 percentage point." --mechanism "A policy-rate increase is explicitly stated."
```

The command deliberately omits `--enable`. It creates a deterministic,
review-required shadow result with no provider request.
