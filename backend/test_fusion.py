import sys
import os
import asyncio
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.models.schemas import CanonicalClinicalFeatureSchema
from api.models.database.models import Patient, VitalSigns, DeviceType, HealthStatus
from api.services.fusion_engine import fusion_engine
from api.services.prediction_service import prediction_service

async def run_test():
    print("Testing Canonical Feature Vector Creation...")
    # Mock Patient
    patient = Patient(
        id="P001",
        first_name="John",
        last_name="Doe",
        age=65,
        gender="male",
        diabetes="true",
        smoking_status="former_smoker",
        medications=["Metformin"],
        past_conditions=["Hypertension"]
    )
    
    # Mock Vitals
    vitals = VitalSigns(
        id="V001",
        patient_id="P001",
        heart_rate=125.0, # High
        spo2=96.0,
        temperature=37.2,
        systolic_bp=140.0,
        diastolic_bp=90.0,
        data_source=DeviceType.IOT_HARDWARE,
        timestamp=datetime.utcnow()
    )
    
    features = fusion_engine.create_canonical_feature_vector(patient, vitals)
    print("Features Created:", features.dict())
    
    print("\nTesting Deterministic Rules Engine...")
    det_out = fusion_engine.evaluate_deterministic_rules(features)
    print("Deterministic Output:", det_out)
    
    print("\nTesting Fusion...")
    ml_mock = {
        "probability": 0.65,
        "predicted_class": "warning"
    }
    fusion_out = fusion_engine.fuse_risk(det_out, ml_mock)
    print("Fusion Output:", fusion_out)
    
    print("\nSUCCESS: No syntax errors detected.")

if __name__ == "__main__":
    asyncio.run(run_test())
