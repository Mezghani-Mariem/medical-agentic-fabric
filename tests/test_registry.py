import hashlib
import json
import os
import uuid
from pathlib import Path

import pytest

from app.hashing import canonical_json, sha256_bytes, sha256_canonical
from app import registry


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    p = tmp_path / "mock_ledger.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(registry, "MOCK_LEDGER_PATH", p)
    monkeypatch.setattr(registry, "LEDGER_MODE", "mock")
    yield p


def make_record(**over):
    base = {
        "artifact_id": str(uuid.uuid4()),
        "case_id": str(uuid.uuid4()),
        "type": "raw_ecg",
        "sha256": "0" * 64,
        "created_at": "2026-10-21T10:00:00+00:00",
        "version": "v1",
        "parent_id": None,
        "storage_ref": "data/cases/x/y.bin",
        "created_by": "orchestrator",
    }
    base.update(over)
    return base


def test_hashing_is_deterministic():
    a = {"b": 2, "a": "é", "n": [1, 2, 3]}
    b = {"n": [1, 2, 3], "a": "é", "b": 2}
    assert canonical_json(a) == canonical_json(b)
    assert sha256_canonical(a) == sha256_canonical(b)


def test_raw_bytes_sha():
    data = b"signal\n1\n2\n3\n"
    assert sha256_bytes(data) == hashlib.sha256(data).hexdigest()


def test_record_and_read_roundtrip():
    rec = make_record(sha256=sha256_bytes(b"hello"))
    out = registry.record_artifact(rec)
    assert out["ledger_mode"] == "MOCK"
    assert out["tx_id"].startswith("MOCK-")

    got = registry.get_artifact(rec["artifact_id"])
    assert got is not None
    assert got["sha256"] == rec["sha256"]


def test_duplicate_rejected():
    rec = make_record()
    registry.record_artifact(rec)
    with pytest.raises(ValueError, match="déjà enregistré"):
        registry.record_artifact(rec)


def test_get_unknown_returns_none():
    assert registry.get_artifact(str(uuid.uuid4())) is None


def test_tamper_detection():
    original = b"ECG original bytes"
    rec = make_record(sha256=sha256_bytes(original))
    registry.record_artifact(rec)

    stored = registry.get_artifact(rec["artifact_id"])
    tampered = b"ECG modified bytes"
    assert sha256_bytes(tampered) != stored["sha256"]


def test_validation_rejects_missing_keys():
    rec = make_record()
    del rec["storage_ref"]
    with pytest.raises(ValueError):
        registry.record_artifact(rec)


def test_validation_rejects_bad_type():
    rec = make_record(type="not_a_type")
    with pytest.raises(ValueError):
        registry.record_artifact(rec)