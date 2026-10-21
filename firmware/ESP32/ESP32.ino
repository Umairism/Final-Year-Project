/**
 * ============================================================================
 *  HealSense — ESP32 Dual I2C Sensor Sketch (Arduino IDE)
 * ============================================================================
 *  Reads BOTH sensors on ONE shared I2C bus:
 *
 *    • MAX30102  — heart rate + SpO2          (I2C address 0x57)
 *    • MLX90614  — non-contact IR temperature (I2C address 0x5A)
 *
 *  Wiring (ESP32 DevKit default I2C pins):
 *
 *    ESP32        MAX30102        MLX90614 (GY-906)
 *    ---------    ----------      ----------------
 *    3V3     -->  VIN             VIN / VCC
 *    GND     -->  GND             GND
 *    GPIO21  -->  SDA      ------ SDA        (shared bus)
 *    GPIO22  -->  SCL      ------ SCL        (shared bus)
 *
 *    Both sensors connect to the SAME SDA/SCL wires. That is normal —
 *    I2C devices share the bus and are told apart by their addresses
 *    (0x57 vs 0x5A), so there is no conflict.
 *
 *  Arduino IDE setup:
 *    Tools > Board  : "ESP32 Dev Module"   (esp32 by Espressif Systems)
 *    Tools > Port   : your ESP32 COM port
 *    Serial Monitor : 115200 baud
 *
 *  Libraries (Tools > Manage Libraries, install these two):
 *    1. "SparkFun MAX3010x Pulse and Proximity Sensor Library"
 *    2. "Adafruit MLX90614 Library"   (Adafruit BusIO installs with it)
 *    Nothing else is needed — no ArduinoJson, no extra .h/.cpp files.
 *
 *  What it does:
 *    • On boot: scans the I2C bus and prints every address it finds,
 *      so you can confirm both sensors are wired correctly.
 *    • Every ~5 s: collects 100 samples from the MAX30102 (keep your
 *      finger STILL), computes HR + SpO2, reads the MLX90614, and
 *      prints one combined result to the Serial Monitor.
 *    • Optional: set ENABLE_WIFI_UPLOAD to 1 (below) to also POST each
 *      valid reading to your HealSense backend. Leave it at 0 while
 *      you are only testing the sensors.
 *
 *  NOTE: the MAX30102 does NOT output HR/SpO2 directly. It outputs raw
 *  red/IR light counts; the `spo2_algorithm.h` code from the SparkFun
 *  library turns 100 samples of those counts into HR and SpO2. That DSP
 *  step is unavoidable and is why each reading takes ~4 seconds.
 *
 *  These are prototype-grade sensors, NOT medical devices. For accuracy
 *  and calibration details see docs/firmware/ESP32_Sensor_Guide.md.
 * ============================================================================
 */

#include <Wire.h>
#include "MAX30105.h"          // from SparkFun MAX3010x library (works with MAX30102)
#include "spo2_algorithm.h"    // Maxim HR/SpO2 algorithm, ships with the same library
#include <Adafruit_MLX90614.h>

// ─────────────────────── OPTIONAL BACKEND UPLOAD ────────────────────────────
// 0 = sensor test only (Serial Monitor). Recommended first.
// 1 = also POST valid readings to the HealSense FastAPI backend.
#define ENABLE_WIFI_UPLOAD 0

#if ENABLE_WIFI_UPLOAD
  #include <WiFi.h>
  #include <HTTPClient.h>

  const char* WIFI_SSID      = "YOUR_WIFI_SSID";
  const char* WIFI_PASSWORD  = "YOUR_WIFI_PASSWORD";
  // IP of the PC running your backend on the same WiFi, e.g.
  // "http://192.168.1.50:8000"  (use your uvicorn port)
  const char* API_BASE       = "http://192.168.1.50:8000";
  const char* TELEMETRY_PATH = "/api/v1/telemetry";
  const char* DEVICE_ID      = "ESP32-001";
  const char* PATIENT_ID     = "P001";
  const char* API_KEY        = "esp32_phase5_key";  // must match the seeded Device row
#endif

// ─────────────────────────── I2C CONFIGURATION ──────────────────────────────
#define I2C_SDA_PIN    21
#define I2C_SCL_PIN    22
// 100 kHz on purpose: the MLX90614 speaks SMBus, whose maximum clock is
// 100 kHz. The MAX30102 could run at 400 kHz, but the bus speed is set
// by the slowest device on it — running the shared bus at 400 kHz makes
// the MLX90614 return NaN / disappear intermittently.
#define I2C_CLOCK_HZ   100000

