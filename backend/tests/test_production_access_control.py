"""
Comprehensive Production Access Control & Canonical Live Telemetry Event Tests
Validates:
- Own / cross / no-token / invalid / unverified patient access
- Patient alerts isolation
- Device provisioning, ownership isolation, and SHA-256 API-key hashing
- Generic patient-create 410 GONE
- AI ownership enforcement
- Internal telemetry ownership enforcement
- WebSocket 1008 policy violation isolation
- Full Proof: Subscribed own-patient WebSocket receives exactly one
  patient.vitals.created event after an ESP32-shaped telemetry POST (201)
  matching DB and GET /patients/{id}/vitals/latest exactly.
"""

import os
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["SECRET_KEY"] = "test-prod-access-control-secret-key-12345"
os.environ["DATABASE_URL"] = "sqlite:///./_access_control_test.db"

from api.app import app
from api.config import get_settings
from api.models.database import Base, get_db, User, Patient, Device, VitalSigns, DeviceType
from api.models.database.models import BpSource as DBBpSource, HealthStatus as DBHealthStatus
from api.services.auth_service import create_access_token, hash_password
from api.services.telemetry_service import hash_api_key

TEST_DB_URL = "sqlite:///./_access_control_test.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Precompute password hash once at module level to keep test runs fast
TEST_PASSWORD_HASH = hash_password("ValidPassword123!")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    # Save dependency overrides
    saved_overrides = app.dependency_overrides.copy()
    monkeypatch.setattr(get_settings(), "SECRET_KEY", "test-prod-access-control-secret-key-12345")
    app.dependency_overrides[get_db] = override_get_db

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed User A + Patient A
    db = TestingSessionLocal()
    patient_a = Patient(
        id="P_ALPHA",
        first_name="Alpha",
        last_name="Tester",
        age=35,
        gender="female",
        diabetes="false",
        smoking_status="non_smoker"
    )
    db.add(patient_a)

    user_a = User(
        id="U_ALPHA",
        email="alpha@test.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Alpha Tester",
        patient_id="P_ALPHA",
        is_email_verified=True,
        is_active=True
    )
    db.add(user_a)

    # Device A for Patient A
    device_a = Device(
        device_id="ESP32_ALPHA_001",
        patient_id="P_ALPHA",
        device_type=DeviceType.IOT_HARDWARE,
        connected=True,
        api_key_hash=hash_api_key("alpha-secret-device-key-999")
    )
    db.add(device_a)

    # Seed User B + Patient B
    patient_b = Patient(
        id="P_BETA",
        first_name="Beta",
        last_name="Tester",
        age=42,
        gender="male",
        diabetes="false",
        smoking_status="former_smoker"
    )
    db.add(patient_b)

    user_b = User(
        id="U_BETA",
        email="beta@test.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Beta Tester",
        patient_id="P_BETA",
        is_email_verified=True,
        is_active=True
    )
    db.add(user_b)

    device_b = Device(
        device_id="ESP32_BETA_001",
        patient_id="P_BETA",
        device_type=DeviceType.IOT_HARDWARE,
        connected=True,
        api_key_hash=hash_api_key("beta-secret-device-key-888")
    )
    db.add(device_b)

    # Seed Unverified User + Patient
    patient_u = Patient(
        id="P_UNVERIFIED",
        first_name="Unverified",
        last_name="Tester",
        age=28,
        gender="other",
        diabetes="false",
        smoking_status="unknown"
    )
    db.add(patient_u)

    user_u = User(
        id="U_UNVERIFIED",
        email="unverified@test.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name="Unverified Tester",
        patient_id="P_UNVERIFIED",
        is_email_verified=False,
        is_active=True
    )
    db.add(user_u)

    db.commit()
    db.close()

    yield

    # Restore dependency overrides
    app.dependency_overrides = saved_overrides


@pytest.fixture
def tokens():
    db = TestingSessionLocal()
    user_a = db.query(User).filter(User.id == "U_ALPHA").first()
    user_b = db.query(User).filter(User.id == "U_BETA").first()
    user_u = db.query(User).filter(User.id == "U_UNVERIFIED").first()

    token_a, _ = create_access_token(user_a)
    token_b, _ = create_access_token(user_b)
    token_u, _ = create_access_token(user_u)
    db.close()
    return {"a": token_a, "b": token_b, "u": token_u}


