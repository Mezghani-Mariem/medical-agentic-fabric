from copy import deepcopy

import pytest

from app.validation import CONTEXT_REASON, validate

PREDICTION = {"label": "demo_class_A", "confidence": 0.91, "model_name": "mock_fixture", "model_version": "v1"}
QUALITY = {"valid": True, "reasons": []}


@pytest.mark.parametrize("confidence", [0.75, 0.91, 1])
def test_high_confidence_and_inclusive_threshold(confidence):
    result = validate({**PREDICTION, "confidence": confidence}, QUALITY)
    assert result == {"status": "ACCEPTED", "reasons": []}


@pytest.mark.parametrize("confidence", [0, 0.62, 0.749999])
def test_low_confidence(confidence):
    result = validate({**PREDICTION, "confidence": confidence}, QUALITY)
    assert result["status"] == "REVIEW_REQUIRED" and result["reasons"]


def test_bad_signal_and_all_reasons_are_retained():
    result = validate({**PREDICTION, "confidence": 0.5}, {"valid": False, "reasons": ["Signal trop court"]})
    assert result["status"] == "REVIEW_REQUIRED"
    assert any("court" in reason for reason in result["reasons"])
    assert any("Confiance" in reason for reason in result["reasons"])


@pytest.mark.parametrize("flags", [{"artifacts_ok": False}, {"integrity_ok": False},
                                   {"artifacts_ok": False, "integrity_ok": False},
                                   {"artifacts_ok": None}, {"integrity_ok": "true"}])
def test_missing_artifacts_integrity_failure_and_unknown_flags(flags):
    result = validate(PREDICTION, QUALITY, **flags)
    assert result["status"] == "REJECTED" and result["reasons"]


@pytest.mark.parametrize("prediction", [None, {}, [], "prediction", {"confidence": 0.9},
    {"label": ""}, {"label": "   ", "confidence": 0.9}, {"label": 42, "confidence": 0.9},
    {"label": "demo"}, {"label": "demo", "confidence": "0.9"},
    *[{"label": "demo", "confidence": score} for score in [True, False, -0.1, 1.1, float("nan"), float("inf"), float("-inf"), None, 10**1000]],
])
def test_absent_or_malformed_prediction_fails_closed(prediction):
    assert validate(prediction, QUALITY)["status"] == "REJECTED"


@pytest.mark.parametrize("quality", [None, {}, [], {"valid": "true"}, {"valid": 1}, {"valid": False, "reasons": None}])
def test_unconfirmed_quality_requires_review(quality):
    assert validate(PREDICTION, quality)["status"] == "REVIEW_REQUIRED"


def test_rejection_takes_precedence_over_review():
    result = validate({**PREDICTION, "confidence": 0.4}, {"valid": False}, False, False)
    assert result["status"] == "REJECTED"
    assert len(result["reasons"]) >= 4


def test_report_is_context_only_and_inputs_are_not_mutated():
    prediction, quality = deepcopy(PREDICTION), deepcopy(QUALITY)
    result = validate(prediction, quality, report_text="Rapport fictif sans cohérence clinique évaluée.")
    assert result == {"status": "ACCEPTED", "reasons": [CONTEXT_REASON]}
    assert prediction == PREDICTION and quality == QUALITY


def test_quality_reason_types_and_duplicates():
    result = validate(PREDICTION, {"valid": False, "reasons": ["bruit", "bruit", 3, None, ""]})
    assert result["reasons"].count("Qualité : bruit") == 1
