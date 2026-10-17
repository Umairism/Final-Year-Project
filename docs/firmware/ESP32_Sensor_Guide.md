# ESP32 → Cloud AI → App: Complete Data Path

**Hardware:** ESP32 DevKit · MAX30102 (HR/SpO₂) · MLX90614 (IR temperature)
**Updated:** 17 Oct 2026

---

## 1. What the two sensors actually give you

### MAX30102 — pulse oximetry + heart rate

**I2C address `0x57`**

This is the single most misunderstood part of the project. **The MAX30102 does not
output heart rate or SpO₂.** It is a photodiode front-end. It gives you raw optical
counts:

| Register / reading | What it is |
|---|---|
| `IR` channel | 18-bit ADC count (0–262,143) from the infrared LED |
| `RED` channel | 18-bit ADC count from the red LED |
| FIFO | Up to 32 samples, read over I2C |
| Temperature | On-die die temperature (NOT body temperature — ignore it) |

Everything else is **computed by you**:

- **Heart rate** — peak detection on the IR waveform (bandpass ~0.5–5 Hz, count
  systolic peaks over a window, convert to bpm).
- **SpO₂** — the empirical "ratio of ratios":

```
R        = (AC_red / DC_red) / (AC_ir / DC_ir)
SpO₂ ≈ a - b·R          (calibration curve, manufacturer-proprietary)
```

The `a`/`b` constants come from a calibration study on human volunteers against
arterial blood gas. **Maxim does not publish the exact curve**, so every open-source
implementation uses an approximation. This is why accuracy is poor.

Your firmware uses Maxim's own `spo2_algorithm.h` (shipped with the SparkFun
library), which is the best free option available — but it is still an approximation.

**Practical constraints:**

| Item | Value |
|---|---|
| Sample rate | 50–3200 Hz (100 Hz used here) |
| Buffer for HR/SpO₂ | ≥ 4 s of samples (`spo2_algorithm.h` needs 500+) |
| Skin contact | **Required.** IR must exceed ~50,000 counts or the reading is noise |
| Motion | Destroys the signal — the finger/wrist must be still |
| Typical achievable accuracy | HR ±3–5 bpm · SpO₂ ±2–3 % *under good conditions* |
| When conditions are poor | Wrong by 10+ %, or no valid output at all |

### MLX90614 — non-contact IR thermometer

**I2C address `0x5A`**

| Reading | Meaning |
|---|---|
| `readObjectTempC()` | Temperature of whatever the sensor is aimed at |
| `readAmbientTempC()` | Temperature of the sensor package itself |

This one **does** give a temperature directly, but that does not make it a body
thermometer. Three things determine whether the number means anything:

1. **Field of view (FOV).** The common `MLX90614ESF-BAA` has a 35° cone. At 2 cm
   distance the spot is ≈1.3 cm diameter. Aim it at a wrist and half the cone may be
   reading the room.
2. **Distance.** 1–5 cm. At 10 cm you are largely measuring background.
3. **Emissivity.** Default is 0.98, which is close to human skin (~0.98). Leave it.

---

## 2. ⚠️ The temperature problem — read this before you calibrate

**Skin surface temperature is not core body temperature, and the gap is large.**

| Site | Typical surface reading |
|---|---|
| Wrist | **32 – 34 °C** |
| Forehead / temporal | 34 – 35 °C |
| Axilla | 36 – 37 °C |
| **Core (what the model was trained on)** | **36.5 – 37.5 °C** |

Now compare that with the thresholds in your own system:

| Threshold | Value | Source |
|---|---|---|
| Backend rejects below | **30 °C** | `schemas.py:204` `ge=30` |
| Rules engine fever warning | **≥ 38.0 °C** | `fusion_engine.py` |
| PhysioNet training distribution | mean ≈ 37 °C (core) | training data |

**Consequences:**

1. A wrist-mounted MLX90614 reads ~33 °C. **The fever rule at 38 °C will never fire.**
   Your temperature branch is effectively dead code in deployment.
2. If the sensor misses the skin and reads ambient (25 °C), the payload is **rejected
   outright** by Pydantic's `ge=30` validator — you get HTTP 422.
3. The LSTM was trained on core temperatures clustered around 37 °C. Feeding it 33 °C
   puts that input channel **far outside the training distribution**, which degrades
   the prediction even when nothing is wrong with the patient.

### What to do about it

| Option | Action | Honest assessment |
|---|---|---|
| **A (recommended)** | Move the sensor to the **forehead/temporal artery**, 2 cm distance. Add a **per-device offset** calibrated against an oral/axillary reference on 5+ people. | Best accuracy. Offset ≈ +2 to +3 °C, but it is person- and site-dependent. |
| B | Keep wrist placement, apply `SKIN_TO_CORE_OFFSET = 3.0`, document it as a crude approximation | Firmware already supports this constant. Usable, but be explicit in the report. |
| C | Treat temperature as a **screening** channel only and state that febrile detection is out of scope for this hardware | Defensible; removes the false precision. |

