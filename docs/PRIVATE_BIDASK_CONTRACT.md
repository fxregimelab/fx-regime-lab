# Private bid/ask evidence — bounded contract

Owner scope: private FX research only, 1 October 2026. This packet advances R1 by adding a strict FXCM minute-archive reader and a visible source-quality audit. It does not establish executable fills, a new strategy, current probability or the full R1 outcome.

The witnessed archive has nine columns: DateTime, BidOpen, BidHigh, BidLow, BidClose, AskOpen, AskHigh, AskLow, AskClose. Dates use MM/DD/YYYY HH:MM:SS.mmm; FXCM documents UTC. Timestamp start/end role and exact boundary tick allocation remain unknown. Prices are indicative lowest Active Trader quotes, not this owner's broker fills. Preserve both sides without mid-price conversion or invented volume.

Require the exact header, finite positive prices, valid OHLC on each side, uncrossed side bounds, strictly increasing minute-aligned timestamps inside the requested Sunday-to-Saturday ISO-week envelope, and no observation after the receipt clock. Reject a malformed archive in full. Preserve successful and failed bounded HTTP bodies with source URL, status, UTC receipt, SHA-256 and unique immutable receipts. Cache reuse must verify the request identity, path boundary and body hash; cache corruption must not silently refetch or repair itself.

Union explicitly requested weeks only. Equal duplicate timestamps count once; conflicting same-time quotes fail the whole pair cohort. Report observed counts/ranges and missing minutes under an explicitly unverified Sunday 17:00 to Friday 17:00 New York market-clock proxy. No missing minute is forward-filled or declared a holiday. Side-open/close price differences in pips are descriptive OHLC differences, not synchronized tick spreads or realised costs. Full archive continuity, source corrections, execution/slippage/financing, holidays and historical receipt/vintage remain open.

CLI captures only named ISO weeks, with at most twelve per invocation, for the seven private pairs or a specified pair. Report rebuilds read and verify the saved evidence without automatic bulk acquisition. The dashboard shows this separate cohort and its limits; existing price backtests and candidate eligibility remain unchanged. Offline replay recomputes this audit from pinned raw bodies.

Acceptance: adverse parsing/time/identity/hash/HTTP/duplicate/size controls, actual seven-pair sample capture, complete gap inventory, exact offline audit reproduction, report/UI integration, full pipeline regression/lint/types and real authenticated browser rendering. R1 remains open after this packet.
