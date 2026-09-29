# PUBLICATION_READINESS.md — HealSense Full Repository Audit

> **Audited by:** Senior Software Architect / ML Engineer / Clinical-AI Reviewer / FYP Defense Evaluator  
> **Audit Date:** 2026-09-29  
> **Repository:** `/home/umairism/Desktop/Github/Final-Year-Project`  
> **Methodology:** Every finding is derived directly from repository evidence. No assumption is made about code that was not inspected.

---

## 1. Executive Verdict

| Dimension | Score |
|---|---|
| Backend Architecture | 7 / 10 |
| ML Pipeline | 3 / 10 |
| Clinical Safety | 7 / 10 |
| Frontend | 5 / 10 |
| Firmware | 3 / 10 |
| Testing | 5 / 10 |
| Deployment / DevOps | 1 / 10 |
| Documentation vs Reality Gap | 4 / 10 |
| **Overall Readiness** | **~42 %** |

### Biggest Strengths

1. **Fusion engine architecture is sound** — deterministic rules genuinely override ML (`fusion_engine.py:100-107`). The critical safety invariant holds in code.
2. **Telemetry pipeline is real** — device authentication, schema validation, persistence, LSTM prediction, fusion, and WebSocket broadcast all chain correctly in `telemetry_service.py`.
3. **Integration test suite exists and is meaningful** — `tests/test_phase2_telemetry.py` and `test_phase5_ml_scenarios.py` cover auth, persistence, and clinical-override scenarios using a real in-memory DB, not mocks.
4. **Pydantic schema contracts are tight** — `schemas.py` validates physiological ranges and enumerates every BP source and device type.
5. **LLM is correctly constrained** — the system prompt in `fusion_engine.py:148-163` explicitly prevents Gemini from modifying the risk decision; it is explanatory-only.

### Biggest Weaknesses

1. **🔴 FABRICATED ML EVALUATION METRICS** — `backend/ml/evaluate_model.py` generates `y_true` from `np.random` and then adds noise. The reported metrics (Accuracy 87%, F1 87.7%) are completely synthetic. No real model has been trained or evaluated.
2. **🔴 NO TRAINED MODEL EXISTS** — `data/models/checkpoints/` and `data/models/tflite/` contain only `.gitkeep` files. The backend silently degrades to deterministic-only mode.
3. **🔴 NO DOCKER / DEPLOYMENT CONFIGURATION** — zero `Dockerfile` or `docker-compose.yml` exists anywhere in the repository.
4. **🔴 FRONTEND AUTHENTICATION IS PURE MOCK** — `AuthContext.tsx` stores users in `localStorage` with plaintext passwords. There is no backend `/auth` route. The route is commented out in `app.py:148`.
5. **🔴 NO `.env` FILE OR TEMPLATE** — `config.py` has a hardcoded `SECRET_KEY` and default `DATABASE_URL`. There is no `.env.example`.
6. **HIGH** — Firmware is skeleton code. `telemetry_client.cpp:50` has `bool success = true; // Simulated HTTP POST result` — it never performs an actual HTTP request.
7. **HIGH** — Dashboard's `RiskGauge` and `GeminiExplanationCard` are hardcoded (`Dashboard.tsx:190-196`): `mlProbability={0.15}` and a static explanation string, not fetched from the backend.

### Is it Defensible?

**Conditionally yes** — if demonstrated in mock-data mode (`VITE_USE_MOCK_DATA=true`) and the examiner is not shown the ML evaluation script. The backend pipeline is architecturally solid and the safety rule chain can be demonstrated via the test suite.

**Will fail scrutiny on:** ML metrics, model existence, authentication, firmware, and production deployment.

### Is it Publication-Ready?

**No.** The reported ML evaluation is scientifically invalid. A real trained model on a real dataset with a correct train/val/test split is required before any claim of an ML-augmented system can appear in a paper.

---

## 2. Current Architecture (Reconstructed from Code)