Whichever you pick, **write it in the limitations section**. "We measured skin
temperature and estimated core with a constant offset of +3 °C, which is not clinically
validated" is honest and costs you nothing. Claiming clinical thermometry from a
wrist-mounted IR sensor will get picked apart.

> The firmware implements Option B by default (`SKIN_TO_CORE_OFFSET = 2.0`). Change
> that constant after calibrating.

---

## 3. ⚠️ The cadence mismatch — the biggest architectural issue

Your LSTM was trained on:

```
24 steps × 1 hour  =  24 hours of history  →  predict next 6 hours
```

Your device sends a reading every **10 seconds**. Twenty-four consecutive device
readings therefore span:

```
24 × 10 s  =  4 minutes
```

That is a **360× mismatch** in temporal scale. The model learned hour-to-hour
deterioration dynamics; you are feeding it four minutes of data and asking for a
six-hour forecast. **It will behave unpredictably, and the output cannot be defended
as trained.**

### Fix: aggregate before inference

Do not feed raw device rows to the LSTM. Have the backend bucket them:

```
Device: 1 reading / 10 s  →  Backend: 1-minute median bucket  →  LSTM consumes buckets
24 buckets × 1 min = 24 minutes of history
```

Even then, 24 minutes ≠ 24 hours. Two defensible options:

| Option | What it means | Report wording |
|---|---|---|
| **A — Retrain at deployment cadence** | Re-run the pipeline with 1-minute bins and a 24-min window; horizon 15–30 min | *"The model was trained on the deployed sampling regime."* ✅ strongest |
| **B — Two-timescale design** | Rules fire instantly on each reading (real-time safety); LSTM runs hourly on aggregated trends | *"Real-time safety is handled by the deterministic layer, which needs only a single reading. The temporal model operates on hourly trend windows."* ✅ defensible and honest |

**Option B is legitimate and matches your existing 5-layer architecture** — the rules
layer is designed to be instantaneous, the LSTM to be temporal. Just make sure the
backend aggregates hourly (or 1-minute, consistently) rather than feeding raw 10-second
rows into a 60-hour-trained model.

Until you resolve this, treat LSTM output from live device data as unreliable and rely
on the deterministic rules for the live demo.

---

## 4. Blood pressure is absent — and that is fine

You have no BP sensor. Both `systolic_bp` and `diastolic_bp` are sent as `null` with
`bp_source: "none"`.

This is **supported by design**:

- `TelemetryPayload` declares both as `Optional[float] = None`
- The rules engine now skips BP checks when they are `None` (fixed in v1.1)
- `PredictionService` imputes missing BP from the training medians

Do **not** fabricate 120/80 on the device. A normal-looking invented BP is exactly the
kind of silent false reassurance a clinical safety reviewer will flag.

Optional future route: a BLE/USB blood-pressure cuff paired to the phone app, POSTed
separately with `bp_source: "ble_cuff"`. The schema already supports this.

---

## 5. The complete data path

```
┌─────────────────────────────────────────────────────────────────┐
│ ESP32                                                            │
│                                                                  │
│  MAX30102 ──I2C 0x57──► IR + RED counts ──► HR/SpO₂ algorithm    │
│  MLX90614 ──I2C 0x5A──► object temp ──────► + offset             │
│                                                                  │
│  Every 10 s → JSON → HTTPS POST                                  │
│  Offline? → NVS ring buffer (200 records) → replay on reconnect  │
└────────────────────────────┬────────────────────────────────────┘
                             │  POST /api/v1/telemetry
                             │  X-Device-API-Key: <key>
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI backend (cloud)                                          │
│                                                                  │
│  1. Device auth        SHA-256 key hash vs Device.api_key_hash   │
│  2. Pydantic validate  ranges: HR 0-300, SpO2 0-100, T 30-45     │
│  3. Persist            PostgreSQL VitalSigns row                 │
│  4. Aggregate          → 1-min / hourly buckets for the LSTM     │
│  5. Rules engine       instant, single reading → CRITICAL is abs │
│  6. LSTM               buckets → 3-class probabilities           │
│  7. Fusion             0.6·det + 0.4·ml, critical is never ML    │
│  8. Gemini             plain-language explanation                │
│  9. Broadcast          WebSocket /ws/patients/{id}               │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
             ▼                               ▼
      Web dashboard                   Flutter mobile app
      React + WebSocket               REST + WebSocket
      (live cards, trend,             (vitals, alerts,
       risk gauge, alerts)             emergency button)
```

---

## 6. The wire format

**Request**

```http
POST /api/v1/telemetry HTTP/1.1
Host: healsense.example.com
Content-Type: application/json
X-Device-API-Key: esp32_phase5_key

{
  "device_id": "ESP32-001",
  "patient_id": "P001",
  "heart_rate": 78.5,
  "spo2": 97.2,
  "temperature": 36.4,
  "systolic_bp": null,
  "diastolic_bp": null,
  "bp_source": "none",
  "delayed_sync": false,
  "timestamp": "2026-10-17T10:30:00Z"
}
```

**Response (201 Created)**

