"""Orchestration du pipeline : 8 artefacts, chaîne parent -> enfant, vérification d'intégrité.

Appelle (sans les modifier) :
  app.input_checks.check_inputs   (Mezghani)
  app.validation.validate         (Mezghani)
  app.hashing.canonical_json/sha256_bytes, app.registry.record_artifact/get_artifact (Rimeh)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.hashing import canonical_json, sha256_bytes as sha256
from app.input_checks import check_inputs
from app.predict import predict_with_trace
from app.preprocess import PipelineError, preprocess
from app.registry import get_artifact, record_artifact
from app.validation import validate

log = logging.getLogger("orchestrator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "cases"


# ------------------------------------------------------------- utilitaires --
def _canon(obj) -> bytes:
    out = canonical_json(obj)
    return out if isinstance(out, bytes) else out.encode("utf-8")


def _sha(data: bytes) -> str:
    h = sha256(data)
    return h if isinstance(h, str) else h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_dir(case_id: str) -> Path:
    try:
        uuid.UUID(case_id)  # empêche les chemins du type ../..
    except ValueError:
        raise PipelineError(404, "Cas introuvable")
    return DATA_DIR / case_id


def _store(case_id: str, art_type: str, content: bytes, parent_id: str | None) -> dict:
    """Écrit l'artefact hors chaîne puis enregistre son empreinte dans le registre."""
    artifact_id = str(uuid.uuid4())
    sha = _sha(content)
    storage_ref = f"data/cases/{case_id}/{artifact_id}.bin"
    path = PROJECT_ROOT / storage_ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    record = {
        "artifact_id": artifact_id, "case_id": case_id, "type": art_type, "sha256": sha,
        "created_at": _now(), "version": "v1", "parent_id": parent_id,
        "storage_ref": storage_ref, "created_by": "orchestrator",
    }
    try:
        receipt = record_artifact(record)
    except Exception as e:  # registre indisponible, doublon, etc.
        log.exception("record_artifact a échoué")
        raise PipelineError(500, "Registre indisponible", [str(e)])
    return {
        "artifact_id": artifact_id, "type": art_type, "sha256": sha, "parent_id": parent_id,
        "storage_ref": storage_ref, "tx_id": receipt["tx_id"],
        "_ledger_mode": receipt.get("ledger_mode", "MOCK"),
    }


def _public(a: dict) -> dict:
    return {k: v for k, v in a.items() if not k.startswith("_")}


def _integrity_ok(artifacts: list[dict]) -> bool:
    """Relit chaque fichier stocké et compare avec l'empreinte du registre."""
    for a in artifacts:
        entry = get_artifact(a["artifact_id"])
        path = PROJECT_ROOT / a["storage_ref"]
        if entry is None or not path.exists():
            return False
        if _sha(path.read_bytes()) != entry["sha256"]:
            return False
    return True


def _device_summary(trace: list[dict]) -> str:
    if not trace:
        return "heuristique de démonstration (aucun modèle chargé)"
    parts = ", ".join(f"{t['partition'].upper()}:{t['device']}" for t in trace)
    sim = any(t["device"] == "fpga-sim" for t in trace)
    return f"modèle int8 en {len(trace)} partitions ({parts})" + (" ; FPGA simulé, pas de carte" if sim else "")


