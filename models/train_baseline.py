"""Entraîne le petit réseau de base (scikit-learn) et sauvegarde les poids float.

Usage (depuis la racine du projet) :
    python -m models.train_baseline --data synthetic
    python -m models.train_baseline --data mitbih      # nécessite : pip install wfdb + Internet
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

from models.engine import SEGMENT_LEN, to_segment

OUT_DIR = Path(__file__).resolve().parent / "artifacts"


# ---------------------------------------------------------------- données --
def synth_beat(rng: np.random.Generator, kind: int, n: int = SEGMENT_LEN) -> np.ndarray:
    """Battement synthétique : classe 0 = rythme normal, classe 1 = QRS large + onde T inversée."""
    t = np.linspace(0.0, 1.0, n)

    def g(mu, s, a):
        return a * np.exp(-((t - mu) ** 2) / (2 * s * s))

    j = rng.uniform(-0.03, 0.03)
    amp = rng.uniform(0.8, 1.2)
    if kind == 0:
        y = g(0.20 + j, 0.04, 0.15) + g(0.45 + j, 0.015, -0.10) + g(0.50 + j, 0.012, 1.0) \
            + g(0.55 + j, 0.015, -0.20) + g(0.75 + j, 0.06, 0.30)
    else:
        y = g(0.42 + j, 0.05, 0.90) + g(0.70 + j, 0.08, -0.40)
    y = amp * y + rng.normal(0.0, 0.03, n)
    return to_segment(y)


def make_synthetic(n_per_class: int = 1500, seed: int = 42):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for k in (0, 1):
        for _ in range(n_per_class):
            X.append(synth_beat(rng, k))
            y.append(k)
    return np.array(X), np.array(y), ["demo_class_A", "demo_class_B"]


def load_mitbih(n_per_class: int = 2000, seed: int = 42):
    """Battements MIT-BIH : N (normal) contre V (extrasystole ventriculaire). Non testé hors ligne."""
    import wfdb  # pip install wfdb

    rng = np.random.default_rng(seed)
    records = ["100", "101", "103", "106", "119", "200", "203", "208", "233"]
    N, V = [], []
    for rec in records:
        r = wfdb.rdrecord(rec, pn_dir="mitdb", channels=[0])
        a = wfdb.rdann(rec, "atr", pn_dir="mitdb")
        sig = r.p_signal[:, 0]
        for s, sym in zip(a.sample, a.symbol):
            if sym not in ("N", "V") or s - 90 < 0 or s + 90 > len(sig):
                continue
            seg = to_segment(sig[s - 90: s + 90])
            (N if sym == "N" else V).append(seg)
    k = min(n_per_class, len(N), len(V))
    N = [N[i] for i in rng.permutation(len(N))[:k]]
    V = [V[i] for i in rng.permutation(len(V))[:k]]
    X = np.array(N + V)
    y = np.array([0] * k + [1] * k)
    return X, y, ["normal", "abnormal"]


# ---------------------------------------------------------- entraînement --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", choices=["synthetic", "mitbih"], default="synthetic")
    ap.add_argument("--hidden", default="32,16", help="tailles des couches cachées")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    X, y, labels = make_synthetic() if args.data == "synthetic" else load_mitbih()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=args.seed, stratify=y)

    hidden = tuple(int(h) for h in args.hidden.split(","))
    clf = MLPClassifier(hidden_layer_sizes=hidden, activation="relu",
                        max_iter=400, random_state=args.seed)
    clf.fit(Xtr, ytr)
    acc = clf.score(Xte, yte)
    print(f"Précision float sur test : {acc:.4f}  ({len(Xtr)} train / {len(Xte)} test)")

    Ws = [w.copy() for w in clf.coefs_]
    bs = [b.copy() for b in clf.intercepts_]
    if Ws[-1].shape[1] == 1:
        # sklearn binaire = 1 neurone sigmoïde ; on passe à 2 logits (softmax équivalent)
        Ws[-1] = np.concatenate([-Ws[-1] / 2, Ws[-1] / 2], axis=1)
        bs[-1] = np.concatenate([-bs[-1] / 2, bs[-1] / 2])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"labels": np.array(labels), "X_calib": Xtr[:256], "X_test": Xte, "y_test": yte,
               "float_acc": np.array(acc)}
    for i, (W, b) in enumerate(zip(Ws, bs), start=1):
        payload[f"W{i}"] = W
        payload[f"b{i}"] = b
    np.savez(OUT_DIR / "float_model.npz", **payload)
    (OUT_DIR / "train_info.json").write_text(
        json.dumps({"data": args.data, "hidden": hidden, "seed": args.seed,
                    "float_accuracy": round(float(acc), 4), "labels": labels}, indent=2),
        encoding="utf-8")
    print("Sauvegardé :", OUT_DIR / "float_model.npz")


if __name__ == "__main__":
    main()