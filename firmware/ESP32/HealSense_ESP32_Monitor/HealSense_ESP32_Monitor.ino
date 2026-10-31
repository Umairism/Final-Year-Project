/**
 * ============================================================================
 *  HealSense — ESP32 Patient Monitor  (Sensors + OLED + Backend Upload)
 * ============================================================================
 *  BUILD IDENTITY (printed on Serial + OLED at boot — check this to prove
 *  you are running THIS sketch and not an old copy):
 *      HEALSENSE-ESP32 v3.4 CONTINUITY-FIX (2026-10-31)
 *
 *  THREE devices on ONE shared I2C bus (shared SDA/SCL is normal — each
 *  device has its own address):
 *
 *    • MAX30102       — heart rate + SpO2           (I2C 0x57)
 *    • MLX90614       — non-contact IR temperature  (I2C 0x5A)
 *    • OLED GME12864-50 — 128x64 SSD1306 display    (I2C 0x3C)
 *
 *  Wiring (ESP32 DevKit, 30-pin):
 *
 *    ESP32     MAX30102    MLX90614     OLED (GME12864-50)
 *    -------   ---------   ----------   ------------------
 *    3V3  ---> VIN         VIN          VDD / VCC
 *    GND  ---> GND         GND          GND
 *    D21  ---> SDA    ---- SDA     ---- SDA        (shared)
 *    D22  ---> SCL    ---- SCL     ---- SCK / SCL  (shared)
 *
 *    !! OLED WARNING: on most GME12864-50 boards the pin order printed
 *       on the board is  GND | VDD | SCK | SDA  (power pins first).
 *       READ THE SILKSCREEN on YOUR board and wire by LABEL, not by
 *       position. Swapping VDD/GND can kill the display instantly.
 *
 *  Arduino IDE setup:
 *    Tools > Board : "ESP32 Dev Module"   (esp32 by Espressif Systems)
 *    Tools > Port  : your ESP32 COM port
 *    Serial Monitor: 115200 baud
 *
 *  Libraries (Tools > Manage Libraries — install these three):
 *    1. "SparkFun MAX3010x Pulse and Proximity Sensor Library"
 *    2. "Adafruit MLX90614 Library"
 *    3. "Adafruit SSD1306"        (Adafruit GFX + BusIO install with it)
 *
 *  What it does:
 *    • Boot: scans the I2C bus (expect 0x3C, 0x57, 0x5A), shows a
 *      HealSense splash on the OLED, connects WiFi if configured.
 *    • Loop: after a stable finger is detected, 2 s of samples are
 *      discarded while the OLED shows the LIVE infrared signal level.
 *      A 100-sample window is then analysed, followed by rolling
 *      25-sample updates (~1 s). Three consecutive windows must agree
 *      before the median HR/SpO2 is called stable. Only a stable
 *      reading + plausible temperature is POSTed to the backend:
 *      POST /api/v1/telemetry (header X-Device-API-Key). Bad windows
 *      are shown as "UNRELIABLE" and are NEVER uploaded.
 *    • Measurement cycle: the final result stays on the OLED for at
 *      least 5 s (FIFO drained meanwhile so it cannot overflow),
 *      then the sample arrays and sensor FIFO are WIPED and a fresh
 *      cycle starts. Memory use is fixed: two 100x4-byte arrays
 *      (800 bytes total) reused every cycle, plus at most ONE queued
 *      result (3 numbers) if an upload fails.
 *    • Bench mode: if you leave WIFI_SSID as "YOUR_WIFI_SSID", the
 *      sketch skips networking entirely (OLED shows OFFLINE) so you
 *      can test sensors first. Fill in WiFi + API_BASE to go live.
 *
 *  These are prototype-grade sensors, NOT medical devices.
 * ============================================================================
 */

#include <Wire.h>
#include "MAX30105.h"          // SparkFun MAX3010x library (works with MAX30102)
#include "spo2_algorithm.h"    // Maxim HR/SpO2 algorithm, ships with the library
#include <Adafruit_MLX90614.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SKETCH_ID "HEALSENSE-ESP32 v3.4 CONTINUITY-FIX (2026-10-31)"

// ══════════════════════ USER CONFIGURATION ═════════════════════════════════
#if __has_include("healsense_local_config.h")
#include "healsense_local_config.h"
#else
// 1 = enable WiFi + backend upload. 0 = OLED/Serial bench test only.
#define ENABLE_WIFI_UPLOAD 1

const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // <-- your WiFi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // <-- your WiFi password

// HealSense backend address — pick ONE shape and edit the value:
//   Laptop on same WiFi (closed-loop test):  "http://192.168.1.50:5000"
//        (find the IP: run `ipconfig` on the laptop -> WLAN IPv4.
//         Backend must be running: python run.py  -> port 5000.
//         Windows Firewall: allow Python through on Private network.)
//   Oracle Cloud (later):                    "https://your-backend-domain"
const char* API_BASE       = "http://YOUR_LAN_IP:5000";
const char* TELEMETRY_PATH = "/api/v1/telemetry";

// Must match a Device row in the backend database. If the backend log
// says "Unregistered device", register it first (dashboard Devices
// page, or POST /api/v1/devices/ESP32-001/connect?patient_id=P001
// from http://localhost:5000/api/docs).
const char* DEVICE_ID  = "ESP32-001";
const char* PATIENT_ID = "P001";
const char* API_KEY    = "YOUR_DEVICE_API_KEY";
#endif

// MAX30102 FIFO channel order:
//   1 = generic / MH-ET LIVE MAX30102 breakout. Through the SparkFun
//       library these boards deliver IR in the first FIFO slot and
//       Red in the second, the opposite of the library's MAX30105
//       labels. HR still works when swapped, but the SpO2 ratio is
//       inverted and produces impossible values (e.g. 11-20%).
//       HealSense uses a MAX30102 breakout, so this stays 1.
//   0 = SparkFun MAX30105 breakout (first FIFO slot really is Red).
// The Serial log prints BOTH orientations each window ("Orientation
// test" line) so the correct setting is provable from data: the
// correct orientation is the one whose SpO2 agrees with a fingertip
// oximeter. If the opposite orientation is the sane one, flip this.
#define MAX30102_SWAP_RED_IR 1
// ═══════════════════════════════════════════════════════════════════════════

