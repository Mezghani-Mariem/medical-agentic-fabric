"""Quantification int8 (post-entraînement) puis découpe en partitions P1/P2/P3.

Usage (depuis la racine du projet) :
    python -m models.quantize_partition --groups 1,1,1 --plan fpga,fpga,arm
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from models.engine import (MODELS_DIR, PART_DIR, PartitionedModel, count_macs,
                           quantize_multiplier, weights_digest)

ART = MODELS_DIR / "artifacts"


def _pct(a: np.ndarray, p: float = 99.9) -> float:
    return float(np.percentile(np.abs(a), p)) or 1.0


def quantize_network(d) -> tuple[list[dict], float, float]:
    Ws = [d[f"W{i}"] for i in range(1, 10) if f"W{i}" in d.files]
    bs = [d[f"b{i}"] for i in range(1, len(Ws) + 1)]
    a = d["X_calib"]
    s_in = _pct(a) / 127.0
    s_prev = s_in
    layers, logit_scale = [], None
    for i, (W, b) in enumerate(zip(Ws, bs)):
        last = i == len(Ws) - 1
        z = a @ W + b
        s_w = float(np.abs(W).max()) / 127.0
        s_acc = s_prev * s_w
        W_q = np.clip(np.round(W / s_w), -127, 127).astype(np.int8)
        b_q = np.round(b / s_acc).astype(np.int32)
        if last:
            layers.append({"W": W_q, "b": b_q, "m0": 0, "shift": 0, "relu": False, "last": True})
            logit_scale = s_acc
        else:
            a = np.maximum(z, 0.0)
            s_out = _pct(a) / 127.0
            m0, shift = quantize_multiplier(s_acc / s_out)
            layers.append({"W": W_q, "b": b_q, "m0": m0, "shift": shift, "relu": True, "last": False})
            s_prev = s_out
    return layers, s_in, logit_scale


def save_partition(path: Path, layers: list[dict]):
    arrays = {}
    for j, L in enumerate(layers):
        arrays[f"L{j}_W"] = L["W"]
        arrays[f"L{j}_b"] = L["b"]
        arrays[f"L{j}_m0"] = np.array(L["m0"], dtype=np.int64)
        arrays[f"L{j}_shift"] = np.array(L["shift"], dtype=np.int64)
        arrays[f"L{j}_relu"] = np.array(L["relu"])
        arrays[f"L{j}_last"] = np.array(L["last"])
    np.savez(path, **arrays)


def write_hls_header(path: Path, pname: str, layers: list[dict]):
    """En-tête C des poids int8 : point de départ pour Vitis HLS / hls4ml."""
    out = ["#pragma once", "#include <stdint.h>", ""]
    for j, L in enumerate(layers):
        i, o = L["W"].shape
        out.append(f"// {pname} couche {j} : {i} -> {o}, m0={L['m0']}, shift={L['shift']}")
        out.append(f"static const int8_t {pname}_l{j}_W[{i}][{o}] = {{")
        for row in L["W"]:
            out.append("  {" + ", ".join(str(int(v)) for v in row) + "},")
        out.append("};")
        out.append(f"static const int32_t {pname}_l{j}_b[{o}] = {{"
                   + ", ".join(str(int(v)) for v in L["b"]) + "};")
        out.append(f"#define {pname.upper()}_L{j}_M0 {int(L['m0'])}")
        out.append(f"#define {pname.upper()}_L{j}_SHIFT {int(L['shift'])}")
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default="1,1,1", help="nombre de couches par partition")
    ap.add_argument("--plan", default="fpga,fpga,arm", help="placement par défaut des partitions")
    args = ap.parse_args()

    d = np.load(ART / "float_model.npz", allow_pickle=False)
    labels = [str(x) for x in d["labels"]]
    layers, s_in, logit_scale = quantize_network(d)
    groups = [int(g) for g in args.groups.split(",")]
    plan = [x.strip() for x in args.plan.split(",")]
    assert sum(groups) == len(layers), f"--groups doit totaliser {len(layers)} couches"
    assert len(plan) == len(groups), "--plan : une valeur par partition"

    PART_DIR.mkdir(parents=True, exist_ok=True)
    (PART_DIR / "hls").mkdir(exist_ok=True)
    parts, k = [], 0
    for idx, g in enumerate(groups, start=1):
        sub = layers[k:k + g]
        k += g
        name = f"p{idx}"
        save_partition(PART_DIR / f"{name}.npz", sub)
        write_hls_header(PART_DIR / "hls" / f"{name}_weights.h", name, sub)
        parts.append({
            "name": name, "file": f"{name}.npz", "device": plan[idx - 1],
            "in_dim": int(sub[0]["W"].shape[0]), "out_dim": int(sub[-1]["W"].shape[1]),
            "macs": count_macs(sub),
            "bytes_int8": int(sum(L["W"].size + 4 * L["b"].size for L in sub)),
        })

    digest = weights_digest(layers)
    manifest = {
        "model_name": "ecg_mlp_int8_partitioned",
        "model_version": f"v2-int8-p{len(groups)}-{digest[:8]}",
        "labels": labels, "segment_len": int(layers[0]["W"].shape[0]),
        "input_scale": s_in, "logit_scale": logit_scale,
        "weights_sha256": digest, "partitions": parts,
    }
    (PART_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # ---- Contrôle : précision float vs int8, taille ----
    Xte, yte = d["X_test"], d["y_test"]
    model = PartitionedModel(PART_DIR)
    pred = np.array([labels.index(model.infer(x)["label"]) for x in Xte])
    int8_acc = float((pred == yte).mean())
    float_acc = float(d["float_acc"])
    n_params = sum(L["W"].size + L["b"].size for L in layers)
    print(f"Modèle : {manifest['model_version']}")
    print(f"Paramètres : {n_params}   float32 ≈ {4 * n_params} o   int8 ≈ {sum(p['bytes_int8'] for p in parts)} o")
    print(f"Précision float : {float_acc:.4f}   int8 : {int8_acc:.4f}   écart : {float_acc - int8_acc:+.4f}")
    for p in parts:
        print(f"  {p['name']}: {p['in_dim']}->{p['out_dim']}  {p['macs']} MAC  défaut={p['device']}")


if __name__ == "__main__":
    main()