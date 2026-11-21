"""Authored fixtures for the NSDL FPI HTML parser; no source table is copied."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from typing import cast

import pytest

from src.research.fpi_observation import FPI_ROUTES, select_fpi_history
from src.research.fpi_parser import FPI_PARSER_VERSION, ParsedFpiDay, parse_nsdl_fpi_html

_VERIFIER_PATH = Path(__file__).parents[1] / "scripts" / "verify_fpi_source_capture.py"
_VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "_fpi_source_capture_verifier_test", _VERIFIER_PATH
)
if _VERIFIER_SPEC is None or _VERIFIER_SPEC.loader is None:
    raise RuntimeError("Unable to load the FPI source-capture verifier for its precision test")
_VERIFIER_MODULE = importlib.util.module_from_spec(_VERIFIER_SPEC)
_VERIFIER_SPEC.loader.exec_module(_VERIFIER_MODULE)
_parse_timestamp = cast(Callable[[str], datetime], getattr(_VERIFIER_MODULE, "_parse_timestamp"))

LATEST = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"
MONTHLY = "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx"
HEADERS = (
    "Reporting Date",
    "Debt/Debt-VRR/Equity/Hybrid",
    "Investment Route",
    "Gross Purchases(Rs. Crore)",
    "Gross Sales (Rs. Crore)",
    "Net Investment (Rs. Crore)",
    "Net Investment US($) million",
    "Conversion (1 USD TO INR)*",
)


def _cell(value: str, *, rowspan: int | None = None) -> str:
    span = f" rowspan='{rowspan}'" if rowspan is not None else ""
    return f"<td{span}>{escape(value)}</td>"


def _day(day: int, *, negative: bool = False) -> list[str]:
    rows: list[str] = []
    route_count = 0
    first = True
    for category, routes in FPI_ROUTES.items():
        category_span = len(routes) + 1 + (1 if category == "AIFs" else 0)
        for route_index, route in enumerate(routes):
            prefix = ""
            if first:
                prefix += _cell(f"{day:02d}-Sep-2026", rowspan=25)
            if route_index == 0:
                prefix += _cell(category, rowspan=category_span)
            net = "(7.00)" if negative and route_count == 0 else "7.00"
            cells = (
                _cell(route)
                + _cell("10.00")
                + _cell("3.00")
                + _cell(net)
                + _cell("0.70")
            )
            if first:
                cells += _cell("Rs. 80.1234", rowspan=25)
            rows.append(f"<tr>{prefix}{cells}</tr>")
            first = False
            route_count += 1
        count = len(routes)
        rows.append(
            "<tr>"
            + _cell("Sub-total")
            + _cell(f"{10 * count}.00")
            + _cell(f"{3 * count}.00")
            + _cell(f"{7 * count}.00")
            + _cell(f"{0.7 * count:.2f}")
            + "</tr>"
        )
    total_net = 105 if negative else 119
    rows.append(
        "<tr class='total'>"
        + _cell("Total")
        + _cell("170.00")
        + _cell("51.00")
        + _cell(f"{total_net}.00")
        + _cell("11.90")
        + "</tr>"
    )
    return rows


def _report(*days: int, malformed_footer: bool = True) -> bytes:
    headings = "".join(f"<th>{escape(value)}</th>" for value in HEADERS)
    investment = (
        "<table class='tbls01'>"
        "<tr><th colspan='9'>Authored explanation</th></tr>"
        "<tr><th colspan='8'>Daily Trends in FPI Investments on 25-Sep-2026</th></tr>"
        f"<tr>{headings}</tr>"
        + "".join(row for day in days for row in _day(day))
        + (
            "<tr><td colspan='8'></td><tr><td colspan='8'>Note</td></tr>"
            if malformed_footer
            else ""
        )
        + "</table>"
    )
    derivatives = (
        "<table class='tbls01'><tr><th colspan='8'>Daily Trends in FPI Derivative Trades"
        "</th></tr><tr><th>Reporting Date</th><th>Derivative Product</th></tr>"
        "<tr><td>25-Sep-2026</td><td>INDEX FUTURES</td></tr></table>"
    )
    return f"<html><body><div id='rpt'>{investment}{derivatives}</div></body></html>".encode()


def _parse(
    body: bytes, *, source_url: str = LATEST, second: int = 0
) -> tuple[ParsedFpiDay, ...]:
    return parse_nsdl_fpi_html(
        body,
        source_url=source_url,
        retrieved_at=datetime(2026, 9, 27, 12, 30, second, tzinfo=UTC),
    )


def test_parse_complete_day_and_preserve_separate_source_evidence() -> None:
    body = _report(25)
    parsed = _parse(body)

    assert len(parsed) == 1
    day = parsed[0]
    assert day.observation.net_hundredths_cr == 11900
    assert day.observation.raw_sha256 == hashlib.sha256(body).hexdigest()
    assert day.observation.parser_version == FPI_PARSER_VERSION
    assert day.observation.first_seen_at == day.observation.retrieved_at
    evidence = json.loads(day.source_evidence.document_json)
    assert evidence["categories"]["Mutual Funds"]["routes_net_usd_million"] == {
        route: "0.70" for route in FPI_ROUTES["Mutual Funds"]
    }
    assert day.source_evidence.total_net_usd_million == "11.90"
    assert day.source_evidence.conversion_rate_inr_per_usd == "80.1234"
    assert day.source_evidence.evidence_sha256 == hashlib.sha256(
        day.source_evidence.document_json.encode("ascii")
    ).hexdigest()


def test_parentheses_are_negative_and_zero_is_not_missing() -> None:
    body = _report(25).replace(
        b"<td>10.00</td><td>3.00</td><td>7.00</td>",
        b"<td>3.00</td><td>10.00</td><td>(7.00)</td>",
        1,
    )
    body = body.replace(
        b"<td>20.00</td><td>6.00</td><td>14.00</td>",
        b"<td>13.00</td><td>13.00</td><td>0.00</td>",
        1,
    )
    body = body.replace(
        b"<td>170.00</td><td>51.00</td><td>119.00</td>",
        b"<td>163.00</td><td>58.00</td><td>105.00</td>",
        1,
    )
    parsed = _parse(body)[0]
    document = json.loads(parsed.observation.document_json)

    assert document["categories"]["Equity"]["routes"]["Stock Exchange"]["net_cr"] == "-7.00"
    assert document["categories"]["Debt-General Limit"]["routes"]["Stock Exchange"][
        "purchases_cr"
    ] == "10.00"
    assert document["categories"]["Equity"]["subtotal"]["net_cr"] == "0.00"


def test_monthly_capture_metadata_does_not_establish_decision_visibility() -> None:
    retrieved = datetime(2026, 9, 27, 12, 32, 32, tzinfo=UTC)
    parsed = parse_nsdl_fpi_html(_report(1, 2, 25), source_url=MONTHLY, retrieved_at=retrieved)
    observations = [day.observation for day in parsed]

    assert [item.reporting_date.day for item in observations] == [1, 2, 25]
    assert all(item.retrieved_at == retrieved for item in observations)
    assert all(item.first_seen_at == retrieved for item in observations)
    for decision_time in (retrieved - timedelta(microseconds=1), retrieved):
        with pytest.raises(RuntimeError, match="exact qualified decision snapshot"):
            select_fpi_history(
                observations,
                as_of=decision_time,
                max_current_age_days=40,
                max_history_age_days=40,
            )


def test_receipt_timestamp_rounds_discarded_precision_up() -> None:
    assert _parse_timestamp("2026-09-27T12:32:32.0884114Z") == datetime(
        2026, 9, 27, 12, 32, 32, 88412, tzinfo=UTC
    )
    assert _parse_timestamp("2026-09-27T12:32:32.0884110Z") == datetime(
        2026, 9, 27, 12, 32, 32, 88411, tzinfo=UTC
    )


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("wrong header units", lambda body: body.replace(b"Rs. Crore", b"Rs. Lakh", 1)),
        ("invalid number", lambda body: body.replace(b">10.00</td>", b">ten</td>", 1)),
        ("blank is not zero", lambda body: body.replace(b">10.00</td>", b"></td>", 1)),
        (
            "comma extension rejected",
            lambda body: body.replace(b">10.00</td>", b">1,000.00</td>", 1),
        ),
        ("leading minus rejected", lambda body: body.replace(b">7.00</td>", b">-7.00</td>", 1)),
        ("bad rate precision", lambda body: body.replace(b"80.1234", b"80.12", 1)),
        ("zero rate", lambda body: body.replace(b"80.1234", b"0.0000", 1)),
        (
            "oversized USD",
            lambda body: body.replace(b">0.70</td>", b">12345678901234567.00</td>", 1),
        ),
        ("wrong USD subtotal", lambda body: body.replace(b">1.40</td>", b">1.42</td>", 1)),
        ("wrong USD total", lambda body: body.replace(b">11.90</td>", b">12.00</td>", 1)),
        ("malformed date span", lambda body: body.replace(b"rowspan='25'", b"rowspan='24'", 1)),
        ("malformed category span", lambda body: body.replace(b"rowspan='3'", b"rowspan='2'", 1)),
        ("missing category", lambda body: body.replace(_day(25)[3].encode(), b"", 1)),
        ("duplicate category", lambda body: body.replace(b"Debt-General Limit", b"Equity", 1)),
        ("reordered category", lambda body: body.replace(b"Debt-General Limit", b"Hybrid", 1)),
        (
            "missing total class",
            lambda body: body.replace(b"class='total'", b"class='subtotal'", 1),
        ),
        ("partial total", lambda body: body.replace(b"<td>11.90</td>", b"", 1)),
        (
            "data after footer",
            lambda body: body.replace(b"</table><table", b"<tr><td>x</td></tr></table><table", 1),
        ),
        ("unknown footer", lambda body: body.replace(b">Note</td>", b">Totals 1.00</td>", 1)),
        ("blank final footer", lambda body: body.replace(b">Note</td>", b"></td>", 1)),
        (
            "duplicate investment table",
            lambda body: body.replace(
                b"</div>",
                body[body.index(b"<table") : body.index(b"</table>") + 8] + b"</div>",
            ),
        ),
    ],
)
def test_reject_malformed_or_incomplete_investment_reports(case: str, mutate: object) -> None:
    del case
    body = mutate(_report(25))  # type: ignore[operator]
    with pytest.raises(ValueError):
        _parse(body)


def test_reject_duplicate_or_out_of_order_dates() -> None:
    with pytest.raises(ValueError, match="unique and ordered"):
        _parse(_report(25, 25), source_url=MONTHLY)
    with pytest.raises(ValueError, match="unique and ordered"):
        _parse(_report(2, 1), source_url=MONTHLY)


def test_reject_route_title_and_month_disagreement() -> None:
    with pytest.raises(ValueError, match="Latest"):
        _parse(_report(1))
    with pytest.raises(ValueError, match="Monthly"):
        _parse(_report(1, 2, 24), source_url=MONTHLY)
    wrong_month = _report(1, 25).replace(b"01-Sep-2026", b"01-Aug-2026", 1)
    with pytest.raises(ValueError, match="Monthly"):
        _parse(wrong_month, source_url=MONTHLY)


def test_derivatives_are_excluded_and_cannot_stand_in_for_investment() -> None:
    body = _report(25)
    derivative_only = body[body.index(b"<table", body.index(b"</table>") + 1) :]
    derivative_only = b"<div id='rpt'>" + derivative_only
    with pytest.raises(ValueError, match="two unnested report tables"):
        _parse(derivative_only)


def test_reject_nested_report_table_before_descendant_row_scans() -> None:
    body = _report(25).replace(
        b"<table class='tbls01'><tr><th colspan='8'>Daily Trends in FPI Derivative Trades",
        b"<table class='tbls01'><tr><td><table class='tbls01'></table></td></tr>"
        b"<tr><th colspan='8'>Daily Trends in FPI Derivative Trades",
        1,
    )
    with pytest.raises(ValueError, match="two unnested"):
        _parse(body)


def test_reject_unclassed_nested_table_before_descendant_row_scans() -> None:
    body = _report(25).replace(
        b"<table class='tbls01'><tr><th colspan='8'>Daily Trends in FPI Derivative Trades",
        b"<table class='tbls01'><tr><td><table></table></td></tr>"
        b"<tr><th colspan='8'>Daily Trends in FPI Derivative Trades",
        1,
    )
    with pytest.raises(ValueError, match="two unnested"):
        _parse(body)


@pytest.mark.parametrize(
    "body",
    [
        b"<html><body>Request Rejected. Support ID: 123</body></html>",
        b"<html><body><div id='rpt'></div></body></html>",
        b"<html><body><div id='rpt'></div><div id='rpt'></div></body></html>",
    ],
)
def test_reject_non_report_responses(body: bytes) -> None:
    with pytest.raises(ValueError):
        _parse(body)


def test_reject_wrong_source_route_and_naive_retrieval_time() -> None:
    with pytest.raises(ValueError, match="source URL"):
        _parse(_report(25), source_url="https://www.fpi.nsdl.co.in/web/Reports/Derivative.aspx")
    with pytest.raises(ValueError, match="source URL"):
        parse_nsdl_fpi_html(
            _report(25),
            source_url=cast(str, []),
            retrieved_at=datetime(2026, 9, 27, 12, 30, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_nsdl_fpi_html(
            _report(25), source_url=LATEST, retrieved_at=datetime(2026, 9, 27, 12, 30)
        )
