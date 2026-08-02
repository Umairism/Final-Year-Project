"""
Phase 5 Synthetic Clinical Scenario Test Suite
Tests normal vitals, low oxygen hypoxemia override, temperature trend, and missing BP.
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from api.app import app
from api.models.database import Base, get_db, Patient, Device, VitalSigns, DeviceType
from api.services.telemetry_service import hash_api_key
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase5_simulation.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db_p5():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db_p5
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    patient = Patient(
        id="p_phase5",
        first_name="Bob",
        last_name="Taylor",
        age=50,
        gender="male"
    )
    db.add(patient)
    
    raw_api_key = "esp32_phase5_key"
    device = Device(
        device_id="ESP32_P5_001",
        patient_id="p_phase5",
        device_type=DeviceType.IOT_HARDWARE,
        connected=True,
        api_key_hash=hash_api_key(raw_api_key)
    )
    db.add(device)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)
headers = {"X-Device-API-Key": "esp32_phase5_key"}


def test_scenario_1_normal_patient():
    """Scenario 1: Normal vitals -> Risk: normal"""
    payload = {
        "device_id": "ESP32_P5_001",
        "patient_id": "p_phase5",
        "heart_rate": 75.0,
        "spo2": 98.0,
        "temperature": 36.7,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
        "bp_source": "ble_cuff"
    }
    res = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "normal"


def test_scenario_2_low_oxygen_override():
    """Scenario 2: Low oxygen (SpO2=88%) -> Deterministic override -> Risk: critical"""
    payload = {
        "device_id": "ESP32_P5_001",
        "patient_id": "p_phase5",
        "heart_rate": 110.0,
        "spo2": 88.0,
        "temperature": 37.0
    }
    res = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "critical"
    assert "Severe Hypoxemia (SpO2 < 92%)" in data["fused_decision"]["deterministic_flags"]


def test_scenario_3_temperature_trend_escalation():
    """Scenario 3: Temperature trend increase (36.8 -> 37.2 -> 37.8 -> 38.5)"""
    temps = [36.8, 37.2, 37.8, 38.5]
    statuses = []
    
    for t in temps:
        payload = {
            "device_id": "ESP32_P5_001",
            "patient_id": "p_phase5",
            "heart_rate": 80.0,
            "spo2": 97.0,
            "temperature": t
        }
        res = client.post("/api/v1/telemetry", json=payload, headers=headers)
        assert res.status_code == 201
        statuses.append(res.json()["status"])

    assert statuses[0] == "normal"
    assert statuses[-1] in ["warning", "critical"]


def test_scenario_4_missing_bp_resilience():
    """Scenario 4: Missing BP (systolic/diastolic null) -> System processes cleanly without fake imputation"""
    payload = {
        "device_id": "ESP32_P5_001",
        "patient_id": "p_phase5",
        "heart_rate": 72.0,
        "spo2": 99.0,
        "temperature": 36.5,
        "systolic_bp": None,
        "diastolic_bp": None,
        "bp_source": "none"
    }
    res = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["success"] is True
