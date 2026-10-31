# HealSense Live ESP32 Wi-Fi Telemetry Runbook & Verification Guide

## 1. Scope & System Architecture

This runbook defines the canonical procedures for provisioning, local UI testing, and physical ESP32 Wi-Fi telemetry streaming into the HealSense platform.

### Canonical Telemetry Pipeline
```
┌──────────────────────────────────────────────┐
│             ESP32 DevKit Prototype           │
│  • MAX30102 (HR + SpO2) [I2C 0x57]           │
│  • MLX90614 (Infrared Temp) [I2C 0x5A]       │
│  • SSD1306 OLED (128x64) [I2C 0x3C]          │
└──────────────────────┬───────────────────────┘
                       │ HTTP POST /api/v1/telemetry
                       │ Header: X-Device-API-Key: <DEVICE_KEY>
                       │ Payload: {device_id, patient_id, heart_rate, spo2, temperature, timestamp}
                       ▼
┌──────────────────────────────────────────────┐
│               FastAPI Backend                │
│  • SHA-256 device key verification          │
│  • Imputation + Dual-channel LSTM inference  │
│  • SQLite (local) / PostgreSQL (production)  │
└──────────────────────┬───────────────────────┘
                       │ Authenticated WebSocket: /ws/patients/{patient_id}?token={JWT}
                       │ Broadcast Event: patient.vitals.created
                       │ Payload: {vital: SerializedVital, device_id, fused_decision}
                       ├─────────────────────────────────┐
                       ▼                                 ▼
┌──────────────────────────────────────────────┐ ┌──────────────────────────────────────────────┐
│                React Web App                 │ │              Flutter Mobile App              │
│  • Vital ID deduplication                    │ │  • Vital ID deduplication                    │
│  • Strictly ascending timestamp ordering     │ │  • Strictly ascending timestamp ordering     │
│  • Live metric cards & trend charts          │ │  • Real-time dashboard view                  │
└──────────────────────────────────────────────┘ └──────────────────────────────────────────────┘
```

> **TELEMETRY POLICY**: Wi-Fi REST POST `/api/v1/telemetry` is the sole telemetry ingress path. Bluetooth/BLE telemetry is disabled.

---

## 2. Firmware Identity & Secret Isolation

- **Canonical Sketch**: `firmware/ESP32/HealSense_ESP32_Monitor/HealSense_ESP32_Monitor.ino`
- **Build Identity**: `HEALSENSE-ESP32 v3.3 CHANNEL-FIX (2026-10-27)`
- **Arena v3.3 Baseline SHA-256**: `9eae2514cfe485552605c4a3b766c0c8bef73e4dc3fa6301bccc7f908da79780`
- **Zero-Secret Architecture**: Credentials are never hardcoded in tracked files. The sketch includes `healsense_local_config.h` via `__has_include`, which is strictly ignored by Git.

### Verification of Local Config Isolation
```powershell
git check-ignore -v firmware/ESP32/HealSense_ESP32_Monitor/healsense_local_config.h
# Expected output: .gitignore:112:**/healsense_local_config.h
```

---

## 3. Operational Modes

> **Placeholder Reference**:
> - `<PYTHON>`: Python executable in virtual environment (e.g., `python` or `<REPO_ROOT>/backend/.venv/Scripts/python.exe`).
> - `<REPO_ROOT>`: Local repository root path.
> - `<LAN_IP>`: Workstation host private IPv4 address on local Wi-Fi.
> - `<ESP32_IP>`: Private IPv4 address assigned to the ESP32 by the local router.
> - `<WIFI_SSID>`: Name of the local 2.4 GHz Wi-Fi network.

### MODE A: Same-Laptop Browser Visual Test
*For operator visual verification of React Web and Flutter interfaces without physical hardware.*

