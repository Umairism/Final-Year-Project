# HealSense Cloud Architecture Transition Specification

**Document Version**: 1.0.0  
**Project**: HealSense – Deep Learning-Based Smart Health Surveillance and Prediction Model Using IoT  
**Status**: DRAFT FOR MANUAL REVIEW (NO CODE MODIFIED YET)  
**Date**: August 2, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*  
> This specification documents the transition path from the current repository state to the approved cloud-native architecture.

---

## 1. Current Architecture (As-Is Baseline)

The current implementation in the repository consists of:
* **IoT Hardware / Device Interface**: Basic device registration endpoints in `backend/api/routes/devices.py`. Vitals telemetry is posted under patient management endpoints (`POST /api/v1/patients/{patient_id}/vitals`).
* **Intermediate Layer**: Documentation (`docs/diagrams/`) visually depicts a Raspberry Pi 5 node between ESP32 and Backend, though no active backend code depends on the Pi.
* **Cloud Backend**: FastAPI application (`backend/api/app.py`) using SQLAlchemy ORM (`backend/api/models/database/models.py`) and PostgreSQL.
* **Canonical Schema**: Defined in `backend/api/models/schemas.py` (`CanonicalClinicalFeatureSchema`).
* **Deterministic Rules Engine**: Implemented in `backend/api/services/fusion_engine.py`.
* **Temporal LSTM Pipeline**: Implemented in `backend/api/services/prediction_service.py` requiring a sliding window of 60 historical vital records.
* **Hybrid Fusion Engine**: Combines deterministic rule scores with ML probability, defaulting to a hard critical override when rules trigger `CRITICAL`.
* **LLM Explanation Layer**: Asynchronous HTTP calls to Google Gemini API (`gemini-2.5-flash`) generating clinical reasoning text.
* **Presentation**: Web/Mobile interfaces in `frontend/`.

---

## 2. Final Architecture (Target State)

The approved target architecture establishes a direct, cloud-native telemetry pipeline with full offline resilience:

```
MAX30100 + MLX90614 + Optional BP Input
                │
                ▼
      ESP32 IoT Telemetry Gateway
      • Local NVS ring buffer (500 samples)
      • Automatic reconnect & retry loop
                │
                │ Direct HTTPS Telemetry Payload
                │ Headers: X-Device-API-Key
                │ Payload: { "heart_rate": 78, "spo2": 98, "temperature": 36.8, 
                │            "systolic_bp": null, "bp_source": null, "delayed_sync": false }
                ▼
      FastAPI Telemetry Ingestion Endpoint (/api/v1/telemetry)
                │
                ▼
      Canonical Clinical Schema Validation (Pydantic)
                │
        ┌───────┴───────┐
        ▼               ▼
Deterministic Rules   Temporal LSTM Analysis
(Safety Override)     (Rule-Derived Proxy Labels)
        │               │
        └───────┬───────┘
                ▼
          Fusion Engine (Hard Override + Experimental Weights)
                │
                ▼
     Gemini Explanation Layer (Non-Diagnostic Summary)
                │
                ▼
          PostgreSQL Database (With delayed_sync & bp_source flags)
                │
      Web & Mobile Dashboards
```

---

## 3. Files Requiring Modification

### A. Backend Files
1. [models.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/models/database/models.py)
   * Add `bp_source` (Enum/String: `manual_entry`, `ble_cuff`, `hardware_uart`, `none`) to `VitalSigns` table.
   * Add `delayed_sync` (Boolean, default `False`) to `VitalSigns` table.
   * Add `api_key_hash` (String, nullable) to `Device` table.
2. [schemas.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/models/schemas.py)
   * Add `bp_source` and `delayed_sync` to `VitalSignsBase` and `CanonicalClinicalFeatureSchema`.
   * Make `systolic_bp` and `diastolic_bp` fully optional/nullable in `CanonicalClinicalFeatureSchema`.
3. [devices.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/routes/devices.py)
   * Add dedicated `POST /api/v1/telemetry` endpoint supporting device header authentication (`X-Device-API-Key`).
4. [patients.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/routes/patients.py)
   * Refactor `create_vital_signs` to delegate to the standardized ingestion service.
5. [fusion_engine.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/services/fusion_engine.py)
   * Remove hardcoded default BP imputations (`systolic_bp = vitals.systolic_bp or 120.0`); handle missing BP gracefully during rule evaluation.

### B. Database Migration Files
6. `backend/alembic/versions/<new_migration_hash>_add_bp_source_and_delayed_sync.py`
   * Migration script adding `bp_source` and `delayed_sync` columns to `vital_signs` table, and `api_key_hash` to `devices` table.

### C. Firmware Specifications / Sensor Code
7. `scripts/firmware/esp32_main.ino` (or C++ equivalent spec)
   * Implement NVS ring-buffer storage for offline telemetry caching.
   * Implement connection retry loop every 30 seconds.
   * Flag re-uploaded records with `"delayed_sync": true`.

### D. Frontend Files
8. `frontend/src/components/vitals/VitalsCard.tsx` (or equivalent display component)
   * Update Blood Pressure component to display optional badge showing `bp_source` (Manual, BLE Cuff, or Hardware).
   * Render an indicator icon for vitals ingested via `delayed_sync`.

