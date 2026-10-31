"""
scripts/run_l2_pipe_proof.py
Executes the real local L2 pipe check against a disposable local SQLite backend.
Zero hardcoded passwords, tokens, or device keys.
"""

import asyncio
import hashlib
import json
import os
import secrets
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    import websockets
except ImportError:
    websockets = None

DB_FILE = os.path.abspath(os.path.join("backend", "live_local.db"))
DB_URL = f"sqlite:///{DB_FILE}"
USER_EMAIL = "tester@healsense.example.com"
PATIENT_ID = "P001"
DEVICE_ID = "ESP32-001"


def setup_database():
    print("=" * 70)
    print(" [L2 SETUP] PREPARING DISPOSABLE LOCAL SQLITE DATABASE")
    print("=" * 70)
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass

    secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    device_raw_key = os.environ.get("LOCAL_DEVICE_API_KEY") or f"probe_key_{secrets.token_hex(12)}"
    user_password = os.environ.get("LOCAL_TESTER_PASSWORD") or secrets.token_urlsafe(16)

    os.environ["DATABASE_URL"] = DB_URL
    os.environ["SECRET_KEY"] = secret_key
    os.environ["AUTH_ENFORCEMENT_ENABLED"] = "true"
    os.environ["ALLOW_SIMULATED_TELEMETRY"] = "true"

    sys.path.insert(0, "backend")
    from api.models.database import create_tables, get_db_context
    from api.models.database.models import Device, DeviceType, Patient, User
    from api.services.auth_service import create_access_token, hash_password

    create_tables()
    print(" [L2 SETUP] Tables created via api.models.database.create_tables()")

    with get_db_context() as db:
        p = Patient(
            id=PATIENT_ID,
            first_name="Local",
            last_name="Tester",
            age=32,
            gender="other",
            email=USER_EMAIL,
        )
        db.add(p)
        db.commit()

        u = User(
            id="user_l2_tester",
            email=USER_EMAIL,
            password_hash=hash_password(user_password),
            full_name="Local Tester",
            patient_id=PATIENT_ID,
            is_email_verified=True,
            is_active=True,
        )
        db.add(u)
        db.commit()

        d = Device(
            device_id=DEVICE_ID,
            patient_id=PATIENT_ID,
            device_type=DeviceType.IOT_HARDWARE,
            api_key_hash=hashlib.sha256(device_raw_key.encode("utf-8")).hexdigest(),
            connected=True,
        )
        db.add(d)
        db.commit()

        token, _ = create_access_token(u)
    print(f" [L2 SETUP] Patient {PATIENT_ID}, User, and Device {DEVICE_ID} provisioned.")

    # Write git-ignored healsense_local_config.h
    header_path = os.path.join("firmware", "ESP32", "HealSense_ESP32_Monitor", "healsense_local_config.h")
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(
            f'#ifndef HEALSENSE_LOCAL_CONFIG_H\n'
            f'#define HEALSENSE_LOCAL_CONFIG_H\n\n'
            f'#define ENABLE_WIFI_UPLOAD 1\n\n'
            f'static const char* WIFI_SSID     = "LOCAL_TEST_SSID";\n'
            f'static const char* WIFI_PASSWORD = "LOCAL_TEST_PASSWORD";\n'
            f'static const char* API_BASE       = "http://127.0.0.1:5000";\n'
            f'static const char* TELEMETRY_PATH = "/api/v1/telemetry";\n'
            f'static const char* DEVICE_ID      = "{DEVICE_ID}";\n'
            f'static const char* PATIENT_ID     = "{PATIENT_ID}";\n'
            f'static const char* API_KEY        = "{device_raw_key}";\n\n'
            f'#endif // HEALSENSE_LOCAL_CONFIG_H\n'
        )
    print(f" [L2 SETUP] Firmware config written to git-ignored header.")

    return token, device_raw_key, secret_key


def count_db_rows() -> int:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vital_signs WHERE patient_id = ?", (PATIENT_ID,))
    count = cur.fetchone()[0]
    conn.close()
    return count


