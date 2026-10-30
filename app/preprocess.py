"""Prétraitement de l'ECG : lecture CSV, nettoyage, qualité, features.

Contrat gelé : preprocess(csv_bytes) -> (processed, quality)
  processed = {"n_points", "removed_invalid", "signal", "features"}
  quality   = {"valid": bool, "reasons": [str]}
L'orchestrateur sépare "features" de "processed" pour fabriquer deux artefacts.
"""
from __future__ import annotations

import csv
import io
import math

import numpy as np

from models.engine import SEGMENT_LEN, to_segment

MIN_POINTS = 30
MAX_INVALID_RATIO = 0.20
MAX_ABS = 1e100  # au-delà, le signal est remis à l'échelle pour éviter les débordements


class PipelineError(Exception):
    """Erreur métier : l'API la convertit en réponse JSON (400/422/500)."""

    def __init__(self, status: int, message: str, reasons: list[str] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.reasons = reasons or []


def _r(v: float) -> float:
    return round(float(v), 6)


def preprocess(csv_bytes: bytes) -> tuple[dict, dict]:
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise PipelineError(422, "ECG illisible", ["Encodage non UTF-8"])

    # newline="" : les fins de ligne CRLF / CR sont gérées par le module csv
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fields = [f.strip() for f in (reader.fieldnames or [])]
    if "signal" not in fields:
        raise PipelineError(422, "ECG illisible", ["Colonne 'signal' absente"])

    values, invalid = [], 0
    for row in reader:
        raw = {k.strip(): v for k, v in row.items() if k is not None}
        try:
            v = float(raw["signal"])
        except (KeyError, TypeError, ValueError):
            invalid += 1
            continue
        if math.isfinite(v):
            values.append(v)
        else:
            invalid += 1

    if not values:
        raise PipelineError(422, "ECG illisible", ["Aucune valeur numérique exploitable"])

    x = np.asarray(values, dtype=np.float64)
    blocking: list[str] = []   # motifs qui rendent la qualité invalide (-> REVIEW_REQUIRED)
    notes: list[str] = []      # simples informations
    if len(x) < MIN_POINTS:
        blocking.append(f"Signal trop court : {len(x)} points (minimum {MIN_POINTS})")
    total = len(x) + invalid
    if invalid:
        notes.append(f"{invalid} valeur(s) non finie(s) retirée(s)")
        if invalid / total > MAX_INVALID_RATIO:
            blocking.append("Trop de valeurs invalides (> 20 %)")
    peak = float(np.abs(x).max())
    if peak > MAX_ABS:
        blocking.append("Amplitude hors plage de calcul (valeurs > 1e100)")
        x = x / peak           # remise à l'échelle : aucun débordement numérique
    if float(x.std()) < 1e-9:
        blocking.append("Signal constant (aucune variation)")
    quality = {"valid": not blocking, "reasons": blocking + notes}

    mean, std = float(x.mean()), float(x.std())
    norm = (x - mean) / std if std > 1e-9 else np.zeros_like(x)
    features = {
        "mean": _r(mean), "std": _r(std), "min": _r(x.min()), "max": _r(x.max()),
        "abs_mean": _r(np.abs(x).mean()),
        "segment": [_r(v) for v in to_segment(x, SEGMENT_LEN)],
    }
    processed = {
        "n_points": int(len(x)), "removed_invalid": int(invalid),
        "signal": [_r(v) for v in norm], "features": features,
    }
    return processed, quality