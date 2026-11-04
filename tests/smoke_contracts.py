"""Vérifie, en lecture seule, que les modules des coéquipières respectent le contrat gelé."""
import inspect

from app.hashing import canonical_json, sha256_bytes as sha256
from app.input_checks import check_inputs
from app.registry import get_artifact, record_artifact
from app.validation import validate

print("check_inputs   ", inspect.signature(check_inputs))
print("validate       ", inspect.signature(validate))
print("record_artifact", inspect.signature(record_artifact))
print("get_artifact   ", inspect.signature(get_artifact))

# 1. JSON canonique : clés triées, sans espaces, UTF-8, ensure_ascii=False
c = canonical_json({"b": 1, "a": "é"})
c = c if isinstance(c, bytes) else c.encode("utf-8")
assert c == '{"a":"é","b":1}'.encode("utf-8"), c

# 2. SHA-256 : valeur de référence de "abc"
h = sha256(b"abc")
h = h if isinstance(h, str) else h.hexdigest()
assert h == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", h

# 3. check_inputs : clés attendues
r = check_inputs(b"signal\n0.1\n0.2\n", "Compte rendu fictif".encode("utf-8"))
assert set(r) >= {"valid", "reasons", "report_clean"}, r

# 4. validate : statuts exacts
v = validate({"label": "x", "confidence": 0.9, "model_name": "m", "model_version": "v"},
             {"valid": True, "reasons": []})
assert v["status"] in {"ACCEPTED", "REVIEW_REQUIRED", "REJECTED"}, v
print("OK : contrats respectés")

