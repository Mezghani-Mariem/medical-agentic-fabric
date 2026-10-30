"""Compare tous les plans ARM/FPGA : équivalence des sorties, latence mesurée, latence FPGA estimée.

Usage (depuis la racine du projet) : python -m models.benchmark [--runs 200]
Écrit models/artifacts/benchmark.md
"""
from __future__ import annotations

import argparse
import itertools
import time

import numpy as np

from models.engine import MODELS_DIR, PART_DIR, PartitionedModel

OUT = MODELS_DIR / "artifacts" / "benchmark.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=200)
    args = ap.parse_args()

    d = np.load(MODELS_DIR / "artifacts" / "float_model.npz", allow_pickle=False)
    X = d["X_test"][: args.runs]
    base = PartitionedModel(PART_DIR, "arm,arm,arm")
    n = len(base.partitions)

    ref = [base.infer(x) for x in X]
    lines = [
        f"# Benchmark des plans — modèle {base.version}",
        "",
        f"{len(X)} inférences par plan. Latence mesurée sur la machine hôte ; "
        "latence FPGA = estimation (MAC / (16 PE × 100 MHz)), pas une mesure.",
        "",
        "| Plan | Sorties identiques à ARM seul | Latence hôte (ms/inférence) | Latence FPGA estimée des partitions FPGA (µs) |",
        "| --- | --- | --- | --- |",
    ]
    for plan in itertools.product(("arm", "fpga"), repeat=n):
        m = PartitionedModel(PART_DIR, ",".join(plan))
        t0 = time.perf_counter()
        outs = [m.infer(x) for x in X]
        ms = (time.perf_counter() - t0) * 1000.0 / len(X)
        same = all(o["label"] == r["label"] and o["confidence"] == r["confidence"] for o, r in zip(outs, ref))
        est = sum(t["fpga_est_ms"] for t in outs[0]["trace"] if t["fpga_est_ms"] is not None) * 1000.0
        lines.append(f"| {'/'.join(plan)} | {'oui' if same else 'NON'} | {ms:.3f} | {est:.2f} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\nÉcrit :", OUT)


if __name__ == "__main__":
    main()