# --------------------------------------------------------------- pipeline --
def run_case(ecg_bytes: bytes, report_bytes: bytes) -> dict:
    # 1. contrôle des entrées (Mezghani) : rien n'est écrit avant d'être sûr
    checked = check_inputs(ecg_bytes, report_bytes)
    if not checked["valid"]:
        raise PipelineError(422, "Entrées invalides", list(checked["reasons"]))

    # 2. calculs en mémoire (aucune écriture si ça échoue)
    processed, quality = preprocess(ecg_bytes)
    features = processed.pop("features")
    prediction, trace = predict_with_trace(features)

    case_id = str(uuid.uuid4())
    artifacts: list[dict] = []

    # 3. artefacts 1 à 5
    raw_ecg = _store(case_id, "raw_ecg", ecg_bytes, None)
    raw_report = _store(case_id, "raw_report", report_bytes, raw_ecg["artifact_id"])
    art_processed = _store(case_id, "processed", _canon(processed), raw_report["artifact_id"])
    art_features = _store(case_id, "features", _canon(features), art_processed["artifact_id"])
    pred_doc = dict(prediction, case_id=case_id, input_artifact_id=art_features["artifact_id"],
                    analyzed_at=_now())
    art_pred = _store(case_id, "prediction", _canon(pred_doc), art_features["artifact_id"])
    artifacts += [raw_ecg, raw_report, art_processed, art_features, art_pred]

    # 4. validation (Mezghani) avec une vraie vérification d'intégrité
    validation = validate(prediction, quality, artifacts_ok=len(artifacts) == 5,
                          integrity_ok=_integrity_ok(artifacts), report_text=checked["report_clean"])
    art_val = _store(case_id, "validation", _canon(validation), art_pred["artifact_id"])

    # 5. explication et résultat final
    explanation = (
        f"Classe indicative du prototype : {prediction['label']} "
        f"(confiance {prediction['confidence']:.0%}). Statut de validation : {validation['status']}. "
        f"Inférence : {_device_summary(trace)}. Prototype pédagogique, non diagnostique."
    )
    art_expl = _store(case_id, "explanation",
                      _canon({"case_id": case_id, "text": explanation}),
                      art_val["artifact_id"])
    final_doc = {
        "case_id": case_id, "label": prediction["label"], "confidence": prediction["confidence"],
        "validation_status": validation["status"], "reasons": list(validation["reasons"]),
        "review_required": validation["status"] != "ACCEPTED",
    }
    art_final = _store(case_id, "final", _canon(final_doc), art_expl["artifact_id"])
    artifacts += [art_val, art_expl, art_final]

    response = {
        "case_id": case_id, "prediction": prediction,
        "validation": {"status": validation["status"], "reasons": list(validation["reasons"])},
        "explanation": explanation,
        "artifacts": [_public(a) for a in artifacts],
        "ledger_mode": art_final["_ledger_mode"],
    }
    # index du cas (hors artefacts, non haché) pour GET /cases/{id}
    (DATA_DIR / case_id / "case.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return response


# --------------------------------------------------------- lecture / verify --
def get_case(case_id: str) -> dict:
    path = _case_dir(case_id) / "case.json"
    if not path.exists():
        raise PipelineError(404, "Cas introuvable")
    return json.loads(path.read_text(encoding="utf-8"))


def get_history(case_id: str) -> dict:
    """Enveloppe attendue par le frontend : {case_id, events:[{timestamp, stage, status, details}]}."""
    case = get_case(case_id)
    events = []
    for a in case["artifacts"]:
        entry = get_artifact(a["artifact_id"])
        when = (entry or {}).get("created_at") or _now()
        events.append({
            "timestamp": when,
            "stage": a["type"],
            "status": "RECORDED" if entry else "UNVERIFIABLE",
            "details": f"sha256 {a['sha256'][:16]}… · tx {a['tx_id']} · registre {case['ledger_mode']}",
        })
    return {"case_id": case_id, "ledger_mode": case["ledger_mode"], "events": events}


def verify_case(case_id: str) -> dict:
    case = get_case(case_id)
    checks, statuses = [], []
    for a in case["artifacts"]:
        entry = get_artifact(a["artifact_id"])
        path = PROJECT_ROOT / a["storage_ref"]
        expected = entry["sha256"] if entry else None
        actual = _sha(path.read_bytes()) if path.exists() else None
        if entry is None:
            status = "UNVERIFIABLE"
        elif actual is None:
            status = "MISSING"
        elif actual != expected:
            status = "MODIFIED"
        else:
            status = "VALID"
        statuses.append(status)
        checks.append({"artifact_id": a["artifact_id"], "type": a["type"], "status": status,
                       "expected_sha256": expected, "actual_sha256": actual})
    for s in ("MODIFIED", "MISSING", "UNVERIFIABLE"):
        if s in statuses:
            overall = s
            break
    else:
        overall = "VALID"
    return {"case_id": case_id, "overall_status": overall, "checks": checks}