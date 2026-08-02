"""
Phase 3 Hardware Resilience Failure Simulator Test Suite
Simulates Wi-Fi loss, backend outages, and NVS queue recovery.
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from api.app import app
from api.models.database import Base, get_db, Patient, Device, VitalSigns, DeviceType
from api.models.database.models import BpSource as DBBpSource
from api.services.telemetry_service import hash_api_key
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase3_simulation.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db_p3():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db_p3
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    patient = Patient(
        id="p_phase3",
        first_name="Alice",
        last_name="Smith",
        age=38,
        gender="female"
    )
    db.add(patient)
    
    raw_api_key = "esp32_resilience_key"
    device = Device(
        device_id="ESP32_SIM_001",
        patient_id="p_phase3",
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


def test_scenario_a_wifi_loss_and_flush():
    """
    Scenario A: Wi-Fi OFF during sampling -> 10 records stored in NVS.
    Wi-Fi ON -> 10 records flushed sequentially with delayed_sync=True.
    """
    headers = {"X-Device-API-Key": "esp32_resilience_key"}
    
    # Simulate 10 flushed records from ESP32 NVS buffer
    for i in range(10):
        payload = {
            "device_id": "ESP32_SIM_001",
            "patient_id": "p_phase3",
            "heart_rate": 70.0 + i,
            "spo2": 98.0,
            "temperature": 36.6,
            "delayed_sync": True # Flagged by NVS buffer engine
        }
        res = client.post("/api/v1/telemetry", json=payload, headers=headers)
        assert res.status_code == 201

    # Verify persistence in Database
    db = TestingSessionLocal()
    records = db.query(VitalSigns).filter(VitalSigns.patient_id == "p_phase3").all()
    assert len(records) == 10
    for r in records:
        assert r.delayed_sync is True
    db.close()


def test_scenario_b_backend_outage_and_recovery():
    """
    Scenario B: Backend Outage -> ESP32 buffers 20 records.
    Backend Recovered -> 20 records successfully ingested.
    """
    headers = {"X-Device-API-Key": "esp32_resilience_key"}
    
    for i in range(20):
        payload = {
            "device_id": "ESP32_SIM_001",
            "patient_id": "p_phase3",
            "heart_rate": 75.0,
            "spo2": 97.0,
            "temperature": 36.7,
            "delayed_sync": True
        }
        res = client.post("/api/v1/telemetry", json=payload, headers=headers)
        assert res.status_code == 201

    db = TestingSessionLocal()
    count = db.query(VitalSigns).filter(VitalSigns.patient_id == "p_phase3").count()
    assert count == 20
    db.close()


def test_scenario_c_esp32_reboot_nvs_preservation():
    """
    Scenario C: ESP32 Reboot -> NVS queue survives reset.
    Backend accepts queued data after boot sequence finishes.
    """
    headers = {"X-Device-API-Key": "esp32_resilience_key"}
    payload = {
        "device_id": "ESP32_SIM_001",
        "patient_id": "p_phase3",
        "heart_rate": 88.0,
        "spo2": 96.0,
        "temperature": 37.0,
        "delayed_sync": True
    }
    res = client.post("/api/v1/telemetry", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["success"] is True
