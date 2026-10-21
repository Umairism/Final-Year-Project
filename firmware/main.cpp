/**
 * ============================================================================
 *  HealSense — ESP32 Sensor Node Firmware
 * ============================================================================
 *  Hardware:
 *    • ESP32 DevKit (any ESP32-WROOM-32 board)
 *    • MAX30102  — pulse oximetry + heart rate   (I2C 0x57)
 *    • MLX90614  — non-contact IR thermometer    (I2C 0x5A)
 *
 *  Wiring (default ESP32 I2C pins):
 *    MAX30102  VIN -> 3V3     GND -> GND     SDA -> GPIO21   SCL -> GPIO22
 *    MLX90614  VCC -> 3V3     GND -> GND     SDA -> GPIO21   SCL -> GPIO22
 *    (Both devices share the bus — different addresses, no conflict.)
 *
 *  Required libraries (Arduino Library Manager):
 *    • "SparkFun MAX3010x Pulse and Proximity Sensor Library"
 *    • "Adafruit MLX90614 Library"
 *    • "ArduinoJson" (v6.x)
 *
 *  Behaviour:
 *    1. Reads the MAX30102 FIFO at 100 Hz and runs the Maxim SpO2/HR
 *       algorithm over a rolling buffer.
 *    2. Reads object temperature from the MLX90614.
 *    3. POSTs a JSON telemetry record to the HealSense cloud backend.
 *    4. If Wi-Fi or the server is unavailable, buffers records in NVS and
 *       replays them with delayed_sync=true when connectivity returns.
 *
 *  IMPORTANT: see docs/firmware/ESP32_Sensor_Guide.md for the calibration and
 *  accuracy limits of these two sensors. They are NOT medical-grade devices.
 * ============================================================================
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Preferences.h>
#include <ArduinoJson.h>

#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>

// ─────────────────────────── CONFIGURATION ──────────────────────────────────
// Edit these before flashing.

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Cloud backend. Use the HTTPS host in production.
// For local testing: http://192.168.1.50:5000  (no TLS)
const char* API_BASE      = "https://healsense.example.com";
const char* TELEMETRY_PATH = "/api/v1/telemetry";

const char* DEVICE_ID  = "ESP32-001";
const char* PATIENT_ID = "P001";
const char* API_KEY    = "esp32_phase5_key";   // must match Device.api_key_hash in DB

// Timing
const uint32_t SEND_INTERVAL_MS   = 10000;  // send one record every 10 s
const uint32_t WIFI_RETRY_MS      = 30000;
const uint32_t HTTP_TIMEOUT_MS    = 8000;
const uint32_t MAX_BACKOFF_MS     = 300000; // 5 min cap on retry backoff

// Sensor validity gates — reject garbage before it reaches the cloud
const float MIN_VALID_HR   = 30.0;
const float MAX_VALID_HR   = 220.0;
const float MIN_VALID_SPO2 = 70.0;
const float MAX_VALID_SPO2 = 100.0;

// MLX90614 skin-temperature calibration.
// A wrist/forehead surface reading is LOWER than core temperature. This offset
// corrects toward an approximate core estimate. It is a crude linear constant,
// NOT a validated clinical conversion — see the guide, section 4.2.
const float SKIN_TO_CORE_OFFSET = 2.0;   // °C added to the IR reading
const float MIN_VALID_TEMP      = 30.0;  // backend rejects anything below this
const float MAX_VALID_TEMP      = 45.0;  // backend rejects anything above this

// NVS ring buffer
const uint16_t NVS_CAPACITY = 200;

// ─────────────────────────── GLOBALS ────────────────────────────────────────

MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
Preferences prefs;

// The Maxim algorithm expects 100 samples; 100 Hz with 4-sample averaging
// gives an effective 25 samples/s, so 100 samples represents a 4 s window.
#define BUFFER_SIZE 100
uint32_t irBuffer[BUFFER_SIZE];
uint32_t redBuffer[BUFFER_SIZE];

int32_t  spo2Value   = 0;
int8_t   validSPO2   = 0;
int32_t  heartRate   = 0;
int8_t   validHeartRate = 0;

uint32_t lastSendMs   = 0;
uint32_t lastWifiTry  = 0;
uint32_t backoffMs    = 0;

struct Record {
  float    hr;
  float    spo2;
  float    temp;
  bool     delayedSync;
  uint32_t timestamp;      // epoch seconds
};

// ─────────────────────────── SENSOR SETUP ───────────────────────────────────

bool initSensors() {
  Wire.begin(21, 22);          // SDA, SCL — default ESP32 pins
  // MLX90614 is SMBus (100 kHz max); 400 kHz makes it disappear/return NaN.
  Wire.setClock(I2C_SPEED_STANDARD);

  if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD)) {
    Serial.println("[FATAL] MAX30102 not found. Check wiring / address 0x57.");
    return false;
  }
  Serial.println("[OK] MAX30102 detected");

  // LED brightness, sample averaging, mode, sample rate, pulse width, ADC range.
  // 100 Hz sample rate with 4-sample averaging gives a clean enough waveform.
  particleSensor.setup(
      60,                  // LED brightness 0-255
      4,                   // sample average
      2,                   // Red + IR
      100,                 // sample rate  (Hz)
      411,                 // pulse width  (us)
      4096                 // ADC range
  );

  if (!mlx.begin()) {
    Serial.println("[FATAL] MLX90614 not found. Check wiring / address 0x5A.");
    return false;
  }
  Serial.print("[OK] MLX90614 detected. Ambient: ");
  Serial.print(mlx.readAmbientTempC());
  Serial.println(" C");

  return true;
}

// ─────────────────────────── HR / SpO2 ACQUISITION ──────────────────────────

/**
 * Fills the sample buffer, then runs the Maxim algorithm.
 * This BLOCKS for ~4 seconds (100 samples at an effective 25 samples/s).
 * The MAX30102 gives raw photodiode counts only — it does not compute HR/SpO2
 * in hardware. This DSP is unavoidable.
 */
