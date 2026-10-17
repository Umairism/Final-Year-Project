# Blood Pressure Sensor — Buying & Integration Guide (Pakistan)

**Question:** should I buy a Bluetooth BP monitor and connect it to the ESP32?
**Date:** 17 Oct 2026

---

## 1. Verdict

> **Update — you already own a suitable cuff. Buy nothing.**
>
> The Braun ExactFit 1 (BUA5000) is an upper-arm oscillometric monitor with
> ESH / ISO 81060-2 validation. It is *exactly* the device this guide would
> have recommended: clinically accurate, non-connected, and a one-minute
> manual entry into the phone app. See §1.1.

**Buying a BP cuff: yes** — if you do not already have one. Blood pressure is the
single biggest hole in your vitals set, and it is one of the three rules the
deterministic engine checks. Without it, a hypertensive crisis (≥180/120) can never be
detected by your system.

**Connecting it to the ESP32: no.** Connect it to the **phone app** instead.

**Buying a *Bluetooth* model: only if you have spare time.** A plain upper-arm cuff plus
manual entry in the app satisfies your architecture completely, for a third of the price
and none of the risk.

---

## 1.1 Your Braun ExactFit 1 — what it is and why it is enough

| Spec | Value |
|---|---|
| Model | BUA5000 (ExactFit 1) — upper arm, oscillometric |
| Measurement range | 30–280 mmHg · pulse 40–199 bpm |
| Laboratory accuracy | ±3 mmHg (cuff pressure) · ±5 % (pulse) |
| **Clinical accuracy** | **< 5 mmHg systematic offset, < 8 mmHg SD** |
| Validation | ESH IP-2002 · EN 1060-1/-3 · ANSI/AAMI SP-10-2002 · ISO 81060-2 |
| Cuff | Universal 22–42 cm |
| Memory | **Last measurement only** |
| Connectivity | **None** — no Bluetooth, no USB, no serial |

**Why this is good enough.** The ±3 mmHg / < 8 mmHg SD figures are better than
the accuracy of most consumer wearables for BP, and are the same class of
device used as the reference standard in cuff-validation studies. For a
research-grade FYP you can cite this as your BP ground truth.

**The one real limitation:** it stores only the most recent reading. There is no
log to download later, so **enter the reading into the app while it is still on
the screen**. If you want a physical backup, write SYS/DIA/pulse/time into the
project logbook — that also gives you a nice "manual record vs app record"
line in the report.

**What to enter:** systolic, diastolic, and the pulse number shown on the
display. That is all three values the device produces.

---

## 1.2 The manual-entry path (already implemented)

`POST /api/v1/patients/{patient_id}/bp`

```json
{
  "systolic_bp": 128,
  "diastolic_bp": 82,
  "pulse": 74,
  "bp_source": "manual_entry",
  "note": "left arm, seated 5 min"
}
```

What the backend does with it:

1. **Validates** the reading against physiology — systolic must exceed diastolic
   by at least 10 mmHg, ranges bounded to 60–260 / 30–200.
2. **Attaches** it to the newest `vital_signs` row within the last 60 minutes
   (configurable via `attach_window_minutes`). BP is intermittent; the wrist
   node is continuous. The reading describes the physiological state that row
   captured, so it is written onto that row rather than duplicating it with
   invented HR/SpO₂/temperature.
3. **Classifies** it with AHA/ACC bands (normal → elevated → stage 1 → stage 2 →
   hypertensive crisis, plus hypotension).
4. **Re-runs the full pipeline** — deterministic rules → LSTM → `fuse_risk()` — so
   the crisis rule at ≥180/120 can finally fire.
5. **Raises a CRITICAL alert** on hypertensive crisis (deduplicated to one per
   10 minutes).
6. **Pushes over WebSocket** as `patient.vitals.created`, so the dashboard and
   the Flutter app update without a refresh.

If the wrist device is not running there is no row to attach to. The API then
returns **HTTP 409 `no_anchor_reading`** with the BP assessment attached, and
accepts `heart_rate`, `spo2` and `temperature` in the same request to store a
standalone reading. It never silently invents the missing vitals.

Try it in the Flutter app: **Dashboard → Log Blood Pressure**, or the
monitor-heart icon in the app bar.

---

## 2. Why not the ESP32 — three concrete reasons

### 2.1 The ESP32 has one radio for both Wi-Fi and BLE

The ESP32 shares a single 2.4 GHz transceiver between Wi-Fi and Bluetooth. They work
via time-division coexistence: when BLE is active, Wi-Fi throughput drops, and latency
rises on both. For a sensor node that must push telemetry every 10 s over HTTPS, adding
a second BLE role makes the timing unpredictable — and HTTPS handshakes are sensitive to
latency spikes.

It is workable if strictly sequenced (BLE read → disconnect → Wi-Fi POST), but it is a
source of flaky behaviour you do not need during a demo.

