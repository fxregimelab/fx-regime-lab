"""Strict, pure parser for confirmed NSDL FPI investment-report HTML.

The parser accepts original response bytes and preserves the published USD
amounts and conversion rate as supplemental evidence.  Only normalized INR
values cross into the canonical observation contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.research.fpi_observation import FPI_ROUTES, FpiObservation, build_fpi_observation

FPI_PARSER_VERSION = "nsdl-fpi-html-v1"
_SOURCE_URLS = frozenset(
    {
        "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
        "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
    }
)
_HEADERS = (
    "Reporting Date",
    "Debt/Debt-VRR/Equity/Hybrid",
    "Investment Route",
    "Gross Purchases(Rs. Crore)",
    "Gross Sales (Rs. Crore)",
    "Net Investment (Rs. Crore)",
    "Net Investment US($) million",
    "Conversion (1 USD TO INR)*",
)
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
_AMOUNT = re.compile(
    r"(?:0|[1-9][0-9]{0,15})\.[0-9]{2}|\((?:0|[1-9][0-9]{0,15})\.[0-9]{2}\)"
)
_RATE = re.compile(r"Rs\.\s*((?:0|[1-9][0-9]{0,5})\.[0-9]{4})")


@dataclass(frozen=True)
class FpiSourceEvidence:
    """Canonical supplemental source values excluded from the INR identity."""

    document_json: str
    evidence_sha256: str
    total_net_usd_million: str
    conversion_rate_inr_per_usd: str


@dataclass(frozen=True)
class ParsedFpiDay:
    """One reporting date parsed from a capture.

    ``first_seen_at`` on ``observation`` equals this parse's retrieval time. A
    durable writer must reconcile retries and establish the real first seen.
    """

    observation: FpiObservation
    source_evidence: FpiSourceEvidence


def _normalized_text(cell: Tag) -> str:
    return " ".join(cell.stripped_strings)


def _parse_amount(text: str, *, field: str) -> str:
    """Normalize the two source forms: unsigned decimals and parentheses."""
    if not _AMOUNT.fullmatch(text):
        raise ValueError(f"Invalid {field} amount in FPI investment report")
    if text.startswith("("):
        magnitude = text[1:-1]
        if magnitude == "0.00":
            raise ValueError(f"Invalid negative zero in FPI {field} amount")
        return f"-{magnitude}"
    return text


def _parse_date(text: str) -> date:
    match = re.fullmatch(r"([0-9]{2})-([A-Z][a-z]{2})-([0-9]{4})", text)
    if match is None or match.group(2) not in _MONTHS:
        raise ValueError("Invalid reporting date in FPI investment report")
    try:
        return date(int(match.group(3)), _MONTHS[match.group(2)], int(match.group(1)))
    except ValueError as exc:
        raise ValueError("Invalid reporting date in FPI investment report") from exc


def _hundredths(text: str) -> int:
    whole, fraction = text.lstrip("-").split(".")
    value = int(whole) * 100 + int(fraction)
    return -value if text.startswith("-") else value


def _reconcile_amounts(children: Sequence[str], parent: str, *, label: str) -> None:
    difference = abs(sum(_hundredths(value) for value in children) - _hundredths(parent))
    if 2 * difference > len(children) + 1:
        raise ValueError(f"FPI {label} amounts do not reconcile")


def _report_title_date(rows: Sequence[Tag]) -> date:
    prefix = "Daily Trends in FPI Investments on "
    titles = []
    for row in rows:
        text = _normalized_text(row)
        if text.startswith(prefix):
            titles.append(text)
    if len(titles) != 1 or not re.fullmatch(
        r"Daily Trends in FPI Investments on [0-9]{2}-[A-Z][a-z]{2}-[0-9]{4}", titles[0]
    ):
        raise ValueError("FPI investment table heading is missing or malformed")
    return _parse_date(titles[0][len(prefix) :])


def _positive_span(cell: Tag, attribute: str) -> int:
    raw = cell.get(attribute, "1")
    if not isinstance(raw, str) or not re.fullmatch(r"[1-9][0-9]*", raw):
        raise ValueError(f"Invalid FPI table {attribute}")
    value = int(raw)
    if value > 25:
        raise ValueError(f"Oversized FPI table {attribute}")
    return value


def _expand_rows(rows: Sequence[Tag]) -> list[tuple[tuple[str, ...], frozenset[str]]]:
    """Expand the observed rowspans into eight logical investment columns."""
    active: dict[int, tuple[str, int]] = {}
    expanded: list[tuple[tuple[str, ...], frozenset[str]]] = []
    footer: list[str] = []
    for row in rows:
        cells = row.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        has_colspan = any(_positive_span(cell, "colspan") != 1 for cell in cells)
        if has_colspan:
            if active:
                raise ValueError("FPI footer interrupts an active data span")
            if len(cells) != 1 or _positive_span(cells[0], "colspan") != 8:
                raise ValueError("Unexpected FPI footer structure")
            footer_text = _normalized_text(cells[0])
            if footer_text not in {"", "Note"}:
                raise ValueError("Unexpected content in FPI report footer")
            footer.append(footer_text)
            continue
        if footer:
            raise ValueError("FPI data appears after the report footer")
        if any(cell.name != "td" for cell in cells):
            raise ValueError("Repeated or malformed FPI investment header")

        logical: list[str | None] = [None] * 8
        next_active: dict[int, tuple[str, int]] = {}
        for column, (value, remaining) in active.items():
            logical[column] = value
            if remaining > 1:
                next_active[column] = (value, remaining - 1)
        active = next_active

        for cell in cells:
            try:
                column = logical.index(None)
            except ValueError as exc:
                raise ValueError("FPI investment row has more than eight columns") from exc
            text = _normalized_text(cell)
            if not text:
                raise ValueError("FPI investment cells cannot be blank")
            logical[column] = text
            rowspan = _positive_span(cell, "rowspan")
            if rowspan > 1:
                active[column] = (text, rowspan - 1)
        if any(value is None for value in logical):
            raise ValueError("FPI investment row does not have eight logical columns")
        classes = row.get("class")
        row_classes = frozenset(classes) if isinstance(classes, list) else frozenset()
        expanded.append((tuple(value for value in logical if value is not None), row_classes))
    if active:
        raise ValueError("FPI investment table ends inside a rowspan")
    if len(footer) != 2 or footer[-1] != "Note":
        raise ValueError("FPI investment report footer is incomplete")
    return expanded


def _source_amounts(row: tuple[str, ...]) -> tuple[dict[str, str], str]:
    inr = {
        "purchases_cr": _parse_amount(row[3], field="INR purchases"),
        "sales_cr": _parse_amount(row[4], field="INR sales"),
        "net_cr": _parse_amount(row[5], field="INR net"),
    }
    return inr, _parse_amount(row[6], field="USD net")


def _build_day(
    rows: Sequence[tuple[tuple[str, ...], frozenset[str]]],
    *,
    source_url: str,
    raw_sha256: str,
    retrieved_at: datetime,
) -> ParsedFpiDay:
    if len(rows) != 25:
        raise ValueError("Each FPI reporting date must contain exactly 25 investment rows")
    reporting_date = _parse_date(rows[0][0][0])
    dates = {row[0][0] for row in rows}
    rates = {row[0][7] for row in rows}
    if len(dates) != 1 or len(rates) != 1:
        raise ValueError("FPI date or conversion span is incomplete")
    rate_match = _RATE.fullmatch(next(iter(rates)))
    if rate_match is None:
        raise ValueError("Invalid FPI INR per USD conversion rate")
    rate = rate_match.group(1)
    if int(rate.replace(".", "")) == 0:
        raise ValueError("FPI INR per USD conversion rate must be positive")

    categories: dict[str, Any] = {}
    evidence_categories: dict[str, Any] = {}
    subtotal_usd_values: list[str] = []
    position = 0
    for category, expected_routes in FPI_ROUTES.items():
        routes: dict[str, Any] = {}
        evidence_routes: dict[str, str] = {}
        for expected_route in expected_routes:
            values, classes = rows[position]
            if values[1] != category or values[2] != expected_route or "total" in classes:
                raise ValueError("FPI categories or routes are missing, duplicated or reordered")
            amounts, usd = _source_amounts(values)
            routes[expected_route] = amounts
            evidence_routes[expected_route] = usd
            position += 1
        values, classes = rows[position]
        if values[1] != category or values[2] != "Sub-total" or "total" in classes:
            raise ValueError("FPI category subtotal is missing or misplaced")
        subtotal, subtotal_usd = _source_amounts(values)
        _reconcile_amounts(list(evidence_routes.values()), subtotal_usd, label="USD category")
        subtotal_usd_values.append(subtotal_usd)
        categories[category] = {"routes": routes, "subtotal": subtotal}
        evidence_categories[category] = {
            "routes_net_usd_million": evidence_routes,
            "subtotal_net_usd_million": subtotal_usd,
        }
        position += 1

    values, classes = rows[position]
    if values[2] != "Total" or "total" not in classes:
        raise ValueError("FPI grand total row is missing or malformed")
    total, total_usd = _source_amounts(values)
    _reconcile_amounts(subtotal_usd_values, total_usd, label="USD total")
    observation = build_fpi_observation(
        reporting_date=reporting_date,
        categories=categories,
        total=total,
        source_url=source_url,
        raw_sha256=raw_sha256,
        parser_version=FPI_PARSER_VERSION,
        retrieved_at=retrieved_at,
        first_seen_at=retrieved_at,
    )
    evidence_document = {
        "version": "nsdl-fpi-source-evidence-v1",
        "reporting_date": reporting_date.isoformat(),
        "usd_units": "USD_MILLION",
        "conversion_rate_units": "INR_PER_USD",
        "conversion_rate_inr_per_usd": rate,
        "categories": evidence_categories,
        "total_net_usd_million": total_usd,
    }
    encoded = json.dumps(evidence_document, sort_keys=True, separators=(",", ":"))
    evidence = FpiSourceEvidence(
        encoded,
        hashlib.sha256(encoded.encode("ascii")).hexdigest(),
        total_usd,
        rate,
    )
    return ParsedFpiDay(observation, evidence)


def parse_nsdl_fpi_html(
    body: bytes, *, source_url: str, retrieved_at: datetime
) -> tuple[ParsedFpiDay, ...]:
    """Parse complete investment days from an original NSDL HTML response.

    This function performs no I/O. It rejects rejection pages, derivatives-only
    tables, partial dates and unknown structures instead of filling gaps.
    """
    if type(body) is not bytes or not 1 <= len(body) <= 5_000_000:
        raise ValueError("FPI parser requires bounded original response bytes")
    if not isinstance(source_url, str) or source_url not in _SOURCE_URLS:
        raise ValueError("Unsupported FPI source URL")
    raw_sha256 = hashlib.sha256(body).hexdigest()
    soup = BeautifulSoup(body, "html.parser")
    report_nodes = soup.select("div#rpt")
    if len(report_nodes) != 1:
        raise ValueError("FPI response does not contain one report container")

    all_report_tables = report_nodes[0].find_all("table")
    report_tables = report_nodes[0].select("table.tbls01")
    if len(all_report_tables) != 2 or len(report_tables) != 2 or any(
        table.find_parent("table") is not None for table in report_tables
    ):
        raise ValueError("FPI response must contain two unnested report tables")
    candidates: list[tuple[Tag, int]] = []
    derivative_tables = 0
    for table in report_tables:
        header_indexes = []
        table_rows = table.find_all("tr")
        if any(
            "Daily Trends in FPI Derivative Trades" in _normalized_text(row)
            for row in table_rows
        ):
            derivative_tables += 1
        for index, row in enumerate(table_rows):
            cells = row.find_all(["th", "td"], recursive=False)
            if tuple(_normalized_text(cell) for cell in cells) == _HEADERS:
                header_indexes.append(index)
        if len(header_indexes) == 1:
            candidates.append((table, header_indexes[0]))
    if len(candidates) != 1 or derivative_tables != 1:
        raise ValueError("FPI response must contain one identified investment table")

    table, header_index = candidates[0]
    table_rows = table.find_all("tr")
    title_date = _report_title_date(table_rows[:header_index])
    expanded = _expand_rows(table_rows[header_index + 1 :])
    if not expanded or len(expanded) % 25:
        raise ValueError("FPI investment table contains a partial reporting date")

    blocks: list[list[tuple[tuple[str, ...], frozenset[str]]]] = []
    for offset in range(0, len(expanded), 25):
        blocks.append(expanded[offset : offset + 25])
    parsed = tuple(
        _build_day(
            block,
            source_url=source_url,
            raw_sha256=raw_sha256,
            retrieved_at=retrieved_at,
        )
        for block in blocks
    )
    dates = [day.observation.reporting_date for day in parsed]
    if len(dates) != len(set(dates)) or dates != sorted(dates):
        raise ValueError("FPI reporting dates must be unique and ordered")
    if source_url.endswith("/Latest.aspx"):
        if len(parsed) != 1 or dates[0] != title_date:
            raise ValueError("Latest FPI report must contain its titled reporting date only")
    elif title_date != max(dates) or any(
        (reporting_date.year, reporting_date.month) != (title_date.year, title_date.month)
        for reporting_date in dates
    ):
        raise ValueError("Monthly FPI dates must agree with the titled month and latest date")
    return parsed