#if ENABLE_WIFI_UPLOAD
  #include <WiFi.h>
  #include <WiFiClientSecure.h>
  #include <HTTPClient.h>
#endif

// ─────────────────────────── I2C CONFIGURATION ──────────────────────────────
#define I2C_SDA_PIN    21
#define I2C_SCL_PIN    22
// 100 kHz on purpose: the MLX90614 speaks SMBus (max 100 kHz). The bus
// runs at the speed of its slowest device; 400 kHz makes the MLX90614
// return NaN / drop off the bus intermittently.
#define I2C_CLOCK_HZ   100000

#define MAX30102_ADDR  0x57
#define MLX90614_ADDR  0x5A
#define OLED_ADDR      0x3C   // some boards answer at 0x3D — the boot
                              // I2C scan tells you. Change if needed.

// ─────────────────────────── OLED (GME12864-50) ─────────────────────────────
#define SCREEN_WIDTH   128
#define SCREEN_HEIGHT  64
#define OLED_RESET     -1     // no reset pin on this module
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
bool oledOk = false;

// ─────────────────────────── SENSOR SETTINGS ────────────────────────────────
// FIFO: 100 Hz sample rate with 4-sample averaging = 25 samples/sec.
// The Maxim algorithm expects exactly 100 samples (= 4 s) per window.
#define BUFFER_SIZE 100
#define PPG_SAMPLE_RATE_HZ 25
#define SETTLE_SAMPLES 50             // 2 s discarded after finger contact
#define ROLLING_STEP_SAMPLES 25       // then recalculate every ~1 s
#define REQUIRED_STABLE_WINDOWS 3     // windows must agree before "stable"
uint32_t irBuffer[BUFFER_SIZE];
uint32_t redBuffer[BUFFER_SIZE];

const uint32_t IR_FINGER_THRESHOLD = 50000;  // below this: no finger
const uint32_t IR_SATURATION_LEVEL = 250000; // near the 18-bit ADC limit
const float MIN_PERFUSION_INDEX_PCT = 0.10f; // AC variation / DC mean, %
const uint8_t MAX_LOW_SAMPLES = 5;
const uint8_t MAX_SATURATED_SAMPLES = 2;
// Red channel needs a real pulse too, or SpO2 is meaningless even
// when IR/HR look perfect. Floors are deliberately lenient.
const float MIN_RED_MEAN = 10000.0f;
const float MIN_RED_PERFUSION_INDEX_PCT = 0.03f;
const uint8_t MAX_RED_SATURATED_SAMPLES = 2;

// Validity gates — outside these, it's a bad window, not a reading.
const float MIN_VALID_HR   = 30.0;
const float MAX_VALID_HR   = 220.0;
const float MIN_VALID_SPO2 = 70.0;
const float MAX_VALID_SPO2 = 100.0;

// Skin surface reads lower than core; crude estimate offset only.
const float SKIN_TO_CORE_OFFSET = 2.0;   // °C
// Backend schema accepts temperature only within 30–45 °C.
const float MIN_VALID_TEMP = 30.0;
const float MAX_VALID_TEMP = 45.0;

#define LED_PIN 2   // built-in LED — blinks on a GOOD reading

// Rolling windows update every ~1 s during a cycle. Uploads happen
// once per completed cycle and never more often than this interval;
// a reading that becomes due earlier waits in the 1-slot queue.
const uint32_t MIN_UPLOAD_INTERVAL_MS = 10000;

// The final result screen must stay readable for at least this long.
// During the hold the MAX30102 FIFO is continuously drained (samples
// discarded) so the 32-sample hardware FIFO can never overflow.
#define RESULT_HOLD_MS 5000

// ───────────────────────────── GLOBALS ─────────────────────────────────────
MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

bool maxOk = false;
bool mlxOk = false;

#if ENABLE_WIFI_UPLOAD
bool wifiConfigured = false;   // false while SSID is still the placeholder
#endif
int      lastPostCode = 0;         // 0 = nothing sent yet
uint32_t lastUploadMs = 0;
bool     hasLastGood  = false;     // last GOOD reading, shown when a
int32_t  lastGoodHr   = 0;         // later window is unstable
int32_t  lastGoodSpo2 = 0;
float    lastGoodTemp = 0.0;

struct PpgStats {
  float    meanIR = 0.0;
  uint32_t minIR = 0;
  uint32_t maxIR = 0;
  float    perfusionIndexPct = 0.0;
  uint8_t  lowSamples = 0;
  uint8_t  saturatedSamples = 0;
  float    meanRed = 0.0;
  uint32_t minRed = 0;
  uint32_t maxRed = 0;
  float    redPerfusionIndexPct = 0.0;
  uint8_t  redSaturatedSamples = 0;
};

PpgStats currentStats;
bool     ppgWindowReady = false;
uint32_t lastPpgSampleMs = 0;
uint8_t  ledBrightness = 60;       // adjusted only if signal saturates
int32_t  stableHrHistory[REQUIRED_STABLE_WINDOWS] = {0, 0, 0};
int32_t  stableSpo2History[REQUIRED_STABLE_WINDOWS] = {0, 0, 0};
uint8_t  stableWindowCount = 0;
bool     hasStableReading = false;
int32_t  stableHr = 0;
int32_t  stableSpo2 = 0;

// Opposite-orientation result for the same window (diagnostic only;
// never used for acceptance or upload). Lets the Serial log prove
// which way MAX30102_SWAP_RED_IR must be set for this physical board.
int32_t  diagAltHr = 0;
int32_t  diagAltSpo2 = 0;
bool     diagAltHrValid = false;
bool     diagAltSpo2Valid = false;

// Bounded upload queue: exactly ONE pending result (3 numbers), used
// only when a POST fails. The 100-sample arrays are wiped regardless,
// so memory can never grow cycle after cycle.
struct PendingUpload {
  int32_t hr = 0;
  int32_t spo2 = 0;
  float   temperatureC = 0.0f;
};
PendingUpload pendingUpload;
bool     hasPendingUpload = false;
uint32_t measurementCycle = 0;

