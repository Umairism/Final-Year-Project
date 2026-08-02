# Phase 1: Pre-Implementation Analysis Report

**Project Title**: HealSense Cloud-Native Migration  
**Subsystem**: Database Models, Pydantic Schemas, and Migrations  
**Phase**: Step 1 - Repository Analysis  
**Status**: ANALYSIS COMPLETE (NO CODE MODIFIED YET)  
**Date**: August 2, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. Existing Database & Schema Snapshot

### A. Current SQLAlchemy Models (`backend/api/models/database/models.py`)
* **`Patient`**: Primary patient demographic and medical history entity (`diabetes`, `smoking_status`, `medications`, `past_conditions`).
* **`VitalSigns`**: Time-series health telemetry measurements. Current columns: `id`, `patient_id`, `device_id`, `heart_rate`, `spo2`, `temperature`, `systolic_bp`, `diastolic_bp`, `respiratory_rate`, `data_source`, `sensor_accuracy`, `activity_context`, `location_lat`, `location_lng`, `timestamp`, `status`, `risk_score`, `prediction_confidence`, `full_probability_distribution`, `model_version`.
* **`Device`**: IoT node & mobile phone sensor entity. Columns: `device_id`, `patient_id`, `device_type`, `phone_model`, `phone_os`, `sensor_capabilities`, `connected`, `battery_level`, `signal_strength`, `last_heartbeat`, `created_at`, `updated_at`.
* **`Alert`** & **`Emergency`**: Event tracking tables.

### B. Current Pydantic Schemas (`backend/api/models/schemas.py`)
* **`VitalSignsBase`**: Base telemetry request model. `heart_rate`, `spo2`, `temperature` are required. `systolic_bp` and `diastolic_bp` are currently optional floats.
* **`CanonicalClinicalFeatureSchema`**: Model contract for Rules & ML processing engines.

### C. Current Alembic Migration Head (`backend/alembic/versions/`)
* **Current Head**: `b52623274ba1_add_phone_sensor_support_devicetype_.py`.

---

## 2. Planned Changes for Phase 1

### A. `VitalSigns` Table Additions
1. **`bp_source`**: Enum column tracking BP measurement origin:
   - `manual_entry`: User/clinician input.
   - `ble_cuff`: External Bluetooth cuff GATT profile.
   - `hardware_uart`: OEM NIBP module on ESP32 serial.
   - `none`: No Blood Pressure data recorded.
2. **`delayed_sync`**: Boolean column (`DEFAULT FALSE`) indicating whether telemetry was ingested in real-time or synced from ESP32 local NVS memory after a Wi-Fi outage.

### B. `Device` Table Additions
1. **`api_key_hash`**: String column (`VARCHAR(128)`, nullable) to store hashed API key credentials for direct hardware HTTP ingestion authentication.

### C. Pydantic Schema Enhancements
1. Add `BpSource` enum and `bp_source` / `delayed_sync` fields to `VitalSignsBase`, `VitalSignsCreate`, `VitalSigns`, and `CanonicalClinicalFeatureSchema`.
2. Explicitly ensure `systolic_bp` and `diastolic_bp` allow `None` without requiring fake default value imputations.

---

## 3. Migration Risk Assessment

* **Risk 1: Enum Creation on PostgreSQL Engine**
  * *Mitigation*: Define `BpSource` explicitly as an Enum type with default value `'none'`. Use `checkfirst=True` in Alembic migration scripts.
* **Risk 2: Backwards Compatibility with Existing Test Fixtures**
  * *Mitigation*: Set `bp_source` default to `'none'` and `delayed_sync` default to `False` in Pydantic models so existing tests passing telemetry payloads without these metadata fields continue to succeed.

---

## 4. Phase 1 Execution Roadmap

1. **Step 2**: Update `backend/api/models/database/models.py`.
2. **Step 3**: Update `backend/api/models/schemas.py`.
3. **Step 4**: Generate Alembic revision `add_telemetry_metadata_fields`.
4. **Step 5**: Run Alembic migration validation (`alembic upgrade head`).
5. **Step 6**: Add pytest test suite `backend/tests/test_database_phase1.py` covering:
   - Telemetry ingestion without BP (`systolic_bp: null`).
   - Telemetry with `delayed_sync: true`.
   - Valid vs. invalid `bp_source` Enum validation.
6. **Step 7**: Generate release notes `docs/releases/v1.1.0-database-alignment.md`.
7. **Step 8**: Commit and push release tag `v1.1.0-database-alignment`.

---

**Status**: Step 1 Complete. Ready for Step 2 Implementation.
