import hashlib
import json

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_canonical(obj) -> str:
    return sha256_bytes(canonical_json(obj).encode("utf-8"))