### 2.2 Reading a BLE device is the hard direction

Every ESP32 BLE tutorial shows the ESP32 as a **peripheral** (it advertises, a phone
connects to it). You need the opposite: the ESP32 as a **central/client**, connecting
*out* to the cuff, discovering services, subscribing to indications, and parsing
binary payloads.

In Arduino that means the NimBLE client API or the ESP-IDF GATT client — several times
more complex than anything in your current firmware, with far fewer working examples.

### 2.3 Your own schema already says the phone is the hub

```python
class BpSource(str, Enum):
    MANUAL_ENTRY   = "manual_entry"
    BLE_CUFF       = "ble_cuff"        # ← this value exists for exactly this design
    HARDWARE_UART  = "hardware_uart"
    NONE           = "none"
```

`bp_source = "ble_cuff"` is already in your backend. The intended architecture is:
**the phone pairs with the cuff and POSTs the reading with its source tagged.** No
backend change is required — the phone is the natural hub for an intermittent peripheral,
the ESP32 stays a continuous vitals node.

---

## 3. ⚠️ The buying trap: most "Bluetooth" BP monitors are not readable

There is a Bluetooth SIG standard for this:

| Item | UUID |
|---|---|
| Blood Pressure Service | `0x1810` |
| Blood Pressure Measurement characteristic | `0x2A35` (Indicate) |
| Intermediate Cuff Pressure | `0x2A36` (Notify) |

Payload format is public: a flags byte, then systolic / diastolic / MAP as IEEE-11073
SFLOAT 16-bit values, then optional pulse rate and timestamp. Anyone can parse it.

**But a device advertising "Bluetooth" is not necessarily using it.**

- **Omron** devices (Evolv, M7 Intelli IT, 10 Series) use a **proprietary protocol** for
  the OMRON Connect app. They generally do **not** expose the standard `0x1810` service.
  Community projects have reverse-engineered some models, but you would be porting
  undocumented, model-specific code.
- **Devices that do expose standard `0x1810`:** A&D Medical UA-651BLE, several **Beurer**
  models, QardioArm.

**Before you buy anything, ask the seller to confirm the device advertises GATT service
`0x1810`.** If they cannot answer, assume it does not.

**Free way to check:** install **nRF Connect** (Android/iOS), scan, and look at the
device's advertised services. If you see `0x1810`, it will work. If you only see a
proprietary UUID, it won't — at least not without reverse engineering.

---

## 4. What to buy in Pakistan (current listings)

Prices from Pakistani retailers (Omron Pakistan, Hamza Surgical, Xiaomi Store PK, Tejar,
Naheed). Verify at purchase — they move.

### Bluetooth models

| Model | Type | Price (PKR) | Notes |
|---|---|---|---|
| **Beurer BC-54** | Wrist | **~10,450** | Cheapest BLE found. Beurer is more open than Omron. **Check for 0x1810.** |
| **Omron M7 Intelli IT HEM-7361T** | Upper arm | **~26,000 – 34,000** | Best accuracy + AFib detection. OMRON Connect only — **proprietary protocol** ⚠️ |
| Omron Evolv BP7000 | Upper arm | ~38,500 – 53,000 | Wireless, popular, proprietary protocol ⚠️ |
| Omron 10 Series BP7465 | Upper arm | ~35,000 – 45,000 | Proprietary ⚠️ |

### Non-Bluetooth models

| Model | Type | Price (PKR) |
|---|---|---|
| **Omron M1 Basic HEM-7121** | Upper arm | **~7,799 – 10,000** |
| Omron HEM-7124 | Upper arm | ~11,000 – 15,000 |
| Omron M3 Comfort HEM-7155-E | Upper arm | ~23,500 |
| Omron RS1 wrist | Wrist | ~7,499 – 12,350 |

**Where:** `omron.pk`, `omronhealthcare.pk`, `hamzasurgical.com`, `xiaomistore.pk`,
`tejar.pk`, `naheed.pk`. All ship nationwide; Abbottabad is well served by courier.
For a local purchase, any large medical store in Abbottabad's Supply/Saddar bazaar
carries Omron — and you can physically inspect the box.

> **Wrist vs upper arm:** upper-arm cuffs are significantly more accurate and are what
> clinical guidelines recommend. Wrist monitors are portable but sensitive to wrist
> position at heart level. If the BP number is going into a clinical system, buy upper arm.

---

## 5. The recommendation, by remaining time

### Option A — Best value (recommended): plain upper-arm cuff + manual entry
**Cost: ~Rs 8,000–10,000 · Time: 1 hour**

Buy an **Omron M1 Basic**. Add a "Add BP reading" form to the web/mobile app posting:

```json
POST /api/v1/patients/{id}/vitals
{
  "heart_rate": 78, "spo2": 97, "temperature": 36.5,
  "systolic_bp": 128, "diastolic_bp": 82,
  "bp_source": "manual_entry"
}
```

