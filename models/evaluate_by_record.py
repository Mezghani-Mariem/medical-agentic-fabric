r"""Evaluation honnete du modele MIT-BIH : leave-one-record-out (aucun patient commun entre train et test).

Usage (racine du projet) : python -m models.evaluate_by_record
Lecture seule : n'ecrit ni poids ni modele. Cache des battements : data/runtime/mitbih_beats.npz.
Rapport ecrit dans models/artifacts/evaluation_by_record.md
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

from models.engine import to_segment

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "runtime" / "mitbih_beats.npz"
REPORT = ROOT / "models" / "artifacts" / "evaluation_by_record.md"
RECORDS = ["100", "101", "103", "106", "119", "200", "203", "208", "233"]
HALF = 90
CAP = 3000          # battements max par classe et par enregistrement
N_PER_CLASS = 2000  # equilibrage de l'entrainement, comme train_baseline
SEED = 42
warnings.filterwarnings("ignore")


def load_beats():
    if CACHE.exists():
        d = np.load(CACHE, allow_pickle=False)
        return d["X"], d["y"], d["rec"]
    import wfdb

    rng = np.random.default_rng(SEED)
    X, y, rec_ids = [], [], []
    for rec in RECORDS:
        r = wfdb.rdrecord(rec, pn_dir="mitdb", channels=[0])
        a = wfdb.rdann(rec, "atr", pn_dir="mitdb")
        sig = r.p_signal[:, 0]
        per = {"N": [], "V": []}
        for s, sym in zip(a.sample, a.symbol):
            if sym in per and s - HALF >= 0 and s + HALF <= len(sig):
                per[sym].append(int(s))
        print(f"record {rec}: N={len(per['N'])} V={len(per['V'])}")
        for sym, label in (("N", 0), ("V", 1)):
            idx = np.array(per[sym], dtype=int)
            if len(idx) > CAP:
                idx = rng.choice(idx, CAP, replace=False)
            for s in idx:
                X.append(to_segment(sig[s - HALF: s + HALF]))
                y.append(label)
                rec_ids.append(int(rec))
    X, y, rec_ids = np.array(X), np.array(y), np.array(rec_ids)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, X=X, y=y, rec=rec_ids)
    return X, y, rec_ids


def balanced(X, y, rng, k=N_PER_CLASS):
    i0, i1 = np.where(y == 0)[0], np.where(y == 1)[0]
    k = min(k, len(i0), len(i1))
    sel = np.concatenate([rng.permutation(i0)[:k], rng.permutation(i1)[:k]])
    return X[sel], y[sel]


def train(X, y):
    clf = MLPClassifier(hidden_layer_sizes=(32, 16), activation="relu", max_iter=400, random_state=SEED)
    clf.fit(X, y)
    return clf


def logit(clf, X):
    """Sortie lineaire avant la sigmoide (meme quantite que les 2 logits +-z/2 du modele deploye)."""
    h = X
    for W, b in zip(clf.coefs_[:-1], clf.intercepts_[:-1]):
        h = np.maximum(h @ W + b, 0.0)
    return (h @ clf.coefs_[-1] + clf.intercepts_[-1]).ravel()


def sigmoid(z):
    return 0.5 * (1.0 + np.tanh(z / 2.0))


def nll(z, y, T):
    zt = z / T
    return float(np.mean(np.logaddexp(0.0, zt) - y * zt))


def calib(z, y, T=1.0, bins=10):
    p1 = sigmoid(z / T)
    pred = (p1 >= 0.5).astype(int)
    conf = np.where(pred == 1, p1, 1.0 - p1)
    ok = (pred == y).astype(float)
    edges = np.linspace(0.5, 1.0, bins + 1)
    ece, rows = 0.0, []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf >= lo) & ((conf < hi) if hi < 1.0 else (conf <= hi))
        if m.sum() == 0:
            continue
        ece += float(m.mean()) * abs(float(conf[m].mean()) - float(ok[m].mean()))
        rows.append((lo, hi, int(m.sum()), float(conf[m].mean()), float(ok[m].mean())))
    return float(ece), rows, conf, ok


def main():
    X, y, rec = load_beats()
    rng = np.random.default_rng(SEED)
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("# Evaluation par enregistrement (leave-one-record-out), MIT-BIH N vs V")
    out(f"Battements : {len(y)} (N={int((y == 0).sum())}, V={int((y == 1).sum())}), 9 enregistrements")

    # 1. Split aleatoire = protocole actuel de train_baseline
    Xb, yb = balanced(X, y, rng)
    Xtr, Xte, ytr, yte = train_test_split(Xb, yb, test_size=0.25, random_state=SEED, stratify=yb)
    acc_rand = train(Xtr, ytr).score(Xte, yte)
    out(f"\nSplit aleatoire (meme patient dans train et test) : precision {acc_rand:.4f}")

    # 2. Leave-one-record-out
    out("\nPar enregistrement laisse de cote :")
    Z, Y = [], []
    for r_ in RECORDS:
        te = rec == int(r_)
        Xtr_, ytr_ = balanced(X[~te], y[~te], rng)
        clf = train(Xtr_, ytr_)
        z = logit(clf, X[te])
        Z.append(z)
        Y.append(y[te])
        acc = float(((z >= 0).astype(int) == y[te]).mean())
        out(f"  record {r_}: N={int((y[te] == 0).sum()):5d} V={int((y[te] == 1).sum()):5d}  precision={acc:.3f}")
    Z, Y = np.concatenate(Z), np.concatenate(Y)
    pred = (Z >= 0).astype(int)
    tn = int(((pred == 0) & (Y == 0)).sum())
    fp = int(((pred == 1) & (Y == 0)).sum())
    fn = int(((pred == 0) & (Y == 1)).sum())
    tp = int(((pred == 1) & (Y == 1)).sum())
    sens = tp / max(tp + fn, 1)
    spec = tn / max(tn + fp, 1)
    out("\nTous enregistrements confondus (patients jamais vus) :")
    out(f"  matrice de confusion : vrai N -> predit N={tn}, predit V={fp} ; vrai V -> predit N={fn}, predit V={tp}")
    out(f"  precision globale = {(tp + tn) / len(Y):.4f}")
    out(f"  sensibilite (V detectes) = {sens:.4f} ; specificite (N reconnus) = {spec:.4f} ; precision equilibree = {(sens + spec) / 2:.4f}")

    # 3. Calibration de la confiance
    ece1, rows1, conf1, ok1 = calib(Z, Y, 1.0)
    hi = conf1 >= 0.99
    out("\nCalibration de la confiance (avant) :")
    out(f"  confiance moyenne = {conf1.mean():.4f} ; exactitude reelle = {ok1.mean():.4f} ; ECE = {ece1:.4f}")
    if hi.sum():
        out(f"  {int(hi.sum())} predictions a confiance >= 99 % ({hi.mean():.1%}) : exactitude reelle {ok1[hi].mean():.4f}")
    out("  tranche de confiance | n | confiance moyenne | exactitude reelle")
    for lo, hi_, n, c, a in rows1:
        out(f"    {lo:.2f}-{hi_:.2f} | {n:6d} | {c:.3f} | {a:.3f}")

    Ts = np.logspace(-0.5, 2.0, 400)
    T = float(Ts[int(np.argmin([nll(Z, Y, t) for t in Ts]))])
    ece2, rows2, conf2, ok2 = calib(Z, Y, T)
    out(f"\nTemperature optimale (minimise la log-vraisemblance negative) T = {T:.2f}")
    out("  (ajustee et evaluee sur les memes predictions : estimation un peu optimiste)")
    out(f"  apres calibration : confiance moyenne = {conf2.mean():.4f} ; exactitude reelle = {ok2.mean():.4f} ; ECE = {ece2:.4f}")
    out(f"  predictions a confiance >= 75 % apres calibration : {float((conf2 >= 0.75).mean()):.1%}")
    out("  tranche de confiance | n | confiance moyenne | exactitude reelle")
    for lo, hi_, n, c, a in rows2:
        out(f"    {lo:.2f}-{hi_:.2f} | {n:6d} | {c:.3f} | {a:.3f}")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nRapport ecrit :", REPORT)


if __name__ == "__main__":
    main()