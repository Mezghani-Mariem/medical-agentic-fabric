"""Génère les ECG de démonstration : python tests/fixtures/make_fixtures.py (depuis la racine)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from models.train_baseline import synth_beat  # noqa: E402

OUT = Path(__file__).resolve().parent
rng = np.random.default_rng(7)


def write(name, values):
    lines = ["signal"] + [f"{v:.6f}" for v in values]
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


write("ecg_demo_valid_A.csv", synth_beat(rng, 0, n=64))
write("ecg_demo_valid_B.csv", synth_beat(rng, 1, n=64))
(OUT / "ecg_demo_invalid.csv").write_text("temps,valeur\n0,abc\n1,xyz\n", encoding="utf-8")
(OUT / "report_demo.txt").write_text(
    "Nom: Test\nPrénom: Demo\nPatient ID: 000\nCompte rendu fictif : ECG de démonstration.\n",
    encoding="utf-8")
print("Fixtures écrites dans", OUT)