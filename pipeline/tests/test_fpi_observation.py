"""Synthetic contract fixtures, never source or point-in-time acceptance evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import localcontext
from typing import Any

import pytest

from src.research.fpi_observation import (
    FPI_ROUTES,
    _validate_fpi_observation,
    build_fpi_observation,
    select_fpi_history,
)


def _fpi_fixture(day: int = 15, *, shift: int = 0, offset: bool = False) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    gross_total = sales_total = 0
    for index, (category, routes) in enumerate(FPI_ROUTES.items()):
        detail: dict[str, Any] = {}
        subtotal = 0
        for route_index, route in enumerate(routes):
            adjustment = 0
            if route_index == 0:
                adjustment = shift if index == 0 else (-shift if offset and index == 1 else 0)
            gross = 100 + index + adjustment
            detail[route] = {
                "purchases_cr": str(gross),
                "sales_cr": "80",
                "net_cr": str(gross - 80),
            }
            subtotal += gross
        sales = 80 * len(routes)
        groups[category] = {
            "routes": detail,
            "subtotal": {
                "purchases_cr": str(subtotal),
                "sales_cr": str(sales),
                "net_cr": str(subtotal - sales),
            },
        }
        gross_total += subtotal
        sales_total += sales
    seen = datetime(2026, 9, day, 12, tzinfo=UTC)
    return {
        "reporting_date": date(2026, 9, day),
        "categories": groups,
        "total": {
            "purchases_cr": str(gross_total),
            "sales_cr": str(sales_total),
            "net_cr": str(gross_total - sales_total),
        },
        "source_url": "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
        "raw_sha256": hashlib.sha256(f"synthetic-{day}-{shift}-{offset}".encode()).hexdigest(),
        "parser_version": "synthetic-contract-v1",
        "retrieved_at": seen,
        "first_seen_at": seen,
    }


@pytest.mark.parametrize(
    "case",
    [
        "roundtrip",
        "detached",
        "order",
        "decimal_context",
        "offset_revision",
        "nan",
        "inf",
        "float",
        "bool",
        "precision",
        "huge",
        "negative_gross",
        "missing",
        "unknown",
        "route",
        "subtotal",
        "total",
        "gross_net",
        "naive",
        "future_date",
        "first_after_retrieval",
        "source",
        "raw_hash",
        "parser",
        "timestamp_date",
        "rounding_pass",
        "rounding_fail",
        "mutated_hash",
        "mutated_document",
        "duplicate_json",
        "wrong_series",
        "forged_scalar",
        "ist_boundary",
        "retired_populated",
        "retired_empty",
        "time_overflow",
    ],
)
def test_fpi_observation(case: str) -> None:
    args = _fpi_fixture()
    original = copy.deepcopy(args)
    seen = args["first_seen_at"]
    invalid_money: dict[str, Any] = {
        "nan": "NaN",
        "inf": "Infinity",
        "float": 100.0,
        "bool": True,
        "precision": "100.001",
        "huge": "1" * 17,
        "negative_gross": "-1",
    }
    if case in invalid_money:
        args["categories"]["Equity"]["routes"]["Stock Exchange"]["purchases_cr"] = invalid_money[
            case
        ]
    elif case == "missing":
        del args["categories"]["Hybrid"]
    elif case == "unknown":
        args["categories"]["Crypto"] = args["categories"].pop("Hybrid")
    elif case == "route":
        del args["categories"]["Mutual Funds"]["routes"]["Other schemes"]
    elif case in {"subtotal", "total", "gross_net"}:
        target = args["total"] if case == "total" else args["categories"]["Equity"]["subtotal"]
        target["net_cr"] = "99999"
        if case != "gross_net":
            target["purchases_cr"] = str(99999 + int(target["sales_cr"]))
    elif case == "naive":
        args["first_seen_at"] = seen.replace(tzinfo=None)
    elif case == "future_date":
        args["reporting_date"] = date(2026, 9, 16)
    elif case == "first_after_retrieval":
        args["first_seen_at"] = seen + timedelta(seconds=1)
    elif case == "source":
        args["source_url"] = "https://pilot.fpi.nsdl.co.in/Reports/Latest.aspx"
    elif case == "raw_hash":
        args["raw_sha256"] = "invalid"
    elif case == "parser":
        args["parser_version"] = ""
    elif case == "time_overflow":
        args["retrieved_at"] = datetime.max.replace(tzinfo=UTC)
    elif case == "timestamp_date":
        args["reporting_date"] = seen
    elif case in {"rounding_pass", "rounding_fail"}:
        args["total"]["net_cr"] = str(int(args["total"]["net_cr"])) + (
            ".01" if case == "rounding_pass" else ".02"
        )
    invalid_cases = set(invalid_money) | {
        "missing",
        "unknown",
        "route",
        "subtotal",
        "total",
        "gross_net",
        "naive",
        "future_date",
        "first_after_retrieval",
        "source",
        "raw_hash",
        "parser",
        "timestamp_date",
        "rounding_fail",
        "time_overflow",
    }
    if case in invalid_cases:
        with pytest.raises(ValueError):
            build_fpi_observation(**args)
        return
    observation = build_fpi_observation(**args)
    if case in {"roundtrip", "rounding_pass"}:
        assert args == original or case == "rounding_pass"
        document = json.loads(observation.document_json)
        assert document["total"]["net_cr"] == ("397.01" if case == "rounding_pass" else "397.00")
        assert hashlib.sha256(observation.document_json.encode()).hexdigest() == (
            observation.observation_sha256
        )
    elif case == "detached":
        args["categories"]["Equity"]["subtotal"]["net_cr"] = "999"
        assert observation == build_fpi_observation(**original)
    elif case == "order":
        args["categories"] = dict(reversed(list(args["categories"].items())))
        assert observation == build_fpi_observation(**args)
    elif case == "decimal_context":
        with localcontext() as context:
            context.prec = 2
            assert observation == build_fpi_observation(**args)
    elif case == "offset_revision":
        offset_observation = build_fpi_observation(**_fpi_fixture(shift=1, offset=True))
        assert offset_observation.net_hundredths_cr == observation.net_hundredths_cr
        assert offset_observation.observation_sha256 != observation.observation_sha256
    elif case in {
        "mutated_hash",
        "mutated_document",
        "duplicate_json",
        "wrong_series",
        "forged_scalar",
    }:
        if case == "mutated_hash":
            observation = replace(observation, observation_sha256="0" * 64)
        elif case == "forged_scalar":
            observation = replace(observation, net_hundredths_cr=True)
        else:
            document_text = observation.document_json
            if case == "duplicate_json":
                document_text = '{"units":"INR_CRORE",' + document_text[1:]
            elif case == "wrong_series":
                document_text = document_text.replace("INR_CRORE", "USD_MILLION")
            else:
                document_text = "[]"
            observation = replace(observation, document_json=document_text)
        with pytest.raises(ValueError):
            _validate_fpi_observation(observation)
    elif case == "ist_boundary":
        args["reporting_date"] = date(2026, 9, 16)
        args["first_seen_at"] = args["retrieved_at"] = datetime(2026, 9, 15, 19, tzinfo=UTC)
        observation = build_fpi_observation(**args)
        _validate_fpi_observation(observation)
        assert observation.reporting_date == date(2026, 9, 16)
    elif case in {"retired_populated", "retired_empty"}:
        candidates = [observation] if case == "retired_populated" else []
        with pytest.raises(RuntimeError, match="exact qualified decision snapshot"):
            select_fpi_history(
                candidates, as_of=seen, max_current_age_days=3, max_history_age_days=40,
            )
    else:
        raise AssertionError(f"Unhandled test case: {case}")