#define MAX30102_ADDR  0x57
#define MLX90614_ADDR  0x5A

// ─────────────────────────── SENSOR SETTINGS ────────────────────────────────
// MAX30102 FIFO: sampleRate 100 Hz with 4-sample averaging gives an
// effective 25 samples/second. The Maxim algorithm expects 100 samples
// (= 4 seconds) per calculation. Do NOT change BUFFER_SIZE to 400.
#define BUFFER_SIZE 100
uint32_t irBuffer[BUFFER_SIZE];
uint32_t redBuffer[BUFFER_SIZE];

// If the IR count is below this, no finger is on the sensor.
const uint32_t IR_FINGER_THRESHOLD = 50000;

// Validity gates — anything outside these is a bad window, not a reading.
const float MIN_VALID_HR    = 30.0;
const float MAX_VALID_HR    = 220.0;
const float MIN_VALID_SPO2  = 70.0;
const float MAX_VALID_SPO2  = 100.0;

// MLX90614 skin-to-core correction. A skin surface reading is lower than
// core temperature, so this constant offset estimates core. It is a crude
// approximation, NOT a validated clinical conversion (see the guide §4.2).
const float SKIN_TO_CORE_OFFSET = 2.0;   // °C
// Your backend rejects temperatures outside 30–45 °C, so the sketch
// applies the same gate before believing a reading.
const float MIN_VALID_TEMP = 30.0;
const float MAX_VALID_TEMP = 45.0;

#define LED_PIN 2   // built-in LED on most ESP32 DevKits — blinks on a valid reading

// ───────────────────────────── GLOBALS ─────────────────────────────────────
MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

bool maxOk = false;
bool mlxOk = false;

// ───────────────────────── I2C BUS SCANNER ─────────────────────────────────
// Runs once at boot. Expect to see exactly two addresses: 0x57 and 0x5A.
// If one is missing, that sensor's wiring is wrong — fix that first,
// before debugging anything else.
void scanI2CBus() {
  Serial.println(F("\n--- I2C bus scan ---"));
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  Found device at 0x%02X", addr);
      if (addr == MAX30102_ADDR) Serial.print("  <- MAX30102 (HR/SpO2)");
      if (addr == MLX90614_ADDR) Serial.print("  <- MLX90614 (temperature)");
      Serial.println();
      found++;
    }
  }
  if (found == 0) {
    Serial.println(F("  NO devices found! Check: 3V3, GND, SDA=GPIO21, SCL=GPIO22."));
  } else {
    Serial.printf("  %u device(s) on the bus (expected 2).\n", found);
  }
  Serial.println(F("--------------------\n"));
}

// ───────────────────── MAX30102 — HR + SpO2 READING ────────────────────────
// Waits (with a timeout) for the next FIFO sample so a disconnected
// sensor can never hang the sketch forever.
bool waitForSample(uint32_t timeoutMs = 600) {
  uint32_t start = millis();
  while (!particleSensor.available()) {
    particleSensor.check();              // pump the FIFO
    if (millis() - start > timeoutMs) return false;
    delay(1);
  }
  return true;
}

/**
 * Takes one HR/SpO2 measurement.
 * Returns false if there is no finger, or the sensor stopped responding.
 * hrValid / spo2Valid come from the algorithm itself — if they are false,
 * the numbers are meaningless even though a window was captured.
 */
bool readHeartRateSpO2(int32_t &hr, int32_t &spo2,
                       bool &hrValid, bool &spo2Valid,
                       uint32_t &lastIR) {
  // Quick finger check first, so we don't burn 4 s on an empty sensor.
  if (!waitForSample()) return false;
  lastIR = particleSensor.getIR();
  particleSensor.nextSample();
  if (lastIR < IR_FINGER_THRESHOLD) return false;

  // Collect 100 fresh samples (~4 s). Keep the finger still.
  // (uint16_t, not byte — a byte overflows at 255 and can make loops
  //  like this run forever when the count is raised.)
  uint8_t lowSamples = 0;
  for (uint16_t i = 0; i < BUFFER_SIZE; i++) {
    if (!waitForSample()) return false;
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i]  = particleSensor.getIR();
    lastIR       = irBuffer[i];
    particleSensor.nextSample();
    if (irBuffer[i] < IR_FINGER_THRESHOLD) lowSamples++;
  }
  if (lowSamples > 10) return false;   // finger moved / lifted mid-window

  int32_t spo2Val = 0, hrVal = 0;
  int8_t  spo2Ok  = 0, hrOk  = 0;
  maxim_heart_rate_and_oxygen_saturation(irBuffer, BUFFER_SIZE, redBuffer,
                                         &spo2Val, &spo2Ok,
                                         &hrVal,   &hrOk);
  hr = hrVal;          spo2 = spo2Val;
  hrValid = (hrOk == 1);  spo2Valid = (spo2Ok == 1);
  return true;
}