// ─────────────────────────── OLED HELPERS ──────────────────────────────────
const char* netStatusText() {
#if ENABLE_WIFI_UPLOAD
  if (!wifiConfigured) return "OFFLINE";
  return (WiFi.status() == WL_CONNECTED) ? "WiFi OK" : "WiFi...";
#else
  return "BENCH";
#endif
}

void oledHeader() {
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print(F("HealSense"));
  const char* st = netStatusText();
  display.setCursor(SCREEN_WIDTH - (int)strlen(st) * 6, 0);
  display.print(st);
  display.drawFastHLine(0, 10, SCREEN_WIDTH, SSD1306_WHITE);
}

void showSplash() {
  if (!oledOk) return;
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(8, 6);
  display.print(F("HealSense"));
  display.setTextSize(1);
  display.setCursor(22, 30);
  display.print(F("ESP32 Monitor"));
  display.setCursor(16, 44);
  display.print(F("v3.4 CONTINUITY-FIX"));
  display.setCursor(28, 55);
  display.print(F("Starting..."));
  display.display();
}

void showSensorStatus() {
  if (!oledOk) return;
  display.clearDisplay();
  oledHeader();
  display.setTextSize(1);
  display.setCursor(0, 18);
  display.printf("MAX30102 : %s\n", maxOk ? "OK" : "MISSING");
  display.printf("MLX90614 : %s\n", mlxOk ? "OK" : "MISSING");
  display.printf("OLED     : OK\n");
  display.setCursor(0, 54);
  display.print(maxOk ? F("Place finger...") : F("Check wiring!"));
  display.display();
}

void showNoFinger(uint32_t liveIR, bool tempOk, float objectC, float ambientC) {
  if (!oledOk) return;
  display.clearDisplay();
  oledHeader();
  display.setTextSize(2);
  display.setCursor(22, 14);
  display.print(F("PLACE"));
  display.setCursor(16, 32);
  display.print(F("FINGER"));
  display.setTextSize(1);
  display.setCursor(0, 54);
  if (tempOk) {
    display.printf("IR:%lu Skin:%.1fC", (unsigned long)liveIR,
                   (double)objectC);
  } else {
    display.printf("IR:%lu Amb:%.1fC", (unsigned long)liveIR,
                   (double)ambientC);
  }
  display.display();
}

// Real-time optical feedback. This is the raw IR level, not HR/SpO2:
// the algorithm still needs a full window before it can calculate.
void showLiveSignal(uint32_t ir, const char* phase, uint8_t progressPct) {
  if (!oledOk) return;
  static uint32_t lastDrawMs = 0;
  uint32_t now = millis();
  if (now - lastDrawMs < 200) return;
  lastDrawMs = now;

  display.clearDisplay();
  oledHeader();
  display.setTextSize(1);
  display.setCursor(0, 15);
  display.print(F("LIVE IR SIGNAL"));
  display.setCursor(0, 26);
  display.printf("%lu", (unsigned long)ir);

  display.drawRect(0, 38, SCREEN_WIDTH, 10, SSD1306_WHITE);
  uint32_t capped = constrain(ir, 0UL, 220000UL);
  uint16_t fill = (uint16_t)map((long)capped, 0L, 220000L, 0L, 124L);
  if (fill > 0) display.fillRect(2, 40, fill, 6, SSD1306_WHITE);

  display.setCursor(0, 54);
  display.print(phase);
  display.setCursor(104, 54);
  display.printf("%u%%", progressPct);
  display.display();
}

void showCandidate(int32_t hr, int32_t spo2, float tempC) {
  if (!oledOk) return;
  display.clearDisplay();
  oledHeader();
  display.setTextSize(2);
  display.setCursor(0, 14);
  display.printf("HR:%ld", (long)hr);
  display.setTextSize(1);
  display.print(F(" bpm"));
  display.setTextSize(2);
  display.setCursor(0, 34);
  display.printf("SpO2:%ld%%", (long)spo2);
  display.setTextSize(1);
  display.setCursor(0, 56);
  display.printf("T:%.1fC STAB %u/%u", (double)tempC,
                 stableWindowCount, REQUIRED_STABLE_WINDOWS);
  display.display();
}

void showSending(int32_t hr, int32_t spo2, float tempC) {
  if (!oledOk) return;
  display.clearDisplay();
  oledHeader();
  display.setTextSize(2);
  display.setCursor(0, 14);
  display.printf("HR:%ld", (long)hr);
  display.setTextSize(1);
  display.print(F(" bpm"));
  display.setTextSize(2);
  display.setCursor(0, 34);
  display.printf("SpO2:%ld%%", (long)spo2);
  display.setTextSize(1);
  display.setCursor(0, 56);
  display.printf("T:%.1fC Sending...", (double)tempC);
  display.display();
}

// hr / spo2 < 0 means "no valid value" and is shown as --
void showReading(int32_t hr, int32_t spo2, float tempC, bool good) {
  if (!oledOk) return;
  display.clearDisplay();
  oledHeader();
  display.setTextSize(2);
  display.setCursor(0, 14);
  if (hr >= 0) display.printf("HR:%ld", (long)hr);
  else         display.print(F("HR:--"));
  display.setTextSize(1);
  display.print(F(" bpm"));
  display.setTextSize(2);
  display.setCursor(0, 34);
  if (spo2 >= 0) display.printf("SpO2:%ld%%", (long)spo2);
  else           display.print(F("SpO2:--%"));
  display.setTextSize(1);
  display.setCursor(0, 56);
  display.printf("T:%.1fC ", (double)tempC);
  if (!good)                    display.print(F("UNRELIABLE"));
  else if (hasPendingUpload)    display.print(F("QUEUED"));
  else if (lastPostCode == 201) display.print(F("Sent OK"));
  else if (lastPostCode > 0)    display.printf("POST %d", lastPostCode);
  else                          display.print(F("GOOD"));
  display.display();
}