1. **Prepare Process-Only Environment (PowerShell)**:
   ```powershell
   # Set process-only variables (never committed to repository)
   $env:PYTHONPATH="backend"
   $env:DATABASE_URL="sqlite:///./backend/live_local.db"
   $env:SECRET_KEY="<OPERATOR_SESSION_SECRET_32_BYTES>"
   $env:AUTH_ENFORCEMENT_ENABLED="true"
   $env:ALLOW_SIMULATED_TELEMETRY="true"
   ```
2. **Start Backend Server**:
   ```powershell
   & "<PYTHON>" -m uvicorn api.app:app --host 127.0.0.1 --port 5000
   ```
   Verify health: `Invoke-RestMethod http://127.0.0.1:5000/health` -> `status: healthy`.
3. **Launch React Web Dashboard**:
   ```powershell
   cd frontend/web-app
   $env:VITE_API_BASE_URL="http://127.0.0.1:5000/api/v1"
   $env:VITE_WS_URL="ws://127.0.0.1:5000"
   npm run dev -- --host 127.0.0.1 --port 8080
   ```
   Open `http://127.0.0.1:8080` in browser. Log in with your local test account (`tester@healsense.example.com`).
4. **Launch Flutter Web Client (Optional)**:
   ```powershell
   cd frontend/mobile-app
   flutter run -d chrome --web-port 8081 --dart-define=API_BASE_URL=http://127.0.0.1:5000/api/v1 --dart-define=WS_BASE_URL=ws://127.0.0.1:5000
   ```
5. **Inject Simulated Telemetry Probe**:
   ```powershell
   $env:HEALSENSE_DEVICE_API_KEY="<PROVISIONED_DEVICE_KEY>"
   & "<PYTHON>" scripts/local_telemetry_pipe_check.py --base-url http://127.0.0.1:5000 --device-id ESP32-001 --patient-id P001
   ```
6. **Visual Confirmation**: Observe vital sign card update instantly in browser without manual page reload.
   - **Mode A Visual Gate**: **PASS (2026-10-31)**
   - **Classification**: **SIMULATOR ONLY** (*Does not constitute physical hardware proof*).
   - **Operator Verification**:
     - React Web (`http://127.0.0.1:8080`): Verified instant WebSocket card update (HR 78 bpm, SpO2 98%, Temp 36.8 °C, BP "Not measured") without manual page reload.
     - Flutter Web (`http://127.0.0.1:8081`): Verified instant WebSocket card update (identical values) without manual page reload.
     - Injected probe: Mode A simulated reading (HR 78 bpm, SpO2 98%, Temp 36.8 °C), Device `ESP32-001`, `data_origin: simulated`.

---

### MODE B: ESP32 LAN Hardware Test
*For streaming real sensor telemetry from physical ESP32 hardware across your local Wi-Fi network.*

1. **Network & Firewall Preflight**:
   - Ensure your laptop and the ESP32 are connected to the **same 2.4 GHz Wi-Fi SSID** (`<WIFI_SSID>`).
   - Verify Windows Firewall allows incoming connections on Private networks for Python:
     ```powershell
     Get-NetFirewallRule -DisplayName "*Python*" | Select-Object Name, Enabled, Direction, Profile
     ```
   - Determine laptop WLAN IPv4 address:
     ```powershell
     (Get-NetIPAddress -InterfaceAlias "*Wi-Fi*" -AddressFamily IPv4).IPAddress
     # Example: <LAN_IP>
     ```
2. **Start Backend Bound to LAN**:
   ```powershell
   $env:PYTHONPATH="backend"
   $env:DATABASE_URL="sqlite:///./backend/live_local.db"
   $env:SECRET_KEY="<OPERATOR_SESSION_SECRET_32_BYTES>"
   $env:AUTH_ENFORCEMENT_ENABLED="true"
   $env:ALLOW_SIMULATED_TELEMETRY="false"
   & "<PYTHON>" -m uvicorn api.app:app --host 0.0.0.0 --port 5000
   ```