// ───────────────────── MLX90614 — TEMPERATURE READING ──────────────────────
// Averages 3 object readings to smooth the sensor noise. Returns the
// raw object (skin) temperature AND the corrected estimate, so you can
// see both in the Serial Monitor and judge the offset yourself.
bool readTemperature(float &ambientC, float &objectC, float &correctedC) {
  if (!mlxOk) return false;

  ambientC = mlx.readAmbientTempC();

  float sum = 0.0;
  for (uint8_t i = 0; i < 3; i++) {
    float t = mlx.readObjectTempC();
    if (isnan(t)) return false;        // read failed (bus problem)
    sum += t;
    delay(60);
  }
  objectC    = sum / 3.0;
  correctedC = objectC + SKIN_TO_CORE_OFFSET;
  return true;
}

// ─────────────────────── OPTIONAL: BACKEND UPLOAD ──────────────────────────
#if ENABLE_WIFI_UPLOAD
bool ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.printf("[WIFI] Connecting to %s ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WIFI] Connected. IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }
  Serial.println(F("[WIFI] Connection failed"));
  return false;
}

bool uploadReading(int32_t hr, int32_t spo2, float temperatureC) {
  if (!ensureWiFi()) return false;

  HTTPClient http;
  String url = String(API_BASE) + TELEMETRY_PATH;
  http.begin(url);
  http.setTimeout(8000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-API-Key", API_KEY);

  // Built by hand so this sketch needs no JSON library. BP is sent as
  // null with bp_source "none" — the ESP32 has no BP sensor, and the
  // backend must never invent a blood-pressure value.
  char payload[320];
  snprintf(payload, sizeof(payload),
    "{\"device_id\":\"%s\",\"patient_id\":\"%s\","
    "\"heart_rate\":%.1f,\"spo2\":%.1f,\"temperature\":%.2f,"
    "\"systolic_bp\":null,\"diastolic_bp\":null,\"bp_source\":\"none\","
    "\"delayed_sync\":false}",
    DEVICE_ID, PATIENT_ID, (double)hr, (double)spo2, (double)temperatureC);

  int code = http.POST(String(payload));
  Serial.printf("[NET] POST %s -> %d\n", TELEMETRY_PATH, code);
  if (code > 0 && code != 200 && code != 201) {
    Serial.print("[NET] Response: ");
    Serial.println(http.getString());
  }
  http.end();
  return (code == 200 || code == 201);
}
#endif

// ───────────────────────────── SETUP ───────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println(F("\n========================================="));
  Serial.println(F(" HealSense ESP32 — Dual I2C Sensor Test"));
  Serial.println(F(" MAX30102 (0x57) + MLX90614 (0x5A)"));
  Serial.println(F("========================================="));

  // One shared bus for both sensors.
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(I2C_CLOCK_HZ);

  scanI2CBus();

  // --- MAX30102 ---
  // I2C_SPEED_STANDARD (100 kHz), NOT I2C_SPEED_FAST — see the comment
  // at I2C_CLOCK_HZ: the MLX90614 on the same bus cannot do 400 kHz.
  if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD, MAX30102_ADDR)) {
    Serial.println(F("[ERROR] MAX30102 not found at 0x57 — HR/SpO2 disabled."));
    Serial.println(F("        Check VIN->3V3, GND, SDA->GPIO21, SCL->GPIO22."));
  } else {
    // LED brightness, sample average, LED mode (2 = Red + IR),
    // sample rate, pulse width, ADC range.
    particleSensor.setup(60, 4, 2, 100, 411, 4096);
    particleSensor.setPulseAmplitudeGreen(0);   // green LED not used
    maxOk = true;
    Serial.println(F("[OK] MAX30102 ready (0x57)"));
  }

  // Re-assert the bus speed before talking to the MLX90614.
  Wire.setClock(I2C_CLOCK_HZ);

  // --- MLX90614 ---
  if (!mlx.begin()) {
    Serial.println(F("[ERROR] MLX90614 not found at 0x5A — temperature disabled."));
    Serial.println(F("        Check VIN->3V3, GND, SDA->GPIO21, SCL->GPIO22."));
  } else {
    mlxOk = true;
    Serial.printf("[OK] MLX90614 ready (0x5A). Ambient: %.2f C\n",
                  (double)mlx.readAmbientTempC());
  }