```
┌─────────────────────────────────────────────────────────────────┐
│  Data Sources (Heterogeneous)                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ESP32 + MAX  │  │ Flutter App  │  │  Manual Web Entry    │  │
│  │ 30102/MLX    │  │ (Samsung/    │  │  (Profile page)      │  │
│  │ 90614 [MOCK] │  │  HealthKit)  │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │ HTTP POST        │ HTTP POST             │             │
│         │ X-Device-API-Key │ /vitals/phone         │             │
└─────────┼──────────────────┼───────────────────────┼────────────┘
          ▼                  ▼                       ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (api/app.py)  — port 5000                     │
│                                                                │
│  POST /api/v1/telemetry ──► TelemetryIngestionService          │
│    1. Device Auth (SHA-256 key hash)                           │
│    2. Patient Link Verify                                      │
│    3. Persist VitalSigns to PostgreSQL                         │
│    4. LSTM PredictionService.predict_risk()  [NO MODEL FILE]   │
│    5. FusionEngine.fuse_risk()                                 │
│       ├─ Layer 2: Deterministic Rules (WHO thresholds)         │
│       │  SpO2<92 → CRITICAL (override, absolute)              │
│       │  HR>150/HR<40 → CRITICAL                              │
│       │  BP≥180/120 → CRITICAL                                │
│       └─ Layer 4: Weighted Fusion (det×0.6 + ml×0.4)          │
│    6. FusionEngine.generate_explanation() → Gemini API         │
│    7. WebSocket broadcast via RealtimeManager                  │
│                                                                │
│  GET  /api/v1/patients/{id}/fusion_risk → Full pipeline        │
│  WS   /ws/patients/{id}                 → Live event stream    │
│                                                                │
│  SQLAlchemy ORM → PostgreSQL                                   │
│  Alembic migrations (2 existing, no initial schema migration)  │
└────────────────────────┬───────────────────────────────────────┘
                         │ WebSocket / REST
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  React/TypeScript Frontend (Vite + TailwindCSS)                │
│                                                                │
│  AuthContext  ──► localStorage mock (NO backend auth)          │
│  useVitals    ──► Mock stream OR WebSocket + polling fallback  │
│  Dashboard    ──► Hardcoded risk gauge + explanation           │
│  useMockData  ──► Defaults to TRUE (real API disabled)         │
└────────────────────────────────────────────────────────────────┘

ML Pipeline (OFFLINE / NOT INTEGRATED AT RUNTIME):
  scripts/train_model.py    ──► requires data/raw/bidmc_vitals.csv [MISSING]
  scripts/preprocess_bidmc.py ──► downloads BIDMC from PhysioNet
  data/models/v1.0.2/lstm_best.h5 ──► DOES NOT EXIST
  backend/ml/evaluate_model.py ──► GENERATES FAKE METRICS FROM np.random

Firmware (SKELETON):
  firmware/telemetry_client.cpp ──► HTTP POST is simulated (line 50)
  firmware/storage_manager.cpp  ──► NVS write is never performed
  No main.cpp / sensor read loop / Arduino sketch present
```

---

## 3. Implementation Audit