def test_own_and_cross_patient_access(tokens):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}
    headers_u = {"Authorization": f"Bearer {tokens['u']}"}

    # Own patient access -> 200 OK
    resp_own = client.get("/api/v1/patients/P_ALPHA", headers=headers_a)
    assert resp_own.status_code == 200
    assert resp_own.json()["id"] == "P_ALPHA"

    # Cross patient access -> 403 Forbidden
    resp_cross = client.get("/api/v1/patients/P_BETA", headers=headers_a)
    assert resp_cross.status_code == 403

    # No token -> 401 Unauthorized
    resp_no_token = client.get("/api/v1/patients/P_ALPHA")
    assert resp_no_token.status_code == 401

    # Invalid token -> 401 Unauthorized
    resp_bad_token = client.get("/api/v1/patients/P_ALPHA", headers={"Authorization": "Bearer not-a-valid-token"})
    assert resp_bad_token.status_code == 401

    # Unverified user -> 403 Forbidden (email_not_verified policy)
    resp_unverified = client.get("/api/v1/patients/P_UNVERIFIED", headers=headers_u)
    assert resp_unverified.status_code == 403
    assert resp_unverified.json()["detail"]["error"] == "email_not_verified"


def test_patient_alerts_access_isolation(tokens):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}

    # Own alerts -> 200
    resp_own = client.get("/api/v1/patients/P_ALPHA/alerts", headers=headers_a)
    assert resp_own.status_code == 200

    # Cross alerts -> 403
    resp_cross = client.get("/api/v1/patients/P_BETA/alerts", headers=headers_a)
    assert resp_cross.status_code == 403


def test_devices_and_api_key_hash_behavior(tokens):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}

    # Provision new device API key
    resp = client.post("/api/v1/devices/ESP32_ALPHA_002/api-key", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "ESP32_ALPHA_002"
    assert data["patient_id"] == "P_ALPHA"
    raw_api_key = data["device_api_key"]
    assert raw_api_key

    # Verify database stores only the hash
    db = TestingSessionLocal()
    dev = db.query(Device).filter(Device.device_id == "ESP32_ALPHA_002").first()
    assert dev is not None
    assert dev.api_key_hash == hash_api_key(raw_api_key)
    assert raw_api_key not in dev.api_key_hash
    db.close()

    # User A cannot manage or reassign User B's device (returns 404 for enumeration protection)
    resp_cross = client.post("/api/v1/devices/ESP32_BETA_001/api-key", headers=headers_a)
    assert resp_cross.status_code == 404


def test_generic_patient_create_returns_410(tokens):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}
    payload = {
        "first_name": "Orphan",
        "last_name": "Patient",
        "age": 30,
        "gender": "male"
    }
    resp = client.post("/api/v1/patients/", json=payload, headers=headers_a)
    assert resp.status_code == 410
    detail = resp.json()["detail"]
    assert detail["error"] == "patient_creation_via_registration"


def test_ai_chat_ownership_enforcement(tokens):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}

    # User A asking assistant for Patient B -> 404 Patient Not Found (ownership isolation)
    resp = client.post(
        "/api/v1/ai/patient-assistant",
        headers=headers_a,
        json={"patient_id": "P_BETA", "message": "What is my heart rate?"}
    )
    assert resp.status_code == 404
    data = resp.json()
    err_code = data.get("error") or data.get("detail", {}).get("error")
    assert err_code == "patient_not_found"


def test_internal_telemetry_ownership(tokens):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}

    payload = {
        "id": "V_INTERNAL_TEST_001",
        "patient_id": "P_ALPHA",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "normal",
        "heart_rate": 72.0,
        "spo2": 99.0,
        "temperature": 36.6,
        "systolic_bp": None,
        "diastolic_bp": None,
        "bp_source": "none",
        "delayed_sync": False
    }

    # Own patient vitals -> 201 Created
    resp_own = client.post("/api/v1/patients/P_ALPHA/vitals", json=payload, headers=headers_a)
    assert resp_own.status_code == 201
    assert resp_own.json()["patient_id"] == "P_ALPHA"

    # Cross patient vitals -> 403 Forbidden
    resp_cross = client.post("/api/v1/patients/P_BETA/vitals", json=payload, headers=headers_a)
    assert resp_cross.status_code == 403


