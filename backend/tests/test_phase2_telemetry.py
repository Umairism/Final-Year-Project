"""
Phase 2 Comprehensive Telemetry Ingestion & Authentication Test Suite
Target: 100% Pass Rate
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import app
from api.models.database import Base, get_db, Patient, Device, VitalSigns, DeviceType
from api.models.database.models import BpSource as DBBpSource
from api.services.telemetry_service import hash_api_key

# In-memory SQLite database for fast isolated integration testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Seed Patient
    patient = Patient(
        id="p_12345",
        first_name="John",
        last_name="Doe",
        age=45,
        gender="male",
        diabetes="false",
        smoking_status="non_smoker"
    )
    db.add(patient)
    
    # Seed Authenticated Connected Device with hashed API Key
    raw_api_key = "secret_esp32_key_123"
    device = Device(
        device_id="ESP32_PATIENT_001",
        patient_id="p_12345",
        device_type=DeviceType.IOT_HARDWARE,
        connected=True,
        api_key_hash=hash_api_key(raw_api_key)
    )
    db.add(device)

    # Seed Disconnected / Disabled Device
    disabled_device = Device(
        device_id="ESP32_DISABLED_002",
        patient_id="p_12345",
        device_type=DeviceType.IOT_HARDWARE,
        connected=False,
        api_key_hash=hash_api_key("disabled_key")
    )
    db.add(disabled_device)

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# --- 1. Authentication Tests ---

def test_telemetry_valid_api_key():
    """Valid device ID and matching X-Device-API-Key header"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "heart_rate": 78.0,
        "spo2": 98.0,
        "temperature": 36.8,
        "systolic_bp": None,
        "diastolic_bp": None,
        "bp_source": "none",
        "delayed_sync": False
    }
    headers = {"X-Device-API-Key": "secret_esp32_key_123"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["device_id"] == "ESP32_PATIENT_001"
    assert data["patient_id"] == "p_12345"
    assert "fused_decision" in data


def test_telemetry_invalid_api_key():
    """Valid device ID but incorrect API Key header"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "heart_rate": 78.0,
        "spo2": 98.0,
        "temperature": 36.8
    }
    headers = {"X-Device-API-Key": "wrong_key_xyz"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid X-Device-API-Key"


def test_telemetry_missing_api_key():
    """Request missing X-Device-API-Key header"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "heart_rate": 78.0,
        "spo2": 98.0,
        "temperature": 36.8
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing X-Device-API-Key header"


def test_telemetry_disabled_device():
    """Submission from a disconnected/disabled device"""
    payload = {
        "device_id": "ESP32_DISABLED_002",
        "patient_id": "p_12345",
        "heart_rate": 78.0,
        "spo2": 98.0,
        "temperature": 36.8
    }
    headers = {"X-Device-API-Key": "disabled_key"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 401
    assert "disabled" in response.json()["detail"].lower()


# --- 2. Payload & Validation Tests ---

def test_telemetry_missing_required_fields():
    """Missing required heart_rate field"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "spo2": 98.0,
        "temperature": 36.8
    }
    headers = {"X-Device-API-Key": "secret_esp32_key_123"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 422


def test_telemetry_invalid_bp_source():
    """Invalid bp_source enum string"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "heart_rate": 78.0,
        "spo2": 98.0,
        "temperature": 36.8,
        "bp_source": "invalid_magic_source"
    }
    headers = {"X-Device-API-Key": "secret_esp32_key_123"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 422


def test_telemetry_unknown_patient():
    """Valid device key but non-existent patient ID"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "non_existent_patient_999",
        "heart_rate": 78.0,
        "spo2": 98.0,
        "temperature": 36.8
    }
    headers = {"X-Device-API-Key": "secret_esp32_key_123"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 404


# --- 3. Database Persistence & Metadata Tests ---

def test_telemetry_persistence_and_metadata():
    """Verify vital signs record, delayed_sync, and bp_source persistence"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "heart_rate": 84.0,
        "spo2": 97.0,
        "temperature": 37.2,
        "systolic_bp": 125.0,
        "diastolic_bp": 82.0,
        "bp_source": "ble_cuff",
        "delayed_sync": True
    }
    headers = {"X-Device-API-Key": "secret_esp32_key_123"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 201
    vital_id = response.json()["vital_id"]

    db = TestingSessionLocal()
    saved_vital = db.query(VitalSigns).filter(VitalSigns.id == vital_id).first()
    assert saved_vital is not None
    assert saved_vital.heart_rate == 84.0
    assert saved_vital.systolic_bp == 125.0
    assert saved_vital.bp_source == DBBpSource.BLE_CUFF
    assert saved_vital.delayed_sync is True
    db.close()


# --- 4. Pipeline Integration Tests (Deterministic Rules & Fusion) ---

def test_telemetry_critical_rules_override():
    """Critical SpO2 (<92%) triggers CRITICAL status override in fusion decision"""
    payload = {
        "device_id": "ESP32_PATIENT_001",
        "patient_id": "p_12345",
        "heart_rate": 95.0,
        "spo2": 89.0, # Critical Hypoxemia
        "temperature": 36.8
    }
    headers = {"X-Device-API-Key": "secret_esp32_key_123"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "critical"
    assert data["fused_decision"]["final_risk_level"] == "critical"
    assert "Severe Hypoxemia (SpO2 < 92%)" in data["fused_decision"]["deterministic_flags"]
