"""
Safety-invariant and imputation-consistency tests (v1.1 hardening).

These are pure unit tests: no database, no TensorFlow, no network required.

Run from backend/:
    python -m pytest tests/test_fusion_safety.py -v
"""
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models.schemas import HealthStatus
from api.models.database.models import Patient, VitalSigns, DeviceType
from api.services.fusion_engine import fusion_engine
from api.services.prediction_service import prediction_service


# ── Helpers ──────────────────────────────────────────────────────────────────

def _det(risk: HealthStatus) -> dict:
    """Build a deterministic-layer output dict for the given risk class."""
    score_map = {
        HealthStatus.NORMAL: 0.0,
        HealthStatus.WARNING: 0.5,
        HealthStatus.CRITICAL: 1.0,
    }
    return {
        "risk_class": risk,
        "triggered_rules": [],
        "rule_confidence": 1.0,
        "score": score_map[risk],
    }


def _ml(predicted_class: str, probability: float = 0.99) -> dict:
    return {"predicted_class": predicted_class, "probability": probability}


def _patient() -> Patient:
    return Patient(id="P1", first_name="A", last_name="B", age=40, gender="male")


def _vitals(**overrides) -> VitalSigns:
    base = dict(
        id="V1",
        patient_id="P1",
        heart_rate=75.0,
        spo2=98.0,
        temperature=36.8,
        data_source=DeviceType.IOT_HARDWARE,
        timestamp=datetime.utcnow(),
    )
    base.update(overrides)
    return VitalSigns(**base)


# ── Safety Invariant 2: ML may never originate a CRITICAL ────────────────────

def test_ml_cannot_escalate_warning_to_critical():
    """
    Regression test for the fusion gap: WARNING (0.6*0.5) + ML CRITICAL
    (0.4*1.0) = 0.70, which used to yield a CRITICAL alarm authored by the ML.
    """
    out = fusion_engine.fuse_risk(_det(HealthStatus.WARNING), _ml("critical"))
    assert out["final_risk_level"] == "warning"
    assert out["ml_escalation_capped"] is True


def test_ml_cannot_escalate_normal_to_critical():
    out = fusion_engine.fuse_risk(_det(HealthStatus.NORMAL), _ml("critical"))
    assert out["final_risk_level"] != "critical"
    assert out["final_risk_level"] == "warning"


def test_ml_can_still_raise_normal_to_warning():
    """
    Early-warning behaviour must survive the safety cap.

    With weights 0.6/0.4 an ML 'critical' on a rules-normal patient scores
    0.6*0.0 + 0.4*1.0 = 0.40 -> WARNING. That is the ML's entire escalation
    authority: it can request a warning, never a critical.
    """
    out = fusion_engine.fuse_risk(_det(HealthStatus.NORMAL), _ml("critical"))
    assert out["final_risk_level"] == "warning"
    assert out["ml_escalation_capped"] is False


def test_ml_warning_alone_does_not_change_normal():
    """
    Documents a property of the 0.6/0.4 weights: an ML 'warning' contributes
    only 0.6*0.0 + 0.4*0.5 = 0.20, below the 0.40 warning threshold. The ML can
    therefore only influence the outcome when it is highly confident of
    *critical*. Worth stating explicitly in the report rather than discovering
    it during the viva.
    """
    out = fusion_engine.fuse_risk(_det(HealthStatus.NORMAL), _ml("warning", 0.95))
    assert out["final_risk_level"] == "normal"


def test_deterministic_critical_is_absolute():
    """A rules-authored CRITICAL can never be downgraded by the ML."""
    out = fusion_engine.fuse_risk(_det(HealthStatus.CRITICAL), _ml("normal", 0.99))
    assert out["final_risk_level"] == "critical"
    assert out["fusion_method"] == "deterministic_override"


def test_deterministic_only_mode_reports_no_cap():
    out = fusion_engine.fuse_risk(_det(HealthStatus.WARNING), None)
    assert out["final_risk_level"] == "warning"
    assert out["fusion_method"] == "deterministic_only"
    assert out["ml_escalation_capped"] is False


# ── Missing blood pressure must not be fabricated as 120/80 ──────────────────

def test_missing_bp_stays_none_in_canonical_vector():
    feats = fusion_engine.create_canonical_feature_vector(_patient(), _vitals())
    assert feats.systolic_bp is None
    assert feats.diastolic_bp is None


def test_missing_bp_does_not_crash_or_trip_rules():
    feats = fusion_engine.create_canonical_feature_vector(_patient(), _vitals())
    out = fusion_engine.evaluate_deterministic_rules(feats)
    assert out["risk_class"] == HealthStatus.NORMAL


def test_hypertensive_crisis_still_detected_when_bp_present():
    feats = fusion_engine.create_canonical_feature_vector(
        _patient(), _vitals(systolic_bp=190.0, diastolic_bp=125.0)
    )
    out = fusion_engine.evaluate_deterministic_rules(feats)
    assert out["risk_class"] == HealthStatus.CRITICAL


# ── Imputation consistency (train == serve) ──────────────────────────────────

@pytest.fixture
def restore_medians():
    original = dict(prediction_service.medians)
    original_source = prediction_service.imputation_source
    yield
    prediction_service.medians = original
    prediction_service.imputation_source = original_source


def test_missing_values_use_medians_never_zero(restore_medians):
    """The previous implementation substituted 0.0 at inference while training
    imputed -1.0 — a train/serve skew that corrupted every prediction."""
    prediction_service.medians = {
        "heart_rate": 78.0,
        "spo2": 97.5,
        "temperature": 36.9,
        "systolic_bp": 118.0,
        "diastolic_bp": 76.0,
    }
    record = {
        "heart_rate": None,
        "spo2": float("nan"),
        "temperature": 37.2,
        # systolic_bp / diastolic_bp intentionally absent
    }

    assert prediction_service._resolve_feature(record, "heart_rate") == 78.0
    assert prediction_service._resolve_feature(record, "spo2") == 97.5
    assert prediction_service._resolve_feature(record, "temperature") == pytest.approx(37.2)
    assert prediction_service._resolve_feature(record, "systolic_bp") == 118.0
    assert prediction_service._resolve_feature(record, "diastolic_bp") == 76.0


def test_present_values_are_never_overwritten(restore_medians):
    prediction_service.medians = {"heart_rate": 78.0}
    assert prediction_service._resolve_feature({"heart_rate": 133.0}, "heart_rate") == 133.0