void showUnstable() {
  if (!oledOk) return;
  display.clearDisplay();
  oledHeader();
  display.setTextSize(1);
  display.setCursor(10, 18);
  display.print(F("Unstable reading"));
  display.setCursor(16, 30);
  display.print(F("Keep finger still"));
  display.setCursor(0, 42);
  display.printf("IR %.0fk PI %.2f%%",
                 (double)(currentStats.meanIR / 1000.0f),
                 (double)currentStats.perfusionIndexPct);
  display.setCursor(0, 54);
  if (hasLastGood) {
    display.printf("Last: HR %ld  SpO2 %ld%%",
                   (long)lastGoodHr, (long)lastGoodSpo2);
  } else {
    display.print(F("No stable reading yet"));
  }
  display.display();
}

// ───────────────────────── I2C BUS SCANNER ─────────────────────────────────
// Expect THREE addresses: 0x3C (OLED), 0x57 (MAX30102), 0x5A (MLX90614).
void scanI2CBus() {
  Serial.println(F("\n--- I2C bus scan ---"));
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  Found device at 0x%02X", addr);
      if (addr == MAX30102_ADDR) Serial.print("  <- MAX30102 (HR/SpO2)");
      if (addr == MLX90614_ADDR) Serial.print("  <- MLX90614 (temperature)");
      if (addr == OLED_ADDR || addr == 0x3D) Serial.print("  <- OLED display");
      Serial.println();
      found++;
    }
  }
  if (found == 0) {
    Serial.println(F("  NO devices found! Check 3V3, GND, SDA=D21, SCL=D22."));
  } else {
    Serial.printf("  %u device(s) on the bus (expected 3).\n", found);
  }
  Serial.println(F("--------------------\n"));
}

// ───────────────────── MAX30102 — HR + SpO2 READING ────────────────────────
bool waitForSample(uint32_t timeoutMs = 600) {
  uint32_t start = millis();
  while (!particleSensor.available()) {
    particleSensor.check();
    if (millis() - start > timeoutMs) return false;
    delay(1);
  }
  return true;
}

void resetPpgWindow(bool clearCandidateHistory) {
  ppgWindowReady = false;
  if (clearCandidateHistory) {
    stableWindowCount = 0;
    hasStableReading = false;
  }
}

int32_t medianOfThree(int32_t a, int32_t b, int32_t c) {
  if ((a >= b && a <= c) || (a >= c && a <= b)) return a;
  if ((b >= a && b <= c) || (b >= c && b <= a)) return b;
  return c;
}

void setPpgLedBrightness(uint8_t value) {
  ledBrightness = value;
  particleSensor.setPulseAmplitudeRed(value);
  particleSensor.setPulseAmplitudeIR(value);
  particleSensor.setPulseAmplitudeGreen(0);
}

bool consumePpgSample(uint32_t &red, uint32_t &ir) {
  if (!waitForSample()) return false;
  // Use the FIFO-pair getters, NOT getRed()/getIR(). Those return the
  // most-recent values and each may wait for a different new sample,
  // so a stored Red/IR pair can be time-shifted. getFIFORed() and
  // getFIFOIR() read the same FIFO slot before nextSample() advances.
  uint32_t fifoFirst  = particleSensor.getFIFORed();  // library label
  uint32_t fifoSecond = particleSensor.getFIFOIR();   // library label
  particleSensor.nextSample();

#if MAX30102_SWAP_RED_IR
  // Generic MAX30102 breakout: first slot is physically IR,
  // second slot is physically Red. Correct the labels here so every
  // downstream buffer/statistic/algorithm sees true wavelengths.
  ir  = fifoFirst;
  red = fifoSecond;
#else
  red = fifoFirst;
  ir  = fifoSecond;
#endif

  lastPpgSampleMs = millis();
  return true;
}

// Five quick samples instead of one: room light or a cable bump should
// not look like a finger. The live IR value is shown while checking.
bool stableFingerPresent(uint32_t &averageIR) {
  uint64_t sum = 0;
  uint8_t votes = 0;
  averageIR = 0;
  for (uint8_t i = 0; i < 5; i++) {
    uint32_t red = 0, ir = 0;
    if (!consumePpgSample(red, ir)) return false;
    sum += ir;
    if (ir >= IR_FINGER_THRESHOLD) votes++;
    showLiveSignal(ir, "CHECK FINGER", (uint8_t)((i + 1) * 20));
  }
  averageIR = (uint32_t)(sum / 5ULL);
  return votes >= 4;
}

// Fills (or discards) samples while giving live OLED feedback. The
// sensor FIFO continues buffering during each short display update.
bool collectPpgSamples(uint16_t startIndex, uint16_t count,
                       const char* phase, bool discard) {
  uint8_t lowSamples = 0;
  const uint8_t lowLimit = discard ? 10 : MAX_LOW_SAMPLES;

  for (uint16_t i = 0; i < count; i++) {
    uint32_t red = 0, ir = 0;
    if (!consumePpgSample(red, ir)) return false;

    if (!discard) {
      redBuffer[startIndex + i] = red;
      irBuffer[startIndex + i]  = ir;
    }
    if (ir < IR_FINGER_THRESHOLD) {
      lowSamples++;
      if (lowSamples > lowLimit) return false;
    }
    showLiveSignal(ir, phase,
                   (uint8_t)(((uint32_t)(i + 1) * 100UL) / count));
  }
  return true;
}

bool preparePpgWindow() {
  particleSensor.clearFIFO();       // remove stale samples first
  resetPpgWindow(false);
  if (!collectPpgSamples(0, SETTLE_SAMPLES, "SETTLING", true)) {
    return false;
  }
  if (!collectPpgSamples(0, BUFFER_SIZE, "MEASURING", false)) {
    return false;
  }
  ppgWindowReady = true;
  return true;
}

bool advancePpgWindow() {
  if (!ppgWindowReady) return preparePpgWindow();

  // A long pause (slow HTTP request, for example) can overflow the
  // 32-sample hardware FIFO. Do not analyse a discontinuous buffer.
  if (millis() - lastPpgSampleMs > 1500) {
    Serial.println(F("[PPG] Sample stream interrupted; reacquiring window."));
    return preparePpgWindow();
  }

  const uint16_t keep = BUFFER_SIZE - ROLLING_STEP_SAMPLES;
  memmove(&irBuffer[0], &irBuffer[ROLLING_STEP_SAMPLES],
          keep * sizeof(irBuffer[0]));
  memmove(&redBuffer[0], &redBuffer[ROLLING_STEP_SAMPLES],
          keep * sizeof(redBuffer[0]));

  if (!collectPpgSamples(keep, ROLLING_STEP_SAMPLES,
                         "LIVE UPDATE", false)) {
    ppgWindowReady = false;
    return false;
  }
  return true;
}

