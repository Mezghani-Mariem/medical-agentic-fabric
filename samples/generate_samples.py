"""Regenerate deterministic synthetic uploads and explicitly MOCK JSON fixtures.

This is test-data generation only. The fixture hashes identify dummy strings,
not uploaded files. No medical model, storage service, registry or Fabric exists
in this script. Do not integrate this generator into the backend pipeline.
"""

import hashlib
import json
import math
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]


def write_samples() -> None:
    samples = ROOT / "samples"
    # Draw a repeating synthetic P/QRS/T-shaped illustration, not patient data.
    values = []
    for index in range(720):
        phase = (index % 100) / 100
        gauss = lambda center, width: math.exp(-0.5 * ((phase - center) / width) ** 2)
        value = (0.10 * gauss(0.17, 0.035) - 0.15 * gauss(0.36, 0.012)
                 + 1.05 * gauss(0.40, 0.010) - 0.24 * gauss(0.44, 0.017)
                 + 0.24 * gauss(0.68, 0.065) + 0.015 * math.sin(index * 0.08))
        values.append(value)
    csv = "sample,signal\n" + "".join(f"{index},{value:.6f}\n" for index, value in enumerate(values))
    (samples / "ecg_valid.csv").write_text(csv, encoding="utf-8", newline="\n")
    (samples / "ecg_invalid.csv").write_text("signal\n0.12\ninvalide\nNaN\n", encoding="utf-8")
    (samples / "ecg_short.csv").write_text("signal\n0.1\n0.2\n0.1\n", encoding="utf-8")
    (samples / "report_valid.txt").write_text(
        "DONNÉES ENTIÈREMENT SYNTHÉTIQUES — AUCUNE IDENTITÉ RÉELLE\n"
        "Nom: Exemple-Démo\nPrénom: Patiente-Fictive\nPatient ID: SYNTHETIC-001\n"
        "Observation: signal généré pour une démonstration universitaire.\n"
        "Contexte: aucune interprétation clinique ni diagnostic attendu.\n", encoding="utf-8")
    (samples / "report_invalid.txt").write_bytes(b"Rapport synth\x00etique : contenu binaire interdit.\n")


def write_fixtures() -> None:
    case_id = str(uuid5(NAMESPACE_URL, "medtrace:mock:case"))
    artifact_types = ["raw_ecg", "raw_report", "processed", "features", "prediction", "validation", "explanation", "final"]
    artifacts, events, checks = [], [], []
    parent = None
    for kind in artifact_types:
        artifact_id = str(uuid5(NAMESPACE_URL, f"medtrace:mock:{kind}"))
        sha = hashlib.sha256(f"MOCK FIXTURE ONLY: {kind}".encode()).hexdigest()
        artifact = {"artifact_id": artifact_id, "type": kind, "sha256": sha, "parent_id": parent,
                    "storage_ref": f"data/cases/{case_id}/{artifact_id}.bin", "tx_id": f"MOCK-{artifact_id}"}
        artifacts.append(artifact)
        events.append({"timestamp": "2026-10-22T09:00:00Z", "stage": kind, "status": "MOCK",
                       "details": "Événement de démonstration simulé.", "artifact_id": artifact_id, "tx_id": artifact["tx_id"]})
        checks.append({"artifact_id": artifact_id, "status": "VALID", "expected_sha256": sha, "actual_sha256": sha})
        parent = artifact_id
    data = {"case_id": case_id,
            "prediction": {"label": "demo_class_A", "confidence": 0.91, "model_name": "mock_fixture_no_model", "model_version": "v1"},
            "validation": {"status": "ACCEPTED", "reasons": ["Cohérence texte/ECG non évaluée automatiquement"]},
            "explanation": "Réponse MOCK préétablie pour tester l’interface. Aucune inférence IA ni évaluation clinique n’a été exécutée.",
            "artifacts": artifacts, "ledger_mode": "MOCK"}
    fixtures = ROOT / "frontend/fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    for name, value in (("demo_case.json", data), ("demo_history.json", {"case_id": case_id, "events": events}),
                        ("demo_verify.json", {"case_id": case_id, "overall_status": "VALID", "checks": checks})):
        (fixtures / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Shared handoff location named explicitly in the integration guide.
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "api_example.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_samples()
    write_fixtures()
    print("Synthetic samples and MOCK fixtures generated.")