| Component | Status | Evidence | Problem | Required Action |
|---|---|---|---|---|
| FastAPI Backend Structure | IMPLEMENTED | `api/app.py`, all route files | Startup TODOs for Redis, MQTT left as comments | No critical action |
| Pydantic Schema Validation | IMPLEMENTED | `schemas.py` with ranges and enums | — | None |
| PostgreSQL ORM Models | IMPLEMENTED | `models.py` (5 tables) | No initial migration; 2 add-column migrations presuppose existing schema | Add baseline migration |
| Alembic Migrations | PARTIAL | 2 migration files (`b52623274ba1`, `c8f92a104b91`) | Missing initial schema migration; base tables created via `init_db.py`, bypassing Alembic version tracking | Create initial migration |
| Device Authentication | IMPLEMENTED | `telemetry_service.py:36-79` | SHA-256 key hash, `connected` flag check | None |
| Telemetry Ingestion Pipeline | IMPLEMENTED | `telemetry_service.py:81-206` | Solid end-to-end pipeline | None |
| Deterministic Rules Engine | IMPLEMENTED | `fusion_engine.py:47-94` | Thresholds correctly match system spec (SpO2<92, HR>150/<40, BP≥180/120) | None |
| ML + Rule Fusion Engine | IMPLEMENTED | `fusion_engine.py:96-141` | Deterministic override is correct and cannot be bypassed by ML | None |
| LSTM PredictionService | PARTIAL | `prediction_service.py:38-63` | Load path references non-existent model files; graceful degradation is implemented | Train and commit model artifacts |
| Gemini LLM Explanation | IMPLEMENTED | `fusion_engine.py:143-208` | Explanation-only; cannot modify decision | Requires `GEMINI_API_KEY` env var |
| WebSocket RealtimeManager | IMPLEMENTED | `services/realtime.py` | Per-patient and per-device rooms, async lock | None |
| Patient CRUD API | IMPLEMENTED | `routes/patients.py` | Patient ID is sequential count-based — race condition possible | Use UUID for patient ID |
| Device Management | IMPLEMENTED | `routes/devices.py` | Phone registration, connect/disconnect | None |
| Frontend Web App | PARTIAL | `frontend/web-app/src/` | Mock data ON by default (`config.ts:6`); hardcoded risk values in Dashboard | Connect to real API |
| Frontend Authentication | MOCKED | `AuthContext.tsx:34-53` | Pure localStorage mock with hardcoded user; no backend auth endpoint | Implement JWT auth |
| Flutter Mobile App | PARTIAL | `frontend/mobile-app/lib/` | API service and models exist; `sensor_service.dart` uses MethodChannel skeleton with no native Android implementation | MethodChannel not implemented |
| ESP32 Firmware | MOCKED | `telemetry_client.cpp:50` | HTTP POST is a comment (`bool success = true`); NVS storage is a counter only | Real Arduino/PlatformIO sketch needed |
| ML Training Script | PARTIAL | `scripts/train_model.py` | Patient-level split, class weights, correct scaler/encoder workflow — but requires `bidmc_vitals.csv` which is not in repo | Download data + run training |
| ML Evaluation Script | **FABRICATED** | `backend/ml/evaluate_model.py:10-21` | `y_true = np.random.choice(...)` — random labels, not real model output | Replace with real evaluation |
| Dataset | MISSING | `data/` dir has only `.gitignore` | No raw or processed data committed | Run preprocessing pipeline |
| Trained Model Artifacts | MISSING | `data/models/checkpoints/.gitkeep` | No `.h5`, `.pkl`, or `.tflite` files | Train model |
| Docker / Deployment | MISSING | `find` returned empty | Zero Dockerfile or docker-compose | Create `docker-compose.yml` |
| `.env` / Config Template | MISSING | `ls -la` shows no `.env` file | `config.py:35` hardcodes `SECRET_KEY`; `config.py:41` has default DB credentials | Add `.env.example` |
| Backend Tests | PARTIAL | `tests/` with 4 test files | Good integration tests; no unit tests for isolated logic; no `pytest.ini` | Add `pytest.ini` + unit tests |
| Authentication / JWT | MISSING | `app.py:148` commented out | No `/api/v1/auth` route; no JWT middleware | Implement |
| Rate Limiting | MISSING | `app.py:75` TODO comment | No rate limiting middleware | Add before production |
| CORS Configuration | PARTIAL | `app.py:67-73` | `ALLOWED_ORIGINS: str = "*"` in config default | Restrict in `.env` |
| Logging | IMPLEMENTED | `utils/logger.py`; `logging.getLogger` throughout | No structured/JSON logging | Low priority |
| Raspberry Pi Integration | MISSING | No Raspberry Pi code anywhere | Documentation mentions RPi; no code exists | Clarify scope in defence |
| pgvector Integration | MISSING | No pgvector imports or usage | Mentioned in project context; not implemented | Not required for FYP |

---

## 4. Critical Problems

### 🔴 CRITICAL

**C1 — Fabricated ML Metrics**
- File: `backend/ml/evaluate_model.py:14-32`
- `y_true = np.random.choice([0,1,2], size=300, p=[0.7,0.2,0.1])` — randomly generated
- `y_pred = y_true.copy()` then noise added — no model involved
- The committed file `backend/ml/results/metrics_report.json` reports `"accuracy": 0.87` computed from random numbers
- **Consequence:** Any claim of "87% accuracy LSTM" is scientifically fraudulent. This alone can fail a defense or retract a paper.

**C2 — No Trained Model Exists**
- `data/models/checkpoints/.gitkeep` — directory is empty
- `data/models/tflite/.gitkeep` — empty
- `config.py:74` references `data/models/v1.0.1/lstm_best.h5`; `train_model.py:34` targets `v1.0.2` — version mismatch even if model existed
- **Consequence:** System silently runs deterministic-only; every "ML + rule hybrid" demo claim is hollow

**C3 — No Dataset in Repository**
- `data/` directory contains only `.gitignore`
- `train_model.py:32` reads `../data/raw/bidmc_vitals.csv` — does not exist
- `evaluate_system.py:16` requires `../data/processed/test_patients.csv` — does not exist
- **Consequence:** Training and evaluation pipelines cannot be run without preparation

**C4 — Frontend Authentication is Fake**
- `AuthContext.tsx:35`: `const MOCK_USERS_KEY = 'healsense_mock_users'`
- Passwords stored in plaintext in localStorage
- No backend `/auth` route; commented out in `app.py:148`
- **Consequence:** No real access control; immediate failure on browser DevTools inspection

