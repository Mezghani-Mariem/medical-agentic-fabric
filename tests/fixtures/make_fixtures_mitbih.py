"""ECG de démonstration issus de MIT-BIH (vrais battements) : remplace A (normal) et B (anormal).

Usage (racine du projet, modèle MIT-BIH déjà entraîné et quantifié) :
    python tests/fixtures/make_fixtures_mitbih.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import wfdb  # noqa: E402

from models.engine import PartitionedModel, to_segment  # noqa: E402

OUT = Path(__file__).resolve().parent
HALF = 90  # 180 points autour du pic R, comme à l'entraînement
SOURCES = {"N": ["100", "101", "103"], "V": ["119", "200", "208"]}


def write(name, values):
    lines = ["signal"] + [f"{v:.6f}" for v in values]
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_beat(model, symbol, expected_label):
    for rec in SOURCES[symbol]:
        r = wfdb.rdrecord(rec, pn_dir="mitdb", channels=[0], sampto=60000)
        a = wfdb.rdann(rec, "atr", pn_dir="mitdb", sampto=60000)
        sig = r.p_signal[:, 0]
        for s, sym in zip(a.sample, a.symbol):
            if sym != symbol or s - HALF < 0 or s + HALF > len(sig):
                continue
            raw = sig[s - HALF: s + HALF]
            out = model.infer(to_segment(raw))
            if out["label"] == expected_label and out["confidence"] >= 0.9:
                return raw, rec, int(s), out
    raise SystemExit(f"Aucun battement {symbol} correctement classé trouvé")


model = PartitionedModel()
labels = model.labels  # ["normal", "abnormal"]
for name, symbol, label in (("ecg_demo_valid_A.csv", "N", labels[0]),
                            ("ecg_demo_valid_B.csv", "V", labels[1])):
    raw, rec, idx, out = find_beat(model, symbol, label)
    write(name, raw)
    print(f"{name}: record {rec}, échantillon {idx}, symbole {symbol} -> {out['label']} ({out['confidence']:.2%})")
print("Fixtures MIT-BIH écrites dans", OUT)