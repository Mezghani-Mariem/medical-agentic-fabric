r"""Verifie un ECG reel : sorties du moteur de l'API -> vecteur de test pour le circuit HLS.

Usage (depuis hls_work) : python ..\models\fpga\verify_case.py <fichier ECG csv> [--out case]
Ecrit <out>\tb_vectors.h (1 vecteur) et copie tb_mlp.cpp dans <out>. N'ecrase pas models\fpga\tb_vectors.h.
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from models.engine import PART_DIR, PartitionedModel, run_layers  # noqa: E402
from app.preprocess import preprocess  # noqa: E402
from app.predict import predict_with_trace  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("ecg")
ap.add_argument("--out", default="case")
args = ap.parse_args()

raw = Path(args.ecg).read_bytes()
processed, quality = preprocess(raw)
api_pred, _ = predict_with_trace(processed["features"])

model = PartitionedModel(PART_DIR, "arm,arm,arm")
seg = np.asarray(processed["features"]["segment"], dtype=np.float64).reshape(1, -1)
x = np.clip(np.round(seg / model.input_scale), -128, 127).astype(np.int8)
h1 = run_layers(model.partitions[0]["layers"], x)
h2 = run_layers(model.partitions[1]["layers"], h1)
z = run_layers(model.partitions[2]["layers"], h2)

logits = z[0].astype(np.float64) * model.logit_scale
p = np.exp(logits - logits.max())
p /= p.sum()
k = int(np.argmax(p))
label_from_logits = model.labels[k]


def table(name, ctype, arr):
    rows = ",\n".join("  {" + ", ".join(str(int(v)) for v in r) + "}" for r in arr)
    return f"static const {ctype} {name}[TB_N][{len(arr[0])}] = {{\n{rows}\n}};\n"


out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
(out / "tb_vectors.h").write_text(
    "#pragma once\n#include <stdint.h>\n#define TB_N 1\n"
    + table("TB_X", "int8_t", x) + table("TB_P1", "int8_t", h1)
    + table("TB_P2", "int8_t", h2) + table("TB_Z", "int32_t", z),
    encoding="utf-8")
shutil.copy(ROOT / "models" / "fpga" / "tb_mlp.cpp", out / "tb_mlp.cpp")

print("qualite signal valide :", quality.get("valid"))
print("API      : label =", api_pred["label"], " confiance =", api_pred["confidence"], " version =", api_pred["model_version"])
print("logits int32 attendus (sortie du circuit) :", [int(v) for v in z[0]])
print("label recalcule depuis ces logits :", label_from_logits, " confiance =", round(float(p[k]), 4))
print("coherent avec l'API :", label_from_logits == api_pred["label"] and round(float(p[k]), 4) == api_pred["confidence"])
print("fichiers ecrits dans", out.resolve())