**C5 — Hardcoded Secret Key in Source Code**
- `config.py:35`: `SECRET_KEY: str = "b104b3038eb465..."` (64 hex chars hardcoded)
- No `.env.example` or secret management
- **Consequence:** Security vulnerability; credibility problem for publication

---

### 🟠 HIGH

**H1 — Firmware HTTP POST is Simulated**
- `telemetry_client.cpp:50`: `bool success = true; // Simulated HTTP POST result`
- `sendTelemetry()` never performs a network call
- `storage_manager.cpp:20-23`: `enqueueRecord()` increments a counter but never writes to NVS

**H2 — Dashboard Risk Values are Hardcoded**
- `Dashboard.tsx:190-192`: `mlProbability={0.15}` hardcoded
- `Dashboard.tsx:195-196`: Static Gemini explanation string, not fetched from `/fusion_risk`
- Real fusion engine results are never displayed in the UI

**H3 — No Initial Alembic Migration**
- The two existing migrations add columns to tables that must be created first
- `init_db.py` calls `Base.metadata.create_all()` bypassing Alembic version tracking
- Fresh deployment with `alembic upgrade head` will fail

**H4 — Model Version Mismatch**
- `config.py:73-74`: specifies `MODEL_VERSION = "v1.0.1"`
- `scripts/train_model.py:33`: targets `MODEL_VERSION = "v1.0.2"`
- Backend would load from wrong path even if training was run

**H5 — Patient ID Race Condition**
- `routes/patients.py:493-494`: `count = db.query(Patient).count()` then `patient_id = f"P{str(count + 1).zfill(3)}"`
- Concurrent creates produce the same ID

---

### 🟡 MEDIUM

**M1 — Flutter MethodChannel Has No Native Android Implementation**
- `sensor_service.dart:4`: `MethodChannel('com.healsense/sensors')` declared
- No corresponding `MainActivity.kt` or plugin registration exists in `frontend/mobile-app/app/`

**M2 — CORS Wildcard in Production Default**
- `config.py:38`: `ALLOWED_ORIGINS: str = "*"` — must be restricted before any deployment

**M3 — Labels are Circular (Critical for Publication)**
- `preprocess_bidmc.py:38-44`: Labels derived by applying the same WHO thresholds to HR/SpO2 that are used in `fusion_engine.py:54-73`
- The ML model is trained to predict the deterministic rules, not external clinical outcomes
- Both `evaluate_system.py:112` and `train_model.py:152` acknowledge: "NOTE: evaluated on internally derived proxy labels"
- This significantly limits the scientific claims that can be made

**M4 — BIDMC Dataset Lacks Temperature and Blood Pressure**
- `preprocess_bidmc.py:31-33`: `temperature = np.nan`, `systolic_bp = np.nan`, `diastolic_bp = np.nan`
- The LSTM uses 5 features; 3 are always NaN for the BIDMC dataset
- `train_model.py:98-99`: NaNs imputed with `-1.0` — a non-physiological value that skews the scaler

**M5 — Emergency Endpoint Has No Authentication**
- `routes/patients.py:447-485`: `trigger_emergency()` has no auth guard, only patient existence check
- Any unauthenticated caller knowing a patient ID can trigger an emergency

**M6 — Missing BP Defaults Silently to Normal**
- `fusion_engine.py:31-32`: Missing BP defaults to `120/80`
- A patient with real BP≥180/120 whose device cannot measure BP will never trigger the hypertensive crisis rule

---

### 🟢 LOW

**L1** — Middleware directory is empty (`backend/api/middleware/__init__.py`: 25 bytes)

**L2** — No `pytest.ini`, `conftest.py`, or `pyproject.toml`; SQLite test DB files left as artifacts

**L3 — Dashboard JSX Structural Bug**
- `Dashboard.tsx:247-265`: A second chart `<div>` block is placed outside the `dashboard` `<TabsContent>` but before its closing tag — it always renders regardless of active tab

**L4** — Raspberry Pi mentioned in docs but zero code exists anywhere in repository

---

## 5. Required Implementation Before Defense

> Priority order. Each item must be completed before the next matters.

**[1] P0 · CRITICAL — Fix or Remove the Fabricated ML Evaluation**
- Task: Either train a real model and produce real metrics, OR clearly label the system as "deterministic-only prototype" and remove the fake metrics file
- Why: Presenting `metrics_report.json` to judges is academic misconduct if not from a real model
- Files: `backend/ml/evaluate_model.py`, `backend/ml/results/metrics_report.json`
- Acceptance: Metrics reproducibly generated from a real trained model OR all claims removed

