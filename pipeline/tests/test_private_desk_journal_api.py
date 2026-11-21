"""Decision history is private, updates are CSRF protected and CSVs retain abstentions."""

import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.private_desk import api, journal
from tests.test_private_desk_journal import NOW, make_report


def client(directory: Path) -> tuple[TestClient, str]:
    app = api.create_app(directory)
    connection = TestClient(app, raise_server_exceptions=False)
    password = (directory / "access.txt").read_text(encoding="utf-8").splitlines()[1]
    response = connection.post("/api/login", json={"password": password})
    assert response.status_code == 200
    return connection, response.json()["csrf_token"]


@pytest.mark.parametrize("endpoint", ["/api/journal", "/api/journal.csv", "/api/journal/update"])
def test_all_history_endpoints_require_authentication(tmp_path: Path, endpoint: str) -> None:
    connection = TestClient(api.create_app(tmp_path))
    response = (
        connection.post(endpoint) if endpoint.endswith("update") else connection.get(endpoint)
    )
    assert response.status_code == 401


def test_get_is_read_only_and_update_requires_csrf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_report(tmp_path)
    connection, token = client(tmp_path)
    assert connection.get("/api/journal").json()["status"] == "EMPTY"
    assert not (tmp_path / "journal").exists()
    assert connection.post("/api/journal/update").status_code == 403
    original = path.read_bytes()
    native = journal.sync_journal
    monkeypatch.setattr(
        api, "sync_journal", lambda directory, saved: native(directory, saved, now=NOW)
    )
    response = connection.post("/api/journal/update", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    assert response.json()["decision_count"] == 8
    assert response.json()["outcome_status_counts"] == {"PENDING": 8}
    assert path.read_bytes() == original
    before = {p: p.read_bytes() for p in (tmp_path / "journal").rglob("*.json")}
    assert connection.get("/api/journal").status_code == 200
    assert all(p.read_bytes() == raw for p, raw in before.items())
    rows = list(csv.DictReader(io.StringIO(connection.get("/api/journal.csv").text)))
    assert len(rows) == 8
    assert {r["decision"] for r in rows} == {"ABSTAIN"}
    assert {r["execution_state"] for r in rows} == {"NOT_RECORDED"}
    assert all(not r["net_r"] for r in rows)


@pytest.mark.parametrize("endpoint", ["/api/journal", "/api/journal.csv", "/api/journal/update"])
def test_damaged_history_fails_closed(tmp_path: Path, endpoint: str) -> None:
    path = make_report(tmp_path)
    journal.sync_journal(tmp_path, path, now=NOW)
    event = next((tmp_path / "journal" / "decisions").glob("*.json"))
    event.write_bytes(b"broken")
    connection, token = client(tmp_path)
    response = (
        connection.post(endpoint, headers={"X-CSRF-Token": token})
        if endpoint.endswith("update")
        else connection.get(endpoint)
    )
    assert response.status_code == 503


def test_csv_formula_pair_clock_is_escaped(tmp_path: Path) -> None:
    path = make_report(tmp_path)
    # Hash-bound report metadata is untrusted content even inside an authenticated export.
    import json

    value = json.loads(path.read_bytes())
    value["pair_reports"][0]["candidate"]["as_of"] = "=unsafe"
    path.write_text(json.dumps(value), encoding="utf-8")
    journal.sync_journal(tmp_path, path, now=NOW)
    connection, _ = client(tmp_path)
    rows = list(csv.DictReader(io.StringIO(connection.get("/api/journal.csv").text)))
    assert next(row for row in rows if row["pair"] == "EURUSD")["as_of"] == "'=unsafe"
