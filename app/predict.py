"""Prédiction. Contrat gelé : predict(features: dict) -> dict

Retour : {"label", "confidence", "model_name", "model_version"}  (exactement ces 4 clés).
Derrière : modèle int8 partitionné (P1/P2/P3). Si le modèle est absent,
repli sur une heuristique déterministe, clairement identifiée comme simulation.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import numpy as np

from models.engine import PART_DIR, SEGMENT_LEN, PartitionedModel

log = logging.getLogger("predict")


@lru_cache(maxsize=16)
def _load_model(plan: str | None):
    try:
        return PartitionedModel(PART_DIR, plan)
    except FileNotFoundError:
        log.warning("Modèle partitionné absent : repli sur l'heuristique de démonstration")
        return None


def _heuristic(features: dict) -> dict:
    """Simulation déterministe : ce n'est PAS un modèle entraîné."""
    std = float(features.get("std", 0.0))
    amp = float(features.get("max", 0.0)) - float(features.get("min", 0.0))
    ratio = amp / (std + 1e-9)
    label = "demo_class_A" if ratio < 6.0 else "demo_class_B"
    conf = round(min(0.95, 0.60 + abs(ratio - 6.0) / 20.0), 4)
    return {"label": label, "confidence": conf, "model_name": "demo_baseline", "model_version": "v1"}


def predict_with_trace(features: dict) -> tuple[dict, list[dict]]:
    seg = features.get("segment")
    model = _load_model(os.getenv("PARTITION_PLAN") or None)
    if model is None or seg is None or len(seg) != SEGMENT_LEN:
        return _heuristic(features), []
    out = model.infer(np.asarray(seg, dtype=np.float64))
    pred = {
        "label": out["label"], "confidence": out["confidence"],
        "model_name": model.name, "model_version": model.version,
    }
    return pred, out["trace"]


def predict(features: dict) -> dict:
    return predict_with_trace(features)[0]


def model_info() -> dict:
    """Pour GET /api/model (optionnel, additif)."""
    model = _load_model(os.getenv("PARTITION_PLAN") or None)
    if model is None:
        return {"mode": "heuristic", "model_name": "demo_baseline", "model_version": "v1"}
    return {
        "mode": "int8-partitioned", "model_name": model.name, "model_version": model.version,
        "plan": model.plan, "fpga_mode": os.getenv("FPGA_MODE", "sim"),
        "partitions": [{"name": p["name"], "macs": int(sum(L["W"].shape[0] * L["W"].shape[1] for L in p["layers"]))}
                       for p in model.partitions],
    }