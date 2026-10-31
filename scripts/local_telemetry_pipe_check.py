"""
====================================================================
[SIMULATOR PIPE CHECK] — LOCAL TELEMETRY PIPE CHECK UTILITY
NOTE: THIS IS A SYNTHETIC TEST PROBE FOR VERIFYING PIPELINE INTEGRITY.
IT DOES NOT CONSTITUTE REAL PATIENT OR PHYSICAL HARDWARE EVIDENCE.
====================================================================
"""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

try:
    import websockets
except ImportError:
    websockets = None


def count_db_vitals(db_path: str, patient_id: str) -> Optional[int]:
    if not db_path or not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vital_signs WHERE patient_id = ?", (patient_id,))
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[SIMULATOR PIPE CHECK] Warning reading DB count: {e}")
        return None


async def run_full_l2_pipe_check(
    base_url: str,
    device_id: str,
    patient_id: str,
    api_key: str,
    auth_token: Optional[str] = None,
    db_path: Optional[str] = None,
    heart_rate: float = 78.0,
    spo2: float = 98.0,
    temperature: float = 36.8,
) -> bool:
    print("=" * 70)
    print(" [SIMULATOR PIPE CHECK] INITIATING SYNTHETIC PIPELINE PROBE")
    print(" WARNING: SIMULATED DATA ONLY - NOT REAL PATIENT EVIDENCE")
    print("=" * 70)
    print(f"Target URL:    {base_url}/api/v1/telemetry")
    print(f"Device ID:     {device_id}")
    print(f"Patient ID:    {patient_id}")
    print(f"Telemetry:     HR={heart_rate} bpm, SpO2={spo2}%, Temp={temperature} C")
    if db_path:
        print(f"Database Path: {db_path}")
    print("-" * 70)

    # 1. DB count before
    initial_db_count = count_db_vitals(db_path, patient_id) if db_path else None
    if initial_db_count is not None:
        print(f"[1/5 DB PRE-CHECK] Current DB vital rows for {patient_id}: {initial_db_count}")

    # 2. WebSocket listener setup
    ws_received_event = None
    ws_task = None
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_endpoint = f"{ws_url.rstrip('/')}/ws/patients/{patient_id}"
    if auth_token:
        ws_endpoint += f"?token={auth_token}"

    ws_client = None
    if auth_token and websockets is not None:
        try:
            print(f"[2/5 WS CONNECT] Connecting to WebSocket: {ws_url}/ws/patients/{patient_id}?token=***")
            ws_client = await asyncio.wait_for(websockets.connect(ws_endpoint), timeout=5.0)
            print("[2/5 WS CONNECT] WebSocket connection established successfully.")
        except Exception as e:
            print(f"[2/5 WS CONNECT] WebSocket connection failed or skipped: {e}")
            ws_client = None

    # 3. HTTP Telemetry POST
    post_success = False
    posted_vital_id = None
    try:
        payload = {
            "device_id": device_id,
            "patient_id": patient_id,
            "heart_rate": heart_rate,
            "spo2": spo2,
            "temperature": temperature,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data_origin": "simulated",
        }
        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/v1/telemetry",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Device-API-Key": api_key,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            print(f"[3/5 HTTP POST] Status: {status_code}")
            resp_json = json.loads(response_body)
            posted_vital_id = resp_json.get("vital_id") or (resp_json.get("vital") or {}).get("id")
            print(f"[3/5 HTTP POST] Success (Vital ID: {posted_vital_id})")
            if status_code in (200, 201):
                post_success = True
    except urllib.error.HTTPError as e:
        error_detail = e.read().decode("utf-8")
        print(f"[3/5 HTTP POST] HTTP ERROR {e.code}: {error_detail}")
        if ws_client:
            await ws_client.close()
        return False
    except Exception as e:
        print(f"[3/5 HTTP POST] POST FAILED: {e}")
        if ws_client:
            await ws_client.close()
        return False

    if not post_success:
        if ws_client:
            await ws_client.close()
        return False

    # 4. DB count verification (exactly +1 new row)
    db_verified = True
    if db_path and initial_db_count is not None:
        time.sleep(0.1)
        final_db_count = count_db_vitals(db_path, patient_id)
        print(f"[4/5 DB POST-CHECK] Final DB vital rows for {patient_id}: {final_db_count}")
        if final_db_count == initial_db_count + 1:
            print("[4/5 DB POST-CHECK] PROVED: Exactly ONE new DB row committed.")
        else:
            print(f"[4/5 DB POST-CHECK] FAILED: Expected {initial_db_count + 1} rows, found {final_db_count}.")
            db_verified = False

    # 5. Authenticated Latest GET & WS Receive
    ws_verified = False
    if ws_client:
        try:
            msg = await asyncio.wait_for(ws_client.recv(), timeout=5.0)
            event_data = json.loads(msg)
            print(f"[5/5 WS RECEIVE] Received event type: '{event_data.get('event_type')}'")
            if event_data.get("event_type") == "patient.vitals.created":
                payload_vital = event_data.get("payload", {}).get("vital", {})
                received_id = payload_vital.get("id")
                received_hr = payload_vital.get("heart_rate")
                print(f"[5/5 WS RECEIVE] PROVED: Event matches vital ID={received_id}, HR={received_hr}")
                ws_verified = True
            else:
                print(f"[5/5 WS RECEIVE] Unexpected event: {event_data}")
        except Exception as e:
            print(f"[5/5 WS RECEIVE] WS recv error: {e}")
        finally:
            await ws_client.close()

    latest_verified = False
    if auth_token:
        try:
            req_latest = urllib.request.Request(
                f"{base_url.rstrip('/')}/api/v1/patients/{patient_id}/vitals/latest",
                headers={"Authorization": f"Bearer {auth_token}"},
                method="GET",
            )
            with urllib.request.urlopen(req_latest, timeout=5) as resp:
                if resp.getcode() == 200:
                    latest_data = json.loads(resp.read().decode("utf-8"))
                    latest_hr = latest_data.get("heart_rate")
                    latest_spo2 = latest_data.get("spo2")
                    print(f"[LATEST GET] PROVED: Own-token GET /latest returned HR={latest_hr}, SpO2={latest_spo2}")
                    if latest_hr == heart_rate and latest_spo2 == spo2:
                        latest_verified = True
        except Exception as e:
            print(f"[LATEST GET] Latest query error: {e}")

    print("-" * 70)
    all_ok = post_success and db_verified and (ws_verified if auth_token else True) and (latest_verified if auth_token else True)
    if all_ok:
        print("[SIMULATOR PIPE CHECK] SUCCESS: Entire telemetry ingress and live pipe verified.")
    else:
        print("[SIMULATOR PIPE CHECK] FAILED: One or more pipeline stages did not verify.")
    print("=" * 70)
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Local ESP32 Telemetry Pipe Check (Synthetic Probe Only)"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Backend base URL")
    parser.add_argument("--device-id", default="ESP32-001", help="Device identifier")
    parser.add_argument("--patient-id", default="P001", help="Assigned patient identifier")
    parser.add_argument("--db-path", default=None, help="Path to local sqlite database file")
    parser.add_argument("--heart-rate", type=float, default=78.0, help="Test heart rate")
    parser.add_argument("--spo2", type=float, default=98.0, help="Test SpO2")
    parser.add_argument("--temperature", type=float, default=36.8, help="Test temperature")

    args = parser.parse_args()

    api_key = os.environ.get("HEALSENSE_DEVICE_API_KEY")
    if not api_key:
        sys.stderr.write(
            "ERROR: Missing environment variable HEALSENSE_DEVICE_API_KEY.\n"
            "Pass device credentials via process environment variables only; command-line secret passing is forbidden.\n"
        )
        sys.exit(1)

    auth_token = os.environ.get("HEALSENSE_AUTH_TOKEN")

    success = asyncio.run(
        run_full_l2_pipe_check(
            base_url=args.base_url,
            device_id=args.device_id,
            patient_id=args.patient_id,
            api_key=api_key,
            auth_token=auth_token,
            db_path=args.db_path,
            heart_rate=args.heart_rate,
            spo2=args.spo2,
            temperature=args.temperature,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