bool readVitals() {
  // Prime the buffer with one reading per sample slot
  // byte wraps at 255, so byte i < 400 would never terminate.
  for (uint16_t i = 0; i < BUFFER_SIZE; i++) {
    while (!particleSensor.available()) {
      particleSensor.check();      // pump the FIFO
    }
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i]  = particleSensor.getIR();
    particleSensor.nextSample();

    // No finger/skin contact: IR must be substantially above the noise floor
    if (irBuffer[i] < 50000) {
      Serial.println("[WARN] No sensor contact (IR low). Skipping window.");
      return false;
    }
  }

  maxim_heart_rate_and_oxygen_saturation(
      irBuffer, BUFFER_SIZE, redBuffer,
      &spo2Value, &validSPO2, &heartRate, &validHeartRate);

  return (validHeartRate == 1 || validSPO2 == 1);
}

float readTemperature() {
  float t = mlx.readObjectTempC();

  if (isnan(t)) {
    return NAN;
  }

  // Sensor aimed at nothing / too far away reads near ambient
  if (t < MIN_VALID_TEMP) {
    Serial.printf("[WARN] Temp %.2f C below %.1f — sensor likely not on skin\n",
                  t, MIN_VALID_TEMP);
    return NAN;
  }

  float coreEstimate = t + SKIN_TO_CORE_OFFSET;

  if (coreEstimate > MAX_VALID_TEMP) {
    Serial.printf("[WARN] Temp %.2f C implausible — discarding\n", coreEstimate);
    return NAN;
  }

  return coreEstimate;
}

// ─────────────────────────── NVS OFFLINE BUFFER ─────────────────────────────

uint16_t nvsCount() { return prefs.getUShort("count", 0); }

void nvsEnqueue(const Record& r) {
  uint16_t count = nvsCount();
  if (count >= NVS_CAPACITY) {
    Serial.println("[WARN] NVS buffer full — dropping oldest record");
    // Shift everything down one slot to make room
    for (uint16_t i = 1; i < NVS_CAPACITY; i++) {
      String from = "r" + String(i);
      String to   = "r" + String(i - 1);
      uint16_t len = prefs.getBytesLength(from.c_str());
      if (len == sizeof(Record)) {
        Record tmp;
        prefs.getBytes(from.c_str(), &tmp, sizeof(Record));
        prefs.putBytes(to.c_str(), &tmp, sizeof(Record));
      }
    }
    count = NVS_CAPACITY - 1;
  }

  String key = "r" + String(count);
  prefs.putBytes(key.c_str(), &r, sizeof(Record));
  prefs.putUShort("count", count + 1);
}

bool nvsPeek(Record& out) {
  if (nvsCount() == 0) return false;
  size_t len = prefs.getBytes("r0", &out, sizeof(Record));
  return len == sizeof(Record);
}

void nvsPop() {
  uint16_t count = nvsCount();
  if (count == 0) return;
  for (uint16_t i = 1; i < count; i++) {
    String from = "r" + String(i);
    String to   = "r" + String(i - 1);
    uint16_t len = prefs.getBytesLength(from.c_str());
    if (len == sizeof(Record)) {
      Record tmp;
      prefs.getBytes(from.c_str(), &tmp, sizeof(Record));
      prefs.putBytes(to.c_str(), &tmp, sizeof(Record));
    }
  }
  prefs.remove(("r" + String(count - 1)).c_str());
  prefs.putUShort("count", count - 1);
}

// ─────────────────────────── HTTP TRANSPORT ─────────────────────────────────

/**
 * Sends one record. Returns HTTP status code, or a negative value on failure.
 */
