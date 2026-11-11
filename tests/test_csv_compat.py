"""Tout CSV accepté par check_inputs (Mezghani) doit être accepté par preprocess (toi)."""
import json
from pathlib import Path

import pytest

from app.input_checks import check_inputs
from app.preprocess import preprocess

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "samples" / "csv_contract_cases.json").read_text(encoding="utf-8"))["cases"]
VALID = [c for c in CASES if c["valid"]]


def _bytes(item, field):
    if f"{field}_hex" in item:
        return bytes.fromhex(item[f"{field}_hex"])
    if f"{field}_parts" in item:
        text = "".join(p if isinstance(p, str) else p["repeat"] * p["count"] for p in item[f"{field}_parts"])
    else:
        text = item.get(field, "Rapport entièrement synthétique.")
    return text.encode("utf-8")


@pytest.mark.parametrize("item", VALID, ids=lambda item: item["id"])
def test_preprocess_accepts_everything_check_inputs_accepts(item):
    ecg = _bytes(item, "ecg")
    assert check_inputs(ecg, _bytes(item, "report"))["valid"]
    processed, quality = preprocess(ecg)
    assert processed["n_points"] == item["points"]
    assert isinstance(quality["valid"], bool)