void calculateBufferStats() {
  uint64_t sumIR = 0, sumRed = 0;
  uint32_t minIR = UINT32_MAX, maxIR = 0;
  uint32_t minRed = UINT32_MAX, maxRed = 0;
  uint8_t low = 0;
  uint8_t saturated = 0;
  uint8_t redSaturated = 0;

  for (uint16_t i = 0; i < BUFFER_SIZE; i++) {
    uint32_t v = irBuffer[i];
    uint32_t r = redBuffer[i];
    sumIR += v;
    sumRed += r;
    if (v < minIR) minIR = v;
    if (v > maxIR) maxIR = v;
    if (r < minRed) minRed = r;
    if (r > maxRed) maxRed = r;
    if (v < IR_FINGER_THRESHOLD) low++;
    if (v >= IR_SATURATION_LEVEL) saturated++;
    if (r >= IR_SATURATION_LEVEL) redSaturated++;
  }

  currentStats.meanIR = (float)((double)sumIR / BUFFER_SIZE);
  currentStats.minIR = minIR;
  currentStats.maxIR = maxIR;
  currentStats.lowSamples = low;
  currentStats.saturatedSamples = saturated;
  currentStats.perfusionIndexPct =
      currentStats.meanIR > 0.0f
          ? ((float)(maxIR - minIR) * 100.0f / currentStats.meanIR)
          : 0.0f;

  currentStats.meanRed = (float)((double)sumRed / BUFFER_SIZE);
  currentStats.minRed = minRed;
  currentStats.maxRed = maxRed;
  currentStats.redSaturatedSamples = redSaturated;
  currentStats.redPerfusionIndexPct =
      currentStats.meanRed > 0.0f
          ? ((float)(maxRed - minRed) * 100.0f / currentStats.meanRed)
          : 0.0f;
}

bool signalStatsGood() {
  return currentStats.meanIR >= IR_FINGER_THRESHOLD &&
         currentStats.meanIR <= 240000.0f &&
         currentStats.lowSamples <= MAX_LOW_SAMPLES &&
         currentStats.saturatedSamples <= MAX_SATURATED_SAMPLES &&
         currentStats.perfusionIndexPct >= MIN_PERFUSION_INDEX_PCT &&
         currentStats.meanRed >= MIN_RED_MEAN &&
         currentStats.meanRed <= 240000.0f &&
         currentStats.redSaturatedSamples <= MAX_RED_SATURATED_SAMPLES &&
         currentStats.redPerfusionIndexPct >= MIN_RED_PERFUSION_INDEX_PCT;
}

// Only handles clear over/under-exposure. Finger pressure and ambient
// light still matter more than LED current in normal use.
bool adjustLedForSignal() {
  if ((currentStats.meanIR > 235000.0f ||
       currentStats.meanRed > 235000.0f ||
       currentStats.saturatedSamples > MAX_SATURATED_SAMPLES ||
       currentStats.redSaturatedSamples > MAX_RED_SATURATED_SAMPLES) &&
      ledBrightness > 25) {
    uint8_t next = ledBrightness > 45 ? ledBrightness - 20 : 25;
    Serial.printf("[PPG] Signal saturated; LED brightness %u -> %u\n",
                  ledBrightness, next);
    setPpgLedBrightness(next);
    return true;
  }
  if ((currentStats.meanIR < IR_FINGER_THRESHOLD ||
       currentStats.meanRed < MIN_RED_MEAN) && ledBrightness < 110) {
    uint8_t next = ledBrightness + 20;
    Serial.printf("[PPG] Signal weak; LED brightness %u -> %u\n",
                  ledBrightness, next);
    setPpgLedBrightness(next);
    return true;
  }
  return false;
}

void analyzePpgWindow(int32_t &hr, int32_t &spo2,
                      bool &hrValid, bool &spo2Valid) {
  calculateBufferStats();

  int32_t spo2Val = 0, hrVal = 0;
  int8_t  spo2Ok  = 0, hrOk  = 0;
  maxim_heart_rate_and_oxygen_saturation(irBuffer, BUFFER_SIZE, redBuffer,
                                         &spo2Val, &spo2Ok,
                                         &hrVal,   &hrOk);
  hr = hrVal;
  spo2 = spo2Val;
  hrValid = (hrOk == 1);
  spo2Valid = (spo2Ok == 1);

  // Diagnostic only: run the same buffers with wavelengths exchanged.
  // The algorithm copies its inputs internally, so this second call
  // does not disturb the primary result above.
  int32_t altSpo2Val = 0, altHrVal = 0;
  int8_t altSpo2Ok = 0, altHrOk = 0;
  maxim_heart_rate_and_oxygen_saturation(redBuffer, BUFFER_SIZE, irBuffer,
                                         &altSpo2Val, &altSpo2Ok,
                                         &altHrVal, &altHrOk);
  diagAltHr = altHrVal;
  diagAltSpo2 = altSpo2Val;
  diagAltHrValid = (altHrOk == 1);
  diagAltSpo2Valid = (altSpo2Ok == 1);
}

