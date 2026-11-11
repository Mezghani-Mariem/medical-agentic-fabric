"""API FastAPI. Lancer : uvicorn app.main:app --reload"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import orchestrator
from app.predict import model_info
from app.preprocess import PipelineError

log = logging.getLogger("main")
app = FastAPI(title="Analyse ECG traçable (prototype pédagogique)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _error(status: int, message: str, reasons: list[str] | None = None) -> JSONResponse:
    # "detail" (convention FastAPI) et "error" : le frontend peut lire l'un ou l'autre
    return JSONResponse(status_code=status,
                        content={"detail": (f"{message} : " + " · ".join(reasons)) if reasons else message,
                                "error": message, "reasons": reasons or []})


def _call(fn, *args):
    try:
        return fn(*args)
    except PipelineError as e:
        return _error(e.status, e.message, e.reasons)
    except Exception:
        log.exception("Erreur interne")
        return _error(500, "Erreur interne du serveur")


@app.post("/api/analyze")
def analyze(ecg: UploadFile = File(...), report: UploadFile = File(...)):
    return _call(orchestrator.run_case, ecg.file.read(), report.file.read())


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    return _call(orchestrator.get_case, case_id)


@app.get("/api/cases/{case_id}/history")
def get_history(case_id: str):
    return _call(orchestrator.get_history, case_id)


@app.post("/api/cases/{case_id}/verify")
def verify(case_id: str):
    return _call(orchestrator.verify_case, case_id)


@app.get("/api/model")  # optionnel, additif : utile pour la démo FPGA/ARM
def model():
    return _call(model_info)


_ROOT = Path(__file__).resolve().parent.parent
_SAMPLES = _ROOT / "samples"
if _SAMPLES.exists():  # fichiers de démonstration attendus par le bouton « Charger les fichiers »
    app.mount("/samples", StaticFiles(directory=_SAMPLES), name="samples")  # AVANT le montage "/"

_FRONT = _ROOT / "frontend"
if _FRONT.exists():  # sert l'interface de Mezghani sur http://localhost:8000/
    app.mount("/", StaticFiles(directory=_FRONT, html=True), name="frontend")