async def execute_l2_proof(token: str, backend_proc: subprocess.Popen, device_key: str) -> bool:
    print("\n" + "=" * 70)
    print(" [L2 EXECUTION] RUNNING AUTHENTICATED TELEMETRY PIPELINE PROBE")
    print("=" * 70)

    # 1. DB count before
    count_before = count_db_rows()
    print(f" 1. DB row count before probe: {count_before}")

    # 2. Connect WebSocket
    ws_url = f"ws://127.0.0.1:5000/ws/patients/{PATIENT_ID}?token={token}"
    print(f" 2. Connecting to WebSocket: ws://127.0.0.1:5000/ws/patients/{PATIENT_ID}?token=***")
    ws = await asyncio.wait_for(websockets.connect(ws_url), timeout=5.0)
    print("    WebSocket handshake completed (101 Switching Protocols). Subscribed to own-patient events.")

    # 3. HTTP Telemetry POST
    post_payload = {
        "device_id": DEVICE_ID,
        "patient_id": PATIENT_ID,
        "heart_rate": 82.5,
        "spo2": 97.5,
        "temperature": 36.9,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_origin": "simulated",
    }
    body = json.dumps(post_payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/v1/telemetry",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Device-API-Key": device_key,
        },
        method="POST",
    )

    print(" 3. Injecting ESP32 telemetry probe via HTTP POST /api/v1/telemetry...")
    with urllib.request.urlopen(req, timeout=5) as resp:
        post_status = resp.getcode()
        post_body = json.loads(resp.read().decode("utf-8"))
        print(f"    POST Response Status: {post_status}")
        vital_id = post_body.get("vital_id") or (post_body.get("vital") or {}).get("id")
        print(f"    Created Vital ID: {vital_id}")
        assert post_status == 201, f"Expected 201 Created, got {post_status}"

    # 4. DB count after
    time.sleep(0.2)
    count_after = count_db_rows()
    print(f" 4. DB row count after probe: {count_after}")
    assert count_after == count_before + 1, f"Expected {count_before + 1} rows, found {count_after}"
    print("    PROVED: Exactly ONE new row committed in vital_signs table.")

    # 5. Receive WebSocket message
    print(" 5. Waiting for canonical WebSocket broadcast event...")
    ws_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
    event_data = json.loads(ws_msg)
    print(f"    Received event_type: '{event_data.get('event_type')}'")
    assert event_data.get("event_type") == "patient.vitals.created", f"Unexpected event: {event_data}"
    ws_vital = event_data.get("payload", {}).get("vital", {})
    print(f"    WebSocket vital payload: id={ws_vital.get('id')}, HR={ws_vital.get('heart_rate')}, SpO2={ws_vital.get('spo2')}")
    assert ws_vital.get("id") == vital_id, f"ID mismatch: {ws_vital.get('id')} vs {vital_id}"
    assert ws_vital.get("heart_rate") == 82.5
    assert ws_vital.get("spo2") == 97.5
    print("    PROVED: WebSocket delivered patient.vitals.created with matching serialized vital.")
    await ws.close()

    # 6. Own-token GET /latest
    print(" 6. Querying /api/v1/patients/P001/vitals/latest with Bearer token...")
    req_latest = urllib.request.Request(
        f"http://127.0.0.1:5000/api/v1/patients/{PATIENT_ID}/vitals/latest",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req_latest, timeout=5) as resp:
        assert resp.getcode() == 200
        latest_data = json.loads(resp.read().decode("utf-8"))
        print(f"    GET /latest response: id={latest_data.get('id')}, HR={latest_data.get('heart_rate')}, SpO2={latest_data.get('spo2')}")
        assert latest_data.get("id") == vital_id
        assert latest_data.get("heart_rate") == 82.5
        assert latest_data.get("spo2") == 97.5
        print("    PROVED: Own-token latest vitals matches committed DB record.")

    print("=" * 70)
    print(" [L2 VERIFICATION] ALL 6 CHECKS PASSED: END-TO-END PIPE PROVEN")
    print("=" * 70)
    return True


def main():
    token, device_key, secret_key = setup_database()

    # Launch local backend server
    print("\nStarting local backend server on 127.0.0.1:5000...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "backend"
    env["DATABASE_URL"] = DB_URL
    env["SECRET_KEY"] = secret_key
    env["AUTH_ENFORCEMENT_ENABLED"] = "true"
    env["ALLOW_SIMULATED_TELEMETRY"] = "true"
    env["PORT"] = "5000"
    env["HOST"] = "127.0.0.1"

    py_bin = sys.executable
    log_file_path = os.path.join("backend", "uvicorn_l2.log")
    log_file = open(log_file_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [py_bin, "-m", "uvicorn", "api.app:app", "--host", "127.0.0.1", "--port", "5000", "--log-level", "warning"],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(f"Backend started with PID: {proc.pid} (logging to {log_file_path})")

    # Wait for health endpoint
    ready = False
    for attempt in range(25):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=1) as resp:
                if resp.getcode() == 200:
                    ready = True
                    print(f"Backend health confirmed on attempt {attempt + 1}")
                    break
        except Exception:
            if proc.poll() is not None:
                print(f"Backend process terminated unexpectedly.")
                sys.exit(1)

    if not ready:
        print("Backend failed to become healthy within 12 seconds.")
        proc.kill()
        sys.exit(1)

    try:
        success = asyncio.run(execute_l2_proof(token, proc, device_key))
    finally:
        print(f"\nStopping backend process (PID {proc.pid})...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log_file.close()
        print(f"Backend process (PID {proc.pid}) stopped successfully.")

    if not success:
        sys.exit(1)
    print("\nL2 Pipe Check Result: PASS (real execution verified).")


if __name__ == "__main__":
    main()