// The Maxim "valid" flags alone are not enough: it can call impossible
// values valid on a noisy window. Require three overlapping windows
// to land close together, then use their median.
bool addStableCandidate(int32_t hr, int32_t spo2) {
  uint8_t idx;
  if (stableWindowCount < REQUIRED_STABLE_WINDOWS) {
    idx = stableWindowCount++;
  } else {
    stableHrHistory[0] = stableHrHistory[1];
    stableHrHistory[1] = stableHrHistory[2];
    stableSpo2History[0] = stableSpo2History[1];
    stableSpo2History[1] = stableSpo2History[2];
    idx = REQUIRED_STABLE_WINDOWS - 1;
  }
  stableHrHistory[idx] = hr;
  stableSpo2History[idx] = spo2;

  if (stableWindowCount < REQUIRED_STABLE_WINDOWS) {
    hasStableReading = false;
    return false;
  }

  int32_t hrMin = min(stableHrHistory[0],
                      min(stableHrHistory[1], stableHrHistory[2]));
  int32_t hrMax = max(stableHrHistory[0],
                      max(stableHrHistory[1], stableHrHistory[2]));
  int32_t spo2Min = min(stableSpo2History[0],
                        min(stableSpo2History[1], stableSpo2History[2]));
  int32_t spo2Max = max(stableSpo2History[0],
                        max(stableSpo2History[1], stableSpo2History[2]));

  stableHr = medianOfThree(stableHrHistory[0], stableHrHistory[1],
                           stableHrHistory[2]);
  stableSpo2 = medianOfThree(stableSpo2History[0], stableSpo2History[1],
                             stableSpo2History[2]);
  hasStableReading = (hrMax - hrMin <= 12) && (spo2Max - spo2Min <= 3);
  return hasStableReading;
}

// ───────────── RESULT HOLD + MEMORY WIPE (cycle housekeeping) ─────────────
// Drains samples the library has already loaded, so neither the
// MAX30102 hardware FIFO (32 samples) nor the library ring can fill
// up while the sketch is busy showing a result or uploading.
void drainPpgFifo() {
  particleSensor.check();
  uint8_t guard = 0;
  while (particleSensor.available() > 0 && guard++ < 64) {
    (void)particleSensor.getFIFORed();
    (void)particleSensor.getFIFOIR();
    particleSensor.nextSample();
  }
}

// Keeps the result screen untouched for holdMs while continuously
// draining/discarding FIFO samples. Sampling restarts afterwards
// from a wiped, known state — no stale or wrapped data is analysed.
void holdResultScreen(uint32_t holdMs) {
  uint32_t started = millis();
  while ((millis() - started) < holdMs) {
    drainPpgFifo();
    delay(10);
  }
  drainPpgFifo();
}

// End-of-cycle wipe: hardware FIFO cleared, both sample arrays
// zeroed, statistics and stability state reset. The arrays are fixed
// globals (800 bytes total) reused next cycle — nothing accumulates.
// Free heap is printed each cycle so long-run stability is provable
// from the Serial log (it should stay flat for hours).
void wipeMeasurementMemory(const char* reason) {
  particleSensor.clearFIFO();
  drainPpgFifo();
  memset(irBuffer, 0, sizeof(irBuffer));
  memset(redBuffer, 0, sizeof(redBuffer));
  currentStats = PpgStats();
  resetPpgWindow(true);
  lastPpgSampleMs = millis();
  Serial.printf("[MEM] Cycle %lu wiped (%s). Free heap: %u bytes. "
                "Sample buffers: %u bytes (fixed, reused).\n",
                (unsigned long)measurementCycle, reason,
                (unsigned)ESP.getFreeHeap(),
                (unsigned)(sizeof(irBuffer) + sizeof(redBuffer)));
}

// ───────────────────── MLX90614 — TEMPERATURE READING ──────────────────────
bool readTemperature(float &ambientC, float &objectC, float &correctedC) {
  if (!mlxOk) return false;
  Wire.setClock(I2C_CLOCK_HZ);   // OLED bursts may raise the clock; the
                                 // MLX90614 must be addressed at 100 kHz
  ambientC = mlx.readAmbientTempC();
  float sum = 0.0;
  for (uint8_t i = 0; i < 3; i++) {
    float t = mlx.readObjectTempC();
    if (isnan(t)) return false;
    sum += t;
    delay(60);
  }
  objectC    = sum / 3.0;
  correctedC = objectC + SKIN_TO_CORE_OFFSET;
  return true;
}

// ─────────────────────────── BACKEND UPLOAD ────────────────────────────────
#if ENABLE_WIFI_UPLOAD
bool ensureWiFi() {
  if (!wifiConfigured) return false;
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
    Serial.print(F("[WIFI] Connected. ESP32 IP: "));
    Serial.println(WiFi.localIP());
    return true;
  }
  Serial.println(F("[WIFI] Connection failed"));
  return false;
}

