import sys
import types

import pytest

import app.explain as explain

PRED = {"label": "demo_class_A", "confidence": 0.93, "model_name": "m", "model_version": "v"}
VAL = {"status": "ACCEPTED", "reasons": []}


@pytest.fixture(autouse=True)
def _reset():
    explain._load_slm.cache_clear()
    yield
    explain._load_slm.cache_clear()


def _fake_llama(monkeypatch, answer, seen=None):
    class FakeLlama:
        def __init__(self, model_path, **kw):
            pass

        def create_chat_completion(self, messages, **kw):
            if seen is not None:
                seen.append(messages)
            return {"choices": [{"message": {"content": answer}}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=FakeLlama))


def test_default_is_template(monkeypatch):
    monkeypatch.delenv("SLM_MODEL_PATH", raising=False)
    text, source = explain.build_explanation(PRED, VAL, "modèle int8")
    assert source == "template" and "non diagnostique" in text and "demo_class_A" in text


def test_slm_used_when_output_is_valid(monkeypatch):
    monkeypatch.setenv("SLM_MODEL_PATH", "/x/slm.gguf")
    seen = []
    _fake_llama(monkeypatch, "La classe demo_class_A est indiquée ; statut ACCEPTED.", seen)
    text, source = explain.build_explanation(PRED, VAL, "modèle int8")
    assert source == "slm:slm.gguf" and "non diagnostique" in text
    assert "rapport" not in seen[-1][-1]["content"].lower()  # le SLM ne reçoit aucune donnée du rapport


def test_slm_output_missing_label_falls_back(monkeypatch):
    monkeypatch.setenv("SLM_MODEL_PATH", "/x/slm.gguf")
    _fake_llama(monkeypatch, "Tout va bien.")
    assert explain.build_explanation(PRED, VAL, "modèle int8")[1] == "template"


def test_slm_output_missing_status_falls_back(monkeypatch):
    monkeypatch.setenv("SLM_MODEL_PATH", "/x/slm.gguf")
    _fake_llama(monkeypatch, "La classe demo_class_A est indiquée.")
    assert explain.build_explanation(PRED, VAL, "modèle int8")[1] == "template"


def test_slm_missing_package_falls_back(monkeypatch):
    monkeypatch.setenv("SLM_MODEL_PATH", "/x/slm.gguf")
    monkeypatch.setitem(sys.modules, "llama_cpp", None)  # simule un import impossible
    assert explain.build_explanation(PRED, VAL, "modèle int8")[1] == "template"