**[2] P0 · CRITICAL — Train the LSTM Model (or Commit a Trained Artifact)**
- Task: `scripts/preprocess_bidmc.py` → `scripts/train_model.py` → commit `data/models/v1.0.2/lstm_best.h5`, `scaler.pkl`, `label_encoder.pkl`
- Files: `scripts/preprocess_bidmc.py`, `scripts/train_model.py`, `data/models/v1.0.2/`
- Acceptance: `prediction_service.load_artifacts()` returns `True` on startup; startup log shows `✅ ML prediction service initialized`

**[3] P0 · HIGH — Align Model Version in `config.py`**
- Task: Change `config.py:73` `MODEL_VERSION = "v1.0.1"` to `"v1.0.2"`
- Files: `backend/api/config.py:73-76`
- Acceptance: Model loads from correct path

**[4] P0 · HIGH — Create Initial Alembic Migration**
- Task: `alembic revision --autogenerate -m "initial_schema"` after schema is stable; set as base
- Files: `backend/alembic/versions/`
- Acceptance: `alembic upgrade head` on a fresh DB creates all tables

**[5] P0 · HIGH — Add `.env.example` and Remove Hardcoded Secret**
- Task: Create `.env.example` with all keys (no values); move `SECRET_KEY` to env
- Files: `backend/api/config.py:35`, new `backend/.env.example`
- Acceptance: App starts with keys from `.env`; no secret in any committed file

**[6] P1 · HIGH — Connect Dashboard to Real Fusion Risk API**
- Task: In `Dashboard.tsx:188-197`, replace hardcoded `mlProbability={0.15}` and static explanation with real data from `/api/v1/patients/{id}/fusion_risk`
- Files: `frontend/web-app/src/pages/Dashboard.tsx:188-197`
- Acceptance: Risk gauge and explanation update from backend on page load/refresh

**[7] P1 · HIGH — Set `useMockData` Default to `false` for Demo**
- Task: Ensure demo env sets `VITE_USE_MOCK_DATA=false`; verify WebSocket works end-to-end
- Files: `frontend/web-app/src/lib/config.ts:6`
- Acceptance: Dashboard shows live data from backend with WebSocket

**[8] P1 · MEDIUM — Implement Minimal JWT Authentication**
- Task: Create `routes/auth.py` with `/auth/login`; issue JWT tokens; add `Depends(get_current_user)` to critical endpoints; update `AuthContext.tsx`
- Files: `backend/api/app.py:148`, new `backend/api/routes/auth.py`, `frontend/web-app/src/contexts/AuthContext.tsx`
- Acceptance: Login page calls backend; invalid token returns 401

**[9] P1 · MEDIUM — Create Docker Compose for Demo**
- Task: `docker-compose.yml` with `db` (postgres:15) + `api` (backend) services
- Files: New `docker-compose.yml`, new `backend/Dockerfile`
- Acceptance: `docker compose up` brings up the full stack with one command

**[10] P1 · LOW — Add `pytest.ini` and Ensure All Tests Pass**
- Files: New `backend/pytest.ini`
- Acceptance: `python -m pytest backend/tests/ -v` passes; no orphan DB files

---

## 6. Required Implementation Before Publication

> In addition to all defense requirements being met.

1. **Real dataset with features matching the feature vector** — BIDMC has only HR and SpO2 without temperature/BP; consider MIMIC-IV or PhysioNet Challenge datasets that include all 5 features and real clinical outcomes.

2. **Labels must not be circular** — the current system trains an LSTM to predict the output of the same rule engine used in the fusion layer. A paper cannot claim clinical validity from this without explicit disclosure and justification.

3. **Ablation study with real numbers** — `scripts/evaluate_system.py` has the correct structure (deterministic-only vs ML-only vs hybrid); run it with a real trained model and real data.

4. **Baseline comparison** — compare against at least one published approach (threshold-only, logistic regression, or a prior LSTM paper on the same dataset).

5. **Statistical significance** — report confidence intervals or bootstrap results for performance metrics.

6. **Reproducibility package** — `pip freeze > requirements-lock.txt`; seed all random operations; document exact dataset version, preprocessing steps, training command.

7. **Limitations section** — explicitly state: labels are proxy labels derived from WHO thresholds (not external clinical outcomes); BIDMC lacks temperature/BP (NaN-imputed with `-1.0`); system is decision-support, not a diagnostic device; no external clinical validation performed.

8. **IRB/ethics statement** — BIDMC is de-identified research data; state PhysioNet Credentialed Health Data License terms.