// Returns the HTTP status code (201 = stored), or <=0 on transport error.
int uploadReading(int32_t hr, int32_t spo2, float temperatureC) {
  // No rate-limit here: the measurement-cycle logic in loop() calls
  // this at most twice per cycle (queued retry + newest) and enforces
  // MIN_UPLOAD_INTERVAL_MS between successful cadence uploads.
  if (!ensureWiFi()) return 0;

  String url = String(API_BASE) + TELEMETRY_PATH;

  // BP is null with bp_source "none": the ESP32 has no BP sensor and
  // must never invent a blood-pressure value (cuff readings enter via
  // the separate BP-entry feature using the Braun monitor).
  char payload[320];
  snprintf(payload, sizeof(payload),
    "{\"device_id\":\"%s\",\"patient_id\":\"%s\","
    "\"heart_rate\":%.1f,\"spo2\":%.1f,\"temperature\":%.2f,"
    "\"systolic_bp\":null,\"diastolic_bp\":null,\"bp_source\":\"none\","
    "\"delayed_sync\":false}",
    DEVICE_ID, PATIENT_ID, (double)hr, (double)spo2, (double)temperatureC);

  WiFiClient       plainClient;
  WiFiClientSecure secureClient;
  HTTPClient http;
  http.setTimeout(8000);
  if (url.startsWith("https://")) {
    // setInsecure() skips certificate verification — acceptable for an
    // FYP prototype; production firmware should pin the root CA.
    secureClient.setInsecure();
    http.begin(secureClient, url);
  } else {
    http.begin(plainClient, url);
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-API-Key", API_KEY);

  int code = http.POST(String(payload));
  Serial.printf("[NET] POST %s -> %d\n", TELEMETRY_PATH, code);
  if (code > 0 && code != 201) {
    Serial.print(F("[NET] Response: "));
    Serial.println(http.getString());
    Serial.println(F("[NET] Hint: 401/403 = API key, 404 = device not "
                     "registered, 422 = payload rejected."));
  }
  http.end();
  lastUploadMs = millis();
  return code;
}
#endif

// ───────────────────────────── SETUP ───────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println(F("\n========================================="));
  Serial.println(F(" " SKETCH_ID));
  Serial.printf(" Built: %s %s\n", __DATE__, __TIME__);
  Serial.println(F(" MAX30102 + MLX90614 + OLED GME12864-50"));
  Serial.println(F("========================================="));

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(I2C_CLOCK_HZ);

  scanI2CBus();

  // --- OLED first, so every later status is visible without a PC ---
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println(F("[ERROR] OLED not found at 0x3C. If the scan showed "
                     "0x3D, set OLED_ADDR to 0x3D. Continuing headless."));
  } else {
    oledOk = true;
    Serial.println(F("[OK] OLED ready (0x3C)"));
    showSplash();
    delay(1200);
  }
  Wire.setClock(I2C_CLOCK_HZ);

  // --- MAX30102 (100 kHz: I2C_SPEED_STANDARD, shared-bus rule) ---
  if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD, MAX30102_ADDR)) {
    Serial.println(F("[ERROR] MAX30102 not found at 0x57 — HR/SpO2 disabled."));
  } else {
    // brightness, sampleAvg, LED mode (2 = Red+IR), sampleRate,
    // pulseWidth, adcRange
    particleSensor.setup(ledBrightness, 4, 2, 100, 411, 4096);
    particleSensor.setPulseAmplitudeGreen(0);
    maxOk = true;
    Serial.printf("[OK] MAX30102 ready (0x57). Part ID 0x%02X "
                  "(expect 0x15), Rev 0x%02X, RED/IR swap=%d\n",
                  particleSensor.readPartID(),
                  particleSensor.getRevisionID(),
                  MAX30102_SWAP_RED_IR);
  }
  Wire.setClock(I2C_CLOCK_HZ);

  // --- MLX90614 ---
  if (!mlx.begin()) {
    Serial.println(F("[ERROR] MLX90614 not found at 0x5A — temp disabled."));
  } else {
    mlxOk = true;
    Serial.printf("[OK] MLX90614 ready (0x5A). Ambient: %.2f C\n",
                  (double)mlx.readAmbientTempC());
  }

#if ENABLE_WIFI_UPLOAD
  wifiConfigured = (strcmp(WIFI_SSID, "YOUR_WIFI_SSID") != 0);
  if (wifiConfigured) {
    ensureWiFi();
  } else {
    Serial.println(F("[WIFI] SSID not configured — bench mode "
                     "(OLED/Serial only, no uploads)."));
  }
#endif

  showSensorStatus();
  delay(1500);
  Serial.println(F("\nPlace your finger flat on the MAX30102, keep still,"));
  Serial.println(F("and aim the MLX90614 at forehead/skin (2-5 cm).\n"));
}