3. **Verify LAN Reachability**:
   From another device on the same Wi-Fi (e.g. mobile phone browser):
   Open `http://<LAN_IP>:5000/health`. Confirm `{"status": "healthy"}` is returned.
4. **Configure Local Firmware Header**:
   In `firmware/ESP32/HealSense_ESP32_Monitor/healsense_local_config.h` (git-ignored):
   ```c
   #ifndef HEALSENSE_LOCAL_CONFIG_H
   #define HEALSENSE_LOCAL_CONFIG_H

   #define ENABLE_WIFI_UPLOAD 1

   static const char* WIFI_SSID     = "<WIFI_SSID>";
   static const char* WIFI_PASSWORD = "<YOUR_WIFI_PASSWORD>";
   static const char* API_BASE       = "http://<LAN_IP>:5000"; // NO trailing slash!
   static const char* TELEMETRY_PATH = "/api/v1/telemetry";
   static const char* DEVICE_ID      = "ESP32-001";
   static const char* PATIENT_ID     = "P001";
   static const char* API_KEY        = "<PROVISIONED_DEVICE_KEY>";

   #endif
   ```
5. **Viewing UI Clients on LAN**:
   If viewing from other devices on the LAN, configure frontend clients with `http://<LAN_IP>:5000/api/v1` and `ws://<LAN_IP>:5000`.

---

### MODE C: Cloud Future Deployment
*For production deployment on remote Oracle Cloud Infrastructure.*

- **Transport Security**: Telemetry must use HTTPS (`https://api.yourdomain.com/api/v1/telemetry`) and WSS (`wss://api.yourdomain.com`). Raw HTTP and plain device keys over the public internet are strictly forbidden.
- **Port Isolation**: Ports 5000 (FastAPI) and 5432 (PostgreSQL) must have **zero public ingress rules** in the Oracle VCN Security List. Only ports 80, 443, and SSH (port 22 restricted to operator IP/CIDR) may be permitted.
- **TLS Termination**: Host-level reverse proxy (Nginx or Caddy) terminates TLS with valid Let's Encrypt certificates.
- **ESP32 Prototype Notice**: Prototype firmware uses basic HTTP/HTTPS clients. Root certificate anchoring and mutual TLS (mTLS) are recommended before full public device deployment.

---

## 4. One-Page Operator Hardware Sequence (L3 Readiness)

Follow this ordered procedure when executing the physical ESP32 flashing and measurement session:

```
[1. POWER DISCONNECT] ──> [2. SOFTWARE GATES] ──> [3. FLASH ARDUINO] ──> [4. BOOT EVIDENCE]
         │
         ▼
[5. FINGER PLACEMENT] ──> [6. CAPTURE READINGS] ──> [7. EVIDENCE GATHERING] ──> [8. SAFE POWER OFF]
```

### Step 1: Power & Wiring Safety
- **ALWAYS disconnect the USB cable and power source** before touching sensor pins or jumper wires.
- Verify wiring on the shared I2C bus:
  - **MAX30102** (0x57): VIN -> 3V3, GND -> GND, SDA -> GPIO 21, SCL -> GPIO 22.
  - **MLX90614** (0x5A): VIN -> 3V3, GND -> GND, SDA -> GPIO 21, SCL -> GPIO 22.
  - **SSD1306 OLED** (0x3C): VDD -> 3V3, GND -> GND, SDA -> GPIO 21, SCK -> GPIO 22.
  > **CAUTION**: Check silkscreen on your OLED board! If the pins read `GND | VDD`, do not swap them. Reversed power destroys SSD1306 chips instantly.

### Step 2: Software Readiness Gates
- [ ] Backend is running on `0.0.0.0:5000` (Mode B).
- [ ] LAN pre-check returns HTTP 200 from `http://<LAN_IP>:5000/health`.
- [ ] Device row exists in database matching `DEVICE_ID` with SHA-256 hash of `API_KEY`.
- [ ] `healsense_local_config.h` is confirmed git-ignored (`git check-ignore -v` passes).
- [ ] Credentials in `healsense_local_config.h` are confirmed local (never committed or shared in chat).