int postRecord(const Record& r) {
  HTTPClient http;

  String url = String(API_BASE) + TELEMETRY_PATH;

  #if defined(USE_TLS)
    WiFiClientSecure client;
    client.setInsecure();          // prototype only — see guide §6
    http.begin(client, url);
  #else
    WiFiClient client;
    http.begin(client, url);
  #endif

  http.setTimeout(HTTP_TIMEOUT_MS);
  http.setReuse(false);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-API-Key", API_KEY);

  StaticJsonDocument<384> doc;
  doc["device_id"]  = DEVICE_ID;
  doc["patient_id"] = PATIENT_ID;
  doc["heart_rate"] = round(r.hr * 10) / 10.0;
  doc["spo2"]       = round(r.spo2 * 10) / 10.0;
  doc["temperature"] = round(r.temp * 100) / 100.0;

  // No BP sensor is fitted. Send null so the backend does not invent a value;
  // the rules engine skips BP checks when these are absent.
  doc["systolic_bp"]  = nullptr;
  doc["diastolic_bp"] = nullptr;
  doc["bp_source"]    = "none";

  doc["delayed_sync"] = r.delayedSync;

  // ISO-8601 UTC, e.g. 2026-10-17T10:30:00Z
  char ts[32];
  time_t t = (time_t)r.timestamp;
  struct tm tmv;
  gmtime_r(&t, &tmv);
  strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%SZ", &tmv);
  doc["timestamp"] = ts;

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  http.end();

  if (code < 0) {
    Serial.printf("[ERR] HTTP %s\n", http.errorToString(code).c_str());
  } else {
    Serial.printf("[NET] POST -> %d\n", code);
  }

  return code;
}

bool wifiEnsure() {
  if (WiFi.status() == WL_CONNECTED) return true;

  uint32_t now = millis();
  if (now - lastWifiTry < WIFI_RETRY_MS) return false;
  lastWifiTry = now;

  Serial.printf("[WIFI] Connecting to %s ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WIFI] Connected. IP: ");
    Serial.println(WiFi.localIP());
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    backoffMs = 0;
    return true;
  }

  Serial.println("[WIFI] Connection failed");
  backoffMs = min(max(backoffMs * 2, 1000UL), MAX_BACKOFF_MS);
  return false;
}

// Replays buffered records oldest-first.
void flushBuffer() {
  if (nvsCount() == 0) return;

  Serial.printf("[SYNC] Replaying %u buffered records\n", nvsCount());

  while (nvsCount() > 0) {
    Record r;
    if (!nvsPeek(r)) break;

    r.delayedSync = true;
    int code = postRecord(r);

    if (code == 201 || code == 200) {
      nvsPop();
      delay(120);              // be gentle on the backend
    } else {
      Serial.println("[SYNC] Replay failed — will retry later");
      break;
    }
  }
}

// ─────────────────────────── ARDUINO LIFECYCLE ──────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n=== HealSense ESP32 Sensor Node ===");

  prefs.begin("healsense", false);

  if (!initSensors()) {
    Serial.println("[FATAL] Sensor init failed. Halting.");
    while (true) delay(1000);
  }

  if (wifiEnsure()) {
    flushBuffer();
  }

  Serial.printf("[INFO] Buffered records in NVS: %u\n", nvsCount());
  Serial.println("[INFO] Entering sampling loop");
}

void loop() {
  wifiEnsure();

  if (nvsCount() > 0 && WiFi.status() == WL_CONNECTED) {
    flushBuffer();
  }

  if (millis() - lastSendMs < SEND_INTERVAL_MS) {
    delay(50);
    return;
  }
  lastSendMs = millis();

  // ── Acquire ──────────────────────────────────────────────────────────────
  float temp = readTemperature();

  if (!readVitals()) {
    Serial.println("[SKIP] Unreliable vitals window");
    return;
  }

  if (heartRate < MIN_VALID_HR || heartRate > MAX_VALID_HR ||
      spo2Value < MIN_VALID_SPO2 || spo2Value > MAX_VALID_SPO2) {
    Serial.printf("[SKIP] Out-of-range HR=%ld SpO2=%ld\n", heartRate, spo2Value);
    return;
  }

  if (isnan(temp)) {
    Serial.println("[SKIP] No valid temperature");
    return;
  }

  Record r;
  r.hr          = (float)heartRate;
  r.spo2        = (float)spo2Value;
  r.temp        = temp;
  r.delayedSync = false;
  r.timestamp   = (uint32_t)time(nullptr);

  Serial.printf("[READ] HR=%.1f SpO2=%.1f%% Temp=%.2fC\n", r.hr, r.spo2, r.temp);

  // ── Transmit, or buffer ──────────────────────────────────────────────────
  if (WiFi.status() == WL_CONNECTED) {
    int code = postRecord(r);
    if (code == 201 || code == 200) {
      return;                       // delivered
    }
    Serial.println("[NET] Delivery failed — buffering");
  } else {
    Serial.println("[NET] Offline — buffering");
  }

  nvsEnqueue(r);
  Serial.printf("[NVS] Buffered. Queue depth: %u\n", nvsCount());
}
