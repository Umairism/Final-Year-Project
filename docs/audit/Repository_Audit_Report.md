# Phase 0: Repository Audit Report

**Project Title**: HealSense – Deep Learning-Based Smart Health Surveillance and Prediction Model Using IoT  
**Audit Purpose**: Complete repository analysis prior to Cloud-Native Architecture refactoring  
**Status**: AUDIT COMPLETE (NO CODE MODIFIED)  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. System Inventory Summary

```
┌────────────────────────────────────────────────────────────────────────┐
│                      HEALSENSE SYSTEM MAP                              │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Hardware & IoT Gateway                                        │
│   • Physical Sensors: MAX30100 (SpO2/HR), MLX90614 (Temp)              │
│   • Gateway: ESP32 (Direct Wi-Fi telemetry poster)                     │
│                                                                        │
│ Layer 2: Backend Framework & Ingestion                                 │
│   • Framework: FastAPI (Uvicorn ASGI runner)                           │
│   • Config: `backend/api/config.py`                                    │
│   • Ingestion Routes: `patients.py` (Vitals POST), `devices.py`        │
│                                                                        │
│ Layer 3: Validation & Canonical Schema                                 │
│   • Schemas: Pydantic v2 (`CanonicalClinicalFeatureSchema`)            │
│   • Nullable BP Handling: Currently imputed with default 120/80 mmHg   │
│                                                                        │
│ Layer 4: Hybrid Risk Evaluation Engine                                 │
│   • Deterministic Safety Rules: `fusion_engine.py` (WHO thresholds)    │
│   • Temporal LSTM Engine: `prediction_service.py` (TensorFlow 60-window│
│   • Decision Fusion: Hard Override on CRITICAL; 0.6/0.4 Weighting      │
│   • LLM Explanation Layer: Gemini API (`gemini-2.5-flash` HTTP client) │
│                                                                        │
│ Layer 5: Data Persistence & Client Services                            │
│   • Database: PostgreSQL (SQLAlchemy ORM + Alembic Migrations)         │
│   • WebSocket: Realtime Manager (`api/services/realtime.py`)          │
│   • Web Frontend: Next.js / React application (`frontend/`)            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure & Asset Inventory

* `backend/`: Primary API service built with FastAPI.
  * `api/app.py`: FastAPI app instance, CORS middleware, lifespan manager, and route registrations.
  * `api/config.py`: Environment setting management via `pydantic-settings`.
  * `api/models/schemas.py`: Request/response schemas and `CanonicalClinicalFeatureSchema`.
  * `api/models/database/`: SQLAlchemy ORM models (`models.py`) and DB connection session (`database.py`).
  * `api/routes/`: Route modules (`patients.py`, `devices.py`, `alerts.py`, `ai.py`, `realtime.py`).
  * `api/services/`: Hybrid core services (`fusion_engine.py`, `prediction_service.py`, `realtime.py`).
  * `alembic/`: Database migration environment and version scripts.
* `frontend/`: Web Dashboard application (Next.js/React).
* `data/`: Local CSV datasets and ML artifact models (`lstm_model.h5`, scalers).
* `docs/`: LaTeX defense presentations (`defence.tex`), architectural report drafts (`Actual_Report.md`), and PlantUML diagrams (`docs/diagrams/`).
* `scripts/`: Development utility scripts and simulation runners.

---

## 3. Findings & Architectural Deviations

1. **Raspberry Pi 5 Status**: Zero backend code requires or imports Raspberry Pi drivers. However, PlantUML diagrams in `docs/diagrams/` still portray the Pi 5 as a mandatory proxy node.
2. **Telemetry Ingestion Route**: Device vitals are currently posted through patient management URLs (`/api/v1/patients/{id}/vitals`) rather than a direct IoT telemetry ingestion endpoint (`/api/v1/telemetry`).
3. **Database Schema Limitations**: `vital_signs` table lacks `bp_source` and `delayed_sync` fields.
4. **Security Gaps**: Ingestion routes currently run without API key or JWT header verification.
5. **Data Imputation**: Missing Blood Pressure inputs are forcibly assigned default values (`120/80 mmHg`) rather than maintaining explicit missingness markers.

---

## 4. Phase 0 Verification Checklist

- [x] Entire workspace indexed and inspected.
- [x] Dependency map and component responsibilities verified.
- [x] Database entities and relations audited.
- [x] API endpoint inventory completed.
- [x] Zero codebase refactoring performed during Phase 0.

**Conclusion**: Phase 0 Complete. Ready for Phase 1 (Database Alignment) review.
