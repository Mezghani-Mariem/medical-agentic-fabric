"""Adaptateur registre : MOCK disque par défaut, FABRIC optionnel."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

LEDGER_MODE = os.getenv("FABRIC_MODE", "mock").lower()  # "mock" | "fabric"
MOCK_LEDGER_PATH = Path(os.getenv("MOCK_LEDGER_PATH", "data/mock_ledger.json"))

REQUIRED_KEYS = {
    "artifact_id", "case_id", "type", "sha256",
    "created_at", "version", "parent_id",
    "storage_ref", "created_by",
}
ALLOWED_TYPES = {
    "raw_ecg", "raw_report", "processed", "features",
    "prediction", "validation", "explanation", "final",
}

_lock = threading.Lock()

def _validate(record: dict) -> None:
    missing = REQUIRED_KEYS - record.keys()
    if missing:
        raise ValueError(f"Champs manquants : {sorted(missing)}")
    if record["type"] not in ALLOWED_TYPES:
        raise ValueError(f"type invalide : {record['type']}")
    sha = record["sha256"]
    if not (isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)):
        raise ValueError("sha256 doit être 64 hex minuscules")

def _load_mock() -> dict:
    if not MOCK_LEDGER_PATH.exists():
        return {}
    with MOCK_LEDGER_PATH.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def _save_mock(data: dict) -> None:
    MOCK_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MOCK_LEDGER_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, MOCK_LEDGER_PATH)

def _mock_tx_id(artifact_id: str) -> str:
    return f"MOCK-{uuid.uuid4().hex[:16]}-{artifact_id[:8]}"

def record_artifact(record: dict) -> dict:
    _validate(record)
    rec = dict(record)
    rec.setdefault("created_at", datetime.now(timezone.utc).isoformat())

    if LEDGER_MODE == "fabric":
        return _record_fabric(rec)

    with _lock:
        data = _load_mock()
        if rec["artifact_id"] in data:
            raise ValueError(f"artifact_id déjà enregistré : {rec['artifact_id']}")
        tx_id = _mock_tx_id(rec["artifact_id"])
        data[rec["artifact_id"]] = {**rec, "tx_id": tx_id}
        _save_mock(data)
    return {"tx_id": tx_id, "ledger_mode": "MOCK"}

def get_artifact(artifact_id: str) -> dict | None:
    if LEDGER_MODE == "fabric":
        return _get_fabric(artifact_id)
    with _lock:
        data = _load_mock()
        return data.get(artifact_id)

def _record_fabric(rec: dict) -> dict:
    raise NotImplementedError("Fabric non branché : fallback MOCK.")

def _get_fabric(artifact_id: str) -> dict | None:
    raise NotImplementedError("Fabric non branché : fallback MOCK.")