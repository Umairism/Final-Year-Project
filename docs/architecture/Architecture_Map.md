# Phase 0: Architecture Map

**Project**: HealSense Target vs Current Architecture Map  
**Date**: August 2, 2026  

---

## 1. System Topology Overview

```
┌────────────────────────────────────────────────────────┐
│ Deployed Hardware Telemetry                            │
│ MAX30100 (SpO2/HR) + MLX90614 (Temp)                   │
└───────────────────────────┬────────────────────────────┘
                            │ I2C
                            ▼
┌────────────────────────────────────────────────────────┐
│ ESP32 IoT Gateway                                      │
│ • Local NVS ring buffer (500 samples)                  │
│ • Connection retry loop & delayed_sync flag            │
└───────────────────────────┬────────────────────────────┘
                            │ Direct Wi-Fi HTTPS Payload
                            │ Header: X-Device-API-Key
                            ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI Backend Gateway (/api/v1/telemetry)            │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Pydantic Validation & Canonical Clinical Schema        │
└───────────────────────────┬────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
┌───────────────────────────┐       ┌───────────────────────────┐
│ Deterministic Safety      │       │ Temporal LSTM Model       │
│ Rules Engine              │       │ (Rule-Derived Proxy       │
│ (Absolute Safety Bounds)  │       │  Label Trajectories)      │
└─────────┬─────────────────┘       └─────────┬─────────────────┘
          │                                   │
          └─────────────────┬─────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Hybrid Fusion Engine                                   │
│ • Deterministic Critical Override (Hard Priority)      │
│ • ML Confidence Augmentation (Experimental Weights)    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Gemini LLM Explanation Service                         │
│ • Natural Language Explanation (Non-diagnostic)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ PostgreSQL Storage & Web/Mobile Client Broadcast       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Infrastructure & Architectural Boundaries

1. **Raspberry Pi 5 Elimination**: Completely removed from operational pathways. Documented purely as legacy benchmarking research.
2. **Clinical Boundary**: System operates as an *explainable clinical decision support prototype*, avoiding diagnostic or mortality claims.
3. **Blood Pressure Handling**: Designated as an **optional contextual feature** (Manual, BLE Cuff, UART Expansion).

---

## 3. Phase 0 Completion Summary

All 4 required Phase 0 deliverables are complete:
- [Repository_Audit_Report.md](file:///e:/Study%20Material/FYP/FYP-Project/healsense/Repository_Audit_Report.md)
- [API_Inventory.md](file:///e:/Study%20Material/FYP/FYP-Project/healsense/API_Inventory.md)
- [Database_Map.md](file:///e:/Study%20Material/FYP/FYP-Project/healsense/Database_Map.md)
- [Architecture_Map.md](file:///e:/Study%20Material/FYP/FYP-Project/healsense/Architecture_Map.md)

**Next Action**: Provide Phase 1 (Database Alignment) design reports for user review before making any schema or code changes.
