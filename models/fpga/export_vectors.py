"""Exporte des vecteurs de test pour le banc HLS : entrees int8 + sorties attendues de P1, P2 et P3.

Usage (racine du projet) : python models/fpga/export_vectors.py [--n 100]
Ecrit models/fpga/tb_vectors.h (tableaux C inclus par tb_mlp.cpp : aucun fichier a lire a l'execution).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from models.engine import PART_DIR, PartitionedModel, run_layers  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=100)
args = ap.parse_args()

model = PartitionedModel(PART_DIR, "arm,arm,arm")
d = np.load(ROOT / "models" / "artifacts" / "float_model.npz", allow_pickle=False)
rng = np.random.default_rng(0)

# 3/4 de vrais battements quantifies, 1/4 d'entrees aleatoires (cas extremes)
n_real = (args.n * 3) // 4
X = np.clip(np.round(d["X_test"][:n_real] / model.input_scale), -128, 127).astype(np.int8)
X = np.vstack([X, rng.integers(-128, 128, size=(args.n - n_real, 64), dtype=np.int8)])

H1, H2, Z = [], [], []
for x in X:
    a = x.reshape(1, -1)
    h1 = run_layers(model.partitions[0]["layers"], a)
    h2 = run_layers(model.partitions[1]["layers"], h1)
    z = run_layers(model.partitions[2]["layers"], h2)
    H1.append(h1[0]); H2.append(h2[0]); Z.append(z[0])


def table(name, ctype, arr):
    rows = ",\n".join("  {" + ", ".join(str(int(v)) for v in r) + "}" for r in arr)
    return f"static const {ctype} {name}[TB_N][{len(arr[0])}] = {{\n{rows}\n}};\n"


out = ROOT / "models" / "fpga" / "tb_vectors.h"
out.write_text(
    "#pragma once\n#include <stdint.h>\n"
    f"#define TB_N {len(X)}\n"
    + table("TB_X", "int8_t", X) + table("TB_P1", "int8_t", H1)
    + table("TB_P2", "int8_t", H2) + table("TB_Z", "int32_t", Z),
    encoding="utf-8")
print(f"{len(X)} vecteurs ecrits dans {out}")