"""Regression guards for BP values passed from patient history into ML."""

from pathlib import Path

from api.services.prediction_service import prediction_service


def test_prediction_service_marks_missing_bp_instead_of_fabricating():
    _, systolic_missing = prediction_service._resolve_feature_with_flag(
        {"systolic_bp": None}, "systolic_bp"
    )
    _, diastolic_missing = prediction_service._resolve_feature_with_flag(
        {"diastolic_bp": None}, "diastolic_bp"
    )

    assert systolic_missing is True
    assert diastolic_missing is True


def test_patient_ml_history_does_not_use_bp_defaults():
    source = Path(__file__).parents[1].joinpath("api/routes/patients.py").read_text()
    assert "or 120.0" not in source
    assert "or 80.0" not in source
