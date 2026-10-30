"""Deterministic project-rule validation, independent of AI and the ledger."""

import math

CONFIDENCE_THRESHOLD = 0.75
CONTEXT_REASON = "Cohérence texte/ECG non évaluée automatiquement"


def validate(prediction: dict, quality: dict, artifacts_ok=True, integrity_ok=True, report_text="") -> dict:
    """Apply V1 precedence: REJECTED > REVIEW_REQUIRED > ACCEPTED.

    Malformed predictions fail closed; unknown quality requires review. Boolean
    confidence values and nonfinite/out-of-range scores are invalid predictions.
    Model metadata is transported by the API, not medically assessed here.
    """
    rejected: list[str] = []
    review: list[str] = []
    if artifacts_ok is not True:
        rejected.append("Artefact manquant ou disponibilité des artefacts non confirmée.")
    if integrity_ok is not True:
        rejected.append("Intégrité compromise ou non confirmée.")
    if not isinstance(prediction, dict) or not prediction:
        rejected.append("Prédiction absente.")
    else:
        label = prediction.get("label")
        confidence = prediction.get("confidence")
        if not isinstance(label, str) or not label.strip():
            rejected.append("Prédiction invalide : label absent ou vide.")
        if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1 or not math.isfinite(confidence)):
            rejected.append("Prédiction invalide : confidence doit être un nombre fini entre 0 et 1.")
        elif confidence < CONFIDENCE_THRESHOLD:
            review.append("Confiance inférieure au seuil de 75 % : revue humaine requise.")
    if not isinstance(quality, dict) or quality.get("valid") is not True:
        review.append("Qualité du signal insuffisante ou non confirmée : revue humaine requise.")
        if isinstance(quality, dict) and isinstance(quality.get("reasons"), list):
            review.extend(f"Qualité : {reason}" for reason in quality["reasons"]
                          if isinstance(reason, str) and reason.strip())
    reasons = rejected + review
    if isinstance(report_text, str) and report_text.strip():
        reasons.append(CONTEXT_REASON)
    return {
        "status": "REJECTED" if rejected else "REVIEW_REQUIRED" if review else "ACCEPTED",
        "reasons": list(dict.fromkeys(reasons)),
    }


if __name__ == "__main__":
    import json

    for score in (0.91, 0.62):
        print(json.dumps(validate({"label": "demo_class_A", "confidence": score}, {"valid": True}),
                         ensure_ascii=False))