// ────────────────────────────── LOOP ───────────────────────────────────────
void loop() {
  float ambientC = NAN, objectC = NAN, correctedC = NAN;

  // Temperature-only fallback so each sensor can be proven separately.
  if (!maxOk) {
    if (readTemperature(ambientC, objectC, correctedC)) {
      Serial.printf("[TEMP] Ambient %.2f C | Object %.2f C | Corrected %.2f C\n",
                    (double)ambientC, (double)objectC, (double)correctedC);
      showReading(-1, -1, correctedC, false);
    } else {
      Serial.println(F("[TEMP] MLX90614 read failed (NaN)."));
      showSensorStatus();
    }
    delay(1000);
    return;
  }

  // --- Require a steady finger before spending seconds sampling ---
  // Once ppgWindowReady is true, loop() must not consume samples outside
  // advancePpgWindow(), otherwise the rolling buffer becomes discontinuous.
  // Finger removal is still detected by collectPpgSamples() through its
  // low-sample limit, which aborts and resets the window.
  uint32_t liveIR = 0;
  if (!ppgWindowReady && !stableFingerPresent(liveIR)) {
    resetPpgWindow(true);
    bool tOk = readTemperature(ambientC, objectC, correctedC);
    Serial.printf("[MAX30102] No stable finger (avg IR=%lu). "
                  "Cover the window fully; gentle pressure only.",
                  (unsigned long)liveIR);
    if (tOk) {
      Serial.printf("  Skin %.2f C (est %.2f C)",
                    (double)objectC, (double)correctedC);
    }
    Serial.println();
    showNoFinger(liveIR, tOk, objectC, ambientC);
    delay(300);
    return;
  }

  // First acquisition: settle 2 s + collect 100 samples. Afterwards:
  // shift the window by 25 samples and recalculate roughly every 1 s.
  if (!advancePpgWindow()) {
    resetPpgWindow(true);
    Serial.println(F("[MAX30102] Window aborted — finger moved, lifted, "
                     "or pressure changed during sampling."));
    showUnstable();
    delay(500);
    return;
  }

  int32_t rawHr = 0, rawSpo2 = 0;
  bool hrValid = false, spo2Valid = false;
  analyzePpgWindow(rawHr, rawSpo2, hrValid, spo2Valid);

  bool tempOk = readTemperature(ambientC, objectC, correctedC);
  bool opticalGood = signalStatsGood();
  bool algorithmPlausible =
      hrValid && spo2Valid &&
      rawHr >= MIN_VALID_HR && rawHr <= MAX_VALID_HR &&
      rawSpo2 >= MIN_VALID_SPO2 && rawSpo2 <= MAX_VALID_SPO2;
  bool candidateGood = opticalGood && algorithmPlausible;
  bool tempGood = tempOk &&
                  correctedC >= MIN_VALID_TEMP &&
                  correctedC <= MAX_VALID_TEMP;

  bool stableNow = false;
  if (candidateGood) {
    stableNow = addStableCandidate(rawHr, rawSpo2);
  }

  Serial.println(F("------------------------------------------"));
  Serial.printf(" Algorithm HR   : %ld bpm   %s\n", (long)rawHr,
                hrValid ? "(flag valid)" : "(flag invalid)");
  Serial.printf(" Algorithm SpO2 : %ld %%     %s\n", (long)rawSpo2,
                spo2Valid ? "(flag valid)" : "(flag invalid)");
  Serial.printf(" Optical signal : IR mean %.0f | min %lu | max %lu\n",
                (double)currentStats.meanIR,
                (unsigned long)currentStats.minIR,
                (unsigned long)currentStats.maxIR);
  Serial.printf("                  PI %.2f%% | low %u | saturated %u | LED %u\n",
                (double)currentStats.perfusionIndexPct,
                currentStats.lowSamples,
                currentStats.saturatedSamples,
                ledBrightness);
  Serial.printf(" Optical RED    : mean %.0f | min %lu | max %lu | PI %.2f%% | sat %u\n",
                (double)currentStats.meanRed,
                (unsigned long)currentStats.minRed,
                (unsigned long)currentStats.maxRed,
                (double)currentStats.redPerfusionIndexPct,
                currentStats.redSaturatedSamples);
  Serial.printf(" Orientation    : swap=%d selected | opposite test HR %ld SpO2 %ld (flags %d/%d)\n",
                MAX30102_SWAP_RED_IR,
                (long)diagAltHr, (long)diagAltSpo2,
                diagAltHrValid ? 1 : 0, diagAltSpo2Valid ? 1 : 0);
  if (tempOk) {
    Serial.printf(" Temp amb/skin  : %.2f C / %.2f C\n",
                  (double)ambientC, (double)objectC);
    Serial.printf(" Temp estimated : %.2f C (skin + %.1f)%s\n",
                  (double)correctedC, (double)SKIN_TO_CORE_OFFSET,
                  tempGood ? "" : "  <- outside 30-45 C; aim at skin");
    if (objectC - ambientC < 3.0f) {
      Serial.println(F(" Temp hint      : object is barely above ambient — "
                       "MLX90614 is seeing background/cold finger. Aim it "
                       "perpendicular at forehead skin, 1-3 cm away."));
    }
  } else {
    Serial.println(F(" Temperature    : read failed (NaN)"));
  }

  if (!candidateGood) {
    Serial.printf(" Result         : %s\n",
                  !opticalGood
                      ? "WEAK OPTICAL SIGNAL — reposition finger, ease pressure, block room light"
                      : "ALGORITHM OUTPUT REJECTED — not uploaded");
    Serial.println(F("------------------------------------------"));

    adjustLedForSignal();
    resetPpgWindow(true);
    showReading((rawHr >= MIN_VALID_HR && rawHr <= MAX_VALID_HR) ? rawHr : -1,
                (rawSpo2 >= MIN_VALID_SPO2 && rawSpo2 <= MAX_VALID_SPO2)
                    ? rawSpo2 : -1,
                tempOk ? correctedC : 0.0, false);
    delay(700);
    showUnstable();
    delay(300);
    return;
  }

  if (!stableNow) {
    Serial.printf(" Result         : STABILIZING %u/%u — keep finger still\n",
                  stableWindowCount, REQUIRED_STABLE_WINDOWS);
    Serial.println(F("------------------------------------------"));
    showCandidate(rawHr, rawSpo2, tempOk ? correctedC : lastGoodTemp);
    delay(100);
    return;
  }

  Serial.printf(" Stable median  : HR %ld bpm | SpO2 %ld %%\n",
                (long)stableHr, (long)stableSpo2);
  Serial.printf(" Result         : %s\n",
                tempGood ? "STABLE READING — eligible to upload"
                         : "VITALS STABLE, TEMP INVALID — not uploaded");
  Serial.println(F("------------------------------------------"));

  measurementCycle++;

  if (tempGood) {
    hasLastGood  = true;
    lastGoodHr   = stableHr;
    lastGoodSpo2 = stableSpo2;
    lastGoodTemp = correctedC;

    digitalWrite(LED_PIN, HIGH);
    delay(120);
    digitalWrite(LED_PIN, LOW);

#if ENABLE_WIFI_UPLOAD
    if (wifiConfigured) {
      showSending(stableHr, stableSpo2, correctedC);

      PendingUpload currentUpload;
      currentUpload.hr = stableHr;
      currentUpload.spo2 = stableSpo2;
      currentUpload.temperatureC = correctedC;

      int displayCode = 0;

      // 1) An older unsent reading goes first.
      if (hasPendingUpload) {
        displayCode = uploadReading(pendingUpload.hr, pendingUpload.spo2,
                                    pendingUpload.temperatureC);
        if (displayCode == 201) {
          hasPendingUpload = false;
          Serial.println(F("[NET] Queued reading uploaded."));
        }
      }

      // 2) Then this cycle's reading — respecting the minimum interval.
      if (!hasPendingUpload) {
        if (lastUploadMs == 0 ||
            millis() - lastUploadMs >= MIN_UPLOAD_INTERVAL_MS) {
          displayCode = uploadReading(currentUpload.hr, currentUpload.spo2,
                                      currentUpload.temperatureC);
          if (displayCode != 201) {
            pendingUpload = currentUpload;
            hasPendingUpload = true;
          }
        } else {
          pendingUpload = currentUpload;
          hasPendingUpload = true;
          displayCode = lastPostCode;
          Serial.println(F("[NET] Upload deferred (interval); "
                           "newest reading queued."));
        }
      } else {
        // Still failing: keep ONLY the newest unsent reading. The
        // queue is one slot by design, so memory stays bounded.
        pendingUpload = currentUpload;
        Serial.println(F("[NET] Upload still failing; newest reading "
                         "kept in 1-slot queue."));
      }
      lastPostCode = displayCode;
    }
#endif
    showReading(stableHr, stableSpo2, correctedC, true);
  } else {
    showReading(stableHr, stableSpo2, correctedC, false);
  }

  // Result stays readable for at least RESULT_HOLD_MS. The FIFO is
  // drained during the hold, then ALL measurement memory is wiped
  // and the next loop iteration restarts acquisition from scratch
  // (CHECK FINGER -> SETTLING -> MEASURING).
  holdResultScreen(RESULT_HOLD_MS);
  wipeMeasurementMemory(tempGood ? "stable cycle complete"
                                 : "stable vitals, invalid temp");
}