### Step 3: Arduino IDE Flashing
1. Connect ESP32 to laptop via USB data cable.
2. Open Arduino IDE.
3. Open `firmware/ESP32/HealSense_ESP32_Monitor/HealSense_ESP32_Monitor.ino`.
4. Confirm libraries installed:
   - `SparkFun MAX3010x Pulse and Proximity Sensor Library` (v1.1.2+)
   - `Adafruit MLX90614 Library`
   - `Adafruit SSD1306` + `Adafruit GFX`
5. Select board: **Tools > Board > esp32 > ESP32 Dev Module**.
6. Select port: **Tools > Port > COMx**.
7. Click **Upload**. Wait for `Leaving... Hard resetting via RTS pin...`.
8. Open **Serial Monitor** at **115200 baud**.

### Step 4: Boot & Network Evidence
Watch Serial Monitor and OLED display:
- [x] Splash banner prints: `HEALSENSE-ESP32 v3.4 CONTINUITY-FIX (2026-10-31)`.
- [x] I2C scan confirms 3 devices: `0x3C` (OLED), `0x57` (MAX30102), `0x5A` (MLX90614).
- [x] Wi-Fi connects: prints `WiFi connected! IP: <ESP32_IP>`.

### Step 5: Finger Placement & Measurement Stability
- Place index finger gently and stably over the MAX30102 sensor optical window.
- Observe OLED IR signal bar graph rise.
- Maintain steady contact without excessive pressure (avoid blanching capillary bed).
- Allow the 2-second stabilization window to discard initial motion artifacts.
- Wait for the rolling 100-sample window agreement (3 consecutive agreeing windows required).
- Display shows 5-second countdown hold while sensor FIFO is safely drained and wiped.

### Step 6: Telemetry Ingress Evidence
- [x] Serial Monitor prints: `[NET] POST /api/v1/telemetry -> 201 Created`.
- [x] Blood pressure displays as `"Not measured"` on OLED and UI (BP-null rule honored).
- [x] React Web UI updates vital cards in real time matching OLED numbers.
- [x] Flutter Mobile UI displays new vital reading in dashboard.

### Step 7: Evidence Return Checklist
Copy and preserve the following evidence for return to the review session:
1. Serial Monitor startup and I2C scan output.
2. Serial Monitor `[NET] POST /api/v1/telemetry -> 201 Created` lines.
3. OLED readings (HR, SpO2, Temperature).
4. Backend log confirming HTTP 201 and WebSocket dispatch.
5. Screenshot or values from React/Flutter live viewer showing matching reading.

### Step 8: Safe Disconnect
- Remove finger from sensor.
- Disconnect USB cable from laptop.
- No need to leave ESP32 powered continuously between measurement sessions.

---

## 5. Physical Hardware Verification Record (L3 Proof)

- **Date**: 2026-10-31
- **Firmware Version**: `HEALSENSE-ESP32 v3.4 CONTINUITY-FIX (2026-10-31)`
- **Verification Status**:
  > **First physical ESP32-to-backend-to-React/Flutter end-to-end proof passed with strap-assisted MAX30102 attachment. Measurement accuracy, repeatability, final finger fixture, and robust DSP remain unvalidated.**
- **Physical Telemetry Ingress Evidence Summary**:
  - Three device-origin `ESP32-001` telemetry rows successfully ingested into database.
  - Three HTTP 201 responses returned to hardware (`POST /api/v1/telemetry -> 201 Created`).
  - Systolic and diastolic BP fields null (`Not measured`), honoring the BP-null constraint.
  - Both React and Flutter client dashboards updated live via WebSocket without manual refresh.
  - Free heap maintained at 216,004 bytes after each FIFO wipe.
