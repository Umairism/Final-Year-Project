# ESP32 Firmware Architecture Specification

**Target Platform**: ESP32 / ESP32-WROOM-32 Microcontroller  
**Framework**: Arduino Framework / ESP-IDF C++  
**Version**: v1.3.0-edge-resilience  
**Date**: August 3, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. Modular Firmware Structure

To maintain clean code architecture and avoid monolithic sketch files (`main.ino`), the firmware is organized into decoupled C++ modules under `firmware/`:

```
firmware/
 ├── storage_manager.h      # NVS Ring Buffer interface & FIFO Queue definitions
 ├── storage_manager.cpp    # 500-sample capacity persistent storage manager
 ├── wifi_manager.h         # Wi-Fi connectivity & 30-sec retry engine header
 ├── wifi_manager.cpp       # Non-blocking Wi-Fi state machine implementation
 ├── telemetry_client.h     # HTTP POST client & JSON payload serializer header
 └── telemetry_client.cpp   # Telemetry upload & NVS queue flush execution
```

---

## 2. Component Specifications

### A. Storage Manager (`storage_manager.cpp` / `.h`)
* **Capacity**: Up to **500 `TelemetryRecord` structs**.
* **Behavior**: First-In First-Out (FIFO). When the queue reaches max capacity, the oldest un-synced sample is automatically evicted to ensure real-time storage for new readings.
* **Reboot Resilience**: Uses ESP32 Preferences / NVS partition to guarantee data survives un-announced reboots or watchdog resets.

### B. Wi-Fi Manager (`wifi_manager.cpp` / `.h`)
* **Non-Blocking Timer**: Executes background connectivity checks every 30 seconds without blocking main sensor sampling loops.
* **Health Check**: Validates network connection before triggering telemetry queue flush.

### C. Telemetry Client (`telemetry_client.cpp` / `.h`)
* **Direct HTTPS Telemetry**: Sends JSON payloads with `X-Device-API-Key` headers directly to `POST /api/v1/telemetry`.
* **Automatic `delayed_sync` Tagging**: Assigns `"delayed_sync": true` to all records queued in NVS and replayed upon network restoration.
