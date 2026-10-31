"""
HealSense Local Database Seeding Utility for Mode A Testing
Usage in integrated terminal:
    python scripts/seed_local_db.py
"""

import hashlib
import os
import re
import secrets
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(REPO_ROOT)

DB_PATH = os.path.abspath(os.path.join(REPO_ROOT, "backend", "live_local.db"))
USER_EMAIL = "tester@healsense.example.com"
PATIENT_ID = "P001"
DEVICE_ID = "ESP32-001"

user_password = os.environ.get("LOCAL_TESTER_PASSWORD")
if not user_password:
    sys.stderr.write(
        "\n[ERROR] Environment variable LOCAL_TESTER_PASSWORD is not set or empty.\n"
        "Please set it first in this terminal session:\n"
        "    $env:LOCAL_TESTER_PASSWORD = \"<your-chosen-password>\"\n\n"
    )
    sys.exit(1)

print("=" * 65)
print(" [SEED] Recreating disposable local database: backend/live_local.db")
print("=" * 65)

# 1. Safely remove existing DB file if present
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
        print(f" [SEED] Removed previous database file: {DB_PATH}")
    except Exception as e:
        sys.stderr.write(f" [SEED] Error removing {DB_PATH}: {e}\n")
        sys.exit(1)

# 2. Inspect existing local firmware header if present (git-ignored)
header_path = os.path.join(REPO_ROOT, "firmware", "ESP32", "HealSense_ESP32_Monitor", "healsense_local_config.h")
existing_header_key = None
header_content = None

if os.path.exists(header_path):
    try:
        with open(header_path, "r", encoding="utf-8") as f:
            header_content = f.read()
        m = re.search(r'(?:static\s+)?const\s+char\*\s+API_KEY\s*=\s*"([^"]*)";', header_content)
        if m:
            existing_header_key = m.group(1)
    except Exception as e:
        sys.stderr.write(f" [SEED] Notice inspecting header: {e}\n")

secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
env_device_key = os.environ.get("LOCAL_DEVICE_API_KEY")

if env_device_key:
    device_raw_key = env_device_key
elif existing_header_key and existing_header_key != "YOUR_DEVICE_API_KEY":
    device_raw_key = existing_header_key
else:
    device_raw_key = f"probe_key_{secrets.token_hex(12)}"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = secret_key
os.environ["AUTH_ENFORCEMENT_ENABLED"] = "true"
os.environ["ALLOW_SIMULATED_TELEMETRY"] = "true"

# 3. Initialize schema and seed entities
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
from api.models.database import create_tables, get_db_context
from api.models.database.models import Device, DeviceType, Patient, User
from api.services.auth_service import hash_password

create_tables()
print(" [SEED] Database tables created via SQLAlchemy create_tables().")

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

print(f" [SEED] Seeded Patient: {PATIENT_ID}")
print(f" [SEED] Seeded User: {USER_EMAIL}")
print(f" [SEED] Seeded Device: {DEVICE_ID}")

# 4. Synchronize local firmware config header (git-ignored)
try:
    if header_content is None or not os.path.exists(header_path):
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
        print(" [SEED] Local firmware template config written to git-ignored header.")
    elif existing_header_key == device_raw_key:
        print(" [SEED] Preserving existing local firmware config (API_KEY matches DB; network fields preserved).")
    else:
        updated_content = re.sub(
            r'((?:static\s+)?const\s+char\*\s+API_KEY\s*=\s*")[^"]*(";)',
            r'\g<1>' + device_raw_key + r'\g<2>',
            header_content
        )
        updated_content = re.sub(
            r'((?:static\s+)?const\s+char\*\s+DEVICE_ID\s*=\s*")[^"]*(";)',
            r'\g<1>' + DEVICE_ID + r'\g<2>',
            updated_content
        )
        updated_content = re.sub(
            r'((?:static\s+)?const\s+char\*\s+PATIENT_ID\s*=\s*")[^"]*(";)',
            r'\g<1>' + PATIENT_ID + r'\g<2>',
            updated_content
        )
        with open(header_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(" [SEED] Targeted update applied to healsense_local_config.h (API_KEY updated; WIFI_SSID, WIFI_PASSWORD, and API_BASE preserved).")
except Exception as e:
    print(f" [SEED] Notice: could not synchronize local header: {e}")

print("=" * 65)
print(" [SEED] SUCCESS: backend/live_local.db is initialized and ready.")
print("=" * 65)