9. **Publication-quality architecture diagram** — 5-layer pipeline (canonical feature vector → deterministic engine → ML prediction → fusion → LLM explanation).

10. **Model card** — training data, features, sequence length, architecture, class distribution, performance per class, known failure modes.

---

## 7. ML / Data Audit

| Dimension | Status | Evidence | Issue |
|---|---|---|---|
| Dataset source | UNVERIFIED | `preprocess_bidmc.py` targets PhysioNet BIDMC; data not committed | Must download and verify |
| Dataset features | PARTIAL | Only HR and SpO2 from BIDMC; temperature/BP always NaN | 3 of 5 LSTM features are always `-1.0` after imputation |
| Label methodology | CIRCULAR | `preprocess_bidmc.py:38-44` labels using same thresholds as `fusion_engine.py:54-73` | ML learns to predict the rule engine, not clinical outcomes |
| Train/val/test split | IMPLEMENTED ✅ | `train_model.py:62-69` — patient-level 80/20 split then 80/20 of train; test patients saved | Correct: no patient-level leakage |
| Data leakage check | IMPLEMENTED ✅ | `scale_3d()` fits scaler only on train; val/test use `.transform()` | Correct |
| Class imbalance handling | IMPLEMENTED ✅ | `train_model.py:111-115` — `compute_class_weight('balanced')` | Correct |
| Reported metrics | **FABRICATED** 🔴 | `evaluate_model.py:14-21` — `np.random.choice()` | Critical scientific integrity issue |
| Trained model exists | MISSING 🔴 | `data/models/checkpoints/.gitkeep` | Cannot demonstrate ML at runtime |
| Model version consistency | BROKEN 🔴 | Config says `v1.0.1`; training targets `v1.0.2` | Will fail to load even if model existed |
| Sequence construction | IMPLEMENTED ✅ | `create_sequences_for_patients()` with 60-step sliding window | Correct |
| NaN handling | PARTIAL ⚠️ | NaNs imputed with `-1.0` | Non-physiological value; consider mean imputation per-feature |
| Reproducibility | PARTIAL | Seeds set; TF version not pinned; no lockfile | Need `requirements-lock.txt` |
| Baseline comparison | MISSING | No comparison model | Required for publication |
| External validation | MISSING | No held-out dataset from different source | Required for publication |

### Summary Statement

The ML pipeline has a **correctly designed training structure** (patient-level split, no leakage, class weighting, correct scaler fit). However: it **does not have a trained model**, **reports metrics generated from random numbers**, and **trains on circular proxy labels**. The scientific value of the ML component as currently evidenced is zero. This must be corrected before any ML performance claim can be made.

---

## 8. Clinical Safety Audit

### Full Pipeline Path Verification

| Step | Status | Evidence | Risk |
|---|---|---|---|
| **Input Validation** | ✅ IMPLEMENTED | `schemas.py:36-41` — Pydantic ranges (HR 0-300, SpO2 0-100, Temp 30-45) | Negative values blocked |
| **Deterministic Rules (Layer 2)** | ✅ IMPLEMENTED | `fusion_engine.py:54-73` — SpO2<92 → CRITICAL, HR>150/<40 → CRITICAL, BP≥180/120 → CRITICAL | Thresholds correct |
| **Critical Safety Override** | ✅ IMPLEMENTED | `fusion_engine.py:99-107` — CRITICAL deterministic → immediate return; ML score ignored | ML cannot override CRITICAL |
| **ML Cannot Escalate Beyond Fusion** | ✅ IMPLEMENTED | `fuse_risk()` only escalates to "critical" if weighted score ≥ 0.7; all real clinicals caught by deterministic | Safe |
| **LLM Cannot Modify Decision** | ✅ IMPLEMENTED | `fusion_engine.py:155-162` — System prompt states LLM does not decide risk; decision is "already determined" | Safe |
| **Missing BP Handling** | ⚠️ PARTIAL | `fusion_engine.py:31-32` — Missing BP silently defaults to 120/80; BP crisis rule never fires without measurement | A patient with real BP≥180/120 whose device cannot measure BP will never trigger hypertensive crisis |
| **UI Displays Correct Risk** | ❌ BROKEN | `Dashboard.tsx:189-196` — Risk gauge computed inline in JSX, not from `/fusion_risk`; hardcoded `mlProbability=0.15` | UI may show different risk than backend computed |

### Safety Verdict

✅ **The deterministic override cannot be bypassed by ML or LLM.** This is the most important safety property and it holds in code.

