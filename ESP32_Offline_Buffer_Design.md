# ESP32 Offline Buffering & Resilience Architecture

**Version**: v1.3.0-edge-resilience  
**Target Hardware**: ESP32 / ESP32-WROOM-32 IoT Gateway  
**Date**: August 3, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. Flowchart & Decision Logic

```
                    ┌─────────────────────────┐
                    │ Sensor Telemetry Sample │
                    │ (MAX30100 + MLX90614)   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Create Telemetry Record │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Network & Cloud Available?
                    └───────┬─────────┬───────┘
                            │         │
                   YES      │         │ NO
            ┌───────────────┘         └───────────────┐
            │                                         │
            ▼                                         ▼
┌───────────────────────┐                 ┌───────────────────────┐
│ Send Direct HTTP POST │                 │ Enqueue into NVS Ring │
│ to /api/v1/telemetry  │                 │ Storage (delayed_sync)│
└───────────┬───────────┘                 └───────────────────────┘
            │
            ▼
    ┌───────────────┐
    │ HTTP Success? │
    └───┬───────┬───┘
        │       │
    YES │       │ NO
        │       └─────────────────────────────┐
        ▼                                     ▼
 ┌─────────────┐                   ┌───────────────────────┐
 │ Telemetry   │                   │ Enqueue into NVS Ring │
 │ Transmitted │                   │ Storage (delayed_sync)│
 └─────────────┘                   └───────────────────────┘
```

---

## 2. NVS Ring Buffer Specification

### Data Structure (`TelemetryRecord`)
```cpp
struct TelemetryRecord {
    float heart_rate;
    float spo2;
    float temperature;
    float systolic_bp;
    float diastolic_bp;
    bool delayed_sync;
    uint64_t timestamp;
};
```

### Storage Characteristics
* **Capacity**: 500 records max (~1.5 to 2 hours of continuous 10-second sampling).
* **Behavior**: First-In, First-Out (FIFO) Ring Buffer. When full, the oldest record is automatically evicted to make room for new incoming samples.
* **Persistence**: Written directly to ESP32 **Preferences / NVS Flash Memory**. Survives power loss, manual reset, or watchdog reboots.
* **Sync Flag**: Replayed queued records are automatically serialized with `"delayed_sync": true` in JSON payloads.