```json
{
  "success": true,
  "message": "Telemetry ingested and evaluated successfully",
  "vital_id": "…",
  "patient_id": "P001",
  "device_id": "ESP32-001",
  "status": "warning",
  "fused_decision": {
    "final_risk_level": "warning",
    "confidence_score": 0.95,
    "deterministic_flags": ["Abnormal Heart Rate"],
    "ml_risk_probability": 0.41,
    "fusion_method": "weighted_fusion",
    "ml_escalation_capped": false
  },
  "explanation": "Heart rate is above the resting threshold..."
}
```

`fusion_method` tells you which path ran:
- `deterministic_override` — rules declared CRITICAL, absolute
- `weighted_fusion` — both layers contributed
- `deterministic_only` — fewer readings than the model needs (normal at startup)

---

## 7. Getting feedback to the apps

### Web dashboard — WebSocket (push)

```javascript
// subscribe once, receive every ingest event
const ws = new WebSocket(`wss://healsense.example.com/ws/patients/${patientId}`);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);   // { type, data: { status, fused_decision, ... } }
  if (msg.data.fused_decision.final_risk_level === "critical") {
    raiseAlert(msg.data);           // banner / sound / emergency modal
  }
};
```

Your `useTelemetrySocket.ts` hook already implements this with polling fallback.

### Flutter app — REST + WebSocket

- `POST /api/v1/devices/register` on first launch → stores `X-Device-API-Key`
- `GET /api/v1/patients/{id}/fusion_risk` for the current assessment
- `ws://…/ws/patients/{id}` for live updates

### Latency budget

| Stage | Typical |
|---|---|
| Sensor acquisition (4 s window) | 4,000 ms |
| HTTPS round trip | 100–400 ms |
| Rules + LSTM + fusion | 5–40 ms |
| Gemini explanation (async, non-blocking) | 500–2,000 ms |
| **Total to alert on screen** | **~4.5 s** |

The 4-second acquisition window dominates. If you need faster alerts, shorten
`BUFFER_SIZE` — at the cost of SpO₂ accuracy.

---

## 8. Security notes for the report

| Concern | Current state | Recommendation |
|---|---|---|
| Device auth | SHA-256 hashed API key, per-device | Fine for a prototype |
| Transport | HTTPS required | `client.setInsecure()` in the sketch **skips cert validation** — prototype only. Pin the CA for anything real. |
| API key on device | Stored in `.cpp` source | Flash-encrypt or load from NVS |
| Replay | No nonce/timestamp check | Acceptable, but note it |

`setInsecure()` disabled certificate validation entirely. Say so in the limitations —
it is the difference between "prototype shortcut" and "undisclosed security hole".

---

## 9. Build & flash

1. **Arduino IDE → Preferences → Additional Board Manager URLs**
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
2. **Boards Manager** → install `esp32` by Espressif
3. **Library Manager** → install:
   - SparkFun MAX3010x Pulse and Proximity Sensor Library
   - Adafruit MLX90614 Library
   - ArduinoJson (v6.x)
4. Open `firmware/main.cpp`, edit the four config blocks at the top
5. Board: **ESP32 Dev Module**, upload speed 921600
6. **Serial Monitor @ 115200** — you should see:

```
=== HealSense ESP32 Sensor Node ===
[OK] MAX30102 detected
[OK] MLX90614 detected. Ambient: 27.31 C
[WIFI] Connected. IP: 192.168.1.42
[READ] HR=78.5 SpO2=97.2% Temp=36.40C
[NET] POST -> 201
```

---

## 10. Tuning the MAX30102 (do this — it matters a lot)

The default `setup()` arguments are a starting point, not an optimum:

| Parameter | Effect |
|---|---|
| LED brightness ↑ | Stronger signal, more power/heat, saturates easily |
| Sample average ↑ | Smoother, but slower response |
| Pulse width ↑ | Better SNR, higher power |
| ADC range ↑ | Avoids saturation on lighter skin; less resolution |

**Saturation check:** if `IR` or `RED` sits near 262,143, the signal is clipping.
Lower LED brightness or raise ADC range.

**Contact check:** with no finger present, IR counts sit around 1,000–30,000. The
firmware rejects windows where IR < 50,000. Tune this threshold to your own baseline
readings.

---

## 11. Limitations to state in the report

1. **Sensors are not medical-grade.** MAX30102 and MLX90614 are consumer/industrial
   parts. Neither carries a medical device certification.
2. **SpO₂ depends on an undisclosed calibration curve.** The firmware uses Maxim's
   reference algorithm, which is an approximation.
3. **Temperature is skin-surface IR, not core thermometry.** A constant offset is
   applied; it is not clinically validated.
4. **No blood pressure sensor.** BP is absent unless supplied by an external cuff.
5. **Cadence mismatch** between the training regime (hourly) and the device (10 s)
   unless the aggregation retrain in §3 is performed.
6. **TLS certificate validation is disabled** in the prototype firmware.
7. **Single-device validation.** Accuracy was not characterised across multiple units
   or subjects.

Stating these costs you nothing and removes the examiner's best attack.