#if ENABLE_WIFI_UPLOAD
  ensureWiFi();
#endif

  Serial.println(F("\nPlace your finger on the MAX30102 and keep it still...\n"));
}

// ────────────────────────────── LOOP ───────────────────────────────────────
void loop() {
  float ambientC = NAN, objectC = NAN, correctedC = NAN;

  // If the MAX30102 is missing, still prove the temperature sensor works.
  if (!maxOk) {
    if (readTemperature(ambientC, objectC, correctedC)) {
      Serial.printf("[TEMP] Ambient %.2f C | Object %.2f C | Corrected %.2f C\n",
                    (double)ambientC, (double)objectC, (double)correctedC);
    } else {
      Serial.println(F("[TEMP] MLX90614 read failed (NaN). Check wiring/bus speed."));
    }
    delay(1000);
    return;
  }

  // --- Take one HR/SpO2 window (blocks ~4 s) ---
  int32_t  hr = 0, spo2 = 0;
  bool     hrValid = false, spo2Valid = false;
  uint32_t lastIR = 0;

  if (!readHeartRateSpO2(hr, spo2, hrValid, spo2Valid, lastIR)) {
    // No finger (or it moved). Still show temperature so you can test
    // the MLX90614 on its own.
    bool tOk = readTemperature(ambientC, objectC, correctedC);
    Serial.printf("[MAX30102] No finger / unstable (IR=%lu). "
                  "Place finger flat on the sensor, don't press hard.",
                  (unsigned long)lastIR);
    if (tOk) {
      Serial.printf("  | Temp obj %.2f C (corrected %.2f C)",
                    (double)objectC, (double)correctedC);
    }
    Serial.println();
    delay(1000);
    return;
  }

  // --- Temperature, taken right after the HR window ---
  bool tempOk = readTemperature(ambientC, objectC, correctedC);

  bool vitalsGood = hrValid && spo2Valid &&
                    hr   >= MIN_VALID_HR   && hr   <= MAX_VALID_HR &&
                    spo2 >= MIN_VALID_SPO2 && spo2 <= MAX_VALID_SPO2;
  bool tempGood = tempOk &&
                  correctedC >= MIN_VALID_TEMP && correctedC <= MAX_VALID_TEMP;

  Serial.println(F("------------------------------------------"));
  Serial.printf(" Heart Rate : %ld bpm   %s\n", (long)hr,
                hrValid ? "(valid)" : "(INVALID - ignore)");
  Serial.printf(" SpO2       : %ld %%     %s\n", (long)spo2,
                spo2Valid ? "(valid)" : "(INVALID - ignore)");
  if (tempOk) {
    Serial.printf(" Temp amb   : %.2f C\n", (double)ambientC);
    Serial.printf(" Temp skin  : %.2f C   (raw MLX90614 object reading)\n",
                  (double)objectC);
    Serial.printf(" Temp est.  : %.2f C   (skin + %.1f correction)%s\n",
                  (double)correctedC, (double)SKIN_TO_CORE_OFFSET,
                  tempGood ? "" : "  <- outside 30-45 C, sensor aim?");
  } else {
    Serial.println(F(" Temp       : read failed (NaN)"));
  }
  Serial.printf(" Result     : %s\n",
                (vitalsGood && tempGood)
                  ? "GOOD reading"
                  : "UNRELIABLE — keep finger still, aim MLX90614 at skin");
  Serial.println(F("------------------------------------------"));

  if (vitalsGood && tempGood) {
    digitalWrite(LED_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);

#if ENABLE_WIFI_UPLOAD
    uploadReading(hr, spo2, correctedC);
#endif
  }
#if ENABLE_WIFI_UPLOAD
  else {
    Serial.println(F("[NET] Reading not valid — nothing sent to backend."));
  }
#endif

  delay(1000);   // next reading in ~1 s (the HR window itself takes ~4 s)
}
