import json
import os
import subprocess
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

# =====================================================================
# PARTIE FABRIC (Utilise la CLI dans WSL)
# =====================================================================

# Chemins vers tes outils Fabric (adaptés à ton installation WSL)
FABRIC_BIN = os.path.expanduser("~/hyperledger/fabric-samples/bin")
TEST_NETWORK = os.path.expanduser("~/hyperledger/fabric-samples/test-network")
ORG1_ADMIN = os.path.join(TEST_NETWORK, "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp")
ORG1_TLS = os.path.join(TEST_NETWORK, "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt")
ORDERER_TLS = os.path.join(TEST_NETWORK, "organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem")

def _get_env():
    """Prépare l'environnement pour que la CLI 'peer' sache qui elle est."""
    env = os.environ.copy()
    env["PATH"] = f"{FABRIC_BIN}:" + env.get("PATH", "")
    env["FABRIC_CFG_PATH"] = os.path.join(FABRIC_BIN, "../config")
    env["CORE_PEER_TLS_ENABLED"] = "true"
    env["CORE_PEER_LOCALMSPID"] = "Org1MSP"
    env["CORE_PEER_TLS_ROOTCERT_FILE"] = ORG1_TLS
    env["CORE_PEER_MSPCONFIGPATH"] = ORG1_ADMIN
    env["CORE_PEER_ADDRESS"] = "localhost:7051"
    return env

def _record_fabric(rec: dict) -> dict:
    """Envoie la transaction au vrai réseau Fabric via la CLI."""
    rec_json = json.dumps(rec)
    args = [
        "peer", "chaincode", "invoke",
        "-o", "localhost:7050", "--ordererTLSHostnameOverride", "orderer.example.com",
        "-C", "mychannel", "-n", "artifact",
        "--tls", "--cafile", ORDERER_TLS,
        "-c", json.dumps({"function": "createArtifact", "Args": [rec_json]})
    ]
    
    # Exécution de la commande Fabric
    result = subprocess.run(args, env=_get_env(), capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Erreur Fabric (create) : {result.stderr}")
        
    # On génère un ID basé sur l'artefact pour prouver que ça vient de Fabric
    return {"tx_id": f"FABRIC-TX-{rec['artifact_id'][:8]}", "ledger_mode": "FABRIC"}

def _get_fabric(artifact_id: str) -> dict | None:
    """Lit un artefact depuis le vrai réseau Fabric."""
    # Utilisation de guillemets simples pour éviter les conflits avec Fabric
    args = [
        "peer", "chaincode", "query",
        "-C", "mychannel", "-n", "artifact",
        "-c", f'{{"function":"readArtifact","Args":["{artifact_id}"]}}'
    ]
    result = subprocess.run(args, env=_get_env(), capture_output=True, text=True)
    
    if result.returncode != 0:
        return None
        
    try:
        # La réponse de Fabric peut contenir des caractères d'échappement ou des sauts de ligne
        raw_output = result.stdout.strip()
        if not raw_output:
            return None
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return None