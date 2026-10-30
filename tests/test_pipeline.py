from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import registry
from app.main import app
from app.orchestrator import PROJECT_ROOT

FIX = Path(__file__).resolve().parent / "fixtures"
client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    """Le registre MOCK de test va dans un dossier temporaire : data/mock_ledger.json reste intact."""
    monkeypatch.setattr(registry, "MOCK_LEDGER_PATH", tmp_path / "mock_ledger.json")


TYPES = ["raw_ecg", "raw_report", "processed", "features", "prediction", "validation", "explanation", "final"]


def _analyze(ecg="ecg_demo_valid_A.csv"):
    return client.post("/api/analyze", files={
        "ecg": (ecg, (FIX / ecg).read_bytes(), "text/csv"),
        "report": ("report.txt", (FIX / "report_demo.txt").read_bytes(), "text/plain")})


def test_valid_csv_returns_contract_schema():
    r = _analyze()
    assert r.status_code == 200
    j = r.json()
    assert set(j) == {"case_id", "prediction", "validation", "explanation", "artifacts", "ledger_mode"}
    assert set(j["prediction"]) == {"label", "confidence", "model_name", "model_version"}
    assert j["validation"]["status"] in {"ACCEPTED", "REVIEW_REQUIRED", "REJECTED"}
    assert [a["type"] for a in j["artifacts"]] == TYPES


def test_parent_chain_is_consistent():
    j = _analyze().json()
    by_id = {a["artifact_id"]: a for a in j["artifacts"]}
    parents = {a["type"]: (by_id[a["parent_id"]]["type"] if a["parent_id"] else None) for a in j["artifacts"]}
    assert parents == {"raw_ecg": None, "raw_report": "raw_ecg", "processed": "raw_report",
                       "features": "processed", "prediction": "features", "validation": "prediction",
                       "explanation": "validation", "final": "explanation"}
    # même règle que tests/test_frontend_contract.py : chaîne linéaire dans l'ordre des artefacts
    previous = None
    for a in j["artifacts"]:
        assert a["parent_id"] == previous
        previous = a["artifact_id"]


def test_broken_csv_gives_422_and_writes_nothing():
    before = len(list((PROJECT_ROOT / "data" / "cases").glob("*")))
    r = _analyze("ecg_demo_invalid.csv")
    assert r.status_code == 422 and r.json()["reasons"]
    assert len(list((PROJECT_ROOT / "data" / "cases").glob("*"))) == before


def test_verify_valid_then_modified():
    j = _analyze().json()
    cid = j["case_id"]
    assert client.post(f"/api/cases/{cid}/verify").json()["overall_status"] == "VALID"
    target = PROJECT_ROOT / j["artifacts"][0]["storage_ref"]
    target.write_bytes(target.read_bytes() + b"\n999")
    v = client.post(f"/api/cases/{cid}/verify").json()
    assert v["overall_status"] == "MODIFIED"
    assert any(c["status"] == "MODIFIED" for c in v["checks"])


def test_missing_file_is_reported():
    j = _analyze().json()
    (PROJECT_ROOT / j["artifacts"][2]["storage_ref"]).unlink()
    assert client.post(f"/api/cases/{j['case_id']}/verify").json()["overall_status"] == "MISSING"


def test_get_case_and_history_and_bad_id():
    j = _analyze().json()
    assert client.get(f"/api/cases/{j['case_id']}").json()["case_id"] == j["case_id"]
    assert len(client.get(f"/api/cases/{j['case_id']}/history").json()["events"]) == 8
    assert client.get("/api/cases/../../etc/passwd").status_code in (404, 405)
    assert client.get("/api/cases/not-a-uuid").status_code == 404


def test_model_endpoint_is_additive():
    j = client.get("/api/model").json()
    assert j["mode"] == "int8-partitioned" and len(j["partitions"]) == 3