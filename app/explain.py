"""Explication en langage naturel.

Par défaut : gabarit déterministe. Si SLM_MODEL_PATH pointe vers un fichier GGUF,
un petit modèle de langage local (SLM) reformule l'explication, sur ARM/CPU.
Le SLM ne reçoit JAMAIS le texte du rapport ni de donnée patient : seulement
la classe, la confiance, le statut et les motifs de validation.
Toute sortie non conforme ou toute erreur -> repli silencieux sur le gabarit.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("explain")

DISCLAIMER = "Prototype pédagogique, non diagnostique."


def _template(prediction: dict, validation: dict, device_summary: str) -> str:
    return (
        f"Classe indicative du prototype : {prediction['label']} "
        f"(confiance {prediction['confidence']:.0%}). Statut de validation : {validation['status']}. "
        f"Inférence : {device_summary}. {DISCLAIMER}"
    )


@lru_cache(maxsize=1)
def _load_slm(path: str):
    from llama_cpp import Llama  # pip install llama-cpp-python

    return Llama(model_path=path, n_ctx=1024,
                 n_threads=int(os.getenv("SLM_THREADS", "4")), verbose=False)


def _slm_text(prediction: dict, validation: dict, path: str) -> str:
    reasons = "; ".join(validation["reasons"])
    facts = (f"CLASSE={prediction['label']} ; CONFIANCE={prediction['confidence']:.0%} ; "
             f"STATUT={validation['status']}" + (f" ; MOTIFS={reasons}" if reasons else ""))
    llm = _load_slm(path)
    out = llm.create_chat_completion(
        messages=[
            {"role": "system",
             "content": "Tu r?diges le compte rendu automatique d'un prototype qui classe des battements "
                        "d'ECG (il ne s'agit pas d'une classe scolaire). ?cris UNE seule phrase en fran?ais. "
                        "Recopie la valeur de CLASSE et la valeur de STATUT exactement comme elles sont "
                        "?crites, sans les traduire ni les modifier (le STATUT reste en MAJUSCULES, en anglais). "
                        "Aucun conseil, aucun diagnostic."},
            {"role": "user",
             "content": "CLASSE=anormal ; CONFIANCE=88% ; STATUT=REVIEW_REQUIRED ; MOTIFS=confiance faible"},
            {"role": "assistant",
             "content": "Le prototype indique la classe anormal avec 88% de confiance ; "
                        "le statut est REVIEW_REQUIRED (confiance faible)."},
            {"role": "user",
             "content": "CLASSE=normal ; CONFIANCE=97% ; STATUT=ACCEPTED ; MOTIFS=contr?le manuel non effectu?"},
            {"role": "assistant",
             "content": "Le prototype indique la classe normal avec 97% de confiance ; "
                        "le statut est ACCEPTED (contr?le manuel non effectu?)."},
            {"role": "user", "content": facts},
        ],
        temperature=0.0,
        max_tokens=80,
    )
    return out["choices"][0]["message"]["content"].strip()


def build_explanation(prediction: dict, validation: dict, device_summary: str) -> tuple[str, str]:
    """Retourne (texte, source) ; source = "template" ou "slm:<fichier>"."""
    path = os.getenv("SLM_MODEL_PATH")
    if not path:
        return _template(prediction, validation, device_summary), "template"
    try:
        text = _slm_text(prediction, validation, path)
        if not text or prediction["label"] not in text or validation["status"] not in text:
            raise ValueError("sortie du SLM non conforme (classe ou statut absent)")
        return f"{text} Inférence : {device_summary}. {DISCLAIMER}", f"slm:{Path(path).name}"
    except Exception as e:
        log.warning("SLM indisponible ou sortie rejetée (%s) : repli sur le gabarit", e)
        return _template(prediction, validation, device_summary), "template"