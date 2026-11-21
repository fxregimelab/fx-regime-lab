"""Private report/refresh/export authorization and safe local credential boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.private_desk.api import create_app
from src.private_desk.report import atomic_json


@pytest.fixture
def desk(tmp_path: Path) -> tuple[TestClient, str, Path]:
    app = create_app(tmp_path)
    password = (tmp_path / "access.txt").read_text().splitlines()[1]
    return TestClient(app), password, tmp_path


def test_protected_endpoints_do_not_leak(desk: tuple[TestClient, str, Path]) -> None:
    client, _, _ = desk
    for path in ("/api/report", "/api/status", "/api/export.csv"):
        assert client.get(path).status_code == 401
    assert client.post("/api/refresh").status_code == 401
    assert client.get("/.private-fx/auth.json").status_code == 404


def test_login_csrf_logout_and_origin(desk: tuple[TestClient, str, Path]) -> None:
    client, password, _ = desk
    assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert (
        client.post(
            "/api/login", json={"password": password}, headers={"Origin": "https://attacker.test"}
        ).status_code
        == 403
    )
    response = client.post("/api/login", json={"password": password})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    csrf = response.json()["csrf_token"]
    assert client.get("/api/report").status_code == 200
    assert client.post("/api/refresh").status_code == 403
    assert client.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/report").status_code == 401


def test_rate_limit_and_untrusted_host(desk: tuple[TestClient, str, Path]) -> None:
    client, _, _ = desk
    for _ in range(5):
        assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"password": "wrong"}).status_code == 429
    assert client.get("/", headers={"Host": "attacker.test"}).status_code == 400


def test_authenticated_export_is_formula_safe(desk: tuple[TestClient, str, Path]) -> None:
    client, password, directory = desk
    atomic_json(
        directory / "report.json",
        {
            "pair_reports": [
                {
                    "pair": "EURUSD",
                    "backtest": {
                        "trades": [{"direction": "=HYPERLINK(1)", "net_r": -1.1}],
                    },
                }
            ]
        },
    )
    client.post("/api/login", json={"password": password})
    response = client.get("/api/export.csv")
    assert response.status_code == 200
    assert "'=HYPERLINK(1)" in response.text
    assert "-1.1" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_authenticated_overlap_export_matches_saved_decisions(
    desk: tuple[TestClient, str, Path],
) -> None:
    import csv
    import io

    client, password, directory = desk
    atomic_json(
        directory / "report.json",
        {
            "pair_reports": [
                {
                    "pair": "EURUSD",
                    "backtest": {"trades": [{"entry_time": "2023-01-05", "net_r": -1.1}]},
                },
                {
                    "pair": "GBPUSD",
                    "backtest": {"trades": [{"entry_time": "2023-01-05", "net_r": 1.9}]},
                },
            ],
            "portfolio_audit": {
                "accepted": [{"pair": "EURUSD", "entry_time": "2023-01-05"}],
                "skipped": [
                    {"pair": "GBPUSD", "entry_time": "2023-01-05", "reason": "CURRENCY_OCCUPIED"}
                ],
            },
        },
    )
    client.post("/api/login", json={"password": password})
    response = client.get("/api/export.csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["overlap_audit_decision"] == "ACCEPTED"
    assert rows[1]["overlap_audit_decision"] == "SKIPPED"
    assert rows[1]["overlap_audit_reason"] == "CURRENCY_OCCUPIED"
    assert all(row["overlap_audit_qualification"] == "UNQUALIFIED" for row in rows)


def test_browser_policy_projection_preserves_saved_report_and_all_other_evidence(
    desk: tuple[TestClient, str, Path],
) -> None:
    from copy import deepcopy

    client, password, directory = desk
    rows = [
        {
            "observation_date": f"test-only-{i}",
            "change_unavailable_reason": "INSTRUMENT_DEFINITION_BREAK" if i < 10 else None,
            "value": i,
        }
        for i in range(1000)
    ]
    value: dict[str, Any] = {
        "historical_policy": {
            "forecast_qualification": "UNQUALIFIED",
            "series_audits": [
                {
                    "currency": "EUR",
                    "rows": rows,
                    "numeric_count": 1000,
                    "metadata": {"source": "test"},
                }
            ],
        },
        "pair_reports": [
            {
                "pair": "EURUSD",
                "candidate": {"probability": None},
                "historical_policy_features": {
                    "rows": rows,
                    "matched_numeric_count": 1000,
                    "forecast_qualification": "UNQUALIFIED",
                },
            }
        ],
        "portfolio_audit": {"status": "ORIGINAL"},
        "news": [{"title": "Original evidence"}],
    }
    target = directory / "report.json"
    atomic_json(target, value)
    original_bytes = target.read_bytes()
    client.post("/api/login", json={"password": password})
    response = client.get("/api/report")
    assert response.status_code == 200
    projected = response.json()
    expected = deepcopy(value)
    expected["historical_policy"]["series_audits"][0].pop("rows")
    features = expected["pair_reports"][0]["historical_policy_features"]
    features.pop("rows")
    features.update(
        recent_rows=rows[-6:],
        last_observed_feature_date="test-only-999",
        definition_break_windows=10,
    )
    projected.pop("csrf_token")
    readiness = projected.pop("operations_readiness")
    assert readiness["status"] == "HOLD"
    assert readiness["global_hold"] is True
    expected["warnings"] = projected["warnings"]
    expected["pair_reports"][0]["candidate"].update(
        status="ABSTAIN", reasons=projected["pair_reports"][0]["candidate"]["reasons"]
    )
    assert projected == expected
    assert target.read_bytes() == original_bytes
    assert len(response.content) < len(json.dumps(value).encode()) / 10


def test_private_ai_rejects_invented_sources_and_probabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.ai import client as ai

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-only")
    response = MagicMock()
    response.choices[0].finish_reason = "stop"
    response.choices[0].message.content = json.dumps(
        {
            "summary": "Evidence",
            "pairs": [
                {
                    "pair": "EURUSD",
                    "thesis": "If future data weakens, the currency could weaken.",
                    "opposing": "If future data strengthens, the currency could strengthen.",
                    "risks": "Surprise and event-timing evidence is missing.",
                    "probability": 0.99,
                    "sources": [
                        "https://www.federalreserve.gov/newsevents/fixture",
                        "https://invented.test",
                    ],
                }
            ],
        }
    )
    mocked = MagicMock()
    mocked.models.list.return_value.data = [SimpleNamespace(id="deepseek-v4-pro")]
    response.usage = None
    mocked.chat.completions.create.return_value = response
    monkeypatch.setattr(ai, "OpenAI", MagicMock(return_value=mocked))
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}],
        [
            {
                "title": "Evidence",
                "sha256": "0" * 64,
                "content_scope": "attributed_headline_only",
                "url": "https://www.federalreserve.gov/newsevents/fixture",
                "source": "Federal Reserve",
                "published_at": "2026-10-01",
                "retrieved_at": "2026-10-01T12:00:00Z",
            }
        ],
        {},
        as_of="2026-10-01T13:00:00Z",
    )
    assert result["status"] == "UNAVAILABLE"
    assert result["pairs"] == []
    assert "invented.test" not in json.dumps(result)
    json.dumps(result, allow_nan=False)
    assert mocked.chat.completions.create.call_args.kwargs["extra_body"] == {
        "thinking": {"type": "disabled"}
    }


@pytest.mark.parametrize(
    "thesis",
    [
        "The UK rate matches the Fed upper bound.",
        "If policy shifts, the current rate is 3.75%.",
        "If policy shifts, USD has a carry advantage.",
        "If policy shifts, the current differential supports GBP.",
    ],
)
def test_private_ai_quantitative_or_unconditional_claim_fails_closed(
    monkeypatch: pytest.MonkeyPatch, thesis: str
) -> None:
    from src.ai import client as ai

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-only")
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "pairs": [
                                {
                                    "pair": "GBPUSD",
                                    "thesis": thesis,
                                    "opposing": "If evidence reverses, sterling could weaken.",
                                    "risks": "Current surprises are unavailable.",
                                    "sources": [
                                        "https://www.federalreserve.gov/newsevents/fixture"
                                    ],
                                }
                            ]
                        }
                    )
                ),
                finish_reason="stop",
            )
        ],
        usage=None,
    )
    mocked = MagicMock()
    mocked.models.list.return_value.data = [SimpleNamespace(id="deepseek-v4-pro")]
    mocked.chat.completions.create.return_value = response
    monkeypatch.setattr(ai, "OpenAI", MagicMock(return_value=mocked))
    result = ai.generate_private_fundamental_brief(
        [{"pair": "GBPUSD"}],
        [
            {
                "title": "Evidence",
                "sha256": "0" * 64,
                "content_scope": "attributed_headline_only",
                "url": "https://www.federalreserve.gov/newsevents/fixture",
                "source": "Federal Reserve",
                "published_at": "2026-10-01",
                "retrieved_at": "2026-10-01T12:00:00Z",
            }
        ],
        {},
        as_of="2026-10-01T13:00:00Z",
    )
    mocked.chat.completions.create.assert_called_once()
    assert result["status"] == "UNAVAILABLE"
    assert result["pairs"] == []
    assert "thesis" not in json.dumps(result)


def test_private_ai_empty_response_fails_closed_with_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.ai import client as ai

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-only")
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""), finish_reason="length")],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=3000),
    )
    mocked = MagicMock()
    mocked.models.list.return_value.data = [SimpleNamespace(id="deepseek-v4-pro")]
    mocked.chat.completions.create.return_value = response
    monkeypatch.setattr(ai, "OpenAI", MagicMock(return_value=mocked))
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}],
        [
            {
                "title": "Evidence",
                "sha256": "0" * 64,
                "content_scope": "attributed_headline_only",
                "url": "https://www.federalreserve.gov/newsevents/fixture",
                "source": "Federal Reserve",
                "published_at": "2026-10-01",
                "retrieved_at": "2026-10-01T12:00:00Z",
            }
        ],
        {},
        as_of="2026-10-01T13:00:00Z",
    )
    assert result["status"] == "UNAVAILABLE"
    assert result["pairs"] == []
    assert result["finish_reason"] == "length"
    assert result["usage"]["output_tokens"] == 3000
    assert result["output_char_count"] == 0
    json.dumps(result, allow_nan=False)


def test_private_ai_unavailable_requested_model_does_not_call_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.ai import client as ai

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-only")
    monkeypatch.setenv("PRIVATE_FX_AI_MODEL", "unavailable-model")
    mocked = MagicMock()
    mocked.models.list.return_value.data = [SimpleNamespace(id="deepseek-v4-pro")]
    monkeypatch.setattr(ai, "OpenAI", MagicMock(return_value=mocked))
    result = ai.generate_private_fundamental_brief(
        [{"pair": "EURUSD"}],
        [
            {
                "title": "Evidence",
                "sha256": "0" * 64,
                "content_scope": "attributed_headline_only",
                "url": "https://www.federalreserve.gov/newsevents/fixture",
                "source": "Federal Reserve",
                "published_at": "2026-10-01",
                "retrieved_at": "2026-10-01T12:00:00Z",
            }
        ],
        {},
        as_of="2026-10-01T13:00:00Z",
    )
    mocked.models.list.assert_called_once()
    assert result["status"] == "UNAVAILABLE"
    mocked.chat.completions.create.assert_not_called()
