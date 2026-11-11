import numpy as np
import pytest

import app.predict as predict_mod
from app.predict import predict
from models.engine import PART_DIR, PartitionedModel

CONTRACT_KEYS = {"label", "confidence", "model_name", "model_version"}


def _features(seed=0):
    rng = np.random.default_rng(seed)
    return {"mean": 0.0, "std": 1.0, "min": -1.0, "max": 1.0, "abs_mean": 0.5,
            "segment": [float(v) for v in rng.normal(size=64)]}


def test_predict_returns_exactly_the_frozen_keys():
    assert set(predict(_features())) == CONTRACT_KEYS


@pytest.mark.parametrize("plan", ["arm,arm,arm", "fpga,fpga,arm", "fpga,arm,fpga", "fpga,fpga,fpga"])
def test_all_plans_give_identical_results(plan, monkeypatch):
    f = _features(3)
    monkeypatch.setenv("PARTITION_PLAN", "arm,arm,arm")
    ref = predict(f)
    monkeypatch.setenv("PARTITION_PLAN", plan)
    assert predict(f) == ref


def test_plan_invalid_is_rejected():
    with pytest.raises(ValueError):
        PartitionedModel(PART_DIR, "arm,gpu,arm")


def test_tampered_weights_are_detected(tmp_path):
    import json
    import shutil
    shutil.copytree(PART_DIR, tmp_path / "p")
    mpath = tmp_path / "p" / "manifest.json"
    m = json.loads(mpath.read_text(encoding="utf-8"))
    m["weights_sha256"] = "0" * 64
    mpath.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(ValueError):
        PartitionedModel(tmp_path / "p")


def test_fallback_heuristic_when_model_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(predict_mod, "PART_DIR", tmp_path)
    predict_mod._load_model.cache_clear()
    out = predict(_features())
    predict_mod._load_model.cache_clear()
    assert set(out) == CONTRACT_KEYS and out["model_name"] == "demo_baseline"