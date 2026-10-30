"""Moteur d'inférence entier partitionné (P1 / P2 / P3). NumPy uniquement.

Chaque partition est exécutée par un "exécuteur" :
  - arm  : CPU (sur une carte ARM, ce même code tourne tel quel)
  - fpga : simulation bit à bit du circuit (mêmes entiers) + estimation de latence.
           Le mode FPGA_MODE=board est un point d'accroche pour une vraie carte.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from pathlib import Path

import numpy as np

log = logging.getLogger("engine")

MODELS_DIR = Path(__file__).resolve().parent
PART_DIR = MODELS_DIR / "partitions"
SEGMENT_LEN = 64
DEVICES = ("arm", "fpga")

# Hypothèses du modèle de latence FPGA (à adapter à ta carte)
FPGA_PE = 16        # nombre de MAC en parallèle
FPGA_MHZ = 100.0    # fréquence d'horloge en MHz


# --------------------------------------------------------------------------
# Segment d'entrée (utilisé à l'entraînement ET à l'inférence : même fonction)
# --------------------------------------------------------------------------
def to_segment(signal, n: int = SEGMENT_LEN) -> np.ndarray:
    """Rééchantillonne le signal sur n points puis le centre-réduit (z-score)."""
    x = np.asarray(signal, dtype=np.float64)
    if x.size == 0:
        return np.zeros(n)
    if x.size == 1:
        x = np.repeat(x, 2)
    xp = np.linspace(0.0, 1.0, num=x.size)
    xi = np.linspace(0.0, 1.0, num=n)
    seg = np.interp(xi, xp, x)
    sd = seg.std()
    if sd < 1e-9:
        return np.zeros(n)
    return (seg - seg.mean()) / sd


# --------------------------------------------------------------------------
# Arithmétique entière
# --------------------------------------------------------------------------
def quantize_multiplier(m: float) -> tuple[int, int]:
    """Représente m (> 0) par (m0, shift) : m ≈ m0 / 2**shift, m0 sur 31 bits."""
    if m <= 0:
        return 0, 0
    frac, exp = math.frexp(m)            # m = frac * 2**exp, frac dans [0.5, 1)
    m0 = int(round(frac * (1 << 31)))
    shift = 31 - exp
    if m0 == (1 << 31):                  # arrondi qui déborde
        m0 //= 2
        shift -= 1
    return m0, shift


def requantize(acc: np.ndarray, m0: int, shift: int) -> np.ndarray:
    prod = acc.astype(np.int64) * np.int64(m0)
    return (prod + (1 << (shift - 1))) >> shift


def run_layers(layers: list[dict], x: np.ndarray) -> np.ndarray:
    """x : int8 (batch, in). Retourne int8 (batch, out) ou int32 si dernière couche."""
    for L in layers:
        acc = x.astype(np.int32) @ L["W"].astype(np.int32) + L["b"].astype(np.int32)
        if L["last"]:
            return acc
        if L["relu"]:
            acc = np.maximum(acc, 0)
        x = np.clip(requantize(acc, int(L["m0"]), int(L["shift"])), -128, 127).astype(np.int8)
    return x


def count_macs(layers: list[dict]) -> int:
    return int(sum(L["W"].shape[0] * L["W"].shape[1] for L in layers))


def weights_digest(all_layers: list[dict]) -> str:
    """Empreinte SHA-256 déterministe des poids quantifiés (traçabilité du modèle)."""
    h = hashlib.sha256()
    for L in all_layers:
        h.update(np.ascontiguousarray(L["W"], dtype=np.int8).tobytes())
        h.update(np.ascontiguousarray(L["b"], dtype=np.int32).tobytes())
        h.update(f"{int(L['m0'])}:{int(L['shift'])}:{int(L['relu'])}:{int(L['last'])}".encode())
    return h.hexdigest()


# --------------------------------------------------------------------------
# Chargement d'une partition
# --------------------------------------------------------------------------
def load_layers(npz_path: Path) -> list[dict]:
    d = np.load(npz_path, allow_pickle=False)
    n = len({k.split("_")[0] for k in d.files if k.startswith("L")})
    layers = []
    for j in range(n):
        layers.append({
            "W": d[f"L{j}_W"], "b": d[f"L{j}_b"],
            "m0": int(d[f"L{j}_m0"]), "shift": int(d[f"L{j}_shift"]),
            "relu": bool(d[f"L{j}_relu"]), "last": bool(d[f"L{j}_last"]),
        })
    return layers


# --------------------------------------------------------------------------
# Exécuteurs
# --------------------------------------------------------------------------
class FpgaUnavailable(RuntimeError):
    pass


class ArmExecutor:
    name = "arm"

    def run(self, layers, x):
        t0 = time.perf_counter()
        y = run_layers(layers, x)
        return y, (time.perf_counter() - t0) * 1000.0, None


class FpgaSimExecutor:
    """Simulation logicielle du circuit : mêmes entiers que le matériel."""
    name = "fpga"
    label = "fpga-sim"

    def run(self, layers, x):
        t0 = time.perf_counter()
        y = run_layers(layers, x)
        host_ms = (time.perf_counter() - t0) * 1000.0
        cycles = math.ceil(count_macs(layers) / FPGA_PE)
        est_ms = cycles / (FPGA_MHZ * 1e3)
        return y, host_ms, est_ms


class FpgaBoardExecutor:
    """Point d'accroche pour une vraie carte (PYNQ). Voir l'annexe du guide."""
    name = "fpga"
    label = "fpga"

    def __init__(self):
        raise FpgaUnavailable("FPGA_MODE=board : pilote PYNQ non branché (voir annexe)")


def make_executors() -> dict:
    ex = {"arm": ArmExecutor()}
    mode = os.getenv("FPGA_MODE", "sim").lower()
    if mode == "board":
        try:
            ex["fpga"] = FpgaBoardExecutor()
        except FpgaUnavailable as e:
            log.warning("%s -> repli sur la simulation", e)
            ex["fpga"] = FpgaSimExecutor()
    else:
        ex["fpga"] = FpgaSimExecutor()
    return ex


# --------------------------------------------------------------------------
# Modèle partitionné
# --------------------------------------------------------------------------
class PartitionedModel:
    def __init__(self, part_dir: Path = PART_DIR, plan: str | None = None):
        part_dir = Path(part_dir)
        manifest_path = part_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest introuvable : {manifest_path}")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        m = self.manifest
        self.labels = m["labels"]
        self.input_scale = float(m["input_scale"])
        self.logit_scale = float(m["logit_scale"])
        self.name = m["model_name"]
        self.partitions = [
            {"name": p["name"], "layers": load_layers(part_dir / p["file"])}
            for p in m["partitions"]
        ]
        digest = weights_digest([L for p in self.partitions for L in p["layers"]])
        if digest != m["weights_sha256"]:
            raise ValueError("Poids du modèle modifiés : empreinte différente du manifest")
        self.version = m["model_version"]
        plan = plan or os.getenv("PARTITION_PLAN") or ",".join(p["device"] for p in m["partitions"])
        self.plan = [d.strip().lower() for d in plan.split(",")]
        if len(self.plan) != len(self.partitions) or any(d not in DEVICES for d in self.plan):
            raise ValueError(f"Plan invalide {self.plan} : attendu {len(self.partitions)} valeurs parmi {DEVICES}")
        self.executors = make_executors()

    def infer(self, segment) -> dict:
        seg = np.asarray(segment, dtype=np.float64).reshape(1, -1)
        x = np.clip(np.round(seg / self.input_scale), -128, 127).astype(np.int8)
        trace = []
        for part, dev in zip(self.partitions, self.plan):
            ex = self.executors[dev]
            x, host_ms, est_ms = ex.run(part["layers"], x)
            trace.append({
                "partition": part["name"],
                "device": getattr(ex, "label", ex.name),
                "macs": count_macs(part["layers"]),
                "host_ms": round(host_ms, 4),
                "fpga_est_ms": None if est_ms is None else round(est_ms, 6),
            })
        logits = x.astype(np.float64)[0] * self.logit_scale
        z = logits - logits.max()
        probs = np.exp(z) / np.exp(z).sum()
        k = int(np.argmax(probs))
        return {
            "label": self.labels[k],
            "confidence": round(float(probs[k]), 4),
            "probs": [round(float(p), 4) for p in probs],
            "trace": trace,
        }