⚠️ **Gap 1:** Missing BP defaults to normal values. A patient with undetectable hypertensive crisis (no BP sensor) will never receive a BP-based alert. This must be documented as a system limitation.

⚠️ **Gap 2:** The web UI does not reflect backend fusion results. A patient could be `CRITICAL` in the backend while the frontend shows a different inline-computed value. This must be fixed before defense.

---

## 9. Testing Plan

### Already Implemented (Verify They Pass)

```bash
cd backend && python -m pytest tests/ -v
```

- `test_phase2_telemetry.py` — auth, payload validation, persistence, critical override (9 tests) ✅
- `test_phase5_ml_scenarios.py` — 4 clinical scenarios including SpO2 override ✅

### Required Before Defense (Missing Unit Tests)

| Test | File | What to Verify |
|---|---|---|
| `test_deterministic_rules_boundaries` | `tests/test_fusion_unit.py` | SpO2 at 91, 92, 93, 94, 95; HR at 39, 40, 50, 120, 150, 151; BP at 179/119, 180/120 |
| `test_fusion_critical_override` | `tests/test_fusion_unit.py` | CRITICAL deterministic → override regardless of ML score input |
| `test_fusion_weighted_calculation` | `tests/test_fusion_unit.py` | Warning det + ML critical → weighted score → correct label |
| `test_canonical_feature_missing_bp` | `tests/test_fusion_unit.py` | BP defaults to 120/80 when None |
| `test_prediction_service_degradation` | `tests/test_prediction_unit.py` | `predict_risk()` returns None when model not loaded (not an exception) |

### Required Safety Tests

| Test | Acceptance Criteria |
|---|---|
| SpO2 = 91 → always CRITICAL | Even if ML predicts "normal", `final_risk_level == "critical"` and `fusion_method == "deterministic_override"` |
| HR = 40 → always CRITICAL | As above |
| BP = 180/120 → always CRITICAL | As above |
| LLM timeout → risk unchanged | `explanation` fails gracefully; risk still returned in response |
| Model not loaded → deterministic-only | No 500 error; `ml_evaluation: null`; `fusion_method: "deterministic_only"` |

---

## 10. Publication Evidence Package

| Evidence | How to Produce | Where to Save |
|---|---|---|
| Trained model (`.h5` + `.pkl` × 2) | `scripts/train_model.py` | `data/models/v1.0.2/` |
| Training loss/accuracy curves | Add `matplotlib` callback to `train_model.py` | `backend/ml/results/training_curves.png` |
| Real confusion matrix | `scripts/evaluate_system.py` with real model | `backend/ml/results/confusion_matrix_real.png` |
| Full classification report | Output of `evaluate_system.py` | `backend/ml/results/classification_report.txt` |
| Ablation table (Det-only vs ML-only vs Hybrid) | `evaluate_system.py` already has this structure | `backend/ml/results/ablation_study.md` |
| Dataset statistics (class distribution, patient count) | Add to `preprocess_bidmc.py` output | `backend/ml/results/dataset_stats.md` |
| Architecture diagram | Draw 5-layer pipeline | `docs/architecture_diagram.png` |
| Model card | Training data, hyperparams, per-class performance | `docs/model_card.md` |
| Safety test results | `pytest --tb=short > safety_test_results.txt` | `backend/ml/results/safety_test_results.txt` |
| API demo screenshots | Backend running with real data + Swagger UI | `docs/screenshots/` |
| Limitations statement | Written in paper AND `README.md` | — |
| Reproducibility instructions | Step-by-step from clone to running system | `backend/README.md` |

---

## 11. Final Implementation Roadmap

### P0 — Must Fix (Defense Blockers)

| Task | Effort | Files |
|---|---|---|
| Replace fabricated metrics with real evaluation OR remove all ML claims | L | `evaluate_model.py`, `metrics_report.json`, `evaluation_summary.md` |
| Run preprocessing + training; commit model artifacts | L | `scripts/preprocess_bidmc.py`, `scripts/train_model.py`, `data/models/v1.0.2/` |
| Fix `config.py` model version (`v1.0.1` → `v1.0.2`) | S | `config.py:73` |
| Add `.env.example`; move `SECRET_KEY` to env | S | `config.py:35`, new `.env.example` |
| Create initial Alembic migration (base schema) | M | `alembic/versions/` |

### P1 — Must Implement (Defense Quality)