### E. Documentation Files
9. `docs/diagrams/healsense_architecture.puml`
   * Remove Raspberry Pi 5 from production pipeline diagram; depict direct ESP32 to FastAPI Cloud Backend Wi-Fi connection.
10. `docs/diagrams/deployment_workflow.puml`
   * Remove Raspberry Pi 5 deployment steps.
11. `README.md`
   * Update architecture overview diagram and feature checklist to reflect direct cloud ingestion and optional BP feature status.

---

## 4. Database Changes

### Schema Modification Details (`vital_signs` Table)
```sql
ALTER TABLE vital_signs 
ADD COLUMN bp_source VARCHAR(20) DEFAULT 'none',
ADD COLUMN delayed_sync BOOLEAN DEFAULT FALSE;

ALTER TABLE devices
ADD COLUMN api_key_hash VARCHAR(128) NULL;
```

### SQLAlchemy Model Updates (`backend/api/models/database/models.py`)
```python
class BpSource(str, PyEnum):
    MANUAL_ENTRY = "manual_entry"
    BLE_CUFF = "ble_cuff"
    HARDWARE_UART = "hardware_uart"
    NONE = "none"

# Inside VitalSigns class:
bp_source = Column(Enum(BpSource), default=BpSource.NONE)
delayed_sync = Column(Boolean, default=False)

# Inside Device class:
api_key_hash = Column(String(128), nullable=True)
```

---

## 5. API Changes

### New Endpoint: Direct IoT Telemetry Ingestion
* **Route**: `POST /api/v1/telemetry`
* **Headers**: `X-Device-API-Key: <device_secret>`
* **Request Payload**:
```json
{
  "device_id": "ESP32_PATIENT_001",
  "patient_id": "p_12345",
  "heart_rate": 76.5,
  "spo2": 98.0,
  "temperature": 36.7,
  "systolic_bp": null,
  "diastolic_bp": null,
  "bp_source": "none",
  "delayed_sync": false,
  "timestamp": "2026-08-02T03:45:00Z"
}
```
* **Response**: `201 Created` with fused risk evaluation snippet and persistent record ID.

---

## 6. ESP32 Firmware Changes

1. **Direct Ingestion Path**: Re-target HTTP POST endpoint from Raspberry Pi proxy URL directly to `https://<cloud_host>/api/v1/telemetry`.
2. **Device Header Authentication**: Include `X-Device-API-Key` header in HTTP POST request headers.
3. **NVS Local Ring Buffer**:
   * Allocate SPIFFS/NVS storage partition for up to 500 JSON telemetry structs.
   * If `http.POST()` returns failure or Wi-Fi is disconnected, write record to NVS queue.
4. **Retry & Backlog Flush**:
   * Timer checks Wi-Fi / API availability every 30 seconds.
   * On reconnection, flush NVS backlog records sequentially with `"delayed_sync": true`.

---

## 7. Frontend Changes

1. **BP Source Indicator**: Render distinct UI tags on the vital signs panel (`[Manual]`, `[BLE Cuff]`, `[UART Device]`, or `[No BP Recorded]`).
2. **Offline Sync Badge**: Display a subtle "Historical Sync" icon next to vitals loaded with `delayed_sync: true`.
3. **Direct Telemetry Stream Status**: Update RealTime WebSocket subscriber component to listen for `telemetry.ingested` topics broadcast by FastAPI.

---

## 8. Documentation Changes

1. Update `docs/diagrams/healsense_architecture.puml` to delete Pi 5 and show direct ESP32 -> Cloud ingestion.
2. Update `docs/diagrams/deployment_workflow.puml` to purge Pi 5 setup commands.
3. Update project `README.md` to state project identity:  
   *"HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis."*

---

## 9. Migration Execution Order

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MIGRATION SEQUENCING                            │
├────────────────────────────────────────────────────────────────────────┤
│ Step 1: Database Migration (Alembic Script for bp_source & delayed_sync)│
│ Step 2: Schema & Pydantic Model Alignment                              │
│ Step 3: FastAPI Backend Endpoint (`POST /api/v1/telemetry`)            │
│ Step 4: Rule Engine Refactoring (Handle nullable BP gracefully)        │
│ Step 5: Documentation & Diagram Cleanup                                │
│ Step 6: ESP32 Firmware Specification Update                            │
│ Step 7: Frontend UI Indicator Integration                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Rollback Strategy

If any failure or breaking bug occurs during migration steps:

1. **Database Rollback**:
   * Execute Alembic downgrade command: `alembic downgrade -1`.
   * Restores `vital_signs` and `devices` tables to previous baseline schema.
2. **Backend Code Rollback**:
   * Git revert migration commits or restore target files from backup state (`git checkout main -- backend/`).
3. **API Compatibility Layer**:
   * Legacy endpoint `POST /api/v1/patients/{patient_id}/vitals` remains fully operational throughout migration to prevent breaking existing mobile/web client tests.

---

## Conclusion & Next Action

This document outlines every exact file change, database alteration, schema modification, and rollback step required. 

**Status**: Ready for manual review. No repository source code has been altered yet.
