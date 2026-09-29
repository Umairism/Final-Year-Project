# Phase 0: API Inventory & Service Map

**Project**: HealSense API Service Map  
**Date**: August 2, 2026  

---

## 1. Registered API Endpoints Summary

```
┌────────────────────────────────────────────────────────────────────────┐
│                        API ENDPOINT INVENTORY                          │
├──────────────────────┬────────┬────────────────────────────────────────┤
│ Endpoint Path        │ Method │ Description & Handler Function        │
├──────────────────────┼────────┼────────────────────────────────────────┤
│ /health              │ GET    │ API Health Status Check                │
│ /                    │ GET    │ Root Endpoint & Navigation Index       │
│                      │        │                                        │
│ -- Patients Router --│        │                                        │
│ /api/v1/patients/{id}│ GET    │ Fetch patient record by ID             │
│ /{id}/profile        │ GET    │ Patient profile with latest vitals     │
│ /{id}/vitals/latest  │ GET    │ Latest vital signs record              │
│ /{id}/vitals         │ POST   │ Ingest vital signs & trigger ML/Alerts │
│ /{id}/fusion_risk    │ GET    │ Evaluate 5-layer hybrid risk decision  │
│ /{id}/alerts         │ GET    │ Fetch patient alert history            │
│                      │        │                                        │
│ -- Devices Router -- │        │                                        │
│ /devices/{id}/status │ GET    │ Query device connection status         │
│ /devices/{id}/connect│ POST   │ Connect device to patient              │
│ /devices/register/phone POST  │ Register mobile phone as telemetry node│
│                      │        │                                        │
│ -- AI Router --      │        │                                        │
│ /api/v1/ai/predict   │ POST   │ Direct ML sequence risk prediction     │
│ /api/v1/ai/explain   │ POST   │ Direct Gemini explanation generation   │
│                      │        │                                        │
│ -- Realtime Router --│        │                                        │
│ /ws/patients/{id}    │ WS     │ WebSocket real-time patient stream     │
│ /ws/devices/{id}     │ WS     │ WebSocket real-time device stream      │
└──────────────────────┴────────┴────────────────────────────────────────┘
```

---

## 2. Ingestion Route Deficiency Analysis

* **Deficiency**: There is currently **no dedicated direct-device telemetry endpoint** (e.g., `POST /api/v1/telemetry`).
* **Current Workaround**: Hardware sensors post data under `/api/v1/patients/{patient_id}/vitals`.
* **Required Target Refactor**: Implement `POST /api/v1/telemetry` which accepts hardware device tokens, validates Pydantic schemas, maps `device_id` to `patient_id`, records `bp_source` and `delayed_sync`, and broadcasts real-time events.