| Task | Effort | Files |
|---|---|---|
| Connect Dashboard RiskGauge to `/fusion_risk` API | M | `Dashboard.tsx:188-197` |
| Set `VITE_USE_MOCK_DATA=false` for demo; verify WS end-to-end | S | `config.ts:6`, frontend `.env` |
| Implement basic JWT auth (`/auth/login`, `/auth/register`) | L | New `routes/auth.py`, `AuthContext.tsx` |
| Create `docker-compose.yml` (postgres + backend) | M | New `docker-compose.yml`, `backend/Dockerfile` |
| Add `pytest.ini`; ensure all tests pass | S | New `pytest.ini` |

### P2 — Strongly Recommended (Publication / Demo Polish)

| Task | Effort | Files |
|---|---|---|
| Add auth guard to patient and telemetry endpoints | M | `routes/patients.py`, `routes/telemetry.py` |
| Fix patient ID to use UUID | S | `routes/patients.py:493-494` |
| Document missing-BP limitation in UI and README | S | `README.md`, Dashboard tooltip |
| Run ablation study with real model; commit results | M | `scripts/evaluate_system.py` |
| Add `requirements-lock.txt` (`pip freeze`) | S | root |
| Fix Dashboard JSX structural bug (orphaned chart div) | S | `Dashboard.tsx:247-265` |
| Restrict CORS to specific origins | S | `config.py:38`, `.env` |

### P3 — Optional (Production Quality)

| Task | Effort | Files |
|---|---|---|
| Implement Flutter MethodChannel native Android integration | XL | `frontend/mobile-app/app/src/main/` |
| Replace ESP32 firmware stub with real PlatformIO sketch + sensor drivers | XL | `firmware/` |
| Add rate limiting middleware (slowapi) | M | `api/app.py` |
| Add pgvector support for patient similarity | XL | New dependency + migration |
| Structured JSON logging | S | `utils/logger.py` |
| Redis-based session management | L | `api/app.py:47` |

> **Effort Key:** `S = <2 hrs` · `M = 2–6 hrs` · `L = 6–15 hrs` · `XL = >15 hrs`

---

## 12. Final Defense Checklist

- [ ] Backend starts without errors (`python run.py`)
- [ ] PostgreSQL running; `init_db.py` executed; tables present
- [ ] ML model loads at startup (log: `✅ ML prediction service initialized`)
- [ ] `GET /health` returns `{"status": "healthy"}`
- [ ] Swagger UI at `http://localhost:5000/api/docs` accessible
- [ ] Create patient via `POST /api/v1/patients/`
- [ ] Register device and submit telemetry via `POST /api/v1/telemetry` with `X-Device-API-Key`
- [ ] Submit telemetry with `spo2: 88` → response `status == "critical"` and `fusion_method == "deterministic_override"`
- [ ] `GET /api/v1/patients/{id}/fusion_risk` returns full fusion decision with clinical reasoning
- [ ] WebSocket connects on `ws://localhost:5000/ws/patients/{id}` and receives `telemetry.ingested` event
- [ ] Frontend dashboard loads and shows vitals (real backend, not mock)
- [ ] Alert banner appears for warning/critical vitals
- [ ] Emergency button triggers `POST /api/v1/patients/{id}/emergency`
- [ ] Integration tests pass: `python -m pytest backend/tests/ -v`
- [ ] Safety invariant demonstrated live: critical deterministic rule cannot be overridden by ML

---

## 13. Final Publication Checklist

- [ ] Real trained LSTM model committed (or hosted with reproducible training script)
- [ ] All evaluation metrics derived from real model predictions on held-out test set
- [ ] Labels not circular OR circular-label limitation explicitly stated and justified
- [ ] Patient-level train/val/test split documented and reproducible
- [ ] Ablation study completed: Deterministic-only vs ML-only vs Hybrid, with real numbers
- [ ] At least one baseline comparison included
- [ ] All 5 LSTM input features documented; NaN handling for missing features explained
- [ ] Model card completed
- [ ] Architecture diagram (publication-quality figure)
- [ ] No secrets in committed code; `.env.example` present
- [ ] System described as "decision-support / risk classification," never as "diagnostic"
- [ ] Limitations section: proxy labels, missing-BP fallback, no external clinical validation, single-centre dataset
- [ ] Dataset licensing and ethics statement (PhysioNet credentialed access, BIDMC de-identification)
- [ ] Reproducibility: `requirements-lock.txt`, exact dataset version, seed values, training command documented
- [ ] All pytest tests pass (unit + integration + safety)
- [ ] API documented (Swagger / OpenAPI spec exported or linked)

---

*End of Audit — HealSense FYP Repository*  
*Generated: 2026-09-29 | All findings evidence-based and file-cited*
