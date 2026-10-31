/**
 * HealSense ESP32 Local Configuration Template
 * 
 * Instructions:
 * 1. Copy this file to "healsense_local_config.h" in this same directory.
 * 2. Replace placeholders below with your local Wi-Fi and device credentials.
 * 3. "healsense_local_config.h" is ignored by git so secrets are never committed.
 */

#ifndef HEALSENSE_LOCAL_CONFIG_H
#define HEALSENSE_LOCAL_CONFIG_H

// 1 = enable WiFi + backend upload. 0 = OLED/Serial bench test only.
#define ENABLE_WIFI_UPLOAD 1

// Wi-Fi network credentials
static const char* WIFI_SSID     = "YOUR_WIFI_SSID";
static const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// HealSense backend address:
//   Local closed-loop test: "http://<LAPTOP_LAN_IP>:5000"  (e.g. "http://192.168.1.50:5000")
//   Cloud deployment:        "https://your-backend-domain"
static const char* API_BASE       = "http://192.168.1.50:5000";
static const char* TELEMETRY_PATH = "/api/v1/telemetry";

// Device credentials (must match registered Device row in backend DB)
static const char* DEVICE_ID  = "ESP32-001";
static const char* PATIENT_ID = "P001";
static const char* API_KEY    = "YOUR_DEVICE_API_KEY";

#endif // HEALSENSE_LOCAL_CONFIG_H