- Clinically accurate BP (validated device, correct technique)
- Zero protocol risk, zero firmware work
- Uses the schema exactly as designed
- Defensible at viva: *"BP is an intermittent measurement captured by the patient or
  clinician and source-tagged; continuous vitals come from the wearable."*

This is **not** a compromise — it is the honest representation of how BP is actually
measured in home monitoring.

### Option B — BLE cuff into the phone app
**Cost: ~Rs 10,450 (Beurer BC-54) · Time: 2–4 days**

Use `flutter_blue_plus` in your existing Flutter app:

```dart
final service = await device.discoverServices()
    .then((s) => s.firstWhere((s) => s.uuid == "1810"));
final char = service.characteristics.firstWhere((c) => c.uuid == "2a35");
await char.setNotifyValue(true);
char.onValueReceived.listen((bytes) {
  final flags = bytes[0];
  final mmHg = (flags & 0x01) == 0;
  int sfloat(int lo, int hi) => ((hi << 8) | lo).toSigned(16).abs() * (mmHg ? 1 : 1);
  final systolic  = sfloat(bytes[1], bytes[2]);
  final diastolic = sfloat(bytes[3], bytes[4]);
  // POST with bp_source: "ble_cuff"
});
```

Then POST with `bp_source = "ble_cuff"`. Adds real "IoT" credibility at low risk, because
Flutter's BLE stack is mature and well-documented.

**Check for `0x1810` first with nRF Connect before buying.**

### Option C — BLE cuff into the ESP32
**Cost: same hardware + 1–2 weeks · Risk: high**

Requires a NimBLE central-client implementation, radio coexistence tuning, and — if you
buy Omron — reverse-engineering a proprietary protocol. With under a month left and the
model work still open, this is a poor trade. **Not recommended.**

---

## 6. What each option does for your grade

| | Option A | Option B | Option C |
|---|---|---|---|
| BP in the system | ✅ | ✅ | ✅ |
| Hypertensive-crisis rule works | ✅ | ✅ | ✅ |
| "IoT peripheral integration" story | ⚠️ modest | ✅ good | ✅ best |
| Risk of eating your remaining time | none | low | **high** |
| Cost (PKR) | 8–10k | ~10.5k | ~10.5–34k |

An examiner will not penalise manual BP entry if it is source-tagged and you explain
*why* (intermittent measurement vs continuous monitoring). They **will** penalise a
half-finished BLE integration and a broken demo.

---

## 7. If you buy one — how to use it properly

Regardless of path:

1. **Rest 5 minutes** before measuring; seated, back supported, arm at heart level.
2. **Same arm, same time of day.** BP varies 10–15 mmHg through the day.
3. **Two readings, 1 minute apart**, record the average.
4. Record `bp_source` honestly — `manual_entry` if typed, `ble_cuff` if read over BLE.
   Never backfill `hardware_uart` for something that wasn't hardware.

### What your backend does with it once present

| Reading | Deterministic rule |
|---|---|
| SBP ≥ 180 **or** DBP ≥ 120 | **CRITICAL** — Hypertensive Crisis (absolute override) |
| Normal range | Contributes nothing; other vitals decide |

Note the rules only check the *critical* end for BP — there is no "warning" band. That is
intentional and matches your current `fusion_engine.py`. Worth stating in the report.

### Note on cadence

BP is not a continuous signal. A reading every few hours is normal and clinically correct.
The LSTM was trained on hourly features, so a BP value should be **held constant
(step-function) between measurements** and the missing-indicator channel left at 0 while
a reading is current — not left at `null`, which would be imputed to the population median.

---

## 8. Bottom line

1. **You already own the right device.** Braun ExactFit 1 — upper-arm, ESH/ISO
   validated, ±3 mmHg. **Buy nothing.**
2. **Do not connect it to the ESP32.** Manual entry in the app, tagged
   `bp_source = "manual_entry"`.
3. **Enter the reading immediately** — the device keeps only the last one.
4. The endpoint and the Flutter screen are **already built** (§1.2); the only
   work left is measuring and typing.
5. **If you ever do buy Bluetooth: verify `0x1810` with nRF Connect before
   paying.** Omron's consumer range is proprietary and will not work.

### In the report

> *"Blood pressure is acquired with a validated upper-arm oscillometric cuff
> (Braun ExactFit 1, ±3 mmHg, ESH/ISO 81060-2) and entered through the mobile
> application as an intermittent measurement, because BP cannot be measured
> continuously by a wrist-worn optical device. The reading is fused with the
> continuous HR/SpO₂/temperature stream from the ESP32 node and tagged with its
> acquisition source (`manual_entry` | `ble_cuff` | `hardware_uart`), so the
> provenance of every BP value is auditable."*

That paragraph is stronger than a half-finished BLE integration, because it
shows you understand *why* the measurement is intermittent — which is the
actual engineering point.