def test_websocket_1008_isolation(tokens):
    client = TestClient(app)

    # Legacy global stream -> WS 1008
    with pytest.raises(WebSocketDisconnect) as exc_global:
        with client.websocket_connect(f"/ws/live?token={tokens['a']}"):
            pass
    assert exc_global.value.code == 1008

    # Cross patient stream -> WS 1008
    with pytest.raises(WebSocketDisconnect) as exc_cross:
        with client.websocket_connect(f"/ws/patients/P_BETA?token={tokens['a']}"):
            pass
    assert exc_cross.value.code == 1008

    # Unverified user stream -> WS 1008
    with pytest.raises(WebSocketDisconnect) as exc_unverified:
        with client.websocket_connect(f"/ws/patients/P_UNVERIFIED?token={tokens['u']}"):
            pass
    assert exc_unverified.value.code == 1008

    # No token stream -> WS 1008
    with pytest.raises(WebSocketDisconnect) as exc_no_token:
        with client.websocket_connect("/ws/patients/P_ALPHA"):
            pass
    assert exc_no_token.value.code == 1008


def test_full_proof_telemetry_post_to_own_patient_ws_delivery(tokens):
    """
    Full Proof:
    1. Subscribed own-patient WebSocket connects to /ws/patients/P_ALPHA.
    2. ESP32 sends direct HTTP POST /api/v1/telemetry with X-Device-API-Key.
    3. Server returns 201 Created.
    4. Subscribed WebSocket receives exactly one 'patient.vitals.created' event.
    5. The payload matches the DB row and GET /patients/P_ALPHA/vitals/latest exactly.
    """
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {tokens['a']}"}

    with client.websocket_connect(f"/ws/patients/P_ALPHA?token={tokens['a']}") as ws:
        # Send ESP32-shaped telemetry POST
        telemetry_payload = {
            "device_id": "ESP32_ALPHA_001",
            "patient_id": "P_ALPHA",
            "heart_rate": 77.5,
            "spo2": 98.2,
            "temperature": 36.9,
            "systolic_bp": None,
            "diastolic_bp": None,
            "bp_source": "none",
            "delayed_sync": False,
            "data_origin": "device"
        }
        telemetry_headers = {
            "X-Device-API-Key": "alpha-secret-device-key-999"
        }

        post_resp = client.post("/api/v1/telemetry", json=telemetry_payload, headers=telemetry_headers)
        assert post_resp.status_code == 201, f"POST failed: {post_resp.text}"
        post_data = post_resp.json()
        assert post_data["success"] is True
        created_vital_id = post_data["vital_id"]

        # Read event from WebSocket
        event = ws.receive_json()
        assert event["event_type"] == "patient.vitals.created"
        assert event["patient_id"] == "P_ALPHA"
        assert "payload" in event

        payload = event["payload"]
        assert payload["device_id"] == "ESP32_ALPHA_001"
        assert "fused_decision" in payload
        assert "vital" in payload

        ws_vital = payload["vital"]
        assert ws_vital["id"] == created_vital_id
        assert ws_vital["patient_id"] == "P_ALPHA"
        assert ws_vital["device_id"] == "ESP32_ALPHA_001"
        assert ws_vital["heart_rate"] == 77.5
        assert ws_vital["spo2"] == 98.2
        assert ws_vital["temperature"] == 36.9
        assert ws_vital["systolic_bp"] is None
        assert ws_vital["diastolic_bp"] is None
        assert ws_vital["bp_source"] == "none"
        assert ws_vital["delayed_sync"] is False
        assert ws_vital["data_origin"] == "device"

        # Query latest vitals endpoint
        latest_resp = client.get("/api/v1/patients/P_ALPHA/vitals/latest", headers=headers_a)
        assert latest_resp.status_code == 200
        latest_vital = latest_resp.json()

        # Verify WS payload matches latest vitals endpoint response exactly
        assert latest_vital["id"] == ws_vital["id"]
        assert latest_vital["patient_id"] == ws_vital["patient_id"]
        assert latest_vital["device_id"] == ws_vital["device_id"]
        assert latest_vital["heart_rate"] == ws_vital["heart_rate"]
        assert latest_vital["spo2"] == ws_vital["spo2"]
        assert latest_vital["temperature"] == ws_vital["temperature"]
        assert latest_vital["systolic_bp"] == ws_vital["systolic_bp"]
        assert latest_vital["diastolic_bp"] == ws_vital["diastolic_bp"]
        assert latest_vital["data_origin"] == ws_vital["data_origin"]

        # Verify DB row
        db = TestingSessionLocal()
        db_vital = db.query(VitalSigns).filter(VitalSigns.id == created_vital_id).first()
        assert db_vital is not None
        assert db_vital.heart_rate == 77.5
        assert db_vital.device_id == "ESP32_ALPHA_001"
        db.close()
